# SPDX-License-Identifier: GPL-3.0-only
"""BeatFlow Composition 1.0: explicit, style-neutral musical plans."""

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
    def register_is_ordered(self) -> "TrackPlan":
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
    def duration_is_positive(self) -> "HarmonySpan":
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
    def fields_match_basis(self) -> "PitchTarget":
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
    def range_is_ordered(self) -> "ChordEvent":
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
    def boundaries_and_order_are_valid(self) -> "SegmentPlan":
        if self.duration.numerator == 0:
            raise ValueError("segment duration must be positive")
        onsets = [event.onset.fraction for event in self.events]
        if onsets != sorted(onsets):
            raise ValueError("segment events must be ordered by onset")
        return self


class SectionPlan(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=100)
    length_bars: int = Field(ge=1, le=256)
    energy: float = Field(default=0.6, ge=0.0, le=1.0)
    harmony: list[HarmonySpan] = Field(default_factory=list)
    segments: list[SegmentPlan] = Field(min_length=1)


class SegmentTreatment(StrictModel):
    segment_id: Identifier
    enabled: bool | None = None
    transpose_semitones: int = Field(default=0, ge=-24, le=24)
    octave_shift: int = Field(default=0, ge=-2, le=2)
    velocity_scale: float = Field(default=1.0, ge=0.1, le=2.0)
    gate_scale: float = Field(default=1.0, ge=0.1, le=2.0)

    @model_validator(mode="after")
    def disabled_treatment_has_no_transform(self) -> "SegmentTreatment":
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
    def overlap_range_is_ordered(self) -> "InteractionIntent":
        if self.minimum_overlap > self.maximum_overlap:
            raise ValueError("minimum_overlap cannot exceed maximum_overlap")
        return self


class Composition(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
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
