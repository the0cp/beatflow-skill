# SPDX-License-Identifier: GPL-3.0-only
"""Style-neutral diagnostics and candidate comparison for Composition 1.1."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import pairwise
from statistics import median
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
        for previous, current in pairwise(ordered):
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
    off_tactus = [
        event
        for event in pitched
        if not profile.is_tactus(event.onset.fraction)
    ]
    off_tactus_bridges = [
        event
        for event in off_tactus
        if event.onset.fraction + event.duration.fraction
        > ((event.onset.fraction // profile.tactus) + 1) * profile.tactus
    ]

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
        "off_tactus_attacks": len(off_tactus),
        "off_tactus_bridge_attacks": len(off_tactus_bridges),
        "off_tactus_bridge_ratio": _round(
            len(off_tactus_bridges) / max(1, len(off_tactus))
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


def _merge_spans(
    spans: list[tuple[Fraction, Fraction]],
) -> list[tuple[Fraction, Fraction]]:
    if not spans:
        return []
    merged: list[tuple[Fraction, Fraction]] = []
    ordered = sorted(spans)
    current_start, current_end = ordered[0]
    for start, end in ordered[1:]:
        if start <= current_end:
            current_end = max(current_end, end)
        else:
            merged.append((current_start, current_end))
            current_start, current_end = start, end
    merged.append((current_start, current_end))
    return merged


def _section_silence_metrics(
    composition: Composition,
    section,
) -> dict[str, Any]:
    section_length = composition.beats_per_bar_fraction * section.length_bars
    pitched_spans = [
        (
            event.onset.fraction,
            event.onset.fraction + event.duration.fraction,
        )
        for segment in section.segments
        if segment.default_enabled
        for event in segment.events
        if isinstance(event, (PitchedEvent, ChordEvent))
    ]
    merged = _merge_spans(pitched_spans)
    gaps: list[tuple[Fraction, Fraction]] = []
    cursor = Fraction(0)
    for start, end in merged:
        if start > cursor:
            gaps.append((cursor, start))
        cursor = max(cursor, end)
    if cursor < section_length:
        gaps.append((cursor, section_length))
    durations = [end - start for start, end in gaps]
    total = sum(durations, Fraction(0))
    return {
        "pitched_events": len(pitched_spans),
        "total_silence_beats": _round(float(total)),
        "silence_ratio": _round(float(total / section_length)),
        "longest_silence_beats": _round(
            float(max(durations, default=Fraction(0)))
        ),
        "gaps_ge_tactus": sum(
            duration >= meter_profile(composition.time_signature).tactus
            for duration in durations
        ),
        "gaps": [
            {
                "onset": _fraction_text(start),
                "duration": _fraction_text(end - start),
            }
            for start, end in gaps
        ],
    }


def _section_attack_density(
    composition: Composition,
    section,
) -> dict[str, Any]:
    measure = composition.beats_per_bar_fraction
    per_bar = [0 for _ in range(section.length_bars)]
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        for event in segment.events:
            if not isinstance(event, (PitchedEvent, ChordEvent)):
                continue
            bar = int(event.onset.fraction // measure)
            if 0 <= bar < section.length_bars:
                per_bar[bar] += 1
    adjacent = [
        abs(current - previous)
        for previous, current in pairwise(per_bar)
    ]
    largest_index = (
        adjacent.index(max(adjacent)) + 1
        if adjacent
        else 0
    )
    return {
        "per_bar": per_bar,
        "mean": _round(sum(per_bar) / max(1, len(per_bar))),
        "minimum": min(per_bar, default=0),
        "maximum": max(per_bar, default=0),
        "largest_adjacent_change": max(adjacent, default=0),
        "largest_change_after_bar": largest_index,
    }


def _declared_silence_metrics(section, silence) -> dict[str, Any]:
    silence_start = silence.onset.fraction
    silence_end = silence_start + silence.duration.fraction
    overlaps: list[dict[str, Any]] = []
    selected_functions = set(silence.functions)
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        if selected_functions and selected_functions.isdisjoint(segment.functions):
            continue
        for event in segment.events:
            event_start = event.onset.fraction
            event_end = event_start + event.duration.fraction
            if event_start < silence_end and event_end > silence_start:
                overlaps.append(
                    {
                        "segment_id": segment.id,
                        "event_type": event.type,
                        "onset": _fraction_text(event_start),
                        "duration": _fraction_text(event.duration.fraction),
                    }
                )
    return {
        "onset": _fraction_text(silence_start),
        "duration": _fraction_text(silence.duration.fraction),
        "functions": list(silence.functions),
        "overlapping_events": len(overlaps),
        "overlaps": overlaps[:12],
    }


def _phrase_events(section, phrase) -> list[tuple[str, PitchedEvent | ChordEvent]]:
    """Return enabled pitched events belonging to the phrase's selected roles."""

    selected_functions = set(phrase.functions)
    result: list[tuple[str, PitchedEvent | ChordEvent]] = []
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        if selected_functions and selected_functions.isdisjoint(segment.functions):
            continue
        for event in segment.events:
            if isinstance(event, (PitchedEvent, ChordEvent)):
                result.append((segment.id, event))
    return result


def _continuous_span_lengths(
    spans: list[tuple[Fraction, Fraction]],
    separation: Fraction,
) -> list[Fraction]:
    """Return sounding-run lengths separated by at least the given gap."""

    merged = _merge_spans(spans)
    if not merged:
        return []
    run_start, run_end = merged[0]
    lengths: list[Fraction] = []
    for start, end in merged[1:]:
        if start - run_end >= separation:
            lengths.append(run_end - run_start)
            run_start, run_end = start, end
        else:
            run_end = max(run_end, end)
    lengths.append(run_end - run_start)
    return lengths


