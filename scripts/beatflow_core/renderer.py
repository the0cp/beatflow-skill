# SPDX-License-Identifier: GPL-3.0-only
"""Deterministic materialization of BeatFlow projects into Standard MIDI files."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import math
from pathlib import Path
from mido import Message, MetaMessage, MidiFile, MidiTrack, bpm2tempo
from pydantic import BaseModel, ConfigDict

from .models import CompositionLink, Mode, Project
from .transforms import RenderedNote, apply_chain
from .validation import ValidationReport, validate_project


class RenderError(ValueError):
    def __init__(self, message: str, report: ValidationReport | None = None):
        super().__init__(message)
        self.report = report


class RenderSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    output: str
    midi_tracks: int
    notes: int
    bars: int
    beats: float
    seconds: float
    ppq: int


@dataclass(frozen=True, slots=True)
class MaterializedNote:
    track_id: str
    channel: int
    pitch: int
    start: float
    duration: float
    velocity: int


def _assign_channels(project: Project) -> dict[str, int]:
    assignments: dict[str, int] = {}
    reserved = {
        track.channel
        for track in project.tracks
        if not track.percussion and track.channel is not None
    }
    available = [channel for channel in range(16) if channel != 9 and channel not in reserved]
    cursor = 0
    for track in project.tracks:
        if track.percussion:
            assignments[track.id] = 9
        elif track.channel is not None:
            assignments[track.id] = track.channel
        else:
            if cursor >= len(available):
                raise RenderError("Not enough free MIDI channels for automatic assignment.")
            assignments[track.id] = available[cursor]
            cursor += 1
    return assignments


def _link_applies(link: CompositionLink, occurrence_id: str) -> bool:
    return link.occurrence_ids is None or occurrence_id in link.occurrence_ids


def materialize_notes(project: Project) -> list[MaterializedNote]:
    """Resolve sections, links, loops and transformations into absolute beat events."""
    report = validate_project(project)
    if not report.valid:
        raise RenderError("Project has validation errors.", report)

    tracks = {track.id: track for track in project.tracks}
    sections = {section.id: section for section in project.sections}
    clips = {clip.id: clip for clip in project.clips}
    transforms = {transform.id: transform for transform in project.transformations}
    channels = _assign_channels(project)
    links_by_section: defaultdict[str, list[CompositionLink]] = defaultdict(list)
    for link in project.links:
        links_by_section[link.section_id].append(link)

    result: list[MaterializedNote] = []
    occurrence_start = 0.0
    beats_per_bar = project.beats_per_bar
    for occurrence in project.timeline:
        section = sections[occurrence.section_id]
        section_beats = section.length_bars * beats_per_bar
        section_end = occurrence_start + section_beats
        for link in links_by_section[section.id]:
            if not _link_applies(link, occurrence.id):
                continue
            track = tracks[link.track_id]
            clip = clips[link.clip_id]
            clip_beats = clip.length_bars * beats_per_bar
            link_start = occurrence_start + (link.start_bar * beats_per_bar)
            available_beats = max(0.0, section_end - link_start)
            repeats = math.ceil(available_beats / clip_beats) if link.repeat else 1
            chain = [transforms[transform_id] for transform_id in link.transform_ids]
            for repeat_index in range(repeats):
                loop_start = link_start + (repeat_index * clip_beats)
                if loop_start >= section_end:
                    break
                for note_index, note in enumerate(clip.notes):
                    identity = (
                        f"{occurrence.id}:{link.id}:{repeat_index}:{note_index}:"
                        f"{note.pitch}:{note.start}"
                    )
                    transformed = apply_chain(
                        RenderedNote(
                            pitch=note.pitch,
                            start=loop_start + note.start,
                            duration=note.duration,
                            velocity=note.velocity,
                        ),
                        chain,
                        seed=project.seed,
                        identity=identity,
                    )
                    if transformed is None:
                        continue
                    if not 0 <= transformed.pitch <= 127:
                        raise RenderError(
                            f"Link '{link.id}' transforms pitch {note.pitch} outside MIDI range: "
                            f"{transformed.pitch}."
                        )
                    start = max(occurrence_start, transformed.start)
                    end = min(section_end, transformed.start + transformed.duration)
                    if end <= start:
                        continue
                    result.append(
                        MaterializedNote(
                            track_id=track.id,
                            channel=channels[track.id],
                            pitch=transformed.pitch,
                            start=start,
                            duration=end - start,
                            velocity=max(
                                1,
                                min(127, round(transformed.velocity * track.volume)),
                            ),
                        )
                    )
        occurrence_start = section_end
    return result


def _events_to_track(
    *,
    name: str,
    channel: int,
    program: int,
    percussion: bool,
    performance: str,
    notes: list[MaterializedNote],
    ppq: int,
) -> MidiTrack:
    midi_track = MidiTrack()
    midi_track.append(MetaMessage("track_name", name=name, time=0))
    if not percussion:
        midi_track.append(Message("program_change", channel=channel, program=program, time=0))

    events: list[tuple[int, int, int, Message]] = []
    for note in notes:
        start_tick = max(0, round(note.start * ppq))
        end_tick = max(start_tick + 1, round((note.start + note.duration) * ppq))
        events.append(
            (
                start_tick,
                2,
                note.pitch,
                Message(
                    "note_on",
                    channel=channel,
                    note=note.pitch,
                    velocity=note.velocity,
                    time=0,
                ),
            )
        )
        events.append(
            (
                end_tick,
                0,
                note.pitch,
                Message("note_off", channel=channel, note=note.pitch, velocity=0, time=0),
            )
        )
        if performance == "sustained" and not percussion:
            expression = max(32, min(127, round(44 + (0.62 * note.velocity))))
            events.append(
                (
                    start_tick,
                    1,
                    11,
                    Message(
                        "control_change",
                        channel=channel,
                        control=11,
                        value=expression,
                        time=0,
                    ),
                )
            )
            if end_tick - start_tick >= ppq // 2:
                middle_tick = start_tick + ((end_tick - start_tick) // 2)
                events.append(
                    (
                        middle_tick,
                        1,
                        11,
                        Message(
                            "control_change",
                            channel=channel,
                            control=11,
                            value=max(24, expression - 8),
                            time=0,
                        ),
                    )
                )
            if end_tick - start_tick >= ppq:
                middle_tick = start_tick + ((end_tick - start_tick) // 2)
                events.extend(
                    [
                        (
                            middle_tick,
                            1,
                            1,
                            Message(
                                "control_change",
                                channel=channel,
                                control=1,
                                value=10,
                                time=0,
                            ),
                        ),
                        (
                            end_tick,
                            1,
                            1,
                            Message(
                                "control_change",
                                channel=channel,
                                control=1,
                                value=0,
                                time=0,
                            ),
                        ),
                    ]
                )
    events.sort(key=lambda event: (event[0], event[1], event[2]))

    previous_tick = 0
    for absolute_tick, _, _, message in events:
        message.time = absolute_tick - previous_tick
        midi_track.append(message)
        previous_tick = absolute_tick
    midi_track.append(MetaMessage("end_of_track", time=0))
    return midi_track


def _conductor_track(project: Project) -> MidiTrack:
    track = MidiTrack()
    track.append(MetaMessage("track_name", name="BeatFlow Conductor", time=0))
    track.append(MetaMessage("set_tempo", tempo=bpm2tempo(project.bpm), time=0))
    track.append(
        MetaMessage(
            "time_signature",
            numerator=project.time_signature.numerator,
            denominator=project.time_signature.denominator,
            time=0,
        )
    )
    major_keys = {"C", "G", "D", "A", "E", "B", "F#", "C#", "F", "Bb", "Eb", "Ab", "Db", "Gb", "Cb"}
    minor_keys = {"A", "E", "B", "F#", "C#", "G#", "D#", "A#", "D", "G", "C", "F", "Bb", "Eb", "Ab"}
    encodable = (
        project.key.mode == Mode.MAJOR and project.key.tonic in major_keys
    ) or (
        project.key.mode == Mode.MINOR and project.key.tonic in minor_keys
    )
    if encodable:
        key_name = project.key.tonic
        if project.key.mode == Mode.MINOR:
            key_name += "m"
        track.append(MetaMessage("key_signature", key=key_name, time=0))
    else:
        track.append(
            MetaMessage(
                "text",
                text=f"Key: {project.key.tonic} {project.key.mode.value}",
                time=0,
            )
        )

    sections = {section.id: section for section in project.sections}
    previous_tick = 0
    current_beat = 0.0
    for occurrence in project.timeline:
        section = sections[occurrence.section_id]
        absolute_tick = round(current_beat * project.ppq)
        label = occurrence.label or section.name
        energy = (
            occurrence.energy_override
            if occurrence.energy_override is not None
            else section.energy
        )
        track.append(
            MetaMessage(
                "marker",
                text=f"{occurrence.id} | {label} | energy={energy:.2f}",
                time=absolute_tick - previous_tick,
            )
        )
        previous_tick = absolute_tick
        current_beat += section.length_bars * project.beats_per_bar
    end_tick = round(current_beat * project.ppq)
    track.append(
        MetaMessage(
            "marker",
            text="END",
            time=end_tick - previous_tick,
        )
    )
    track.append(MetaMessage("end_of_track", time=0))
    return track


def render_project(project: Project, output: str | Path) -> RenderSummary:
    """Validate and save a type-1 MIDI arrangement."""
    notes = materialize_notes(project)
    destination = Path(output).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)

    midi = MidiFile(type=1, ticks_per_beat=project.ppq)
    midi.tracks.append(_conductor_track(project))
    by_track: defaultdict[str, list[MaterializedNote]] = defaultdict(list)
    for note in notes:
        by_track[note.track_id].append(note)
    channels = _assign_channels(project)
    for track in project.tracks:
        midi.tracks.append(
            _events_to_track(
                name=track.name,
                channel=channels[track.id],
                program=track.program,
                percussion=track.percussion,
                performance=track.performance,
                notes=by_track[track.id],
                ppq=project.ppq,
            )
        )
    midi.save(destination)

    bars = sum(
        next(section.length_bars for section in project.sections if section.id == occ.section_id)
        for occ in project.timeline
    )
    beats = bars * project.beats_per_bar
    seconds = beats * (60.0 / project.bpm)
    return RenderSummary(
        output=str(destination),
        midi_tracks=len(midi.tracks),
        notes=len(notes),
        bars=bars,
        beats=beats,
        seconds=round(seconds, 6),
        ppq=project.ppq,
    )
