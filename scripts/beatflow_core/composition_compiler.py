# SPDX-License-Identifier: GPL-3.0-only
"""Compile Composition 1.1 functional events into deterministic MIDI notes."""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations, product

from .composition_models import (
    ChordEvent,
    Composition,
    DrumEvent,
    PitchedEvent,
    SectionPlan,
    SegmentPlan,
    SegmentTreatment,
    TrackPlan,
)
from .composition_validation import validate_composition
from .harmony_utils import parse_chord_symbol
from .models import (
    Clip,
    ClipKind,
    CompositionLink,
    Note,
    Project,
    Section,
    SectionOccurrence,
    Track,
    TrackRole,
)
from .validation import ValidationReport

MODE_INTERVALS = {
    "major": [0, 2, 4, 5, 7, 9, 11],
    "minor": [0, 2, 3, 5, 7, 8, 10],
    "dorian": [0, 2, 3, 5, 7, 9, 10],
    "phrygian": [0, 1, 3, 5, 7, 8, 10],
    "lydian": [0, 2, 4, 6, 7, 9, 11],
    "mixolydian": [0, 2, 4, 5, 7, 9, 10],
    "locrian": [0, 1, 3, 5, 6, 8, 10],
}
TONIC_TO_PC = {
    "C": 0,
    "C#": 1,
    "Db": 1,
    "D": 2,
    "D#": 3,
    "Eb": 3,
    "E": 4,
    "F": 5,
    "F#": 6,
    "Gb": 6,
    "G": 7,
    "G#": 8,
    "Ab": 8,
    "A": 9,
    "A#": 10,
    "Bb": 10,
    "B": 11,
}
STEP_INDEX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


class CompositionCompileError(ValueError):
    def __init__(self, message: str, report: ValidationReport | None = None):
        super().__init__(message)
        self.report = report


def beat_value(value) -> Fraction:
    return value.fraction


def _active_harmony(section: SectionPlan, onset: Fraction):
    for event in section.harmony:
        start = event.onset.fraction
        if start <= onset < start + event.duration.fraction:
            return event
    raise CompositionCompileError(
        f"No harmony covers section '{section.id}' at beat {onset}."
    )


def _next_harmony(section: SectionPlan, onset: Fraction):
    for event in section.harmony:
        if event.onset.fraction > onset:
            return event
    if section.harmony:
        return section.harmony[-1]
    raise CompositionCompileError(f"Section '{section.id}' has no harmony.")


def _root_and_intervals(symbol: str) -> tuple[int, list[int], dict[int, int]]:
    chord = parse_chord_symbol(symbol)
    root = chord.root()
    if root is None:
        raise CompositionCompileError(f"Chord '{symbol}' has no root.")
    root_pc = root.pitchClass
    root_step = STEP_INDEX[root.step]
    intervals = sorted({(pitch.pitchClass - root_pc) % 12 for pitch in chord.pitches})
    degrees: dict[int, int] = {}
    for pitch in chord.pitches:
        degree = ((STEP_INDEX[pitch.step] - root_step) % 7) + 1
        degrees[degree] = (pitch.pitchClass - root_pc) % 12
    return root_pc, intervals, degrees


def _target_pitch_class(
    composition: Composition,
    section: SectionPlan,
    onset: Fraction,
    target,
) -> int:
    if target.basis == "absolute":
        return int(target.midi) % 12
    if target.basis == "scale":
        intervals = MODE_INTERVALS[composition.key.mode.value]
        return (
            TONIC_TO_PC[composition.key.tonic]
            + intervals[(int(target.degree) - 1) % 7]
            + target.alter
        ) % 12

    harmony = (
        _next_harmony(section, onset)
        if target.basis == "next_chord"
        else _active_harmony(section, onset)
    )
    root_pc, intervals, degrees = _root_and_intervals(harmony.symbol)
    if target.basis in {"chord", "next_chord"}:
        degree = ((int(target.degree) - 1) % 7) + 1
        if degree not in degrees:
            raise CompositionCompileError(
                f"Chord '{harmony.symbol}' lacks requested degree {target.degree}."
            )
        return (root_pc + degrees[degree] + target.alter) % 12
    if target.basis == "chord_index":
        index = (int(target.degree) - 1) % len(intervals)
        return (root_pc + intervals[index] + target.alter) % 12
    raise CompositionCompileError(
        f"Target basis '{target.basis}' does not resolve through harmony."
    )