def _phrase_metrics(
    section,
    phrase,
    profile: MeterProfile,
) -> dict[str, Any]:
    """Measure phrase continuity and multi-cue evidence at its end."""

    phrase_start = phrase.onset.fraction
    phrase_end = phrase_start + phrase.duration.fraction
    selected = _phrase_events(section, phrase)
    attacks = [
        event
        for _, event in selected
        if phrase_start <= event.onset.fraction < phrase_end
    ]
    spans = [
        (
            max(phrase_start, event.onset.fraction),
            min(
                phrase_end,
                event.onset.fraction + event.duration.fraction,
            ),
        )
        for _, event in selected
        if event.onset.fraction < phrase_end
        and event.onset.fraction + event.duration.fraction > phrase_start
    ]
    spans = [(start, end) for start, end in spans if end > start]

    third = phrase.duration.fraction / 3
    density: list[float] = []
    for index in range(3):
        window_start = phrase_start + third * index
        window_end = (
            phrase_end
            if index == 2
            else phrase_start + third * (index + 1)
        )
        count = sum(
            window_start <= event.onset.fraction < window_end
            for event in attacks
        )
        density.append(_round(count / max(float(window_end - window_start), 1e-9)))

    final_candidates = [
        event
        for _, event in selected
        if phrase_start <= event.onset.fraction < phrase_end
    ]
    final_event = (
        max(final_candidates, key=lambda event: event.onset.fraction)
        if final_candidates
        else None
    )
    durations = [float(event.duration.fraction) for event in attacks]
    median_duration = median(durations) if durations else 0.0
    final_duration = (
        float(
            min(
                final_event.duration.fraction,
                phrase_end - final_event.onset.fraction,
            )
        )
        if final_event is not None
        else 0.0
    )
    lengthening_ratio = (
        final_duration / median_duration
        if median_duration > 0
        else 0.0
    )

    previous_offsets = [
        event.onset.fraction + event.duration.fraction
        for _, event in selected
        if event.onset.fraction < phrase_end
    ]
    previous_offset = max(previous_offsets, default=phrase_start)
    next_onsets = [
        event.onset.fraction
        for _, event in selected
        if event.onset.fraction >= phrase_end
    ]
    next_onset = min(next_onsets, default=phrase_end)
    if previous_offset >= phrase_end:
        boundary_gap = Fraction(0)
    else:
        boundary_gap = max(
            Fraction(0),
            next_onset - previous_offset,
        )

    prior_start = max(phrase_start, phrase_end - profile.tactus * 2)
    terminal_start = max(phrase_start, phrase_end - profile.tactus)
    prior_attacks = sum(
        prior_start <= event.onset.fraction < terminal_start
        for event in attacks
    )
    terminal_attacks = sum(
        terminal_start <= event.onset.fraction < phrase_end
        for event in attacks
    )
    density_release = max(
        0.0,
        1.0 - terminal_attacks / max(1, prior_attacks),
    )
    gap_score = min(1.0, float(boundary_gap / (profile.tactus * 2)))
    lengthening_score = min(
        1.0,
        max(0.0, (lengthening_ratio - 1.0) / 1.5),
    )
    boundary_evidence = (
        (
            0.5 * gap_score
            + 0.3 * lengthening_score
            + 0.2 * density_release
        )
        if attacks
        else 0.0
    )
    continuous_spans = _continuous_span_lengths(
        spans,
        profile.tactus,
    )
    longest_continuous = max(continuous_spans, default=Fraction(0))
    tactus_windows = math.ceil(
        float(phrase.duration.fraction / profile.tactus)
    )
    tactus_activity: list[bool] = []
    tactus_attack_counts: list[int] = []
    for index in range(tactus_windows):
        window_start = phrase_start + profile.tactus * index
        window_end = min(phrase_end, window_start + profile.tactus)
        tactus_activity.append(
            any(
                start < window_end and end > window_start
                for start, end in spans
            )
        )
        tactus_attack_counts.append(
            sum(
                window_start <= event.onset.fraction < window_end
                for event in attacks
            )
        )
    activity_runs: list[int] = []
    current_run = 0
    for active in tactus_activity:
        if active:
            current_run += 1
        elif current_run:
            activity_runs.append(current_run)
            current_run = 0
    if current_run:
        activity_runs.append(current_run)
    subphrase_boundary_tactus: list[int] = []
    cursor = 0
    for bars in phrase.subphrase_bars[:-1]:
        cursor += bars * profile.pulses_per_bar
        subphrase_boundary_tactus.append(cursor)

    return {
        "onset": _fraction_text(phrase_start),
        "duration": _fraction_text(phrase.duration.fraction),
        "functions": list(phrase.functions),
        "attention": phrase.attention,
        "goal": phrase.goal,
        "attacks": len(attacks),
        "grouping": phrase.grouping,
        "subphrase_bars": list(phrase.subphrase_bars),
        "duration_bars": _round(
            float(phrase.duration.fraction / profile.measure)
        ),
        "duration_tactus": _round(
            float(phrase.duration.fraction / profile.tactus)
        ),
        "subphrase_boundary_tactus": subphrase_boundary_tactus,
        "tactus_activity_pattern": "".join(
            "1" if active else "0"
            for active in tactus_activity
        ),
        "tactus_attack_counts": tactus_attack_counts,
        "active_tactus_runs": activity_runs,
        "full_tactus_rest_positions": [
            index + 1
            for index, active in enumerate(tactus_activity)
            if not active
        ],
        "continuous_spans_tactus": [
            _round(float(value / profile.tactus))
            for value in continuous_spans
        ],
        "attack_density_per_beat": {
            "start": density[0],
            "middle": density[1],
            "end": density[2],
        },
        "intended_tension": (
            phrase.tension.model_dump(mode="json")
            if phrase.tension is not None
            else None
        ),
        "intended_boundary_strength": phrase.boundary_strength,
        "boundary_evidence": _round(boundary_evidence),
        "boundary_gap_beats": _round(float(boundary_gap)),
        "final_note_duration_beats": _round(final_duration),
        "median_note_duration_beats": _round(median_duration),
        "final_lengthening_ratio": _round(lengthening_ratio),
        "preterminal_attacks": prior_attacks,
        "terminal_attacks": terminal_attacks,
        "longest_continuous_beats": _round(float(longest_continuous)),
        "continuous_spans_beats": [
            _round(float(value))
            for value in continuous_spans
        ],
        "max_continuous_beats": (
            _round(float(phrase.max_continuous_beats.fraction))
            if phrase.max_continuous_beats is not None
            else None
        ),
    }


