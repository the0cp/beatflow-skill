# SPDX-License-Identifier: GPL-3.0-only
"""Semantic validation for style-neutral Composition 1.1 plans."""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from itertools import pairwise

from music21.chord import ChordException

from .composition_models import (
    BeatTime,
    ChordEvent,
    Composition,
    DrumEvent,
    PitchedEvent,
)
from .harmony_utils import parse_chord_symbol
from .meter import meter_profile
from .validation import Issue, ValidationReport

STEP_INDEX = {"C": 0, "D": 1, "E": 2, "F": 3, "G": 4, "A": 5, "B": 6}


def _duplicates(values: list[str]) -> set[str]:
    return {value for value, count in Counter(values).items() if count > 1}


def _is_representable(time: BeatTime, ppq: int) -> bool:
    return (time.numerator * ppq) % time.denominator == 0


def _active_harmony(section, onset: Fraction):
    for span in section.harmony:
        start = span.onset.fraction
        if start <= onset < start + span.duration.fraction:
            return span
    return None


def _target_harmony(section, event: PitchedEvent):
    return _harmony_for_target(section, event.onset.fraction, event.target)


def _harmony_for_target(section, onset: Fraction, target):
    if target.basis != "next_chord":
        return _active_harmony(section, onset)
    for span in section.harmony:
        if span.onset.fraction > onset:
            return span
    return section.harmony[-1] if section.harmony else None


def _chord_degrees(symbol: str) -> set[int]:
    parsed = parse_chord_symbol(symbol)
    root = parsed.root()
    if root is None or not parsed.pitches:
        raise ValueError("no pitches")
    root_step = STEP_INDEX[root.step]
    return {
        ((STEP_INDEX[pitch.step] - root_step) % 7) + 1
        for pitch in parsed.pitches
    }


