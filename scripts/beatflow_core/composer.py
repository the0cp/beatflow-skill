# SPDX-License-Identifier: GPL-3.0-only
"""Small Python authoring DSL for style-neutral Composition 1.1 plans."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from typing import Iterable

from .composition_models import (
    ArrivalIntent,
    BeatTime,
    ChordEvent,
    Composition,
    DrumEvent,
    HarmonySpan,
    InteractionIntent,
    PitchedEvent,
    PitchTarget,
    PlaySection,
    PhraseIntent,
    PhraseStageIntent,
    SectionPlan,
    SegmentPlan,
    SegmentTreatment,
    SilenceIntent,
    TensionContour,
    TrackPlan,
)
from .models import KeySignature, Mode, TimeSignature
from .meter import meter_profile


TimeLike = BeatTime | Fraction | int | tuple[int, int]

DRUM_PITCH = {
    "kick": 36,
    "snare": 38,
    "rim": 37,
    "closed_hat": 42,
    "open_hat": 46,
    "low_tom": 45,
    "mid_tom": 47,
    "high_tom": 50,
    "ride": 51,
    "crash": 49,
}


def _fraction(value: TimeLike) -> Fraction:
    if isinstance(value, BeatTime):
        return value.fraction
    if isinstance(value, Fraction):
        return value
    if isinstance(value, tuple):
        return Fraction(value[0], value[1])
    return Fraction(value, 1)


def beat(numerator: int, denominator: int = 1) -> BeatTime:
    """Create an exact quarter-note beat value."""
    value = Fraction(numerator, denominator)
    if value < 0:
        raise ValueError("beat values cannot be negative")
    return BeatTime(numerator=value.numerator, denominator=value.denominator)


def chord(degree: int, alter: int = 0) -> PitchTarget:
    return PitchTarget(basis="chord", degree=degree, alter=alter)


def chord_index(index: int, alter: int = 0) -> PitchTarget:
    return PitchTarget(basis="chord_index", degree=index, alter=alter)


def scale(degree: int, alter: int = 0) -> PitchTarget:
    return PitchTarget(basis="scale", degree=degree, alter=alter)


def next_chord(degree: int, alter: int = 0) -> PitchTarget:
    return PitchTarget(basis="next_chord", degree=degree, alter=alter)


def midi(pitch: int) -> PitchTarget:
    return PitchTarget(basis="absolute", midi=pitch)


def relative(semitones: int) -> PitchTarget:
    return PitchTarget(basis="relative", semitones=semitones)


def root(alter: int = 0) -> PitchTarget:
    return chord(1, alter)


@dataclass
class SegmentBuilder:
    owner: "SectionBuilder"
    id: str
    name: str
    track_id: str
    functions: list[str]
    start: BeatTime
    duration: BeatTime
    intent: str
    default_enabled: bool
    events: list

    def note(
        self,
        onset: TimeLike,
        duration: TimeLike,
        target: PitchTarget,
        *,
        articulation: str = "normal",
        accent: float = 0.72,
        contour: str = "free",
        register_hint: int | None = None,
        importance: float = 0.5,
        function: str = "",
        motif: str | None = None,
    ) -> "SegmentBuilder":
        self.events.append(
            PitchedEvent(
                onset=self.owner.owner.time(onset),
                duration=self.owner.owner.time(duration),
                target=target,
                articulation=articulation,
                accent=accent,
                contour=contour,
                register_hint=register_hint,
                importance=importance,
                function=function,
                motif=motif,
            )
        )
        return self

    def chord(
        self,
        onset: TimeLike,
        duration: TimeLike,
        *,
        notes: int = 3,
        omit_root: bool = True,
        low: int | None = None,
        high: int | None = None,
        top_target: PitchTarget | None = None,
        articulation: str = "normal",
        accent: float = 0.64,
    ) -> "SegmentBuilder":
        self.events.append(
            ChordEvent(
                onset=self.owner.owner.time(onset),
                duration=self.owner.owner.time(duration),
                notes=notes,
                omit_root=omit_root,
                low=low,
                high=high,
                top_target=top_target,
                articulation=articulation,
                accent=accent,
            )
        )
        return self

    def drum(
        self,
        onset: TimeLike,
        duration: TimeLike,
        lane_or_pitch: str | int,
        *,
        velocity: int = 84,
    ) -> "SegmentBuilder":
        pitch = (
            DRUM_PITCH[lane_or_pitch]
            if isinstance(lane_or_pitch, str)
            else lane_or_pitch
        )
        self.events.append(
            DrumEvent(
                onset=self.owner.owner.time(onset),
                duration=self.owner.owner.time(duration),
                pitch=pitch,
                velocity=velocity,
            )
        )
        return self

    def drums(
        self,
        lane_or_pitch: str | int,
        onsets: Iterable[TimeLike],
        *,
        duration: TimeLike = (1, 16),
        velocities: int | Iterable[int] = 84,
    ) -> "SegmentBuilder":
        values = list(onsets)
        velocity_values = (
            [velocities] * len(values)
            if isinstance(velocities, int)
            else list(velocities)
        )
        if len(values) != len(velocity_values):
            raise ValueError("drum velocities must match onsets")
        for onset, velocity in zip(values, velocity_values, strict=True):
            self.drum(onset, duration, lane_or_pitch, velocity=velocity)
        return self

    def end(self) -> "SectionBuilder":
        self.owner.segments.append(
            SegmentPlan(
                id=self.id,
                name=self.name,
                track_id=self.track_id,
                functions=self.functions,
                start=self.start,
                duration=self.duration,
                intent=self.intent,
                default_enabled=self.default_enabled,
                events=sorted(
                    self.events,
                    key=lambda item: (
                        item.onset.fraction,
                        item.type,
                        getattr(item, "pitch", -1),
                    ),
                ),
            )
        )
        return self.owner


@dataclass
class SectionBuilder:
    owner: "SongBuilder"
    id: str
    name: str
    length_bars: int
    energy: float
    harmony: list[HarmonySpan]
    phrases: list[PhraseIntent]
    phrase_stages: list[PhraseStageIntent]
    arrivals: list[ArrivalIntent]
    silences: list[SilenceIntent]
    segments: list[SegmentPlan]

    @property
    def length(self) -> BeatTime:
        value = self.length_bars * self.owner.beats_per_bar
        return self.owner.time(value)

    def harmony_span(
        self,
        onset: TimeLike,
        duration: TimeLike,
        symbol: str,
        *,
        function: str = "",
    ) -> "SectionBuilder":
        self.harmony.append(
            HarmonySpan(
                onset=self.owner.time(onset),
                duration=self.owner.time(duration),
                symbol=symbol,
                function=function,
            )
        )
        return self

    def chord_bar(
        self,
        bar: int,
        symbol: str,
        *,
        function: str = "",
    ) -> "SectionBuilder":
        return self.harmony_span(
            self.owner.at(bar),
            self.owner.time(self.owner.beats_per_bar),
            symbol,
            function=function,
        )

    def silence(
        self,
        id: str,
        onset: TimeLike,
        duration: TimeLike,
        *,
        functions: list[str] | None = None,
        description: str = "",
    ) -> "SectionBuilder":
        """Declare a window that all or selected functions should leave empty."""

        self.silences.append(
            SilenceIntent(
                id=id,
                onset=self.owner.time(onset),
                duration=self.owner.time(duration),
                functions=functions or [],
                description=description,
            )
        )
        return self

    def phrase(
        self,
        id: str,
        onset: TimeLike,
        duration: TimeLike,
        *,
        functions: list[str] | None = None,
        attention: str | None = None,
        boundary_strength: float = 0.5,
        max_continuous: TimeLike | None = None,
        grouping: str = "free",
        subphrase_bars: list[int] | None = None,
        tension: tuple[float, float, float] | None = None,
        goal: str = "",
    ) -> "SectionBuilder":
        """Declare phrase scope, release intent, and optional tension shape."""

        self.phrases.append(
            PhraseIntent(
                id=id,
                onset=self.owner.time(onset),
                duration=self.owner.time(duration),
                functions=functions or [],
                attention=attention,
                boundary_strength=boundary_strength,
                max_continuous_beats=(
                    self.owner.time(max_continuous)
                    if max_continuous is not None
                    else None
                ),
                grouping=grouping,
                subphrase_bars=subphrase_bars or [],
                tension=(
                    TensionContour(
                        start=tension[0],
                        peak=tension[1],
                        end=tension[2],
                    )
                    if tension is not None
                    else None
                ),
                goal=goal,
            )
        )
        return self

    def arrival(
        self,
        id: str,
        phrase_id: str,
        onset: TimeLike,
        *,
        functions: list[str] | None = None,
        closure: str = "partial",
        strength: float = 0.5,
        min_hold: TimeLike | None = None,
        harmonic_stability: str = "free",
        post_action: str = "stop",
        max_post_attacks: int = 0,
        goal: str = "",
    ) -> "SectionBuilder":
        """Declare the audible completion point inside a phrase."""

        self.arrivals.append(
            ArrivalIntent(
                id=id,
                phrase_id=phrase_id,
                onset=self.owner.time(onset),
                functions=functions or [],
                closure=closure,
                strength=strength,
                min_hold=(
                    self.owner.time(min_hold)
                    if min_hold is not None
                    else None
                ),
                harmonic_stability=harmonic_stability,
                post_action=post_action,
                max_post_attacks=max_post_attacks,
                goal=goal,
            )
        )
        return self

    def phrase_stage(
        self,
        id: str,
        phrase_id: str,
        onset: TimeLike,
        duration: TimeLike,
        *,
        functions: list[str] | None = None,
        role: str = "develop",
        min_attacks: int = 0,
        max_attacks: int = 256,
        min_connected_ratio: float | None = None,
        max_gesture: TimeLike | None = None,
        min_polyphonic_attacks: int = 0,
        max_polyphonic_attacks: int = 256,
        metric_role: str = "free",
        entry_anchor: str = "free",
        min_tactus_attack_ratio: float | None = None,
        max_off_tactus_bridge_ratio: float | None = None,
        exit_behavior: str = "free",
        focus: bool = False,
        focus_cue: str | None = None,
        goal: str = "",
    ) -> "SectionBuilder":
        """Declare one internally contrasted stage of a phrase."""

        self.phrase_stages.append(
            PhraseStageIntent(
                id=id,
                phrase_id=phrase_id,
                onset=self.owner.time(onset),
                duration=self.owner.time(duration),
                functions=functions or [],
                role=role,
                min_attacks=min_attacks,
                max_attacks=max_attacks,
                min_connected_ratio=min_connected_ratio,
                max_gesture_beats=(
                    self.owner.time(max_gesture)
                    if max_gesture is not None
                    else None
                ),
                min_polyphonic_attacks=min_polyphonic_attacks,
                max_polyphonic_attacks=max_polyphonic_attacks,
                metric_role=metric_role,
                entry_anchor=entry_anchor,
                min_tactus_attack_ratio=min_tactus_attack_ratio,
                max_off_tactus_bridge_ratio=max_off_tactus_bridge_ratio,
                exit_behavior=exit_behavior,
                focus=focus,
                focus_cue=focus_cue,
                goal=goal,
            )
        )
        return self

    def segment(
        self,
        id: str,
        name: str,
        *,
        track: str,
        functions: list[str],
        start: TimeLike,
        duration: TimeLike,
        intent: str = "",
        default_enabled: bool = True,
    ) -> SegmentBuilder:
        return SegmentBuilder(
            owner=self,
            id=id,
            name=name,
            track_id=track,
            functions=functions,
            start=self.owner.time(start),
            duration=self.owner.time(duration),
            intent=intent,
            default_enabled=default_enabled,
            events=[],
        )

    def end(self) -> "SongBuilder":
        self.owner._sections.append(
            SectionPlan(
                id=self.id,
                name=self.name,
                length_bars=self.length_bars,
                energy=self.energy,
                harmony=sorted(
                    self.harmony,
                    key=lambda item: item.onset.fraction,
                ),
                phrases=sorted(
                    self.phrases,
                    key=lambda item: (item.onset.fraction, item.id),
                ),
                phrase_stages=sorted(
                    self.phrase_stages,
                    key=lambda item: (item.onset.fraction, item.id),
                ),
                arrivals=sorted(
                    self.arrivals,
                    key=lambda item: (item.onset.fraction, item.id),
                ),
                silences=sorted(
                    self.silences,
                    key=lambda item: (item.onset.fraction, item.id),
                ),
                segments=sorted(
                    self.segments,
                    key=lambda item: (item.start.fraction, item.id),
                ),
            )
        )
        return self.owner


class SongBuilder:
    def __init__(
        self,
        title: str,
        *,
        intent: str,
        bpm: float,
        tonic: str,
        mode: str,
        meter: tuple[int, int] = (4, 4),
        ppq: int = 960,
        priorities: list[str] | None = None,
        exclusions: list[str] | None = None,
        style_tags: list[str] | None = None,
        target_duration_seconds: float | None = None,
    ):
        self.title = title
        self.intent = intent
        self.priorities = priorities or []
        self.exclusions = exclusions or []
        self.bpm = bpm
        self.key = KeySignature(tonic=tonic, mode=Mode(mode))
        self.style_tags = style_tags or []
        self.target_duration_seconds = target_duration_seconds
        self.time_signature = TimeSignature(
            numerator=meter[0],
            denominator=meter[1],
        )
        self.ppq = ppq
        self._tracks: list[TrackPlan] = []
        self._sections: list[SectionPlan] = []
        self._timeline: list[PlaySection] = []
        self._interactions: list[InteractionIntent] = []

    @property
    def beats_per_bar(self) -> Fraction:
        return Fraction(
            self.time_signature.numerator * 4,
            self.time_signature.denominator,
        )

    def time(self, value: TimeLike | Fraction) -> BeatTime:
        fraction = _fraction(value)
        if fraction < 0:
            raise ValueError("time values cannot be negative")
        return BeatTime(
            numerator=fraction.numerator,
            denominator=fraction.denominator,
        )

    def tactus(
        self,
        numerator: int,
        denominator: int = 1,
    ) -> BeatTime:
        """Create a duration in the meter's perceptual beats."""

        count = Fraction(numerator, denominator)
        if count < 0:
            raise ValueError("tactus values cannot be negative")
        return self.time(meter_profile(self.time_signature).tactus * count)

    def bars(
        self,
        numerator: int,
        denominator: int = 1,
    ) -> BeatTime:
        """Create a duration in measures of the current meter."""

        count = Fraction(numerator, denominator)
        if count < 0:
            raise ValueError("bar values cannot be negative")
        return self.time(self.beats_per_bar * count)

    def at(
        self,
        bar: int,
        beat_number: int = 1,
        offset: TimeLike = 0,
    ) -> BeatTime:
        if bar < 1 or beat_number < 1:
            raise ValueError("bar and beat_number are one-based")
        profile = meter_profile(self.time_signature)
        within = (
            Fraction(beat_number - 1, 1) * profile.tactus
            + _fraction(offset)
        )
        if within < 0 or within >= self.beats_per_bar:
            raise ValueError("beat position must fall inside the bar")
        return self.time((bar - 1) * self.beats_per_bar + within)

    def track(
        self,
        id: str,
        name: str,
        *,
        program: int = 0,
        channel: int | None = None,
        percussion: bool = False,
        performance: str = "neutral",
        monophonic: bool = False,
        volume: float = 1.0,
        low: int = 48,
        center: int = 66,
        high: int = 84,
    ) -> "SongBuilder":
        self._tracks.append(
            TrackPlan(
                id=id,
                name=name,
                program=program,
                channel=channel,
                percussion=percussion,
                performance=performance,
                monophonic=monophonic,
                volume=volume,
                register_low=low,
                center_pitch=center,
                register_high=high,
            )
        )
        return self

    def section(
        self,
        id: str,
        name: str,
        *,
        bars: int,
        energy: float,
    ) -> SectionBuilder:
        return SectionBuilder(
            self,
            id,
            name,
            bars,
            energy,
            [],
            [],
            [],
            [],
            [],
            [],
        )

    def play(
        self,
        id: str,
        section: str,
        *,
        label: str = "",
        development: str = "statement",
        energy: float | None = None,
        intent: str = "",
    ) -> "SongBuilder":
        self._timeline.append(
            PlaySection(
                id=id,
                section_id=section,
                label=label,
                development=development,
                energy=energy,
                intent=intent,
            )
        )
        return self

    def arrange(
        self,
        occurrence: str,
        segment: str,
        *,
        enabled: bool | None = None,
        transpose: int = 0,
        octave: int = 0,
        velocity: float = 1.0,
        gate: float = 1.0,
    ) -> "SongBuilder":
        target = next(
            (item for item in self._timeline if item.id == occurrence),
            None,
        )
        if target is None:
            raise ValueError(f"unknown occurrence '{occurrence}'")
        target.treatments.append(
            SegmentTreatment(
                segment_id=segment,
                enabled=enabled,
                transpose_semitones=transpose,
                octave_shift=octave,
                velocity_scale=velocity,
                gate_scale=gate,
            )
        )
        return self

    def interaction(
        self,
        id: str,
        section: str,
        *,
        source: str,
        target: str,
        minimum: float = 0.0,
        maximum: float = 1.0,
        description: str = "",
    ) -> "SongBuilder":
        self._interactions.append(
            InteractionIntent(
                id=id,
                section_id=section,
                source=source,
                target=target,
                minimum_overlap=minimum,
                maximum_overlap=maximum,
                description=description,
            )
        )
        return self

    def build(self) -> Composition:
        return Composition(
            title=self.title,
            intent=self.intent,
            priorities=self.priorities,
            exclusions=self.exclusions,
            style_tags=self.style_tags,
            target_duration_seconds=self.target_duration_seconds,
            bpm=self.bpm,
            time_signature=self.time_signature,
            key=self.key,
            ppq=self.ppq,
            tracks=self._tracks,
            sections=self._sections,
            timeline=self._timeline,
            interactions=self._interactions,
        )