def _pitch_class(
    composition: Composition,
    section: SectionPlan,
    event: PitchedEvent,
) -> int:
    return _target_pitch_class(
        composition,
        section,
        event.onset.fraction,
        event.target,
    )


def _candidate_pitches(pc: int, low: int, high: int) -> list[int]:
    return [pitch for pitch in range(low, high + 1) if pitch % 12 == pc]


def _local_cost(event: PitchedEvent, pitch: int, track: TrackPlan) -> float:
    center = event.register_hint if event.register_hint is not None else track.center_pitch
    weight = 0.12 + (0.24 * event.importance)
    return abs(pitch - center) * weight


def _transition_cost(
    previous: PitchedEvent,
    current: PitchedEvent,
    previous_pitch: int,
    pitch: int,
) -> float:
    interval = pitch - previous_pitch
    distance = abs(interval)
    cost = distance * 0.18
    if distance > 7:
        cost += (distance - 7) * 0.9
    if distance >= 12:
        cost += 5.0
    if (
        (current.contour == "up" and interval <= 0)
        or (current.contour == "down" and interval >= 0)
        or (current.contour == "hold" and distance > 2)
    ):
        cost += 3.0
    if previous.motif and previous.motif == current.motif and distance > 9:
        cost += 1.5
    return cost


def _fixed_candidates(
    composition: Composition,
    section: SectionPlan,
    event: PitchedEvent,
    track: TrackPlan,
) -> list[int]:
    if event.target.basis == "absolute":
        pitch = int(event.target.midi)
        return [pitch] if track.register_low <= pitch <= track.register_high else []
    if event.target.basis == "relative":
        raise CompositionCompileError("Relative targets require a previous pitch.")
    pc = _pitch_class(composition, section, event)
    return _candidate_pitches(pc, track.register_low, track.register_high)


def _realize_pitched_events(
    composition: Composition,
    section: SectionPlan,
    segment: SegmentPlan,
    track: TrackPlan,
    events: list[PitchedEvent],
) -> list[int]:
    if not events:
        return []
    if events[0].target.basis == "relative":
        raise CompositionCompileError(
            f"Segment '{segment.id}' begins with a relative pitch target."
        )

    first_candidates = _fixed_candidates(composition, section, events[0], track)
    if not first_candidates:
        raise CompositionCompileError(
            f"No pitch candidate for segment '{segment.id}' event 0."
        )
    costs: list[dict[int, tuple[float, int | None]]] = [
        {
            pitch: (_local_cost(events[0], pitch, track), None)
            for pitch in first_candidates
        }
    ]

    for index in range(1, len(events)):
        event = events[index]
        layer: dict[int, tuple[float, int | None]] = {}
        if event.target.basis == "relative":
            semitones = int(event.target.semitones)
            pairs = [
                (previous_pitch, previous_pitch + semitones)
                for previous_pitch in costs[index - 1]
                if track.register_low
                <= previous_pitch + semitones
                <= track.register_high
            ]
        else:
            candidates = _fixed_candidates(composition, section, event, track)
            pairs = [
                (previous_pitch, pitch)
                for previous_pitch in costs[index - 1]
                for pitch in candidates
            ]
        for previous_pitch, pitch in pairs:
            previous_cost = costs[index - 1][previous_pitch][0]
            candidate = (
                previous_cost
                + _local_cost(event, pitch, track)
                + _transition_cost(
                    events[index - 1],
                    event,
                    previous_pitch,
                    pitch,
                ),
                previous_pitch,
            )
            if pitch not in layer or candidate[0] < layer[pitch][0]:
                layer[pitch] = candidate
        if not layer:
            raise CompositionCompileError(
                f"No pitch path for segment '{segment.id}' event {index}."
            )
        costs.append(layer)

    cursor = min(costs[-1], key=lambda pitch: costs[-1][pitch][0])
    result = [cursor]
    for index in range(len(costs) - 1, 0, -1):
        previous = costs[index][cursor][1]
        assert previous is not None
        result.append(previous)
        cursor = previous
    return list(reversed(result))


