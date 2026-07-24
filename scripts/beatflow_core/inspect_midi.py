# SPDX-License-Identifier: GPL-3.0-only
"""Round-trip inspection for rendered or third-party MIDI files."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from mido import MidiFile, merge_tracks, tick2second


def inspect_midi(path: str | Path) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    midi = MidiFile(source)
    note_count = 0
    pitches: list[int] = []
    velocities: list[int] = []
    notes_by_channel: Counter[int] = Counter()
    track_names: list[str] = []
    programs: dict[int, int] = {}
    pitched_pitches: list[int] = []
    percussion_pitches: list[int] = []
    track_summaries: list[dict[str, Any]] = []
    control_changes: Counter[int] = Counter()
    for track_index, track in enumerate(midi.tracks):
        name = next(
            (message.name for message in track if message.type == "track_name"),
            f"Track {len(track_names)}",
        )
        track_names.append(name)
        track_pitches: list[int] = []
        track_velocities: list[int] = []
        track_channels: set[int] = set()
        track_programs: dict[str, int] = {}
        track_controls: Counter[int] = Counter()
        for message in track:
            if message.type == "program_change":
                programs[message.channel] = message.program
                track_channels.add(message.channel)
                track_programs[str(message.channel)] = message.program
            elif message.type == "note_on" and message.velocity > 0:
                note_count += 1
                pitches.append(message.note)
                velocities.append(message.velocity)
                notes_by_channel[message.channel] += 1
                track_pitches.append(message.note)
                track_velocities.append(message.velocity)
                track_channels.add(message.channel)
                if message.channel == 9:
                    percussion_pitches.append(message.note)
                else:
                    pitched_pitches.append(message.note)
            elif message.type == "control_change":
                control_changes[message.control] += 1
                track_controls[message.control] += 1
                track_channels.add(message.channel)
        track_summaries.append(
            {
                "index": track_index,
                "name": name,
                "channels": sorted(track_channels),
                "programs_by_channel": track_programs,
                "notes": len(track_pitches),
                "pitch_range": [min(track_pitches), max(track_pitches)]
                if track_pitches
                else None,
                "average_velocity": round(
                    sum(track_velocities) / len(track_velocities), 3
                )
                if track_velocities
                else None,
                "control_changes": {
                    str(key): value for key, value in sorted(track_controls.items())
                },
            }
        )

    tempo = 500_000
    elapsed_seconds = 0.0
    elapsed_ticks = 0
    for message in merge_tracks(midi.tracks):
        elapsed_seconds += tick2second(message.time, midi.ticks_per_beat, tempo)
        elapsed_ticks += message.time
        if message.type == "set_tempo":
            tempo = message.tempo

    return {
        "path": str(source),
        "format": midi.type,
        "tracks": len(midi.tracks),
        "musical_tracks": sum(summary["notes"] > 0 for summary in track_summaries),
        "track_names": track_names,
        "track_summaries": track_summaries,
        "ppq": midi.ticks_per_beat,
        "duration_ticks": elapsed_ticks,
        "duration_seconds": round(elapsed_seconds, 6),
        "notes": note_count,
        "pitch_range": [min(pitches), max(pitches)] if pitches else None,
        "pitched_pitch_range": [min(pitched_pitches), max(pitched_pitches)]
        if pitched_pitches
        else None,
        "percussion_pitch_range": [min(percussion_pitches), max(percussion_pitches)]
        if percussion_pitches
        else None,
        "average_velocity": round(sum(velocities) / len(velocities), 3)
        if velocities
        else None,
        "notes_by_channel": {str(key): value for key, value in sorted(notes_by_channel.items())},
        "programs_by_channel": {str(key): value for key, value in sorted(programs.items())},
        "control_changes": {
            str(key): value for key, value in sorted(control_changes.items())
        },
    }
