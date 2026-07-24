# SPDX-License-Identifier: GPL-3.0-only
"""Style-neutral diagnostics and candidate comparison for Composition 1.0."""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .composition_compiler import CompositionCompileError, compile_composition
from .composition_models import ChordEvent, Composition, DrumEvent, PitchedEvent
from .composition_validation import validate_composition
from .harmony_utils import parse_chord_symbol
from .meter import MeterProfile, meter_profile


class DiagnosticIssue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["warning", "info"]
    dimension: str
    code: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)
    suggestion: str | None = None


class DiagnosticReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    structurally_valid: bool
    warnings: int
    infos: int
    issues: list[DiagnosticIssue]
    metrics: dict[str, Any] = Field(default_factory=dict)


def _round(value: float) -> float:
    return round(value, 4)


def _entropy(values: list[Any]) -> float:
    if not values:
        return 0.0
    counts = Counter(values)
    total = len(values)
    return _round(
        -sum(
            (count / total) * math.log2(count / total)
            for count in counts.values()
        )
    )


def _fraction_text(value: Fraction) -> str:
    return f"{value.numerator}/{value.denominator}"


def _segment_metrics(composition: Composition, segment) -> dict[str, Any]:
    pitched = [event for event in segment.events if isinstance(event, PitchedEvent)]
    chords = [event for event in segment.events if isinstance(event, ChordEvent)]
    profile = meter_profile(composition.time_signature)
    pitched_off_eighth_grid = [
        event
        for event in pitched
        if (event.onset.fraction * 2).denominator != 1
    ]
    pitched_off_meter_division = [
        event
        for event in pitched
        if event.onset.fraction % profile.division != 0
    ]
    durations = [
        _fraction_text(event.duration.fraction)
        for event in segment.events
    ]
    onsets = sorted({event.onset.fraction for event in segment.events})
    pitched_onsets = sorted({event.onset.fraction for event in pitched})
    rest_gaps: list[Fraction] = []
    if pitched:
        ordered = sorted(pitched, key=lambda event: event.onset.fraction)
        for previous, current in zip(ordered, ordered[1:]):
            previous_end = previous.onset.fraction + previous.duration.fraction
            if current.onset.fraction > previous_end:
                rest_gaps.append(current.onset.fraction - previous_end)

    beats_per_bar = composition.beats_per_bar_fraction
    bar_patterns: defaultdict[int, list[tuple[str, str, str]]] = defaultdict(list)
    for event in segment.events:
        bar = int(event.onset.fraction // beats_per_bar)
        within = event.onset.fraction - (bar * beats_per_bar)
        bar_patterns[bar].append(
            (
                event.type,
                _fraction_text(within),
                _fraction_text(event.duration.fraction),
            )
        )
    patterns = [
        tuple(sorted(values))
        for _, values in sorted(bar_patterns.items())
    ]
    pattern_counts = Counter(patterns)
    metric_positions = Counter(
        profile.position(event.onset.fraction)
        for event in segment.events
    )
    tactus_aligned_events = sum(
        profile.is_tactus(event.onset.fraction)
        for event in segment.events
    )
    bar_downbeat_attacks = sum(
        profile.is_bar_downbeat(event.onset.fraction)
        for event in segment.events
    )

    return {
        "track_id": segment.track_id,
        "functions": segment.functions,
        "events": len(segment.events),
        "pitched_events": len(pitched),
        "pitched_off_eighth_grid": len(pitched_off_eighth_grid),
        "pitched_off_eighth_grid_ratio": _round(
            len(pitched_off_eighth_grid) / max(1, len(pitched))
        ),
        "pitched_off_meter_division": len(pitched_off_meter_division),
        "pitched_off_meter_division_ratio": _round(
            len(pitched_off_meter_division) / max(1, len(pitched))
        ),
        "chord_events": len(chords),
        "unique_onsets": len(onsets),
        "duration_vocabulary": len(set(durations)),
        "duration_entropy_bits": _entropy(durations),
        "rest_gaps_ge_half_beat": sum(gap >= Fraction(1, 2) for gap in rest_gaps),
        "longest_rest_beats": _round(float(max(rest_gaps, default=Fraction(0)))),
        "pitched_unique_onsets": len(pitched_onsets),
        "chord_note_counts": sorted({event.notes for event in chords}),
        "active_bar_patterns": len(patterns),
        "unique_bar_pattern_ratio": _round(
            len(pattern_counts) / max(1, len(patterns))
        ),
        "most_repeated_bar_pattern": max(pattern_counts.values(), default=0),
        "metric_positions": dict(sorted(metric_positions.items())),
        "tactus_aligned_events": tactus_aligned_events,
        "tactus_alignment_ratio": _round(
            tactus_aligned_events / max(1, len(segment.events))
        ),
        "bar_downbeat_attacks": bar_downbeat_attacks,
        "bar_downbeat_coverage": _round(
            len(
                {
                    int(event.onset.fraction // profile.measure)
                    for event in segment.events
                    if profile.is_bar_downbeat(event.onset.fraction)
                }
            )
            / max(1, composition_section_bars(composition, segment.id))
        ),
    }


def composition_section_bars(composition: Composition, segment_id: str) -> int:
    for section in composition.sections:
        if any(segment.id == segment_id for segment in section.segments):
            return section.length_bars
    return 1


def _rhythm_fingerprint(
    composition: Composition,
    segment,
) -> tuple[tuple[tuple[str, str], ...], ...]:
    measure = meter_profile(composition.time_signature).measure
    bars: defaultdict[int, list[tuple[str, str]]] = defaultdict(list)
    for event in segment.events:
        bar = int(event.onset.fraction // measure)
        within = event.onset.fraction - bar * measure
        bars[bar].append(
            (
                _fraction_text(within),
                _fraction_text(event.duration.fraction),
            )
        )
    return tuple(
        sorted(
            tuple(sorted(values))
            for values in bars.values()
        )
    )


def _function_onsets(section) -> dict[str, set[Fraction]]:
    result: defaultdict[str, set[Fraction]] = defaultdict(set)
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        onsets = {event.onset.fraction for event in segment.events}
        for function in segment.functions:
            result[function].update(onsets)
    return dict(result)


def _function_activity(composition: Composition, section) -> dict[str, float]:
    section_length = composition.beats_per_bar_fraction * section.length_bars
    spans: defaultdict[str, list[tuple[Fraction, Fraction]]] = defaultdict(list)
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        for function in segment.functions:
            spans[function].extend(
                (
                    event.onset.fraction,
                    event.onset.fraction + event.duration.fraction,
                )
                for event in segment.events
            )
    result: dict[str, float] = {}
    for function, values in spans.items():
        ordered = sorted(values)
        covered = Fraction(0)
        current_start, current_end = ordered[0]
        for start, end in ordered[1:]:
            if start <= current_end:
                current_end = max(current_end, end)
            else:
                covered += current_end - current_start
                current_start, current_end = start, end
        covered += current_end - current_start
        result[function] = _round(float(covered / section_length))
    return result


def _attention_metrics(section) -> dict[str, Any]:
    top_voice_attacks = 0
    top_voice_tracks: set[str] = set()
    top_voice_onsets: set[Fraction] = set()
    foreground_attacks = 0
    foreground_tracks: set[str] = set()
    foreground_onsets: set[Fraction] = set()
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        segment_top_events = [
            event
            for event in segment.events
            if isinstance(event, ChordEvent) and event.top_target is not None
        ]
        segment_top_attacks = len(segment_top_events)
        if segment_top_attacks:
            top_voice_attacks += segment_top_attacks
            top_voice_tracks.add(segment.track_id)
            top_voice_onsets.update(
                event.onset.fraction for event in segment_top_events
            )
        if "foreground" in segment.functions:
            segment_foreground_events = [
                event
                for event in segment.events
                if isinstance(event, PitchedEvent)
            ]
            segment_foreground_attacks = len(segment_foreground_events)
            foreground_attacks += segment_foreground_attacks
            if segment_foreground_attacks:
                foreground_tracks.add(segment.track_id)
                foreground_onsets.update(
                    event.onset.fraction for event in segment_foreground_events
                )
    shared_onsets = top_voice_onsets & foreground_onsets
    return {
        "designed_top_voice_attacks": top_voice_attacks,
        "designed_top_voice_tracks": sorted(top_voice_tracks),
        "designed_top_voice_unique_onsets": len(top_voice_onsets),
        "explicit_foreground_attacks": foreground_attacks,
        "explicit_foreground_tracks": sorted(foreground_tracks),
        "explicit_foreground_unique_onsets": len(foreground_onsets),
        "shared_attack_onsets": len(shared_onsets),
        "shared_smaller_line_ratio": _round(
            len(shared_onsets)
            / max(1, min(len(top_voice_onsets), len(foreground_onsets)))
        ),
    }


def _pulse_phase_metrics(
    section,
    profile: MeterProfile,
) -> dict[str, Any]:
    phases: Counter[Fraction] = Counter()
    events = 0
    for segment in section.segments:
        if not segment.default_enabled or "pulse" not in segment.functions:
            continue
        for event in segment.events:
            if not isinstance(event, DrumEvent):
                continue
            events += 1
            phases[event.onset.fraction % profile.tactus] += 1
    return {
        "percussion_events": events,
        "quarter_phase_count": len(phases),
        "tactus_phase_count": len(phases),
        "quarter_phases": {
            _fraction_text(phase): count
            for phase, count in sorted(phases.items())
        },
        "phase_reference_beats": _fraction_text(profile.tactus),
    }


def _transposition_equivalent_bar_metrics(
    notes,
    beats_per_bar: Fraction,
) -> dict[str, Any]:
    by_bar: defaultdict[int, defaultdict[float, list]] = defaultdict(
        lambda: defaultdict(list)
    )
    for note in notes:
        start = Fraction(str(note.start))
        bar = int(start // beats_per_bar)
        within = float(start - (bar * beats_per_bar))
        by_bar[bar][round(within, 8)].append(note)

    patterns = []
    for _, by_onset in sorted(by_bar.items()):
        line = []
        for onset, onset_notes in sorted(by_onset.items()):
            top = max(onset_notes, key=lambda item: item.pitch)
            line.append((onset, round(top.duration, 8), top.pitch))
        if not line:
            continue
        origin = line[0][2]
        patterns.append(
            tuple(
                (onset, duration, pitch - origin)
                for onset, duration, pitch in line
            )
        )
    counts = Counter(patterns)
    repeated = max(counts.values(), default=0)
    return {
        "active_bars": len(patterns),
        "unique_transposition_equivalent_bar_patterns": len(counts),
        "most_repeated_transposition_equivalent_bar": repeated,
        "dominant_transposition_equivalent_bar_ratio": _round(
            repeated / max(1, len(patterns))
        ),
    }


def _active_chord_pitch_classes(harmony, onset: Fraction) -> set[int]:
    for span in harmony:
        start = span.onset.fraction
        if start <= onset < start + span.duration.fraction:
            return {
                pitch.pitchClass
                for pitch in parse_chord_symbol(span.symbol).pitches
            }
    return set()


def _structural_tone_metrics(
    notes,
    harmony,
    profile: MeterProfile,
) -> dict[str, Any]:
    by_onset: defaultdict[Fraction, list] = defaultdict(list)
    for note in notes:
        by_onset[Fraction(str(note.start))].append(note)
    line = [
        (onset, max(onset_notes, key=lambda item: item.pitch).pitch)
        for onset, onset_notes in sorted(by_onset.items())
    ]
    structural = [
        (index, onset, pitch)
        for index, (onset, pitch) in enumerate(line)
        if profile.is_tactus(onset)
    ]
    chord_tones = 0
    unresolved_nonchord = 0
    for index, onset, pitch in structural:
        pitch_classes = _active_chord_pitch_classes(harmony, onset)
        if not pitch_classes:
            continue
        if pitch % 12 in pitch_classes:
            chord_tones += 1
            continue
        resolved = False
        if index + 1 < len(line):
            next_onset, next_pitch = line[index + 1]
            next_pitch_classes = _active_chord_pitch_classes(
                harmony,
                next_onset,
            )
            resolved = (
                next_onset - onset <= profile.tactus
                and abs(next_pitch - pitch) <= 2
                and next_pitch % 12 in next_pitch_classes
            )
        if not resolved:
            unresolved_nonchord += 1
    return {
        "structural_attacks": len(structural),
        "structural_chord_tones": chord_tones,
        "structural_chord_tone_ratio": _round(
            chord_tones / max(1, len(structural))
        ),
        "unresolved_structural_nonchord_tones": unresolved_nonchord,
        "unresolved_structural_nonchord_ratio": _round(
            unresolved_nonchord / max(1, len(structural))
        ),
    }


def _occurrence_state(composition: Composition, occurrence, section):
    treatments = {item.segment_id: item for item in occurrence.treatments}
    active = []
    signature = []
    for segment in section.segments:
        treatment = treatments.get(segment.id)
        enabled = (
            treatment.enabled
            if treatment is not None and treatment.enabled is not None
            else segment.default_enabled
        )
        if not enabled:
            continue
        active.append((segment, treatment))
        signature.append(
            (
                segment.id,
                treatment.transpose_semitones if treatment else 0,
                treatment.octave_shift if treatment else 0,
                treatment.velocity_scale if treatment else 1.0,
                treatment.gate_scale if treatment else 1.0,
            )
        )

    section_length = composition.beats_per_bar_fraction * section.length_bars
    spans: defaultdict[str, list[tuple[Fraction, Fraction]]] = defaultdict(list)
    for segment, treatment in active:
        gate = Fraction(
            str(treatment.gate_scale if treatment is not None else 1.0)
        )
        for function in segment.functions:
            spans[function].extend(
                (
                    event.onset.fraction,
                    event.onset.fraction + event.duration.fraction * gate,
                )
                for event in segment.events
            )
    activity: dict[str, float] = {}
    for function, values in spans.items():
        ordered = sorted(values)
        covered = Fraction(0)
        start, end = ordered[0]
        for next_start, next_end in ordered[1:]:
            if next_start <= end:
                end = max(end, next_end)
            else:
                covered += end - start
                start, end = next_start, next_end
        covered += end - start
        activity[function] = _round(float(covered / section_length))

    energy = (
        occurrence.energy
        if occurrence.energy is not None
        else section.energy
    )
    return {
        "section_id": section.id,
        "development": occurrence.development,
        "energy": energy,
        "active_segments": [segment.id for segment, _ in active],
        "active_tracks": sorted(
            {segment.track_id for segment, _ in active}
        ),
        "activity": activity,
        "signature": (round(energy, 4), tuple(signature)),
    }


def diagnose_composition(composition: Composition) -> DiagnosticReport:
    validation = validate_composition(composition)
    issues: list[DiagnosticIssue] = []

    def add(
        severity: Literal["warning", "info"],
        dimension: str,
        code: str,
        message: str,
        evidence: dict[str, Any] | None = None,
        suggestion: str | None = None,
    ) -> None:
        issues.append(
            DiagnosticIssue(
                severity=severity,
                dimension=dimension,
                code=code,
                message=message,
                evidence=evidence or {},
                suggestion=suggestion,
            )
        )

    if not validation.valid:
        add(
            "warning",
            "structure",
            "invalid_composition",
            "Diagnostics are incomplete because structural validation failed.",
            {
                "error_codes": [
                    item.code
                    for item in validation.issues
                    if item.severity == "error"
                ]
            },
            "Repair hard validation errors before interpreting musical diagnostics.",
        )
        return DiagnosticReport(
            structurally_valid=False,
            warnings=1,
            infos=0,
            issues=issues,
            metrics={"validation": validation.model_dump(mode="json")},
        )

    sections = {item.id: item for item in composition.sections}
    segment_metrics: dict[str, dict[str, Any]] = {}
    section_metrics: dict[str, dict[str, Any]] = {}
    form_occurrences: dict[str, dict[str, Any]] = {}
    section_occurrences: defaultdict[str, list[tuple[int, Any, dict]]] = (
        defaultdict(list)
    )
    role_rhythm_signatures: defaultdict[
        str,
        defaultdict[
            tuple[tuple[tuple[str, str], ...], ...],
            set[str],
        ],
    ] = defaultdict(lambda: defaultdict(set))
    role_sections: defaultdict[str, set[str]] = defaultdict(set)
    profile = meter_profile(composition.time_signature)

    for index, occurrence in enumerate(composition.timeline):
        section = sections[occurrence.section_id]
        state = _occurrence_state(composition, occurrence, section)
        form_occurrences[occurrence.id] = {
            key: value
            for key, value in state.items()
            if key != "signature"
        }
        section_occurrences[section.id].append((index, occurrence, state))

    validation_seconds = float(validation.stats.get("seconds", 0.0))
    if composition.target_duration_seconds is not None:
        deviation = abs(
            validation_seconds - composition.target_duration_seconds
        ) / composition.target_duration_seconds
        if deviation > 0.1:
            add(
                "warning",
                "form",
                "duration_outside_target",
                "Rendered form duration differs materially from the declared target.",
                {
                    "actual_seconds": _round(validation_seconds),
                    "target_seconds": composition.target_duration_seconds,
                    "deviation_ratio": _round(deviation),
                },
                "Revise the timeline or the declared target duration.",
            )

    energies = [
        state["energy"]
        for _, _, state in (
            item
            for values in section_occurrences.values()
            for item in values
        )
    ]
    if len(energies) >= 6 and max(energies) - min(energies) < 0.2:
        add(
            "warning",
            "form",
            "flat_energy_curve",
            "The long-form timeline declares very little energy contrast.",
            {
                "occurrences": len(energies),
                "minimum": min(energies),
                "maximum": max(energies),
            },
            "Create an intentional rise, withdrawal, climax, or release.",
        )

    for section_id, values in section_occurrences.items():
        signatures = [state["signature"] for _, _, state in values]
        if len(values) >= 3 and len(set(signatures)) == 1:
            add(
                "warning",
                "form",
                "static_repeated_arrangement",
                (
                    f"Section '{section_id}' appears {len(values)} times "
                    "with the same arrangement state."
                ),
                {
                    "occurrences": [
                        occurrence.id for _, occurrence, _ in values
                    ]
                },
                "Change layer state, register, dynamics, gate, or material.",
            )
        previous = None
        for _, occurrence, state in values:
            if (
                previous is not None
                and occurrence.development
                in {"develop", "contrast", "climax", "release"}
                and state["signature"] == previous["signature"]
            ):
                add(
                    "warning",
                    "form",
                    "development_without_arrangement_change",
                    (
                        f"Occurrence '{occurrence.id}' declares "
                        f"'{occurrence.development}' but repeats the prior "
                        "arrangement state."
                    ),
                    {
                        "section_id": section_id,
                        "active_segments": state["active_segments"],
                        "energy": state["energy"],
                    },
                    "Make the declared development audible or label it as a repeat.",
                )
            previous = state

    for section in composition.sections:
        function_onsets = _function_onsets(section)
        function_segments: defaultdict[str, set[str]] = defaultdict(set)
        for segment in section.segments:
            for function in segment.functions:
                function_segments[function].add(segment.id)
        activity = _function_activity(composition, section)
        attention = _attention_metrics(section)
        pulse_phase = _pulse_phase_metrics(section, profile)
        overlap: dict[str, float] = {}
        functions = sorted(function_onsets)
        for source in functions:
            for target in functions:
                if source == target:
                    continue
                shared = function_onsets[source] & function_onsets[target]
                ratio = len(shared) / max(1, len(function_onsets[source]))
                overlap[f"{source}->{target}"] = _round(ratio)
                reverse_shared = len(shared) / max(1, len(function_onsets[target]))
                if (
                    len(function_onsets[source]) >= 8
                    and len(function_onsets[target]) >= 8
                    and function_segments[source] != function_segments[target]
                    and ratio >= 0.95
                    and reverse_shared >= 0.95
                    and source < target
                ):
                    add(
                        "warning",
                        "interaction",
                        "near_identical_role_rhythm",
                        (
                            f"Functions '{source}' and '{target}' in section "
                            f"'{section.id}' use nearly identical onset sets."
                        ),
                        {
                            "source_onsets": len(function_onsets[source]),
                            "target_onsets": len(function_onsets[target]),
                            "source_overlap": _round(ratio),
                            "target_overlap": _round(reverse_shared),
                        },
                        "Keep intentional ensemble hits, but give independent roles their own attacks.",
                    )

        section_metrics[section.id] = {
            "function_onsets": {
                key: len(value)
                for key, value in sorted(function_onsets.items())
            },
            "function_activity_ratio": activity,
            "overlap": overlap,
            "attention": attention,
            "pulse_phase": pulse_phase,
            "meter": {
                "kind": profile.kind,
                "pulses_per_bar": profile.pulses_per_bar,
                "tactus_beats": _fraction_text(profile.tactus),
                "division_beats": _fraction_text(profile.division),
                "measure_beats": _fraction_text(profile.measure),
            },
        }
        attention_threshold = max(4, section.length_bars)
        if (
            attention["designed_top_voice_attacks"] >= attention_threshold
            and attention["explicit_foreground_attacks"] >= attention_threshold
            and attention["shared_smaller_line_ratio"] >= 0.5
            and set(attention["designed_top_voice_tracks"]).isdisjoint(
                attention["explicit_foreground_tracks"]
            )
        ):
            add(
                "warning",
                "arrangement",
                "competing_attention_lines",
                (
                    f"Section '{section.id}' has a designed chord top line "
                    "and a separate active foreground with comparable presence."
                ),
                attention,
                (
                    "Choose one attention owner, or make the extra foreground "
                    "alternate with it as a sparse call-and-response layer."
                ),
            )
        if (
            pulse_phase["percussion_events"] >= 48
            and pulse_phase["quarter_phase_count"] >= 9
        ):
            add(
                "warning",
                "rhythm",
                "diffuse_pulse_phase",
                (
                    f"Percussion in section '{section.id}' uses many distinct "
                    "positions inside the quarter-note beat."
                ),
                pulse_phase,
                (
                    "Keep a stable reference layer; concentrate deliberate "
                    "push or drag in one role instead of shifting every layer."
                ),
            )
        if (
            section.length_bars >= 8
            and activity.get("foreground", 0.0) >= 0.9
        ):
            add(
                "info",
                "arrangement",
                "continuous_foreground_activity",
                (
                    f"Foreground segments cover almost all of section '{section.id}'."
                ),
                {"activity_ratio": activity["foreground"]},
                "Keep this when intentional; otherwise create role handoff or foreground rests.",
            )

        for segment in section.segments:
            metrics = _segment_metrics(composition, segment)
            segment_metrics[segment.id] = metrics
            if (
                segment.default_enabled
                and metrics["events"] >= 8
                and metrics["active_bar_patterns"] >= 4
            ):
                fingerprint = _rhythm_fingerprint(composition, segment)
                for function in segment.functions:
                    role_rhythm_signatures[function][fingerprint].add(section.id)
                    role_sections[function].add(section.id)
            if (
                segment.default_enabled
                and "harmony" in segment.functions
                and metrics["chord_events"] >= 8
                and metrics["tactus_alignment_ratio"] < 0.5
                and metrics["bar_downbeat_coverage"] < 0.5
            ):
                add(
                    "warning",
                    "rhythm",
                    "floating_harmony_attacks",
                    (
                        f"Harmony segment '{segment.id}' places most chord "
                        "attacks between the meter's primary beats."
                    ),
                    {
                        "meter": (
                            f"{composition.time_signature.numerator}/"
                            f"{composition.time_signature.denominator}"
                        ),
                        "chord_events": metrics["chord_events"],
                        "tactus_alignment_ratio": metrics[
                            "tactus_alignment_ratio"
                        ],
                        "bar_downbeat_coverage": metrics[
                            "bar_downbeat_coverage"
                        ],
                        "metric_positions": metrics["metric_positions"],
                    },
                    (
                        "Establish the harmonic change on a perceptible beat; "
                        "use off-beat re-attacks as contrast, preparation, or "
                        "suspension rather than the default placement."
                    ),
                )
            if (
                segment.default_enabled
                and "foreground" in segment.functions
                and pulse_phase["percussion_events"] == 0
                and metrics["pitched_events"] >= 16
                and metrics["pitched_off_meter_division_ratio"] >= 0.2
            ):
                add(
                    "warning",
                    "rhythm",
                    "unanchored_foreground_subdivision",
                    (
                        f"Foreground segment '{segment.id}' has many attacks "
                        "outside the eighth-note grid and no active percussion "
                        "reference in its section."
                    ),
                    {
                        "pitched_events": metrics["pitched_events"],
                        "pitched_off_eighth_grid": metrics[
                            "pitched_off_eighth_grid"
                        ],
                        "pitched_off_eighth_grid_ratio": metrics[
                            "pitched_off_eighth_grid_ratio"
                        ],
                        "pitched_off_meter_division_ratio": metrics[
                            "pitched_off_meter_division_ratio"
                        ],
                    },
                    (
                        "Render a fully quantized baseline first. Preserve "
                        "finer subdivisions only when a stable accompaniment "
                        "makes their metric relationship audible."
                    ),
                )
            if (
                metrics["pitched_events"] + metrics["chord_events"] >= 12
                and metrics["duration_vocabulary"] <= 2
            ):
                add(
                    "warning",
                    "rhythm",
                    "low_duration_vocabulary",
                    f"Segment '{segment.id}' uses very few explicit durations.",
                    {
                        "events": metrics["events"],
                        "duration_vocabulary": metrics["duration_vocabulary"],
                    },
                    "Vary duration only when the musical intent calls for contrast.",
                )
            if (
                metrics["pitched_events"] >= 24
                and metrics["rest_gaps_ge_half_beat"] == 0
            ):
                add(
                    "warning",
                    "phrasing",
                    "continuous_pitched_stream",
                    f"Segment '{segment.id}' has no half-beat phrase gap.",
                    {"pitched_events": metrics["pitched_events"]},
                    "Add a deliberate boundary, density change, or state that continuity is intended.",
                )
            if (
                metrics["chord_events"] >= 8
                and len(metrics["chord_note_counts"]) == 1
                and metrics["duration_vocabulary"] <= 2
            ):
                add(
                    "warning",
                    "texture",
                    "fixed_chord_blocks",
                    f"Segment '{segment.id}' repeats one chord size and little duration variation.",
                    {
                        "chord_events": metrics["chord_events"],
                        "note_counts": metrics["chord_note_counts"],
                        "duration_vocabulary": metrics["duration_vocabulary"],
                    },
                    "Use silence, partial voicings, register changes, or fuller attacks intentionally.",
                )
            if (
                metrics["active_bar_patterns"] >= 8
                and metrics["most_repeated_bar_pattern"]
                / metrics["active_bar_patterns"]
                >= 0.7
            ):
                add(
                    "warning",
                    "development",
                    "dominant_exact_bar_pattern",
                    f"One exact bar rhythm dominates segment '{segment.id}'.",
                    {
                        "bars": metrics["active_bar_patterns"],
                        "most_repeated": metrics["most_repeated_bar_pattern"],
                    },
                    "Preserve identity while changing at least one structural dimension.",
                )

    for function, signatures in role_rhythm_signatures.items():
        if function not in {"harmony", "foreground", "low", "counterline"}:
            continue
        total_sections = len(role_sections[function])
        for sections_with_signature in signatures.values():
            if (
                total_sections >= 4
                and len(sections_with_signature) >= 3
                and len(sections_with_signature) / total_sections >= 0.6
            ):
                add(
                    "warning",
                    "development",
                    "reused_role_rhythm_across_sections",
                    (
                        f"Function '{function}' reuses the same bar-rhythm "
                        f"multiset across {len(sections_with_signature)} sections."
                    ),
                    {
                        "function": function,
                        "sections": sorted(sections_with_signature),
                        "sections_with_function": total_sections,
                        "reuse_ratio": _round(
                            len(sections_with_signature) / total_sections
                        ),
                    },
                    (
                        "Keep an identifying rhythm where useful, but change "
                        "attack density, rests, harmonic rhythm, or phrase role "
                        "between formal sections."
                    ),
                )
                break

    interaction_metrics: dict[str, dict[str, Any]] = {}
    for intent in composition.interactions:
        section = sections[intent.section_id]
        onsets = _function_onsets(section)
        source = onsets.get(intent.source, set())
        target = onsets.get(intent.target, set())
        ratio = len(source & target) / max(1, len(source))
        interaction_metrics[intent.id] = {
            "section_id": intent.section_id,
            "source": intent.source,
            "target": intent.target,
            "overlap": _round(ratio),
            "minimum": intent.minimum_overlap,
            "maximum": intent.maximum_overlap,
        }
        if not intent.minimum_overlap <= ratio <= intent.maximum_overlap:
            add(
                "warning",
                "intent",
                "interaction_outside_declared_range",
                f"Interaction '{intent.id}' contradicts its declared overlap range.",
                interaction_metrics[intent.id],
                intent.description or "Revise the events or the declared musical intent.",
            )

    compiled_metrics: dict[str, dict[str, Any]] = {}
    try:
        project = compile_composition(composition)
    except CompositionCompileError as error:
        add(
            "warning",
            "realization",
            "unrealizable_composition",
            str(error),
            {},
            "Revise pitch targets, register bounds, or chord voicing ranges.",
        )
        project = None

    if project is not None:
        for clip in project.clips:
            if not (
                {"foreground", "counterline", "low"} & set(clip.tags)
            ):
                continue
            by_onset: defaultdict[float, list[int]] = defaultdict(list)
            for note in clip.notes:
                by_onset[round(note.start, 8)].append(note.pitch)
            line = [
                max(by_onset[onset])
                for onset in sorted(by_onset)
            ]
            intervals = [
                line[index] - line[index - 1]
                for index in range(1, len(line))
            ]
            directions = [
                1 if interval > 0 else -1
                for interval in intervals
                if interval
            ]
            changes = sum(
                current != previous
                for previous, current in zip(directions, directions[1:])
            )
            metrics = {
                "notes": len(line),
                "pitch_range": max(line) - min(line) if line else 0,
                "step_ratio": _round(
                    sum(abs(value) <= 2 for value in intervals)
                    / max(1, len(intervals))
                ),
                "large_leap_ratio": _round(
                    sum(abs(value) >= 7 for value in intervals)
                    / max(1, len(intervals))
                ),
                "direction_change_ratio": _round(
                    changes / max(1, len(directions) - 1)
                ),
            }
            compiled_metrics[clip.id] = metrics
            if (
                metrics["notes"] >= 24
                and metrics["direction_change_ratio"] < 0.18
            ):
                add(
                    "warning",
                    "contour",
                    "long_directional_run",
                    f"Compiled line '{clip.id}' changes direction very rarely.",
                    metrics,
                    "Create a phrase-level destination and release rather than one long run.",
                )

        clips = {clip.id: clip for clip in project.clips}
        for section in composition.sections:
            occurrences = [
                occurrence
                for occurrence in composition.timeline
                if occurrence.section_id == section.id
            ]
            for segment in section.segments:
                if "foreground" not in segment.functions:
                    continue
                clip = None
                for occurrence in occurrences:
                    state = _occurrence_state(
                        composition,
                        occurrence,
                        section,
                    )
                    if segment.id not in state["active_segments"]:
                        continue
                    clip = clips.get(f"c1c_{occurrence.id}_{segment.id}")
                    if clip is not None:
                        break
                if clip is None:
                    continue
                pattern_metrics = _transposition_equivalent_bar_metrics(
                    clip.notes,
                    composition.beats_per_bar_fraction,
                )
                compiled_metrics[clip.id][
                    "transposition_equivalent_bars"
                ] = pattern_metrics
                structural_tones = _structural_tone_metrics(
                    clip.notes,
                    section.harmony,
                    profile,
                )
                compiled_metrics[clip.id][
                    "structural_tones"
                ] = structural_tones
                if (
                    structural_tones["structural_attacks"] >= 12
                    and structural_tones[
                        "unresolved_structural_nonchord_tones"
                    ]
                    >= 4
                    and structural_tones[
                        "unresolved_structural_nonchord_ratio"
                    ]
                    >= 0.25
                ):
                    add(
                        "warning",
                        "harmony",
                        "unresolved_structural_nonchord_tones",
                        (
                            f"Foreground segment '{segment.id}' places many "
                            "unresolved non-chord tones on primary beats."
                        ),
                        structural_tones,
                        (
                            "Keep deliberate appoggiaturas and suspensions, "
                            "but make their preparation or stepwise resolution "
                            "audible; prefer chord tones at phrase anchors."
                        ),
                    )
                if (
                    pattern_metrics["active_bars"] >= 6
                    and pattern_metrics[
                        "most_repeated_transposition_equivalent_bar"
                    ]
                    >= 4
                    and pattern_metrics[
                        "dominant_transposition_equivalent_bar_ratio"
                    ]
                    >= 0.5
                ):
                    add(
                        "warning",
                        "development",
                        "transposition_equivalent_foreground_loop",
                        (
                            f"Foreground segment '{segment.id}' repeats one "
                            "bar-level pitch-and-rhythm shape under transposition."
                        ),
                        pattern_metrics,
                        (
                            "Develop a phrase across several bars or alter the "
                            "cell relationship, not only its pitch level."
                        ),
                    )

    warnings = sum(issue.severity == "warning" for issue in issues)
    infos = sum(issue.severity == "info" for issue in issues)
    return DiagnosticReport(
        structurally_valid=True,
        warnings=warnings,
        infos=infos,
        issues=issues,
        metrics={
            "form": {
                "actual_duration_seconds": _round(validation_seconds),
                "target_duration_seconds": composition.target_duration_seconds,
                "occurrences": form_occurrences,
                "energy_range": [
                    min(energies) if energies else 0.0,
                    max(energies) if energies else 0.0,
                ],
                "climax_occurrences": [
                    occurrence.id
                    for occurrence in composition.timeline
                    if occurrence.development == "climax"
                ],
            },
            "segments": segment_metrics,
            "sections": section_metrics,
            "interactions": interaction_metrics,
            "compiled": compiled_metrics,
        },
    )


def _candidate_fingerprints(
    composition: Composition,
) -> dict[str, set[tuple[Any, ...]]]:
    result: defaultdict[str, set[tuple[Any, ...]]] = defaultdict(set)
    section_positions = {
        section.id: index for index, section in enumerate(composition.sections)
    }
    for section_index, section in enumerate(composition.sections):
        for segment in section.segments:
            for event in segment.events:
                token = (
                    section_index,
                    event.type,
                    _fraction_text(event.onset.fraction),
                    _fraction_text(event.duration.fraction),
                    getattr(event, "notes", None),
                    getattr(event, "pitch", None),
                )
                for function in segment.functions:
                    result[function].add(token)
    sections = {section.id: section for section in composition.sections}
    for occurrence_index, occurrence in enumerate(composition.timeline):
        section = sections[occurrence.section_id]
        state = _occurrence_state(composition, occurrence, section)
        treatment_map = {
            treatment.segment_id: treatment
            for treatment in occurrence.treatments
        }
        form_token = (
            "occurrence",
            occurrence_index,
            section_positions[section.id],
            section.length_bars,
            occurrence.development,
            round(state["energy"], 4),
            tuple(state["active_segments"]),
        )
        result["form"].add(form_token)
        for segment_id in state["active_segments"]:
            segment = next(
                item for item in section.segments if item.id == segment_id
            )
            treatment = treatment_map.get(segment_id)
            arrangement_token = (
                "arrangement",
                occurrence_index,
                section_positions[section.id],
                segment_id,
                treatment.transpose_semitones if treatment else 0,
                treatment.octave_shift if treatment else 0,
                treatment.velocity_scale if treatment else 1.0,
                treatment.gate_scale if treatment else 1.0,
            )
            for function in segment.functions:
                result[function].add(arrangement_token)
    return dict(result)


def compare_compositions(compositions: list[Composition]) -> dict[str, Any]:
    if len(compositions) < 2:
        raise ValueError("Compare requires at least two compositions.")
    fingerprints = [_candidate_fingerprints(item) for item in compositions]
    pairs: list[dict[str, Any]] = []
    for left in range(len(compositions)):
        for right in range(left + 1, len(compositions)):
            functions = sorted(
                set(fingerprints[left]) | set(fingerprints[right])
            )
            similarities: dict[str, float] = {}
            for function in functions:
                a = fingerprints[left].get(function, set())
                b = fingerprints[right].get(function, set())
                similarities[function] = _round(
                    len(a & b) / max(1, len(a | b))
                )
            overall = _round(
                sum(similarities.values()) / max(1, len(similarities))
            )
            pairs.append(
                {
                    "left": compositions[left].title,
                    "right": compositions[right].title,
                    "similarity": overall,
                    "too_similar": overall >= 0.82,
                    "function_similarity": similarities,
                }
            )
    return {
        "candidates": [item.title for item in compositions],
        "distinct": not any(item["too_similar"] for item in pairs),
        "pairs": pairs,
    }