def _phrase_stage_metrics(
    section,
    stage,
    phrase,
    profile: MeterProfile,
) -> dict[str, Any]:
    """Measure the realized pacing and emphasis of one phrase stage."""

    selected_functions = set(stage.functions or phrase.functions)
    phrase_start = phrase.onset.fraction
    phrase_end = phrase_start + phrase.duration.fraction
    stage_start = stage.onset.fraction
    stage_end = stage_start + stage.duration.fraction
    selected_events: list[PitchedEvent | ChordEvent] = []
    events: list[PitchedEvent | ChordEvent] = []
    event_groups: list[list[PitchedEvent | ChordEvent]] = []
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        if selected_functions and selected_functions.isdisjoint(segment.functions):
            continue
        group: list[PitchedEvent | ChordEvent] = []
        for event in segment.events:
            if not isinstance(event, (PitchedEvent, ChordEvent)):
                continue
            if (
                event.onset.fraction < phrase_end
                and event.onset.fraction + event.duration.fraction
                > phrase_start
            ):
                selected_events.append(event)
            if stage_start <= event.onset.fraction < stage_end:
                events.append(event)
                group.append(event)
        if group:
            event_groups.append(
                sorted(group, key=lambda event: event.onset.fraction)
            )

    durations = [
        min(event.duration.fraction, stage_end - event.onset.fraction)
        for event in events
    ]
    saliences = [
        max(event.importance, event.accent)
        if isinstance(event, PitchedEvent)
        else event.accent
        for event in events
    ]
    previous_offsets = [
        min(
            phrase_end,
            event.onset.fraction + event.duration.fraction,
        )
        for event in selected_events
        if event.onset.fraction < stage_end
        and event.onset.fraction + event.duration.fraction > stage_start
    ]
    next_onsets = [
        event.onset.fraction
        for event in selected_events
        if stage_end <= event.onset.fraction < phrase_end
    ]
    previous_offset = max(previous_offsets, default=None)
    next_onset = min(next_onsets, default=phrase_end)
    exit_gap = (
        max(Fraction(0), next_onset - previous_offset)
        if previous_offset is not None
        else None
    )
    internal_gaps: list[Fraction] = []
    gate_ratios: list[float] = []
    for group in event_groups:
        for left, right in pairwise(group):
            inter_onset = right.onset.fraction - left.onset.fraction
            if inter_onset <= 0:
                continue
            internal_gaps.append(
                right.onset.fraction
                - (left.onset.fraction + left.duration.fraction)
            )
            gate_ratios.append(float(left.duration.fraction / inter_onset))
    connected_pairs = sum(gap <= 0 for gap in internal_gaps)
    connected_ratio = connected_pairs / max(1, len(internal_gaps))
    micro_gap_pairs = sum(
        Fraction(0) < gap < profile.tactus for gap in internal_gaps
    )
    duration_values = sorted({_fraction_text(value) for value in durations})
    sounding_spans = [
        (
            max(stage_start, event.onset.fraction),
            min(
                stage_end,
                event.onset.fraction + event.duration.fraction,
            ),
        )
        for event in events
        if event.onset.fraction < stage_end
        and event.onset.fraction + event.duration.fraction > stage_start
    ]
    gesture_spans = _continuous_span_lengths(
        [
            (start, end)
            for start, end in sounding_spans
            if end > start
        ],
        profile.division,
    )
    polyphonic_attacks = sum(
        isinstance(event, ChordEvent) and event.notes > 1
        for event in events
    )
    attack_onsets = sorted({event.onset.fraction for event in events})
    tactus_attacks = sum(profile.is_tactus(onset) for onset in attack_onsets)
    off_tactus_events = [
        event
        for event in events
        if not profile.is_tactus(event.onset.fraction)
    ]
    off_tactus_bridges = [
        event
        for event in off_tactus_events
        if event.onset.fraction + event.duration.fraction
        > ((event.onset.fraction // profile.tactus) + 1) * profile.tactus
    ]
    first_attack = min(attack_onsets, default=None)
    entry_anchor_met = (
        True
        if stage.entry_anchor == "free"
        else (
            first_attack is not None
            and (
                (
                    stage.entry_anchor == "division"
                    and first_attack % profile.division == 0
                )
                or (
                    stage.entry_anchor == "tactus"
                    and profile.is_tactus(first_attack)
                )
                or (
                    stage.entry_anchor == "bar_downbeat"
                    and profile.is_bar_downbeat(first_attack)
                )
            )
        )
    )
    return {
        "phrase_id": phrase.id,
        "onset": _fraction_text(stage_start),
        "duration": _fraction_text(stage.duration.fraction),
        "functions": list(stage.functions),
        "role": stage.role,
        "goal": stage.goal,
        "attacks": len(events),
        "min_attacks": stage.min_attacks,
        "max_attacks": stage.max_attacks,
        "transition_pairs": len(internal_gaps),
        "connected_pairs": connected_pairs,
        "connected_pair_ratio": _round(connected_ratio),
        "min_connected_ratio": stage.min_connected_ratio,
        "gesture_count": len(gesture_spans),
        "gesture_spans_beats": [
            _round(float(value))
            for value in gesture_spans
        ],
        "longest_gesture_beats": _round(
            float(max(gesture_spans, default=Fraction(0)))
        ),
        "max_gesture_beats": (
            _round(float(stage.max_gesture_beats.fraction))
            if stage.max_gesture_beats is not None
            else None
        ),
        "single_note_attacks": len(events) - polyphonic_attacks,
        "polyphonic_attacks": polyphonic_attacks,
        "polyphonic_attack_ratio": _round(
            polyphonic_attacks / max(1, len(events))
        ),
        "min_polyphonic_attacks": stage.min_polyphonic_attacks,
        "max_polyphonic_attacks": stage.max_polyphonic_attacks,
        "metric_role": stage.metric_role,
        "entry_anchor": stage.entry_anchor,
        "entry_anchor_met": entry_anchor_met,
        "first_attack_onset": (
            _fraction_text(first_attack) if first_attack is not None else None
        ),
        "first_attack_metric_position": (
            profile.position(first_attack) if first_attack is not None else None
        ),
        "metric_attacks": len(attack_onsets),
        "tactus_attacks": tactus_attacks,
        "tactus_attack_ratio": _round(
            tactus_attacks / max(1, len(attack_onsets))
        ),
        "min_tactus_attack_ratio": stage.min_tactus_attack_ratio,
        "off_tactus_attacks": len(off_tactus_events),
        "off_tactus_bridge_attacks": len(off_tactus_bridges),
        "off_tactus_bridge_ratio": _round(
            len(off_tactus_bridges) / max(1, len(off_tactus_events))
        ),
        "max_off_tactus_bridge_ratio": stage.max_off_tactus_bridge_ratio,
        "micro_gap_pairs": micro_gap_pairs,
        "median_gate_ratio": _round(
            float(median(gate_ratios)) if gate_ratios else 0.0
        ),
        "exit_behavior": stage.exit_behavior,
        "exit_gap_beats": (
            _round(float(exit_gap)) if exit_gap is not None else None
        ),
        "tactus_beats": _round(float(profile.tactus)),
        "attack_density_per_beat": _round(
            len(events) / float(stage.duration.fraction)
        ),
        "duration_vocabulary": duration_values,
        "duration_vocabulary_size": len(duration_values),
        "maximum_duration_beats": _round(
            float(max(durations, default=Fraction(0)))
        ),
        "median_duration_beats": _round(
            float(median(durations)) if durations else 0.0
        ),
        "maximum_salience": _round(max(saliences, default=0.0)),
        "mean_salience": _round(
            sum(saliences) / len(saliences) if saliences else 0.0
        ),
        "focus": stage.focus,
        "focus_cue": stage.focus_cue,
    }


def _arrival_events(
    section,
    arrival,
    phrase,
) -> list[tuple[str, PitchedEvent | ChordEvent]]:
    """Return enabled pitched events selected by an arrival or its phrase."""

    selected_functions = set(arrival.functions or phrase.functions)
    result: list[tuple[str, PitchedEvent | ChordEvent]] = []
    for segment in section.segments:
        if not segment.default_enabled:
            continue
        if selected_functions and selected_functions.isdisjoint(segment.functions):
            continue
        for event in segment.events:
            if isinstance(event, (PitchedEvent, ChordEvent)):
                result.append((segment.id, event))
    return result


def _event_harmonic_stability(
    section,
    event: PitchedEvent | ChordEvent,
    arrival_onset: Fraction,
) -> bool | None:
    """Return whether one observable arrival event is supported by harmony."""

    arrival_pitch_classes = _active_chord_pitch_classes(
        section.harmony,
        arrival_onset,
    )
    if not arrival_pitch_classes:
        return None

    if isinstance(event, ChordEvent):
        if event.onset.fraction != arrival_onset:
            return None
        target = event.top_target
        if target is None:
            return True
    else:
        target = event.target

    if target.basis == "absolute":
        return target.midi % 12 in arrival_pitch_classes
    if (
        target.basis in {"chord", "chord_index"}
        and target.alter == 0
        and event.onset.fraction == arrival_onset
    ):
        return True
    return None


def _arrival_metrics(section, arrival, phrase) -> dict[str, Any]:
    """Measure whether a declared local completion is actually articulated."""

    arrival_onset = arrival.onset.fraction
    phrase_end = phrase.onset.fraction + phrase.duration.fraction
    selected = _arrival_events(section, arrival, phrase)
    sounding = [
        event
        for _, event in selected
        if event.onset.fraction <= arrival_onset
        < event.onset.fraction + event.duration.fraction
    ]
    attacks = [
        event
        for _, event in selected
        if event.onset.fraction == arrival_onset
    ]
    post_attacks = [
        event
        for _, event in selected
        if arrival_onset < event.onset.fraction < phrase_end
    ]
    holds = [
        min(
            phrase_end,
            event.onset.fraction + event.duration.fraction,
        )
        - arrival_onset
        for event in sounding
    ]
    stability = [
        _event_harmonic_stability(section, event, arrival_onset)
        for event in sounding
    ]
    observed = [value for value in stability if value is not None]
    stable = sum(value is True for value in observed)
    unknown = len(stability) - len(observed)

    return {
        "phrase_id": phrase.id,
        "onset": _fraction_text(arrival_onset),
        "functions": list(arrival.functions or phrase.functions),
        "closure": arrival.closure,
        "strength": arrival.strength,
        "goal": arrival.goal,
        "sounding_events": len(sounding),
        "attacks_at_arrival": len(attacks),
        "anchor_hold_beats": _round(float(max(holds, default=Fraction(0)))),
        "minimum_hold_beats": (
            _round(float(arrival.min_hold.fraction))
            if arrival.min_hold is not None
            else None
        ),
        "post_action": arrival.post_action,
        "post_attacks": len(post_attacks),
        "max_post_attacks": arrival.max_post_attacks,
        "harmonic_stability": arrival.harmonic_stability,
        "harmonic_observations": len(observed),
        "harmonically_supported_observations": stable,
        "harmonic_unknowns": unknown,
        "harmonic_support_ratio": (
            _round(stable / len(observed))
            if observed
            else None
        ),
    }


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
        silence = _section_silence_metrics(composition, section)
        density = _section_attack_density(composition, section)
        declared_silences = {
            intent.id: _declared_silence_metrics(section, intent)
            for intent in section.silences
        }
        phrases = {
            intent.id: _phrase_metrics(section, intent, profile)
            for intent in section.phrases
        }
        phrases_by_id = {intent.id: intent for intent in section.phrases}
        phrase_stages = {
            intent.id: _phrase_stage_metrics(
                section,
                intent,
                phrases_by_id[intent.phrase_id],
                profile,
            )
            for intent in section.phrase_stages
        }
        arrivals = {
            intent.id: _arrival_metrics(
                section,
                intent,
                phrases_by_id[intent.phrase_id],
            )
            for intent in section.arrivals
        }
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
            "pitched_texture_silence": silence,
            "pitched_attack_density": density,
            "phrases": phrases,
            "phrase_stages": phrase_stages,
            "arrivals": arrivals,
            "declared_silences": declared_silences,
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
            and silence["pitched_events"] >= section.length_bars * 4
            and silence["silence_ratio"] < 0.08
            and silence["longest_silence_beats"] < float(profile.tactus)
        ):
            add(
                "warning",
                "phrasing",
                "continuous_pitched_texture",
                (
                    f"Pitched roles in section '{section.id}' leave no "
                    "tactus-sized shared release."
                ),
                silence,
                (
                    "Keep this for an intentional motor texture; otherwise "
                    "create a shared release, handoff, or thinner phrase ending."
                ),
            )
        if (
            section.length_bars >= 4
            and density["mean"] >= 4
            and density["largest_adjacent_change"]
            >= max(6, density["mean"] * 0.75)
        ):
            add(
                "info",
                "phrasing",
                "abrupt_pitched_density_change",
                (
                    f"Pitched attack density changes abruptly inside "
                    f"section '{section.id}'."
                ),
                density,
                (
                    "Confirm that the change marks a planned formal event; "
                    "otherwise shape the transition across more than one bar."
                ),
            )
        for intent in section.silences:
            intent_metrics = declared_silences[intent.id]
            if intent_metrics["overlapping_events"]:
                add(
                    "warning",
                    "intent",
                    "declared_silence_occupied",
                    (
                        f"Silence '{intent.id}' in section '{section.id}' "
                        "contains active events."
                    ),
                    intent_metrics,
                    (
                        intent.description
                        or "Shorten the sustaining event or move attacks outside the window."
                    ),
                )
        for intent in section.phrases:
            intent_metrics = phrases[intent.id]
            if not intent_metrics["attacks"]:
                add(
                    "warning",
                    "phrasing",
                    "empty_declared_phrase",
                    (
                        f"Phrase '{intent.id}' in section '{section.id}' "
                        "contains no selected pitched attacks."
                    ),
                    intent_metrics,
                    (
                        "Move the phrase onto active material, select the "
                        "intended functions, or remove the empty declaration."
                    ),
                )
            elif (
                intent_metrics["boundary_evidence"] + 0.15
                < intent.boundary_strength
            ):
                add(
                    "warning",
                    "phrasing",
                    "weak_declared_phrase_boundary",
                    (
                        f"Phrase '{intent.id}' in section '{section.id}' "
                        "does not provide enough audible evidence for its "
                        "declared boundary strength."
                    ),
                    intent_metrics,
                    (
                        "Combine a real gap or voice handoff with pre-boundary "
                        "lengthening, reduced attack density, contour closure, "
                        "or harmonic arrival. Do not rely on a token micro-rest."
                    ),
                )
            if (
                intent.max_continuous_beats is not None
                and intent_metrics["longest_continuous_beats"]
                > float(intent.max_continuous_beats.fraction) + 1e-4
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_continuity_exceeds_declared_limit",
                    (
                        f"Phrase '{intent.id}' in section '{section.id}' "
                        "continues longer than its declared activity limit "
                        "without a tactus-sized release."
                    ),
                    intent_metrics,
                    (
                        "Create a perceivable release inside the phrase, thin "
                        "to one voice, or shorten the continuous gesture."
                    ),
                )
            continuous_spans = intent_metrics["continuous_spans_beats"]
            if (
                intent.duration.fraction >= profile.tactus * 8
                and len(continuous_spans) >= 2
                and min(continuous_spans) >= float(profile.tactus * 4)
                and max(continuous_spans) - min(continuous_spans)
                <= float(profile.tactus)
            ):
                add(
                    "warning",
                    "phrasing",
                    "uniform_long_phrase_gestures",
                    (
                        f"Phrase '{intent.id}' in section '{section.id}' "
                        "is divided only into similarly long continuous "
                        "foreground gestures."
                    ),
                    intent_metrics,
                    (
                        "Keep the long sentence when it has a clear job, but "
                        "contrast it with at least one shorter complete "
                        "gesture or a genuinely denser instrumental burst."
                    ),
                )
            if (
                intent.tension is not None
                and intent.tension.peak - intent.tension.end >= 0.2
                and intent_metrics["attack_density_per_beat"]["end"]
                >= intent_metrics["attack_density_per_beat"]["middle"] * 0.9
                and intent_metrics["boundary_evidence"] < 0.45
            ):
                add(
                    "info",
                    "phrasing",
                    "phrase_release_not_reflected_in_density",
                    (
                        f"Phrase '{intent.id}' in section '{section.id}' "
                        "declares a tension release, but attack density and "
                        "boundary cues do not make the release obvious."
                    ),
                    intent_metrics,
                    (
                        "Confirm that harmony, register, or dynamics supply "
                        "the release; otherwise thin and lengthen the ending."
                    ),
                )
            if intent.grouping == "regular":
                pattern = intent_metrics["tactus_activity_pattern"]
                boundaries = set(
                    intent_metrics["subphrase_boundary_tactus"]
                )
                resumed_at = [
                    index
                    for index in range(1, len(pattern))
                    if pattern[index - 1] == "0"
                    and pattern[index] == "1"
                ]
                unplanned = [
                    index
                    for index in resumed_at
                    if index not in boundaries
                ]
                if unplanned:
                    add(
                        "warning",
                        "phrasing",
                        "unplanned_hypermetric_split",
                        (
                            f"Regular phrase '{intent.id}' in section "
                            f"'{section.id}' resumes after a full tactus rest "
                            "away from its declared subphrase boundary."
                        ),
                        {
                            **intent_metrics,
                            "unplanned_resume_tactus": [
                                index + 1 for index in unplanned
                            ],
                        },
                        (
                            "Move the structural restart to a declared "
                            "subphrase boundary, shorten the internal pause, "
                            "or declare an irregular grouping."
                        ),
                    )
        subtractive_patterns: defaultdict[str, list[str]] = defaultdict(list)
        for intent in section.phrases:
            intent_metrics = phrases[intent.id]
            pattern = intent_metrics["tactus_activity_pattern"]
            if (
                intent.grouping == "regular"
                and pattern.count("0") == 1
                and pattern.startswith("1")
                and pattern.endswith("1")
            ):
                subtractive_patterns[pattern].append(intent.id)
        for pattern, phrase_ids in subtractive_patterns.items():
            if len(phrase_ids) < 2:
                continue
            add(
                "warning",
                "phrasing",
                "repeated_subtractive_phrase_activity",
                (
                    f"Section '{section.id}' repeats the same one-tactus "
                    "hole across multiple regular phrases."
                ),
                {
                    "phrase_ids": phrase_ids,
                    "tactus_activity_pattern": pattern,
                },
                (
                    "Do not create phrase variety by repeatedly subtracting "
                    "one beat from a regular frame. Keep the hypermeter and "
                    "vary density, contour, harmony, register, or texture."
                ),
            )
        stages_by_phrase: defaultdict[str, list[Any]] = defaultdict(list)
        for intent in section.phrase_stages:
            intent_metrics = phrase_stages[intent.id]
            stages_by_phrase[intent.phrase_id].append(intent)
            if not (
                intent.min_attacks
                <= intent_metrics["attacks"]
                <= intent.max_attacks
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_stage_attack_budget_missed",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' contains "
                        f"{intent_metrics['attacks']} attacks, outside its "
                        f"declared {intent.min_attacks}–{intent.max_attacks} "
                        "budget."
                    ),
                    intent_metrics,
                    (
                        "Revise the attacks or stage plan. Contrast density "
                        "when it serves the phrase without forcing unequal "
                        "metrical spans."
                    ),
                )
            if (
                intent.min_connected_ratio is not None
                and intent_metrics["transition_pairs"]
                and intent_metrics["connected_pair_ratio"]
                < intent.min_connected_ratio
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_stage_internal_connection_missed",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' connects "
                        f"{intent_metrics['connected_pair_ratio']:.0%} of "
                        "its adjacent event pairs, below its declared "
                        f"{intent.min_connected_ratio:.0%} minimum."
                    ),
                    intent_metrics,
                    (
                        "Join notes inside the intended gesture and place "
                        "separation at a deliberate group boundary instead "
                        "of after nearly every attack."
                    ),
                )
            if (
                intent.max_gesture_beats is not None
                and intent_metrics["longest_gesture_beats"]
                > float(intent.max_gesture_beats.fraction) + 1e-4
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_stage_gesture_span_exceeded",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' contains a "
                        f"{intent_metrics['longest_gesture_beats']:g}-beat "
                        "gesture, above its declared "
                        f"{float(intent.max_gesture_beats.fraction):g}-beat "
                        "maximum."
                    ),
                    intent_metrics,
                    (
                        "End a locally complete short gesture sooner, leave "
                        "a deliberate division-sized separation, or raise "
                        "the limit when this stage intentionally carries the "
                        "long sentence."
                    ),
                )
            if not (
                intent.min_polyphonic_attacks
                <= intent_metrics["polyphonic_attacks"]
                <= intent.max_polyphonic_attacks
            ):
                add(
                    "warning",
                    "texture",
                    "phrase_stage_polyphonic_attack_budget_missed",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' contains "
                        f"{intent_metrics['polyphonic_attacks']} polyphonic "
                        "attacks, outside its declared "
                        f"{intent.min_polyphonic_attacks}–"
                        f"{intent.max_polyphonic_attacks} budget."
                    ),
                    intent_metrics,
                    (
                        "Use selected dyads or chordal punctuation when the "
                        "foreground texture calls for them; keep the budget "
                        "at zero for a deliberately monophonic line."
                    ),
                )
            if (
                intent.entry_anchor != "free"
                and not intent_metrics["entry_anchor_met"]
            ):
                add(
                    "warning",
                    "rhythm",
                    "phrase_stage_entry_anchor_missed",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' first attacks at "
                        f"{intent_metrics['first_attack_onset']}, outside its "
                        f"declared {intent.entry_anchor} entry anchor."
                    ),
                    intent_metrics,
                    (
                        "Move the first structural attack to the declared "
                        "anchor, or explicitly plan a pickup and leave the "
                        "entry free."
                    ),
                )
            if (
                intent.min_tactus_attack_ratio is not None
                and intent_metrics["metric_attacks"]
                and intent_metrics["tactus_attack_ratio"]
                < intent.min_tactus_attack_ratio
            ):
                add(
                    "warning",
                    "rhythm",
                    "phrase_stage_tactus_alignment_missed",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' places "
                        f"{intent_metrics['tactus_attack_ratio']:.0%} of its "
                        "unique attacks on the tactus, below its declared "
                        f"{intent.min_tactus_attack_ratio:.0%} minimum."
                    ),
                    intent_metrics,
                    (
                        "Keep subdivisions and pickups that have a clear "
                        "function, but return structural attacks to the "
                        "shared perceptual beat."
                    ),
                )
            if (
                intent.max_off_tactus_bridge_ratio is not None
                and intent_metrics["off_tactus_attacks"]
                and intent_metrics["off_tactus_bridge_ratio"]
                > intent.max_off_tactus_bridge_ratio
            ):
                add(
                    "warning",
                    "rhythm",
                    "phrase_stage_displaced_holds_exceeded",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' carries "
                        f"{intent_metrics['off_tactus_bridge_ratio']:.0%} of "
                        "its off-tactus attacks across the following tactus, "
                        "above its declared "
                        f"{intent.max_off_tactus_bridge_ratio:.0%} maximum."
                    ),
                    intent_metrics,
                    (
                        "Keep selected suspensions or anticipations, but "
                        "shorten, resolve, or metrically anchor enough of the "
                        "other displaced holds to preserve one shared clock."
                    ),
                )
            exit_gap = intent_metrics["exit_gap_beats"]
            tactus = intent_metrics["tactus_beats"]
            if (
                intent.exit_behavior == "continue"
                and exit_gap is not None
                and exit_gap >= tactus
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_stage_continuation_interrupted",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' declares continuation, but its "
                        f"selected line leaves a {exit_gap:g}-beat gap at "
                        "the stage exit."
                    ),
                    intent_metrics,
                    (
                        "Connect or sustain the idea across the stage exit, "
                        "or declare a breath only after a locally complete "
                        "gesture."
                    ),
                )
            elif (
                intent.exit_behavior == "breathe"
                and exit_gap is not None
                and exit_gap < tactus
            ):
                add(
                    "warning",
                    "phrasing",
                    "phrase_stage_breath_missing",
                    (
                        f"Phrase stage '{intent.id}' in section "
                        f"'{section.id}' declares a breath, but its "
                        f"{exit_gap:g}-beat exit gap is shorter than one "
                        "perceptual beat."
                    ),
                    intent_metrics,
                    (
                        "Make the breath perceptible, or relabel this exit "
                        "as continuation or arrival."
                    ),
                )
        for phrase in section.phrases:
            if phrase.grouping == "free":
                continue
            declared_boundaries = [phrase.onset.fraction]
            cursor = phrase.onset.fraction
            for bars in phrase.subphrase_bars[:-1]:
                cursor += bars * profile.measure
                declared_boundaries.append(cursor)
            structural_onsets = {
                stage.onset.fraction
                for stage in stages_by_phrase[phrase.id]
                if stage.metric_role == "structural"
            }
            missing = [
                onset
                for onset in declared_boundaries
                if onset not in structural_onsets
            ]
            if missing and stages_by_phrase[phrase.id]:
                add(
                    "warning",
                    "phrasing",
                    "missing_structural_subphrase_entry",
                    (
                        f"Grouped phrase '{phrase.id}' in section "
                        f"'{section.id}' has no structural phrase-stage "
                        "entry at every declared subphrase boundary."
                    ),
                    {
                        **phrases[phrase.id],
                        "missing_boundary_onsets": [
                            _fraction_text(value) for value in missing
                        ],
                    },
                    (
                        "Mark the stage that owns each structural boundary, "
                        "or remove phrase stages when grouping is carried by "
                        "another explicitly documented layer."
                    ),
                )
        focus_fields = {
            "salience": ("maximum_salience", 0.05),
            "density": ("attack_density_per_beat", 0.15),
            "duration": ("maximum_duration_beats", 0.25),
        }
        for phrase_id, stage_intents in stages_by_phrase.items():
            if len(stage_intents) < 2:
                continue
            focus_intent = next(
                (intent for intent in stage_intents if intent.focus),
                None,
            )
            if focus_intent is None or focus_intent.focus_cue is None:
                continue
            field, margin = focus_fields[focus_intent.focus_cue]
            focus_metrics = phrase_stages[focus_intent.id]
            other_values = {
                intent.id: phrase_stages[intent.id][field]
                for intent in stage_intents
                if intent.id != focus_intent.id
            }
            reference = max(other_values.values(), default=0.0)
            if focus_metrics[field] < reference + margin:
                add(
                    "warning",
                    "phrasing",
                    "phrase_focus_not_realized",
                    (
                        f"Focus stage '{focus_intent.id}' in phrase "
                        f"'{phrase_id}' does not exceed the other stages "
                        f"through its declared {focus_intent.focus_cue} cue."
                    ),
                    {
                        **focus_metrics,
                        "comparison_field": field,
                        "required_margin": margin,
                        "other_stage_values": other_values,
                    },
                    (
                        "Make the intended focus perceptually distinct, or "
                        "choose the cue that actually carries the phrase's "
                        "emphasis."
                    ),
                )
        for intent in section.arrivals:
            intent_metrics = arrivals[intent.id]
            if not intent_metrics["sounding_events"]:
                add(
                    "warning",
                    "phrasing",
                    "arrival_missing",
                    (
                        f"Arrival '{intent.id}' in section '{section.id}' "
                        "has no selected pitched event sounding at its "
                        "declared completion point."
                    ),
                    intent_metrics,
                    (
                        "Rewrite the terminal gesture so a selected role "
                        "reaches the declared point; do not hide an early "
                        "cutoff behind trailing phrase silence."
                    ),
                )
            elif (
                intent.closure != "elided"
                and not intent_metrics["attacks_at_arrival"]
            ):
                add(
                    "warning",
                    "phrasing",
                    "arrival_not_articulated",
                    (
                        f"Arrival '{intent.id}' in section '{section.id}' "
                        "is only crossed by sustained material and has no "
                        "selected attack at the declared point."
                    ),
                    intent_metrics,
                    (
                        "Articulate the arrival in at least one selected role "
                        "or mark a genuinely elided arrival explicitly."
                    ),
                )
            if (
                intent.min_hold is not None
                and intent_metrics["anchor_hold_beats"] + 1e-4
                < float(intent.min_hold.fraction)
            ):
                add(
                    "warning",
                    "phrasing",
                    "arrival_hold_too_short",
                    (
                        f"Arrival '{intent.id}' in section '{section.id}' "
                        "does not remain stable for its declared minimum hold."
                    ),
                    intent_metrics,
                    (
                        "Lengthen one structural arrival tone, reduce the "
                        "terminal flourish, or move the declared arrival to "
                        "the point that actually completes the phrase."
                    ),
                )
            if (
                intent_metrics["post_attacks"]
                > intent.max_post_attacks
            ):
                add(
                    "warning",
                    "phrasing",
                    "post_arrival_overrun",
                    (
                        f"Arrival '{intent.id}' in section '{section.id}' "
                        "is followed by more selected attacks than its "
                        "declared post-arrival action permits."
                    ),
                    intent_metrics,
                    (
                        "Stop at the arrival, budget an intentional echo or "
                        "link, or move the arrival later if the continuation "
                        "still performs essential closure work."
                    ),
                )
            if intent.harmonic_stability != "free":
                observations = intent_metrics["harmonic_observations"]
                unknowns = intent_metrics["harmonic_unknowns"]
                supported = intent_metrics[
                    "harmonically_supported_observations"
                ]
                misses_support = (
                    intent.harmonic_stability == "supported"
                    and observations > 0
                    and unknowns == 0
                    and supported == 0
                )
                misses_resolution = (
                    intent.harmonic_stability == "resolved"
                    and observations > 0
                    and unknowns == 0
                    and supported < observations
                )
                if misses_support or misses_resolution:
                    add(
                        "warning",
                        "harmony",
                        "arrival_harmonic_support_missed",
                        (
                            f"Arrival '{intent.id}' in section '{section.id}' "
                            "does not satisfy its declared harmonic stability."
                        ),
                        intent_metrics,
                        (
                            "Revise the structural arrival pitches or the "
                            "governing harmony; keep intentional suspensions "
                            "only when their continuation resolves them."
                        ),
                    )
                elif observations == 0 or unknowns:
                    add(
                        "info",
                        "harmony",
                        "arrival_harmony_not_fully_observable",
                        (
                            f"Arrival '{intent.id}' in section '{section.id}' "
                            "uses targets whose harmonic support cannot be "
                            "fully inferred from the authored plan."
                        ),
                        intent_metrics,
                        (
                            "Inspect the compiled pitches or use observable "
                            "absolute/chord targets when this arrival must be "
                            "verified automatically."
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
                segment.default_enabled
                and "foreground" in segment.functions
                and metrics["pitched_events"] >= 24
                and metrics["bar_downbeat_coverage"] < 0.25
                and metrics["tactus_alignment_ratio"] < 0.4
                and metrics["off_tactus_bridge_ratio"] >= 0.4
            ):
                add(
                    "warning",
                    "rhythm",
                    "foreground_metric_anchor_conflict",
                    (
                        f"Foreground segment '{segment.id}' rarely "
                        "articulates bar downbeats while many displaced "
                        "attacks continue across the next tactus."
                    ),
                    {
                        "pitched_events": metrics["pitched_events"],
                        "tactus_alignment_ratio": metrics[
                            "tactus_alignment_ratio"
                        ],
                        "bar_downbeat_coverage": metrics[
                            "bar_downbeat_coverage"
                        ],
                        "off_tactus_attacks": metrics[
                            "off_tactus_attacks"
                        ],
                        "off_tactus_bridge_ratio": metrics[
                            "off_tactus_bridge_ratio"
                        ],
                    },
                    (
                        "Rewrite the attack-duration skeleton around shared "
                        "bar and tactus anchors. Preserve syncopation as a "
                        "departure that returns to the established meter, "
                        "not as the foreground's permanent phase."
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
                for previous, current in pairwise(directions)
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
