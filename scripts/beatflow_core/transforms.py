# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic note transformations used by the MIDI renderer."""

from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import random

from .models import (
    GateTransform,
    HumanizeTransform,
    InvertTransform,
    OctaveTransform,
    ThinTransform,
    TimeShiftTransform,
    Transformation,
    TransposeTransform,
    VelocityScaleTransform,
)


@dataclass(frozen=True, slots=True)
class RenderedNote:
    pitch: int
    start: float
    duration: float
    velocity: int


def _stable_rng(seed: int, identity: str) -> random.Random:
    digest = hashlib.blake2b(f"{seed}:{identity}".encode("utf-8"), digest_size=8).digest()
    return random.Random(int.from_bytes(digest, byteorder="big", signed=False))


def apply_transform(
    note: RenderedNote,
    transform: Transformation,
    *,
    seed: int,
    identity: str,
) -> RenderedNote | None:
    """Apply one transformation, returning None when a thinning rule drops the note."""
    if isinstance(transform, TransposeTransform):
        return replace(note, pitch=note.pitch + transform.semitones)
    if isinstance(transform, OctaveTransform):
        return replace(note, pitch=note.pitch + (12 * transform.octaves))
    if isinstance(transform, InvertTransform):
        return replace(note, pitch=(2 * transform.axis_pitch) - note.pitch)
    if isinstance(transform, VelocityScaleTransform):
        velocity = max(1, min(127, round(note.velocity * transform.factor)))
        return replace(note, velocity=velocity)
    if isinstance(transform, TimeShiftTransform):
        return replace(note, start=note.start + transform.beats)
    if isinstance(transform, GateTransform):
        return replace(note, duration=max(1e-6, note.duration * transform.factor))
    if isinstance(transform, HumanizeTransform):
        rng = _stable_rng(seed + transform.seed_offset, f"{identity}:{transform.id}")
        timing = rng.uniform(-transform.max_timing_beats, transform.max_timing_beats)
        velocity = rng.randint(-transform.max_velocity, transform.max_velocity)
        return replace(
            note,
            start=note.start + timing,
            velocity=max(1, min(127, note.velocity + velocity)),
        )
    if isinstance(transform, ThinTransform):
        rng = _stable_rng(seed + transform.seed_offset, f"{identity}:{transform.id}")
        return note if rng.random() <= transform.keep_probability else None
    raise TypeError(f"Unsupported transformation: {type(transform).__name__}")


def apply_chain(
    note: RenderedNote,
    transforms: list[Transformation],
    *,
    seed: int,
    identity: str,
) -> RenderedNote | None:
    result: RenderedNote | None = note
    for transform in transforms:
        if result is None:
            break
        result = apply_transform(result, transform, seed=seed, identity=identity)
    return result
