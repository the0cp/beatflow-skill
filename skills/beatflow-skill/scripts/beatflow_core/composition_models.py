# SPDX-License-Identifier: GPL-3.0-only
"""BeatFlow Composition 1.1: explicit, style-neutral musical plans."""

from __future__ import annotations

from fractions import Fraction
from math import gcd
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from .models import Identifier, KeySignature, StrictModel, TimeSignature

Articulation = Literal["staccato", "detached", "normal", "tenuto", "legato"]
Contour = Literal["up", "down", "hold", "free"]
MusicalFunction = Literal[
    "pulse",
    "low",
    "harmony",
    "foreground",
    "counterline",
    "texture",
    "support",
]
PerformanceKind = Literal["neutral", "percussive", "plucked", "sustained"]
DevelopmentIntent = Literal[
    "statement",
    "repeat",
    "develop",
    "contrast",
    "climax",
    "release",
]
ClosureKind = Literal["open", "partial", "closed", "elided"]
HarmonicStability = Literal["free", "supported", "resolved"]
PostArrivalAction = Literal["stop", "echo", "link", "afterglow"]
PhraseStageRole = Literal[
    "initiate",
    "develop",
    "intensify",
    "release",
    "link",
]
PhraseFocusCue = Literal["salience", "density", "duration"]
PhraseStageExitBehavior = Literal["free", "continue", "breathe", "arrive"]
MetricEntryAnchor = Literal["free", "division", "tactus", "bar_downbeat"]
PhraseGrouping = Literal["free", "regular", "irregular"]
PhraseStageMetricRole = Literal[
    "free",
    "structural",
    "pickup",
    "extension",
    "elision",
]


class BeatTime(StrictModel):
    """An exact non-negative position or duration in quarter-note beats."""

    numerator: int = Field(ge=0, le=1_000_000)
    denominator: int = Field(default=1, ge=1, le=9_600)

    @model_validator(mode="before")
    @classmethod
    def normalize_fraction(cls, value):
        if isinstance(value, cls):
            return value
        if not isinstance(value, dict):
            return value
        numerator = int(value.get("numerator", 0))
        denominator = int(value.get("denominator", 1))
        if denominator <= 0:
            raise ValueError("denominator must be positive")
        divisor = gcd(abs(numerator), denominator) or 1
        return {
            **value,
            "numerator": numerator // divisor,
            "denominator": denominator // divisor,
        }

    @property
    def fraction(self) -> Fraction:
        return Fraction(self.numerator, self.denominator)

    @property
    def beats(self) -> float:
        return float(self.fraction)


