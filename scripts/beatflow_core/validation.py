# SPDX-License-Identifier: GPL-3.0-only
"""Semantic validation beyond Pydantic's structural checks."""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ClipKind,
    InvertTransform,
    OctaveTransform,
    Project,
    TrackRole,
    TransposeTransform,
)


class Issue(BaseModel):
    model_config = ConfigDict(extra="forbid")

    severity: Literal["error", "warning"]
    code: str
    path: str
    message: str
    hint: str | None = None


class ValidationReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    valid: bool
    errors: int
    warnings: int
    issues: list[Issue]
    stats: dict[str, Any] = Field(default_factory=dict)


def _duplicates(values: list[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def validate_project(project: Project) -> ValidationReport:
    issues: list[Issue] = []

    def add(
        severity: Literal["error", "warning"],
        code: str,
        path: str,
        message: str,
        hint: str | None = None,
    ) -> None:
        issues.append(
            Issue(severity=severity, code=code, path=path, message=message, hint=hint)
        )

    if "replace this" in project.intent.lower():
        add(
            "warning",
            "placeholder_content",
            "intent",
            "The project intent still contains scaffold instructions.",
            "Replace it with the actual musical brief before rendering.",
        )

    collections = {
        "tracks": project.tracks,
        "sections": project.sections,
        "timeline": project.timeline,
        "clips": project.clips,
        "transformations": project.transformations,
        "links": project.links,
    }
    all_ids: list[str] = []
    for collection_name, objects in collections.items():
        ids = [obj.id for obj in objects]
        all_ids.extend(ids)
        for duplicate in sorted(_duplicates(ids)):
            add(
                "error",
                "duplicate_id",
                collection_name,
                f"ID '{duplicate}' appears more than once in {collection_name}.",
                "Give every object a stable, unique id.",
            )
    for duplicate in sorted(_duplicates(all_ids)):
        locations = [
            name for name, objects in collections.items() if duplicate in {obj.id for obj in objects}
        ]
        if len(locations) > 1:
            add(
                "error",
                "global_id_collision",
                "/",
                f"ID '{duplicate}' is reused across: {', '.join(locations)}.",
                "Use role prefixes such as trk_, sec_, occ_, clip_, tx_, and link_.",
            )

    tracks = {track.id: track for track in project.tracks}
    sections = {section.id: section for section in project.sections}
    occurrences = {occurrence.id: occurrence for occurrence in project.timeline}
    clips = {clip.id: clip for clip in project.clips}
    transforms = {transform.id: transform for transform in project.transformations}

    explicit_channels: defaultdict[int, list[str]] = defaultdict(list)
    pitched_track_count = 0
    for index, track in enumerate(project.tracks):
        path = f"tracks[{index}]"
        if track.percussion:
            if track.channel not in {None, 9}:
                add(
                    "error",
                    "percussion_channel",
                    f"{path}.channel",
                    f"Percussion track '{track.id}' must use MIDI channel 9 or automatic assignment.",
                )
            if track.role != TrackRole.DRUMS:
                add(
                    "warning",
                    "percussion_role",
                    f"{path}.role",
                    f"Percussion track '{track.id}' has role '{track.role.value}'.",
                    "Use role 'drums' unless this is deliberately unconventional.",
                )
        else:
            pitched_track_count += 1
            if track.channel == 9:
                add(
                    "error",
                    "pitched_channel",
                    f"{path}.channel",
                    f"Pitched track '{track.id}' cannot use General MIDI percussion channel 9.",
                )
        if track.channel is not None:
            explicit_channels[track.channel].append(track.id)

    if pitched_track_count > 15:
        add(
            "error",
            "too_many_pitched_tracks",
            "tracks",
            "A single MIDI port supports at most 15 pitched channels.",
            "Merge compatible layers or assign some parts to a second project.",
        )
    for channel, track_ids in explicit_channels.items():
        if len(track_ids) > 1:
            add(
                "warning",
                "shared_channel",
                "tracks",
                f"MIDI channel {channel} is shared by: {', '.join(track_ids)}.",
                "Shared channels also share program changes; use distinct channels unless intentional.",
            )

    for index, occurrence in enumerate(project.timeline):
        if occurrence.section_id not in sections:
            add(
                "error",
                "missing_section",
                f"timeline[{index}].section_id",
                f"Occurrence '{occurrence.id}' references unknown section '{occurrence.section_id}'.",
            )
    for index, section in enumerate(project.sections):
        if "replace-me" in section.tags:
            add(
                "warning",
                "placeholder_content",
                f"sections[{index}].tags",
                f"Section '{section.id}' is still marked as scaffold content.",
            )
    for index, clip in enumerate(project.clips):
        if "replace-me" in clip.tags:
            add(
                "warning",
                "placeholder_content",
                f"clips[{index}].tags",
                f"Clip '{clip.id}' is still marked as scaffold content.",
            )

    active_links_by_occurrence: defaultdict[str, list[str]] = defaultdict(list)
    used_tracks: set[str] = set()
    used_clips: set[str] = set()
    used_transforms: set[str] = set()
    link_signatures: list[tuple[Any, ...]] = []
    beats_per_bar = project.beats_per_bar

    for index, link in enumerate(project.links):
        path = f"links[{index}]"
        section = sections.get(link.section_id)
        track = tracks.get(link.track_id)
        clip = clips.get(link.clip_id)
        link_signatures.append(
            (
                link.section_id,
                link.track_id,
                link.clip_id,
                link.start_bar,
                link.repeat,
                tuple(link.transform_ids),
                tuple(link.occurrence_ids or []),
            )
        )
        if section is None:
            add(
                "error",
                "missing_section",
                f"{path}.section_id",
                f"Link '{link.id}' references unknown section '{link.section_id}'.",
            )
        elif link.start_bar >= section.length_bars:
            add(
                "error",
                "link_outside_section",
                f"{path}.start_bar",
                f"Link '{link.id}' starts at bar {link.start_bar}, outside section '{section.id}'.",
            )
        if track is None:
            add(
                "error",
                "missing_track",
                f"{path}.track_id",
                f"Link '{link.id}' references unknown track '{link.track_id}'.",
            )
        else:
            used_tracks.add(track.id)
        if clip is None:
            add(
                "error",
                "missing_clip",
                f"{path}.clip_id",
                f"Link '{link.id}' references unknown clip '{link.clip_id}'.",
            )
        else:
            used_clips.add(clip.id)
        if track is not None and clip is not None:
            if track.percussion and clip.kind != ClipKind.DRUMS:
                add(
                    "error",
                    "clip_track_kind_mismatch",
                    path,
                    f"Pitched clip '{clip.id}' is linked to percussion track '{track.id}'.",
                )
            if not track.percussion and clip.kind == ClipKind.DRUMS:
                add(
                    "error",
                    "clip_track_kind_mismatch",
                    path,
                    f"Drum clip '{clip.id}' is linked to pitched track '{track.id}'.",
                )
            if not track.percussion:
                for note_index, note in enumerate(clip.notes):
                    transformed_pitch = note.pitch
                    for transform_id in link.transform_ids:
                        transform = transforms.get(transform_id)
                        if isinstance(transform, TransposeTransform):
                            transformed_pitch += transform.semitones
                        elif isinstance(transform, OctaveTransform):
                            transformed_pitch += transform.octaves * 12
                        elif isinstance(transform, InvertTransform):
                            transformed_pitch = (2 * transform.axis_pitch) - transformed_pitch
                    if not 0 <= transformed_pitch <= 127:
                        add(
                            "error",
                            "transformed_pitch_out_of_range",
                            f"{path}.transform_ids",
                            f"Link '{link.id}' transforms clips[{link.clip_id}].notes[{note_index}] "
                            f"to MIDI pitch {transformed_pitch}.",
                            "Reduce the pitch transformation or move the source note into range.",
                        )
        for transform_position, transform_id in enumerate(link.transform_ids):
            if transform_id not in transforms:
                add(
                    "error",
                    "missing_transform",
                    f"{path}.transform_ids[{transform_position}]",
                    f"Link '{link.id}' references unknown transformation '{transform_id}'.",
                )
            else:
                used_transforms.add(transform_id)
        if section is not None and clip is not None and not link.repeat:
            available_beats = (section.length_bars - link.start_bar) * beats_per_bar
            clip_beats = clip.length_bars * beats_per_bar
            if clip_beats > available_beats + 1e-9:
                add(
                    "warning",
                    "clip_truncated_by_section",
                    path,
                    f"Non-repeating clip '{clip.id}' extends beyond section '{section.id}' and will be clipped.",
                )
        target_occurrences = link.occurrence_ids or [
            occurrence.id
            for occurrence in project.timeline
            if occurrence.section_id == link.section_id
        ]
        for occurrence_id in target_occurrences:
            occurrence = occurrences.get(occurrence_id)
            if occurrence is None:
                add(
                    "error",
                    "missing_occurrence",
                    f"{path}.occurrence_ids",
                    f"Link '{link.id}' targets unknown occurrence '{occurrence_id}'.",
                )
            elif occurrence.section_id != link.section_id:
                add(
                    "error",
                    "occurrence_section_mismatch",
                    f"{path}.occurrence_ids",
                    f"Occurrence '{occurrence_id}' belongs to '{occurrence.section_id}', not '{link.section_id}'.",
                )
            else:
                active_links_by_occurrence[occurrence_id].append(link.id)

    for signature in _duplicates(link_signatures):
        duplicate_ids = [
            link.id
            for link in project.links
            if (
                link.section_id,
                link.track_id,
                link.clip_id,
                link.start_bar,
                link.repeat,
                tuple(link.transform_ids),
                tuple(link.occurrence_ids or []),
            )
            == signature
        ]
        add(
            "warning",
            "duplicate_link",
            "links",
            f"Equivalent links may double notes: {', '.join(duplicate_ids)}.",
        )

    for index, clip in enumerate(project.clips):
        clip_beats = clip.length_bars * beats_per_bar
        exact_duplicates = Counter(
            (note.pitch, note.start, note.duration, note.velocity) for note in clip.notes
        )
        for note_index, note in enumerate(clip.notes):
            if note.start >= clip_beats:
                add(
                    "error",
                    "note_starts_outside_clip",
                    f"clips[{index}].notes[{note_index}].start",
                    f"Note starts at beat {note.start}, outside clip '{clip.id}' ({clip_beats:g} beats).",
                )
            elif note.start + note.duration > clip_beats + 1e-9:
                add(
                    "error",
                    "note_ends_outside_clip",
                    f"clips[{index}].notes[{note_index}].duration",
                    f"Note ends beyond clip '{clip.id}' ({clip_beats:g} beats).",
                    "Shorten the note or increase clip.length_bars.",
                )
        if any(count > 1 for count in exact_duplicates.values()):
            add(
                "warning",
                "duplicate_note",
                f"clips[{index}].notes",
                f"Clip '{clip.id}' contains exact duplicate notes.",
            )

    for occurrence in project.timeline:
        if not active_links_by_occurrence[occurrence.id]:
            add(
                "warning",
                "silent_occurrence",
                f"timeline.{occurrence.id}",
                f"Occurrence '{occurrence.id}' has no active composition links.",
                "Keep it only if the silence is intentional.",
            )
    for track_id in sorted(set(tracks) - used_tracks):
        add(
            "warning",
            "unused_track",
            f"tracks.{track_id}",
            f"Track '{track_id}' is never used by a link.",
        )
    for clip_id in sorted(set(clips) - used_clips):
        add(
            "warning",
            "unused_clip",
            f"clips.{clip_id}",
            f"Clip '{clip_id}' is never used by a link.",
        )
    for transform_id in sorted(set(transforms) - used_transforms):
        add(
            "warning",
            "unused_transform",
            f"transformations.{transform_id}",
            f"Transformation '{transform_id}' is never used by a link.",
        )

    total_bars = sum(
        sections[occurrence.section_id].length_bars
        for occurrence in project.timeline
        if occurrence.section_id in sections
    )
    error_count = sum(issue.severity == "error" for issue in issues)
    warning_count = sum(issue.severity == "warning" for issue in issues)
    return ValidationReport(
        valid=error_count == 0,
        errors=error_count,
        warnings=warning_count,
        issues=issues,
        stats={
            "bars": total_bars,
            "beats": total_bars * beats_per_bar,
            "tracks": len(project.tracks),
            "sections": len(project.sections),
            "occurrences": len(project.timeline),
            "clips": len(project.clips),
            "links": len(project.links),
            "notes_in_clips": sum(len(clip.notes) for clip in project.clips),
        },
    )