def _voice_chord(
    symbol: str,
    *,
    low: int,
    high: int,
    count: int,
    omit_root: bool,
    previous: list[int] | None,
    top_pc: int | None = None,
    top_pitch: int | None = None,
) -> list[int]:
    root_pc, intervals, _ = _root_and_intervals(symbol)
    pcs = [(root_pc + interval) % 12 for interval in intervals]
    if omit_root and len(pcs) > 1:
        pcs = [pc for pc in pcs if pc != root_pc]
    if top_pc is not None and top_pc not in pcs:
        pcs.append(top_pc)
    count = min(count, len(pcs))
    if count <= 0:
        raise CompositionCompileError(f"Chord '{symbol}' has no usable pitches.")

    best: tuple[float, list[int]] | None = None
    for subset in combinations(pcs, count):
        if top_pc is not None and top_pc not in subset:
            continue
        choices = [_candidate_pitches(pc, low, high) for pc in subset]
        if any(not values for values in choices):
            continue
        for candidate in product(*choices):
            pitches = sorted(candidate)
            if len(set(pitches)) != len(pitches):
                continue
            if top_pc is not None and pitches[-1] % 12 != top_pc:
                continue
            if top_pitch is not None and pitches[-1] != top_pitch:
                continue
            span = pitches[-1] - pitches[0] if len(pitches) > 1 else 0
            if span > 24:
                continue
            center = sum(pitches) / len(pitches)
            cost = abs(center - ((low + high) / 2)) * 0.12
            if len(pitches) > 1:
                cost += max(0, 4 - span) * 0.4
            if previous:
                cost += sum(
                    min(abs(pitch - old) for old in previous)
                    for pitch in pitches
                )
                cost += abs(len(previous) - len(pitches)) * 0.35
                if top_pc is not None:
                    top_motion = abs(pitches[-1] - previous[-1])
                    cost += top_motion * 1.4
                    if top_motion > 7:
                        cost += (top_motion - 7) * 2.0
            elif not omit_root and root_pc in subset:
                cost -= 0.25
            if best is None or cost < best[0]:
                best = (cost, pitches)
    if best is None:
        raise CompositionCompileError(
            f"Cannot voice chord '{symbol}' in range {low}-{high}."
        )
    return best[1]


def _compile_segment(
    composition: Composition,
    section: SectionPlan,
    segment: SegmentPlan,
    track: TrackPlan,
) -> list[Note]:
    pitched_events = [
        event for event in segment.events if isinstance(event, PitchedEvent)
    ]
    pitched_pitches = _realize_pitched_events(
        composition,
        section,
        segment,
        track,
        pitched_events,
    )
    pitch_cursor = 0
    previous_voicing: list[int] | None = None
    notes: list[Note] = []

    for event in segment.events:
        start = float(event.onset.fraction)
        duration = float(event.duration.fraction)
        if isinstance(event, DrumEvent):
            notes.append(
                Note(
                    pitch=event.pitch,
                    start=start,
                    duration=duration,
                    velocity=event.velocity,
                )
            )
        elif isinstance(event, PitchedEvent):
            pitch = pitched_pitches[pitch_cursor]
            pitch_cursor += 1
            notes.append(
                Note(
                    pitch=pitch,
                    start=start,
                    duration=duration,
                    velocity=max(1, min(127, round(62 + 38 * event.accent))),
                )
            )
        elif isinstance(event, ChordEvent):
            harmony = _active_harmony(section, event.onset.fraction)
            low = event.low if event.low is not None else track.register_low
            high = event.high if event.high is not None else track.register_high
            top_pc = (
                _target_pitch_class(
                    composition,
                    section,
                    event.onset.fraction,
                    event.top_target,
                )
                if event.top_target is not None
                else None
            )
            top_pitch = (
                int(event.top_target.midi)
                if event.top_target is not None
                and event.top_target.basis == "absolute"
                else None
            )
            pitches = _voice_chord(
                harmony.symbol,
                low=low,
                high=high,
                count=event.notes,
                omit_root=event.omit_root,
                previous=previous_voicing,
                top_pc=top_pc,
                top_pitch=top_pitch,
            )
            previous_voicing = pitches
            for pitch in pitches:
                notes.append(
                    Note(
                        pitch=pitch,
                        start=start,
                        duration=duration,
                        velocity=max(1, min(127, round(54 + 38 * event.accent))),
                    )
                )
    return notes


def _project_role(
    track: TrackPlan,
    functions: set[str],
) -> TrackRole:
    if track.percussion or "pulse" in functions:
        return TrackRole.DRUMS if track.percussion else TrackRole.ARP
    if "low" in functions:
        return TrackRole.BASS
    if "harmony" in functions:
        return TrackRole.CHORDS
    if "foreground" in functions or "counterline" in functions:
        return TrackRole.MELODY
    if "texture" in functions:
        return TrackRole.PAD
    return TrackRole.OTHER