class TrackPlan(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    program: int = Field(default=0, ge=0, le=127)
    channel: int | None = Field(default=None, ge=0, le=15)
    percussion: bool = False
    performance: PerformanceKind = "neutral"
    monophonic: bool = False
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    register_low: int = Field(default=48, ge=0, le=127)
    register_high: int = Field(default=84, ge=0, le=127)
    center_pitch: int = Field(default=66, ge=0, le=127)

    @model_validator(mode="after")
    def register_is_ordered(self) -> TrackPlan:
        if not self.register_low <= self.center_pitch <= self.register_high:
            raise ValueError(
                "register_low <= center_pitch <= register_high is required"
            )
        if self.percussion and self.channel not in {None, 9}:
            raise ValueError("percussion tracks must use channel 9 or automatic assignment")
        return self


class HarmonySpan(StrictModel):
    onset: BeatTime
    duration: BeatTime
    symbol: str = Field(min_length=1, max_length=40)
    function: str = Field(default="", max_length=100)

    @model_validator(mode="after")
    def duration_is_positive(self) -> HarmonySpan:
        if self.duration.numerator == 0:
            raise ValueError("harmony duration must be positive")
        return self


class PitchTarget(StrictModel):
    basis: Literal[
        "chord",
        "chord_index",
        "scale",
        "next_chord",
        "absolute",
        "relative",
    ]
    degree: int | None = Field(default=None, ge=1, le=64)
    alter: int = Field(default=0, ge=-24, le=24)
    midi: int | None = Field(default=None, ge=0, le=127)
    semitones: int | None = Field(default=None, ge=-36, le=36)

    @model_validator(mode="after")
    def fields_match_basis(self) -> PitchTarget:
        degree_bases = {"chord", "chord_index", "scale", "next_chord"}
        if self.basis in degree_bases and self.degree is None:
            raise ValueError(f"{self.basis} targets require degree")
        if self.basis not in degree_bases and self.degree is not None:
            raise ValueError("degree is only valid for functional targets")
        if self.basis == "absolute" and self.midi is None:
            raise ValueError("absolute targets require midi")
        if self.basis != "absolute" and self.midi is not None:
            raise ValueError("midi is only valid for absolute targets")
        if self.basis == "relative" and self.semitones is None:
            raise ValueError("relative targets require semitones")
        if self.basis != "relative" and self.semitones is not None:
            raise ValueError("semitones is only valid for relative targets")
        if self.basis in {"absolute", "relative"} and self.alter:
            raise ValueError("alter is only valid for functional targets")
        return self


class EventBase(StrictModel):
    onset: BeatTime
    duration: BeatTime

    @model_validator(mode="after")
    def duration_is_positive(self):
        if self.duration.numerator == 0:
            raise ValueError("event duration must be positive")
        return self


class PitchedEvent(EventBase):
    type: Literal["pitched"] = "pitched"
    target: PitchTarget
    articulation: Articulation = "normal"
    accent: float = Field(default=0.72, ge=0.0, le=1.0)
    contour: Contour = "free"
    register_hint: int | None = Field(default=None, ge=0, le=127)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    function: str = Field(default="", max_length=80)
    motif: str | None = Field(default=None, max_length=64)


class ChordEvent(EventBase):
    type: Literal["chord"] = "chord"
    notes: int = Field(default=3, ge=1, le=8)
    omit_root: bool = True
    low: int | None = Field(default=None, ge=0, le=127)
    high: int | None = Field(default=None, ge=0, le=127)
    top_target: PitchTarget | None = None
    articulation: Articulation = "normal"
    accent: float = Field(default=0.64, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def range_is_ordered(self) -> ChordEvent:
        if self.low is not None and self.high is not None and self.low >= self.high:
            raise ValueError("chord low must be below chord high")
        if self.top_target is not None and self.top_target.basis == "relative":
            raise ValueError("chord top_target cannot be relative")
        return self


class DrumEvent(EventBase):
    type: Literal["drum"] = "drum"
    pitch: int = Field(ge=0, le=127)
    velocity: int = Field(default=84, ge=1, le=127)


MusicalEvent = Annotated[
    PitchedEvent | ChordEvent | DrumEvent,
    Field(discriminator="type"),
]


class SegmentPlan(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=100)
    track_id: Identifier
    functions: list[MusicalFunction] = Field(min_length=1)
    start: BeatTime
    duration: BeatTime
    intent: str = Field(default="", max_length=400)
    default_enabled: bool = True
    events: list[MusicalEvent] = Field(min_length=1)

    @field_validator("functions")
    @classmethod
    def functions_are_unique(
        cls, value: list[MusicalFunction]
    ) -> list[MusicalFunction]:
        if len(value) != len(set(value)):
            raise ValueError("segment functions cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def boundaries_and_order_are_valid(self) -> SegmentPlan:
        if self.duration.numerator == 0:
            raise ValueError("segment duration must be positive")
        onsets = [event.onset.fraction for event in self.events]
        if onsets != sorted(onsets):
            raise ValueError("segment events must be ordered by onset")
        return self


class SilenceIntent(StrictModel):
    """A section-relative window that selected musical functions leave empty."""

    id: Identifier
    onset: BeatTime
    duration: BeatTime
    functions: list[MusicalFunction] = Field(default_factory=list)
    description: str = Field(default="", max_length=300)

    @field_validator("functions")
    @classmethod
    def functions_are_unique(
        cls, value: list[MusicalFunction]
    ) -> list[MusicalFunction]:
        if len(value) != len(set(value)):
            raise ValueError("silence functions cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def duration_is_positive(self) -> SilenceIntent:
        if self.duration.numerator == 0:
            raise ValueError("silence duration must be positive")
        return self


class TensionContour(StrictModel):
    """A phrase-level start, high point, and release target."""

    start: float = Field(ge=0.0, le=1.0)
    peak: float = Field(ge=0.0, le=1.0)
    end: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def peak_is_the_high_point(self) -> TensionContour:
        if self.peak < max(self.start, self.end):
            raise ValueError("tension peak cannot be below start or end")
        return self


class PhraseIntent(StrictModel):
    """A section-relative phrase and its intended perceptual boundary."""

    id: Identifier
    onset: BeatTime
    duration: BeatTime
    functions: list[MusicalFunction] = Field(default_factory=list)
    attention: MusicalFunction | None = None
    boundary_strength: float = Field(default=0.5, ge=0.0, le=1.0)
    max_continuous_beats: BeatTime | None = None
    grouping: PhraseGrouping = "free"
    subphrase_bars: list[int] = Field(default_factory=list)
    tension: TensionContour | None = None
    goal: str = Field(default="", max_length=300)

    @field_validator("functions")
    @classmethod
    def functions_are_unique(
        cls, value: list[MusicalFunction]
    ) -> list[MusicalFunction]:
        if len(value) != len(set(value)):
            raise ValueError("phrase functions cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def phrase_values_are_valid(self) -> PhraseIntent:
        if self.duration.numerator == 0:
            raise ValueError("phrase duration must be positive")
        if (
            self.max_continuous_beats is not None
            and self.max_continuous_beats.numerator == 0
        ):
            raise ValueError("max_continuous_beats must be positive")
        if (
            self.attention is not None
            and self.functions
            and self.attention not in self.functions
        ):
            raise ValueError("phrase attention must be one of its selected functions")
        if self.grouping == "free" and self.subphrase_bars:
            raise ValueError(
                "free phrase grouping cannot declare subphrase_bars"
            )
        if self.grouping != "free" and not self.subphrase_bars:
            raise ValueError(
                "non-free phrase grouping requires subphrase_bars"
            )
        if any(value <= 0 for value in self.subphrase_bars):
            raise ValueError("phrase subphrase_bars must be positive")
        if (
            self.grouping == "regular"
            and len(set(self.subphrase_bars)) > 1
        ):
            raise ValueError(
                "regular phrase grouping requires equal subphrase bars"
            )
        return self


class PhraseStageIntent(StrictModel):
    """One audible job inside a declared phrase."""

    id: Identifier
    phrase_id: Identifier
    onset: BeatTime
    duration: BeatTime
    functions: list[MusicalFunction] = Field(default_factory=list)
    role: PhraseStageRole = "develop"
    min_attacks: int = Field(default=0, ge=0, le=256)
    max_attacks: int = Field(default=256, ge=0, le=256)
    min_connected_ratio: float | None = Field(default=None, ge=0.0, le=1.0)
    max_gesture_beats: BeatTime | None = None
    min_polyphonic_attacks: int = Field(default=0, ge=0, le=256)
    max_polyphonic_attacks: int = Field(default=256, ge=0, le=256)
    metric_role: PhraseStageMetricRole = "free"
    entry_anchor: MetricEntryAnchor = "free"
    min_tactus_attack_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    max_off_tactus_bridge_ratio: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
    )
    exit_behavior: PhraseStageExitBehavior = "free"
    focus: bool = False
    focus_cue: PhraseFocusCue | None = None
    goal: str = Field(default="", max_length=300)

    @field_validator("functions")
    @classmethod
    def functions_are_unique(
        cls, value: list[MusicalFunction]
    ) -> list[MusicalFunction]:
        if len(value) != len(set(value)):
            raise ValueError("phrase stage functions cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def stage_values_are_valid(self) -> PhraseStageIntent:
        if self.duration.numerator == 0:
            raise ValueError("phrase stage duration must be positive")
        if self.min_attacks > self.max_attacks:
            raise ValueError("phrase stage min_attacks cannot exceed max_attacks")
        if (
            self.max_gesture_beats is not None
            and self.max_gesture_beats.numerator == 0
        ):
            raise ValueError("phrase stage max_gesture_beats must be positive")
        if self.min_polyphonic_attacks > self.max_polyphonic_attacks:
            raise ValueError(
                "phrase stage min_polyphonic_attacks cannot exceed "
                "max_polyphonic_attacks"
            )
        if (
            self.metric_role == "structural"
            and self.entry_anchor not in {"tactus", "bar_downbeat"}
        ):
            raise ValueError(
                "structural phrase stages require a tactus or bar-downbeat "
                "entry anchor"
            )
        if self.focus and self.focus_cue is None:
            raise ValueError("a focus phrase stage requires focus_cue")
        if not self.focus and self.focus_cue is not None:
            raise ValueError("focus_cue is only valid on a focus phrase stage")
        return self


class ArrivalIntent(StrictModel):
    """The intended point of local completion inside one declared phrase."""

    id: Identifier
    phrase_id: Identifier
    onset: BeatTime
    functions: list[MusicalFunction] = Field(default_factory=list)
    closure: ClosureKind = "partial"
    strength: float = Field(default=0.5, ge=0.0, le=1.0)
    min_hold: BeatTime | None = None
    harmonic_stability: HarmonicStability = "free"
    post_action: PostArrivalAction = "stop"
    max_post_attacks: int = Field(default=0, ge=0, le=64)
    goal: str = Field(default="", max_length=300)

    @field_validator("functions")
    @classmethod
    def functions_are_unique(
        cls, value: list[MusicalFunction]
    ) -> list[MusicalFunction]:
        if len(value) != len(set(value)):
            raise ValueError("arrival functions cannot contain duplicates")
        return value

    @model_validator(mode="after")
    def arrival_values_are_valid(self) -> ArrivalIntent:
        if self.min_hold is not None and self.min_hold.numerator == 0:
            raise ValueError("arrival min_hold must be positive")
        if self.post_action == "stop" and self.max_post_attacks:
            raise ValueError("a stop arrival cannot permit post-arrival attacks")
        return self


class SectionPlan(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=100)
    length_bars: int = Field(ge=1, le=256)
    energy: float = Field(default=0.6, ge=0.0, le=1.0)
    harmony: list[HarmonySpan] = Field(default_factory=list)
    phrases: list[PhraseIntent] = Field(default_factory=list)
    phrase_stages: list[PhraseStageIntent] = Field(default_factory=list)
    arrivals: list[ArrivalIntent] = Field(default_factory=list)
    silences: list[SilenceIntent] = Field(default_factory=list)
    segments: list[SegmentPlan] = Field(min_length=1)


class SegmentTreatment(StrictModel):
    segment_id: Identifier
    enabled: bool | None = None
    transpose_semitones: int = Field(default=0, ge=-24, le=24)
    octave_shift: int = Field(default=0, ge=-2, le=2)
    velocity_scale: float = Field(default=1.0, ge=0.1, le=2.0)
    gate_scale: float = Field(default=1.0, ge=0.1, le=2.0)

    @model_validator(mode="after")
    def disabled_treatment_has_no_transform(self) -> SegmentTreatment:
        if self.enabled is False and (
            self.transpose_semitones
            or self.octave_shift
            or self.velocity_scale != 1.0
            or self.gate_scale != 1.0
        ):
            raise ValueError("disabled treatments cannot also transform the segment")
        return self


class PlaySection(StrictModel):
    id: Identifier
    section_id: Identifier
    label: str = Field(default="", max_length=100)
    development: DevelopmentIntent = "statement"
    energy: float | None = Field(default=None, ge=0.0, le=1.0)
    intent: str = Field(default="", max_length=300)
    treatments: list[SegmentTreatment] = Field(default_factory=list)

    @field_validator("treatments")
    @classmethod
    def treatment_segments_are_unique(
        cls, value: list[SegmentTreatment]
    ) -> list[SegmentTreatment]:
        ids = [item.segment_id for item in value]
        if len(ids) != len(set(ids)):
            raise ValueError("an occurrence can treat each segment only once")
        return value


class InteractionIntent(StrictModel):
    id: Identifier
    section_id: Identifier
    source: MusicalFunction
    target: MusicalFunction
    minimum_overlap: float = Field(default=0.0, ge=0.0, le=1.0)
    maximum_overlap: float = Field(default=1.0, ge=0.0, le=1.0)
    description: str = Field(default="", max_length=300)

    @model_validator(mode="after")
    def overlap_range_is_ordered(self) -> InteractionIntent:
        if self.minimum_overlap > self.maximum_overlap:
            raise ValueError("minimum_overlap cannot exceed maximum_overlap")
        return self


class Composition(StrictModel):
    schema_version: Literal["1.0", "1.1"] = "1.1"
    title: str = Field(min_length=1, max_length=120)
    intent: str = Field(default="", max_length=1_200)
    priorities: list[str] = Field(default_factory=list)
    exclusions: list[str] = Field(default_factory=list)
    style_tags: list[str] = Field(default_factory=list)
    target_duration_seconds: float | None = Field(default=None, ge=5.0, le=3_600.0)
    bpm: float = Field(default=110.0, ge=20.0, le=300.0)
    time_signature: TimeSignature = Field(default_factory=TimeSignature)
    key: KeySignature = Field(default_factory=KeySignature)
    ppq: int = Field(default=960, ge=96, le=9_600)
    tracks: list[TrackPlan] = Field(min_length=1)
    sections: list[SectionPlan] = Field(min_length=1)
    timeline: list[PlaySection] = Field(min_length=1)
    interactions: list[InteractionIntent] = Field(default_factory=list)

    @property
    def beats_per_bar_fraction(self) -> Fraction:
        return Fraction(
            self.time_signature.numerator * 4,
            self.time_signature.denominator,
        )

    @property
    def beats_per_bar(self) -> float:
        return float(self.beats_per_bar_fraction)
