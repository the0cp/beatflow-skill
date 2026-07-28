# SPDX-License-Identifier: GPL-3.0-only
"""Strict, LLM-friendly project schema for structured MIDI arrangements."""

from __future__ import annotations

from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Identifier = Annotated[str, Field(pattern=r"^[a-z][a-z0-9_-]{0,63}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class TrackRole(str, Enum):
    DRUMS = "drums"
    BASS = "bass"
    CHORDS = "chords"
    MELODY = "melody"
    PAD = "pad"
    ARP = "arp"
    FX = "fx"
    OTHER = "other"


class ClipKind(str, Enum):
    PITCHED = "pitched"
    DRUMS = "drums"


class Mode(str, Enum):
    MAJOR = "major"
    MINOR = "minor"
    DORIAN = "dorian"
    PHRYGIAN = "phrygian"
    LYDIAN = "lydian"
    MIXOLYDIAN = "mixolydian"
    LOCRIAN = "locrian"


class TimeSignature(StrictModel):
    numerator: int = Field(default=4, ge=1, le=32)
    denominator: int = Field(default=4)

    @field_validator("denominator")
    @classmethod
    def denominator_must_be_power_of_two(cls, value: int) -> int:
        if value not in {1, 2, 4, 8, 16, 32}:
            raise ValueError("denominator must be one of 1, 2, 4, 8, 16, 32")
        return value


class KeySignature(StrictModel):
    tonic: str = Field(default="C", pattern=r"^[A-G](?:#|b)?$")
    mode: Mode = Mode.MAJOR


class Track(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    role: TrackRole
    program: int = Field(default=0, ge=0, le=127)
    channel: int | None = Field(default=None, ge=0, le=15)
    percussion: bool = False
    volume: float = Field(default=1.0, ge=0.0, le=2.0)
    performance: Literal["neutral", "percussive", "plucked", "sustained"] = "neutral"


class Note(StrictModel):
    pitch: int = Field(ge=0, le=127)
    start: float = Field(ge=0.0, description="Start in quarter-note beats")
    duration: float = Field(gt=0.0, description="Duration in quarter-note beats")
    velocity: int = Field(default=90, ge=1, le=127)


class Clip(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    kind: ClipKind = ClipKind.PITCHED
    length_bars: float = Field(gt=0.0, le=128.0)
    notes: list[Note] = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)


class Section(StrictModel):
    id: Identifier
    name: str = Field(min_length=1, max_length=80)
    length_bars: int = Field(ge=1, le=256)
    energy: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: list[str] = Field(default_factory=list)


class SectionOccurrence(StrictModel):
    id: Identifier
    section_id: Identifier
    label: str | None = Field(default=None, max_length=80)
    energy_override: float | None = Field(default=None, ge=0.0, le=1.0)
    variation_intent: str = Field(default="", max_length=300)


class TransformBase(StrictModel):
    id: Identifier


class TransposeTransform(TransformBase):
    type: Literal["transpose"]
    semitones: int = Field(ge=-36, le=36)


class OctaveTransform(TransformBase):
    type: Literal["octave"]
    octaves: int = Field(ge=-3, le=3)


class InvertTransform(TransformBase):
    type: Literal["invert"]
    axis_pitch: int = Field(default=60, ge=0, le=127)


class VelocityScaleTransform(TransformBase):
    type: Literal["velocity_scale"]
    factor: float = Field(gt=0.0, le=2.0)


class TimeShiftTransform(TransformBase):
    type: Literal["time_shift"]
    beats: float = Field(ge=-4.0, le=4.0)


class GateTransform(TransformBase):
    type: Literal["gate"]
    factor: float = Field(gt=0.0, le=4.0)


class HumanizeTransform(TransformBase):
    type: Literal["humanize"]
    max_timing_beats: float = Field(default=0.03, ge=0.0, le=0.25)
    max_velocity: int = Field(default=5, ge=0, le=30)
    seed_offset: int = 0


class ThinTransform(TransformBase):
    type: Literal["thin"]
    keep_probability: float = Field(gt=0.0, le=1.0)
    seed_offset: int = 0


Transformation = Annotated[
    TransposeTransform
    | OctaveTransform
    | InvertTransform
    | VelocityScaleTransform
    | TimeShiftTransform
    | GateTransform
    | HumanizeTransform
    | ThinTransform,
    Field(discriminator="type"),
]


class CompositionLink(StrictModel):
    id: Identifier
    section_id: Identifier
    track_id: Identifier
    clip_id: Identifier
    start_bar: float = Field(default=0.0, ge=0.0)
    repeat: bool = True
    transform_ids: list[Identifier] = Field(default_factory=list)
    occurrence_ids: list[Identifier] | None = None

    @model_validator(mode="after")
    def occurrence_filter_cannot_be_empty(self) -> CompositionLink:
        if self.occurrence_ids == []:
            raise ValueError("occurrence_ids must be null or contain at least one occurrence id")
        return self


class Project(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    title: str = Field(min_length=1, max_length=120)
    intent: str = Field(default="", max_length=1000)
    genre_tags: list[str] = Field(default_factory=list)
    bpm: float = Field(default=120.0, ge=20.0, le=300.0)
    time_signature: TimeSignature = Field(default_factory=TimeSignature)
    key: KeySignature = Field(default_factory=KeySignature)
    ppq: int = Field(default=480, ge=96, le=9600)
    seed: int = 0
    tracks: list[Track] = Field(min_length=1)
    sections: list[Section] = Field(min_length=1)
    timeline: list[SectionOccurrence] = Field(min_length=1)
    clips: list[Clip] = Field(min_length=1)
    transformations: list[Transformation] = Field(default_factory=list)
    links: list[CompositionLink] = Field(min_length=1)

    @property
    def beats_per_bar(self) -> float:
        return self.time_signature.numerator * (4.0 / self.time_signature.denominator)