def _apply_treatment(
    notes: list[Note],
    track: TrackPlan,
    treatment: SegmentTreatment | None,
) -> list[Note]:
    if treatment is None:
        return notes
    pitch_shift = treatment.transpose_semitones + (12 * treatment.octave_shift)
    transformed: list[Note] = []
    for note in notes:
        pitch = note.pitch if track.percussion else note.pitch + pitch_shift
        if not 0 <= pitch <= 127:
            raise CompositionCompileError(
                f"Treatment for segment '{treatment.segment_id}' moves pitch "
                f"{note.pitch} outside MIDI range."
            )
        transformed.append(
            Note(
                pitch=pitch,
                start=note.start,
                duration=note.duration * treatment.gate_scale,
                velocity=max(
                    1,
                    min(127, round(note.velocity * treatment.velocity_scale)),
                ),
            )
        )
    return transformed


def compile_composition(composition: Composition) -> Project:
    report = validate_composition(composition)
    if not report.valid:
        raise CompositionCompileError("Composition has validation errors.", report)

    source_tracks = {item.id: item for item in composition.tracks}
    source_sections = {item.id: item for item in composition.sections}
    functions_by_track: dict[str, set[str]] = {
        track.id: set() for track in composition.tracks
    }
    for section in composition.sections:
        for segment in section.segments:
            functions_by_track[segment.track_id].update(segment.functions)

    project_tracks = [
        Track(
            id=track.id,
            name=track.name,
            role=_project_role(track, functions_by_track[track.id]),
            program=track.program,
            channel=9 if track.percussion else track.channel,
            percussion=track.percussion,
            volume=track.volume,
            performance=track.performance,
        )
        for track in composition.tracks
    ]

    project_sections: list[Section] = []
    timeline: list[SectionOccurrence] = []
    clips: list[Clip] = []
    links: list[CompositionLink] = []

    for occurrence_index, occurrence in enumerate(composition.timeline):
        source_section = source_sections[occurrence.section_id]
        treatments = {
            item.segment_id: item for item in occurrence.treatments
        }
        section_id = f"c1s_{occurrence.id}"
        occurrence_energy = (
            occurrence.energy
            if occurrence.energy is not None
            else source_section.energy
        )
        project_sections.append(
            Section(
                id=section_id,
                name=occurrence.label or source_section.name,
                length_bars=source_section.length_bars,
                energy=occurrence_energy,
                tags=[
                    "composition-4",
                    source_section.id,
                    occurrence.development,
                ],
            )
        )
        timeline.append(
            SectionOccurrence(
                id=f"c1o_{occurrence_index}",
                section_id=section_id,
                label=occurrence.label or source_section.name,
                energy_override=occurrence_energy,
                variation_intent=(
                    f"{occurrence.development}: {occurrence.intent}".rstrip(": ")
                ),
            )
        )
        for segment in source_section.segments:
            treatment = treatments.get(segment.id)
            enabled = (
                treatment.enabled
                if treatment is not None and treatment.enabled is not None
                else segment.default_enabled
            )
            if not enabled:
                continue
            track = source_tracks[segment.track_id]
            notes = _apply_treatment(
                _compile_segment(
                    composition,
                    source_section,
                    segment,
                    track,
                ),
                track,
                treatment,
            )
            if not notes:
                continue
            clip_id = f"c1c_{occurrence.id}_{segment.id}"
            link_id = f"c1l_{occurrence.id}_{segment.id}"
            clips.append(
                Clip(
                    id=clip_id,
                    name=segment.name,
                    kind=ClipKind.DRUMS if track.percussion else ClipKind.PITCHED,
                    length_bars=source_section.length_bars,
                    notes=notes,
                    tags=[
                        "composition-4",
                        occurrence.development,
                        *segment.functions,
                    ],
                )
            )
            links.append(
                CompositionLink(
                    id=link_id,
                    section_id=section_id,
                    track_id=track.id,
                    clip_id=clip_id,
                    repeat=False,
                )
            )

    return Project(
        title=composition.title,
        intent=composition.intent,
        genre_tags=composition.style_tags,
        bpm=composition.bpm,
        time_signature=composition.time_signature,
        key=composition.key,
        ppq=composition.ppq,
        seed=0,
        tracks=project_tracks,
        sections=project_sections,
        timeline=timeline,
        clips=clips,
        transformations=[],
        links=links,
    )