def validate_composition(composition: Composition) -> ValidationReport:
    issues: list[Issue] = []
    harmony_degrees: dict[str, set[int]] = {}

    def add(
        severity: str,
        code: str,
        path: str,
        message: str,
        hint: str | None = None,
    ) -> None:
        issues.append(
            Issue(
                severity=severity,
                code=code,
                path=path,
                message=message,
                hint=hint,
            )
        )

    tracks = {item.id: item for item in composition.tracks}
    sections = {item.id: item for item in composition.sections}
    collections: dict[str, list] = {
        "tracks": composition.tracks,
        "sections": composition.sections,
        "timeline": composition.timeline,
        "interactions": composition.interactions,
        "segments": [
            segment
            for section in composition.sections
            for segment in section.segments
        ],
    }
    all_ids: list[str] = []
    for name, items in collections.items():
        ids = [item.id for item in items]
        all_ids.extend(ids)
        for duplicate in sorted(_duplicates(ids)):
            add("error", "duplicate_id", name, f"ID '{duplicate}' is duplicated.")
    for duplicate in sorted(_duplicates(all_ids)):
        locations = [
            name
            for name, items in collections.items()
            if duplicate in {item.id for item in items}
        ]
        if len(locations) > 1:
            add(
                "error",
                "global_id_collision",
                "/",
                f"ID '{duplicate}' is reused across: {', '.join(locations)}.",
            )

    explicit_channels = [
        track.channel
        for track in composition.tracks
        if track.channel is not None and not track.percussion
    ]
    for channel in sorted(
        channel for channel, count in Counter(explicit_channels).items() if count > 1
    ):
        add(
            "error",
            "duplicate_midi_channel",
            "tracks",
            f"Non-percussion MIDI channel {channel} is assigned more than once.",
        )

    used_tracks: set[str] = set()
    used_sections: set[str] = set()
    all_times: list[tuple[str, BeatTime]] = []
    monophonic_intervals: defaultdict[
        tuple[str, str, str], list[tuple[Fraction, Fraction, str]]
    ] = (
        defaultdict(list)
    )
    segments_by_section = {
        section.id: {segment.id: segment for segment in section.segments}
        for section in composition.sections
    }
    active_segments: set[tuple[str, str]] = set()

    for section_index, section in enumerate(composition.sections):
        section_length = (
            composition.beats_per_bar_fraction * section.length_bars
        )
        profile = meter_profile(composition.time_signature)
        section_functions = {
            function
            for segment in section.segments
            for function in segment.functions
        }
        for duplicate in sorted(
            _duplicates([phrase.id for phrase in section.phrases])
        ):
            add(
                "error",
                "duplicate_phrase_id",
                f"sections[{section_index}].phrases",
                (
                    f"Phrase ID '{duplicate}' is duplicated inside "
                    f"section '{section.id}'."
                ),
            )
        for phrase_index, phrase in enumerate(section.phrases):
            path = f"sections[{section_index}].phrases[{phrase_index}]"
            all_times.extend(
                [
                    (f"{path}.onset", phrase.onset),
                    (f"{path}.duration", phrase.duration),
                ]
            )
            if phrase.max_continuous_beats is not None:
                all_times.append(
                    (
                        f"{path}.max_continuous_beats",
                        phrase.max_continuous_beats,
                    )
                )
                if (
                    phrase.max_continuous_beats.fraction
                    > phrase.duration.fraction
                ):
                    add(
                        "error",
                        "phrase_continuity_exceeds_duration",
                        f"{path}.max_continuous_beats",
                        (
                            f"Phrase '{phrase.id}' allows continuous motion "
                            "longer than the phrase itself."
                        ),
                    )
            phrase_end = phrase.onset.fraction + phrase.duration.fraction
            if phrase.grouping != "free":
                expected_duration = (
                    sum(phrase.subphrase_bars) * profile.measure
                )
                if phrase.onset.fraction % profile.measure != 0:
                    add(
                        "error",
                        "grouped_phrase_off_bar_downbeat",
                        f"{path}.onset",
                        (
                            f"Grouped phrase '{phrase.id}' must begin on a "
                            "bar downbeat."
                        ),
                    )
                if phrase.duration.fraction != expected_duration:
                    add(
                        "error",
                        "phrase_grouping_duration_mismatch",
                        f"{path}.subphrase_bars",
                        (
                            f"Phrase '{phrase.id}' declares "
                            f"{sum(phrase.subphrase_bars)} grouped bars but "
                            f"lasts {phrase.duration.fraction} quarter-note "
                            "beats."
                        ),
                        (
                            "Make phrase duration equal the declared "
                            "subphrase bars in the current meter."
                        ),
                    )
            if phrase_end > section_length:
                add(
                    "error",
                    "phrase_out_of_bounds",
                    path,
                    (
                        f"Phrase '{phrase.id}' ends at beat {phrase_end}, "
                        f"beyond section length {section_length}."
                    ),
                )
            for function in phrase.functions:
                if function not in section_functions:
                    add(
                        "error",
                        "missing_phrase_function",
                        f"{path}.functions",
                        (
                            f"Section '{section.id}' has no segment with function "
                            f"'{function}'."
                        ),
                    )
            if (
                phrase.attention is not None
                and phrase.attention not in section_functions
            ):
                add(
                    "error",
                    "missing_phrase_attention",
                    f"{path}.attention",
                    (
                        f"Section '{section.id}' has no segment with function "
                        f"'{phrase.attention}'."
                    ),
                )

        phrases_by_id = {phrase.id: phrase for phrase in section.phrases}
        for duplicate in sorted(
            _duplicates([stage.id for stage in section.phrase_stages])
        ):
            add(
                "error",
                "duplicate_phrase_stage_id",
                f"sections[{section_index}].phrase_stages",
                (
                    f"Phrase stage ID '{duplicate}' is duplicated inside "
                    f"section '{section.id}'."
                ),
            )
        stages_by_phrase: defaultdict[str, list[tuple[int, object]]] = defaultdict(list)
        for stage_index, stage in enumerate(section.phrase_stages):
            path = f"sections[{section_index}].phrase_stages[{stage_index}]"
            all_times.extend(
                [
                    (f"{path}.onset", stage.onset),
                    (f"{path}.duration", stage.duration),
                ]
            )
            phrase = phrases_by_id.get(stage.phrase_id)
            if phrase is None:
                add(
                    "error",
                    "missing_phrase_stage_phrase",
                    f"{path}.phrase_id",
                    (
                        f"Phrase stage '{stage.id}' refers to missing phrase "
                        f"'{stage.phrase_id}'."
                    ),
                )
            else:
                stage_start = stage.onset.fraction
                stage_end = stage_start + stage.duration.fraction
                phrase_start = phrase.onset.fraction
                phrase_end = phrase_start + phrase.duration.fraction
                if stage_start < phrase_start or stage_end > phrase_end:
                    add(
                        "error",
                        "phrase_stage_outside_phrase",
                        path,
                        (
                            f"Phrase stage '{stage.id}' [{stage_start}, "
                            f"{stage_end}) is outside phrase '{phrase.id}' "
                            f"[{phrase_start}, {phrase_end})."
                        ),
                    )
                if (
                    phrase.functions
                    and stage.functions
                    and not set(stage.functions).issubset(phrase.functions)
                ):
                    add(
                        "error",
                        "phrase_stage_function_outside_phrase",
                        f"{path}.functions",
                        (
                            f"Phrase stage '{stage.id}' selects a function "
                            f"not covered by phrase '{phrase.id}'."
                        ),
                    )
                if (
                    stage.metric_role == "structural"
                    and phrase.grouping != "free"
                ):
                    boundaries = [phrase_start]
                    cursor = phrase_start
                    for bars in phrase.subphrase_bars[:-1]:
                        cursor += bars * profile.measure
                        boundaries.append(cursor)
                    if stage_start not in boundaries:
                        add(
                            "error",
                            "structural_stage_off_subphrase_boundary",
                            f"{path}.onset",
                            (
                                f"Structural phrase stage '{stage.id}' "
                                "does not begin at a declared subphrase "
                                f"boundary of phrase '{phrase.id}'."
                            ),
                            (
                                "Move the structural stage to a declared "
                                "boundary or give the displacement an "
                                "explicit pickup, extension, elision, or "
                                "free metric role."
                            ),
                        )
                stages_by_phrase[stage.phrase_id].append((stage_index, stage))
            for function in stage.functions:
                if function not in section_functions:
                    add(
                        "error",
                        "missing_phrase_stage_function",
                        f"{path}.functions",
                        (
                            f"Section '{section.id}' has no segment with "
                            f"function '{function}'."
                        ),
                    )

        for phrase_id, indexed_stages in stages_by_phrase.items():
            focus_stages = [stage for _, stage in indexed_stages if stage.focus]
            if len(focus_stages) > 1:
                add(
                    "error",
                    "multiple_phrase_focus_stages",
                    f"sections[{section_index}].phrase_stages",
                    (
                        f"Phrase '{phrase_id}' has more than one focus stage: "
                        + ", ".join(stage.id for stage in focus_stages)
                        + "."
                    ),
                )
            ordered = sorted(
                indexed_stages,
                key=lambda item: item[1].onset.fraction,
            )
            for (left_index, left), (right_index, right) in pairwise(ordered):
                left_end = left.onset.fraction + left.duration.fraction
                if right.onset.fraction < left_end:
                    add(
                        "error",
                        "overlapping_phrase_stages",
                        (
                            f"sections[{section_index}].phrase_stages"
                            f"[{right_index}]"
                        ),
                        (
                            f"Phrase stages '{left.id}' and '{right.id}' "
                            f"overlap inside phrase '{phrase_id}'."
                        ),
                    )

        for duplicate in sorted(
            _duplicates([arrival.id for arrival in section.arrivals])
        ):
            add(
                "error",
                "duplicate_arrival_id",
                f"sections[{section_index}].arrivals",
                (
                    f"Arrival ID '{duplicate}' is duplicated inside "
                    f"section '{section.id}'."
                ),
            )
        for duplicate in sorted(
            _duplicates([arrival.phrase_id for arrival in section.arrivals])
        ):
            add(
                "error",
                "duplicate_phrase_arrival",
                f"sections[{section_index}].arrivals",
                (
                    f"Phrase '{duplicate}' has more than one primary arrival "
                    f"inside section '{section.id}'."
                ),
            )
        for arrival_index, arrival in enumerate(section.arrivals):
            path = f"sections[{section_index}].arrivals[{arrival_index}]"
            all_times.append((f"{path}.onset", arrival.onset))
            if arrival.min_hold is not None:
                all_times.append((f"{path}.min_hold", arrival.min_hold))
            phrase = phrases_by_id.get(arrival.phrase_id)
            if phrase is None:
                add(
                    "error",
                    "missing_arrival_phrase",
                    f"{path}.phrase_id",
                    (
                        f"Arrival '{arrival.id}' refers to missing phrase "
                        f"'{arrival.phrase_id}'."
                    ),
                )
            else:
                phrase_start = phrase.onset.fraction
                phrase_end = phrase_start + phrase.duration.fraction
                if not phrase_start <= arrival.onset.fraction < phrase_end:
                    add(
                        "error",
                        "arrival_outside_phrase",
                        f"{path}.onset",
                        (
                            f"Arrival '{arrival.id}' at beat "
                            f"{arrival.onset.fraction} is outside phrase "
                            f"'{phrase.id}' [{phrase_start}, {phrase_end})."
                        ),
                    )
                elif (
                    arrival.min_hold is not None
                    and arrival.onset.fraction
                    + arrival.min_hold.fraction
                    > phrase_end
                ):
                    add(
                        "error",
                        "arrival_hold_exceeds_phrase",
                        f"{path}.min_hold",
                        (
                            f"Arrival '{arrival.id}' cannot hold for "
                            f"{arrival.min_hold.fraction} beats before phrase "
                            f"'{phrase.id}' ends."
                        ),
                    )
                if (
                    phrase.functions
                    and arrival.functions
                    and not set(arrival.functions).issubset(phrase.functions)
                ):
                    add(
                        "error",
                        "arrival_function_outside_phrase",
                        f"{path}.functions",
                        (
                            f"Arrival '{arrival.id}' selects a function not "
                            f"covered by phrase '{phrase.id}'."
                        ),
                    )
            for function in arrival.functions:
                if function not in section_functions:
                    add(
                        "error",
                        "missing_arrival_function",
                        f"{path}.functions",
                        (
                            f"Section '{section.id}' has no segment with "
                            f"function '{function}'."
                        ),
                    )

        for duplicate in sorted(
            _duplicates([silence.id for silence in section.silences])
        ):
            add(
                "error",
                "duplicate_silence_id",
                f"sections[{section_index}].silences",
                (
                    f"Silence ID '{duplicate}' is duplicated inside "
                    f"section '{section.id}'."
                ),
            )

        for silence_index, silence in enumerate(section.silences):
            path = f"sections[{section_index}].silences[{silence_index}]"
            all_times.extend(
                [
                    (f"{path}.onset", silence.onset),
                    (f"{path}.duration", silence.duration),
                ]
            )
            silence_end = silence.onset.fraction + silence.duration.fraction
            if silence_end > section_length:
                add(
                    "error",
                    "silence_out_of_bounds",
                    path,
                    (
                        f"Silence '{silence.id}' ends at beat {silence_end}, "
                        f"beyond section length {section_length}."
                    ),
                )
            for function in silence.functions:
                if function not in section_functions:
                    add(
                        "error",
                        "missing_silence_function",
                        f"{path}.functions",
                        (
                            f"Section '{section.id}' has no segment with function "
                            f"'{function}'."
                        ),
                    )

        cursor = Fraction(0)
        for harmony_index, span in enumerate(section.harmony):
            path = f"sections[{section_index}].harmony[{harmony_index}]"
            all_times.extend(
                [
                    (f"{path}.onset", span.onset),
                    (f"{path}.duration", span.duration),
                ]
            )
            try:
                harmony_degrees[span.symbol] = _chord_degrees(span.symbol)
            except (ChordException, ValueError) as error:
                add(
                    "error",
                    "invalid_chord_symbol",
                    f"{path}.symbol",
                    f"Cannot parse chord '{span.symbol}': {error}",
                )
            if span.onset.fraction != cursor:
                add(
                    "error",
                    "harmony_coverage",
                    f"{path}.onset",
                    (
                        f"Harmony in '{section.id}' must be contiguous; "
                        f"expected beat {cursor}."
                    ),
                )
            cursor = span.onset.fraction + span.duration.fraction
            if cursor > section_length:
                add(
                    "error",
                    "harmony_out_of_bounds",
                    path,
                    f"Harmony ends at beat {cursor}, beyond section length {section_length}.",
                )
        if section.harmony and cursor != section_length:
            add(
                "error",
                "harmony_coverage",
                f"sections[{section_index}].harmony",
                (
                    f"Harmony covers {cursor} of {section_length} beats "
                    f"in section '{section.id}'."
                ),
            )

        for segment_index, segment in enumerate(section.segments):
            segment_path = (
                f"sections[{section_index}].segments[{segment_index}]"
            )
            all_times.extend(
                [
                    (f"{segment_path}.start", segment.start),
                    (f"{segment_path}.duration", segment.duration),
                ]
            )
            if segment.track_id not in tracks:
                add(
                    "error",
                    "missing_track",
                    f"{segment_path}.track_id",
                    f"Unknown track '{segment.track_id}'.",
                )
                continue
            track = tracks[segment.track_id]
            used_tracks.add(track.id)
            segment_start = segment.start.fraction
            segment_end = segment_start + segment.duration.fraction
            if segment_end > section_length:
                add(
                    "error",
                    "segment_out_of_bounds",
                    segment_path,
                    (
                        f"Segment '{segment.id}' ends at beat {segment_end}, "
                        f"beyond section length {section_length}."
                    ),
                )

            previous_pitched = None
            exact_events: Counter[tuple] = Counter()
            for event_index, event in enumerate(segment.events):
                event_path = f"{segment_path}.events[{event_index}]"
                all_times.extend(
                    [
                        (f"{event_path}.onset", event.onset),
                        (f"{event_path}.duration", event.duration),
                    ]
                )
                event_start = event.onset.fraction
                event_end = event_start + event.duration.fraction
                if event_start < segment_start or event_end > segment_end:
                    add(
                        "error",
                        "event_outside_segment",
                        event_path,
                        (
                            f"Event spans beats {event_start}..{event_end}, "
                            f"outside segment {segment_start}..{segment_end}."
                        ),
                    )
                if event_end > section_length:
                    add(
                        "error",
                        "event_outside_section",
                        event_path,
                        f"Event ends beyond section '{section.id}'.",
                    )

                exact_key = (
                    event.type,
                    event_start,
                    event.duration.fraction,
                    getattr(event, "pitch", None),
                    str(getattr(event, "target", None)),
                )
                exact_events[exact_key] += 1

                if track.percussion and not isinstance(event, DrumEvent):
                    add(
                        "error",
                        "pitched_event_on_percussion_track",
                        event_path,
                        f"Percussion track '{track.id}' can contain only drum events.",
                    )
                if not track.percussion and isinstance(event, DrumEvent):
                    add(
                        "error",
                        "drum_event_on_pitched_track",
                        event_path,
                        f"Pitched track '{track.id}' cannot contain drum events.",
                    )
                if track.monophonic and isinstance(event, (PitchedEvent, ChordEvent)):
                    monophonic_intervals[
                        (section.id, segment.id, track.id)
                    ].append(
                        (event_start, event_end, event_path)
                    )
                    if isinstance(event, ChordEvent) and event.notes > 1:
                        add(
                            "error",
                            "polyphonic_event_on_monophonic_track",
                            event_path,
                            f"Monophonic track '{track.id}' cannot play a chord event.",
                        )

                if isinstance(event, ChordEvent):
                    if not section.harmony:
                        add(
                            "error",
                            "missing_harmony",
                            event_path,
                            "Chord events require section harmony.",
                        )
                    elif _active_harmony(section, event_start) is None:
                        add(
                            "error",
                            "missing_active_harmony",
                            event_path,
                            f"No harmony covers chord event at beat {event_start}.",
                        )
                    if event.top_target is not None:
                        target = event.top_target
                        target_path = f"{event_path}.top_target"
                        if target.basis == "absolute":
                            low = event.low if event.low is not None else track.register_low
                            high = event.high if event.high is not None else track.register_high
                            if not low <= int(target.midi) <= high:
                                add(
                                    "error",
                                    "chord_top_target_outside_range",
                                    target_path,
                                    (
                                        f"Absolute top target {target.midi} falls outside "
                                        f"the chord range {low}..{high}."
                                    ),
                                )
                        elif target.basis in {
                            "chord",
                            "chord_index",
                            "next_chord",
                        }:
                            harmony = _harmony_for_target(
                                section,
                                event.onset.fraction,
                                target,
                            )
                            if harmony is None:
                                add(
                                    "error",
                                    "missing_harmony",
                                    target_path,
                                    (
                                        f"Top target basis '{target.basis}' requires "
                                        "section harmony."
                                    ),
                                )
                            elif target.basis in {"chord", "next_chord"}:
                                available = harmony_degrees.get(harmony.symbol)
                                requested = ((int(target.degree) - 1) % 7) + 1
                                if (
                                    available is not None
                                    and requested not in available
                                ):
                                    add(
                                        "error",
                                        "unavailable_chord_degree",
                                        f"{target_path}.degree",
                                        (
                                            f"Chord '{harmony.symbol}' does not "
                                            f"contain requested top degree "
                                            f"{target.degree}."
                                        ),
                                    )

                if isinstance(event, PitchedEvent):
                    target = event.target
                    if target.basis == "relative" and previous_pitched is None:
                        add(
                            "error",
                            "relative_target_without_previous_note",
                            f"{event_path}.target",
                            "The first pitched event in a segment cannot be relative.",
                        )
                    if target.basis in {
                        "chord",
                        "chord_index",
                        "next_chord",
                    }:
                        harmony = _target_harmony(section, event)
                        if harmony is None:
                            add(
                                "error",
                                "missing_harmony",
                                event_path,
                                f"Target basis '{target.basis}' requires section harmony.",
                            )
                        elif target.basis in {"chord", "next_chord"}:
                            available = harmony_degrees.get(harmony.symbol)
                            requested = ((int(target.degree) - 1) % 7) + 1
                            if (
                                available is not None
                                and requested not in available
                            ):
                                add(
                                    "error",
                                    "unavailable_chord_degree",
                                    f"{event_path}.target.degree",
                                    (
                                        f"Chord '{harmony.symbol}' does not "
                                        f"contain requested degree {target.degree}."
                                    ),
                                )
                    previous_pitched = event

            if any(count > 1 for count in exact_events.values()):
                add(
                    "warning",
                    "duplicate_event",
                    f"{segment_path}.events",
                    f"Segment '{segment.id}' contains exact duplicate events.",
                )

        for interaction_index, interaction in enumerate(
            item
            for item in composition.interactions
            if item.section_id == section.id
        ):
            path = f"interactions[{interaction_index}]"
            if interaction.source not in section_functions:
                add(
                    "error",
                    "missing_interaction_source",
                    path,
                    (
                        f"Section '{section.id}' has no segment with function "
                        f"'{interaction.source}'."
                    ),
                )
            if interaction.target not in section_functions:
                add(
                    "error",
                    "missing_interaction_target",
                    path,
                    (
                        f"Section '{section.id}' has no segment with function "
                        f"'{interaction.target}'."
                    ),
                )

    for path, time in all_times:
        if not _is_representable(time, composition.ppq):
            add(
                "error",
                "time_not_representable_at_ppq",
                path,
                (
                    f"{time.numerator}/{time.denominator} beat cannot be represented "
                    f"exactly at PPQ {composition.ppq}."
                ),
                "Choose a compatible PPQ or a representable rational value.",
            )

    for timeline_index, occurrence in enumerate(composition.timeline):
        if occurrence.section_id not in sections:
            add(
                "error",
                "missing_section",
                f"timeline[{timeline_index}].section_id",
                f"Unknown section '{occurrence.section_id}'.",
            )
        else:
            used_sections.add(occurrence.section_id)
            section = sections[occurrence.section_id]
            section_segments = segments_by_section[section.id]
            treatments = {
                item.segment_id: item for item in occurrence.treatments
            }
            for treatment_index, treatment in enumerate(occurrence.treatments):
                path = (
                    f"timeline[{timeline_index}].treatments[{treatment_index}]"
                )
                segment = section_segments.get(treatment.segment_id)
                if segment is None:
                    add(
                        "error",
                        "missing_treatment_segment",
                        f"{path}.segment_id",
                        (
                            f"Occurrence '{occurrence.id}' treats unknown segment "
                            f"'{treatment.segment_id}' in section '{section.id}'."
                        ),
                    )
                    continue
                track = tracks.get(segment.track_id)
                if (
                    track is not None
                    and track.percussion
                    and (
                        treatment.transpose_semitones
                        or treatment.octave_shift
                    )
                ):
                    add(
                        "error",
                        "percussion_pitch_treatment",
                        path,
                        "Percussion segments cannot be transposed or octave-shifted.",
                    )
                if treatment.enabled is not False:
                    segment_end = (
                        segment.start.fraction + segment.duration.fraction
                    )
                    for event_index, event in enumerate(segment.events):
                        treated_end = (
                            event.onset.fraction
                            + event.duration.fraction * Fraction(
                                str(treatment.gate_scale)
                            )
                        )
                        if treated_end > segment_end:
                            add(
                                "error",
                                "treated_event_outside_segment",
                                f"{path}.gate_scale",
                                (
                                    f"Gate scale {treatment.gate_scale:g} moves "
                                    f"event {event_index} in '{segment.id}' beyond "
                                    "its segment boundary."
                                ),
                            )

            enabled_segments = []
            for segment in section.segments:
                treatment = treatments.get(segment.id)
                enabled = (
                    treatment.enabled
                    if treatment is not None
                    and treatment.enabled is not None
                    else segment.default_enabled
                )
                if enabled:
                    enabled_segments.append(segment)
                    active_segments.add((section.id, segment.id))
            if not enabled_segments:
                add(
                    "error",
                    "empty_occurrence",
                    f"timeline[{timeline_index}]",
                    f"Occurrence '{occurrence.id}' enables no musical segments.",
                )

            by_track: defaultdict[
                str, list[tuple[Fraction, Fraction, str, str]]
            ] = defaultdict(list)
            for segment in enabled_segments:
                treatment = treatments.get(segment.id)
                gate = Fraction(
                    str(treatment.gate_scale if treatment is not None else 1.0)
                )
                key = (section.id, segment.id, segment.track_id)
                for start, end, path in monophonic_intervals.get(key, []):
                    by_track[segment.track_id].append(
                        (
                            start,
                            start + (end - start) * gate,
                            path,
                            segment.id,
                        )
                    )
            for track_id, intervals in by_track.items():
                ordered = sorted(intervals)
                for previous, current in pairwise(ordered):
                    if current[0] < previous[1]:
                        add(
                            "error",
                            "overlapping_monophonic_events",
                            f"timeline[{timeline_index}]",
                            (
                                f"Occurrence '{occurrence.id}' overlaps track "
                                f"'{track_id}' at beats {previous[0]}..{previous[1]} "
                                f"('{previous[3]}') and {current[0]}..{current[1]} "
                                f"('{current[3]}')."
                            ),
                        )

    for interaction_index, interaction in enumerate(composition.interactions):
        if interaction.section_id not in sections:
            add(
                "error",
                "missing_interaction_section",
                f"interactions[{interaction_index}].section_id",
                f"Unknown section '{interaction.section_id}'.",
            )

    for track_id in sorted(set(tracks) - used_tracks):
        add(
            "warning",
            "unused_track",
            f"tracks.{track_id}",
            f"Track '{track_id}' is never used by a segment.",
        )
    for section_id in sorted(set(sections) - used_sections):
        add(
            "warning",
            "unused_section",
            f"sections.{section_id}",
            f"Section '{section_id}' never appears in the timeline.",
        )
    for section in composition.sections:
        for segment in section.segments:
            if (
                not segment.default_enabled
                and (section.id, segment.id) not in active_segments
            ):
                add(
                    "warning",
                    "unused_optional_segment",
                    f"sections.{section.id}.segments.{segment.id}",
                    (
                        f"Optional segment '{segment.id}' is never enabled by "
                        "a timeline occurrence."
                    ),
                )

    errors = sum(issue.severity == "error" for issue in issues)
    warnings = sum(issue.severity == "warning" for issue in issues)
    bars = sum(
        sections[item.section_id].length_bars
        for item in composition.timeline
        if item.section_id in sections
    )
    beats = composition.beats_per_bar_fraction * bars
    seconds = float(beats) * (60.0 / composition.bpm)
    return ValidationReport(
        valid=errors == 0,
        errors=errors,
        warnings=warnings,
        issues=issues,
        stats={
            "bars": bars,
            "beats": float(beats),
            "seconds": round(seconds, 6),
            "target_duration_seconds": composition.target_duration_seconds,
            "tracks": len(composition.tracks),
            "sections": len(composition.sections),
            "segments": sum(len(section.segments) for section in composition.sections),
            "events": sum(
                len(segment.events)
                for section in composition.sections
                for segment in section.segments
            ),
            "interactions": len(composition.interactions),
            "phrases": sum(
                len(section.phrases) for section in composition.sections
            ),
            "phrase_stages": sum(
                len(section.phrase_stages) for section in composition.sections
            ),
            "arrivals": sum(
                len(section.arrivals) for section in composition.sections
            ),
            "silences": sum(
                len(section.silences) for section in composition.sections
            ),
            "ppq": composition.ppq,
        },
    )
