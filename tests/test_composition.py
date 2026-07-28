# SPDX-License-Identifier: GPL-3.0-only

from __future__ import annotations

import json
import tempfile
import unittest
from fractions import Fraction
from pathlib import Path

from beatflow_core.composer import SongBuilder, beat, chord, midi, next_chord, scale
from beatflow_core.composition_compiler import compile_composition
from beatflow_core.composition_diagnostics import (
    compare_compositions,
    diagnose_composition,
)
from beatflow_core.composition_models import Composition
from beatflow_core.composition_validation import validate_composition
from beatflow_core.harmony_utils import normalize_chord_symbol, parse_chord_symbol
from beatflow_core.inspect_midi import inspect_midi
from beatflow_core.renderer import render_project
from beatflow_core.validation import validate_project


def small_composition(title: str = "Small Composition") -> Composition:
    song = SongBuilder(
        title,
        intent="Test exact rhythm, independent roles, and deterministic realization.",
        priorities=["clear phrase boundary", "audible role contrast"],
        exclusions=["style-specific engine templates"],
        bpm=112,
        tonic="C",
        mode="major",
        ppq=960,
    )
    song.track(
        "trk_drums", "Drums", percussion=True, channel=9, performance="percussive"
    )
    song.track(
        "trk_bass",
        "Bass",
        program=32,
        performance="plucked",
        monophonic=True,
        low=36,
        center=43,
        high=55,
    )
    song.track(
        "trk_keys",
        "Keys",
        program=0,
        performance="percussive",
        low=48,
        center=64,
        high=79,
    )
    song.track(
        "trk_lead",
        "Lead",
        program=40,
        performance="sustained",
        monophonic=True,
        low=60,
        center=70,
        high=84,
    )

    section = song.section("sec_a", "A", bars=2, energy=0.58)
    section.chord_bar(1, "CM7", function="home")
    section.chord_bar(2, "Am7", function="departure")
    section.phrase(
        "phr_question_answer",
        beat(0),
        beat(8),
        functions=["foreground"],
        attention="foreground",
        boundary_strength=0.3,
        max_continuous=beat(4),
        tension=(0.2, 0.65, 0.25),
        goal="Ask, leave space, then answer with a longer arrival.",
    )
    section.arrival(
        "arr_answer",
        "phr_question_answer",
        beat(6),
        functions=["foreground"],
        closure="closed",
        strength=0.75,
        min_hold=beat(1),
        harmonic_stability="resolved",
        post_action="stop",
        max_post_attacks=0,
        goal="Let the answer land on the local harmony and remain still.",
    )
    section.phrase_stage(
        "stg_question",
        "phr_question_answer",
        beat(1, 3),
        beat(8, 3),
        functions=["foreground"],
        role="initiate",
        min_attacks=3,
        max_attacks=3,
        exit_behavior="breathe",
        goal="State the question compactly, then leave a real gap.",
    )
    section.phrase_stage(
        "stg_answer",
        "phr_question_answer",
        beat(13, 3),
        beat(19, 6),
        functions=["foreground"],
        role="release",
        min_attacks=3,
        max_attacks=3,
        exit_behavior="arrive",
        focus=True,
        focus_cue="duration",
        goal="Answer with the phrase's longest structural tone.",
    )
    section.silence(
        "sil_lead_breath",
        beat(3),
        beat(1),
        functions=["foreground"],
        description="Leave the foreground empty before its answer.",
    )

    drums = section.segment(
        "seg_drums",
        "Pulse",
        track="trk_drums",
        functions=["pulse"],
        start=beat(0),
        duration=beat(8),
    )
    drums.drums("closed_hat", [beat(i) for i in range(8)], velocities=62)
    drums.drums("kick", [beat(0), beat(3), beat(5)], velocities=86)
    drums.drums("snare", [beat(1), beat(5)], velocities=82)
    drums.end()

    bass = section.segment(
        "seg_bass",
        "Low motion",
        track="trk_bass",
        functions=["low"],
        start=beat(0),
        duration=beat(8),
    )
    bass.note(beat(0), beat(3, 4), chord(1), register_hint=43)
    bass.note(beat(3, 2), beat(1, 2), chord(5), contour="up")
    bass.note(beat(3), beat(3, 4), next_chord(1), contour="down")
    bass.note(beat(4), beat(1), chord(1), register_hint=45)
    bass.note(beat(11, 2), beat(1, 2), chord(3), contour="up")
    bass.note(beat(7), beat(3, 4), chord(5), contour="down")
    bass.end()

    keys = section.segment(
        "seg_keys",
        "Changing chord texture",
        track="trk_keys",
        functions=["harmony"],
        start=beat(0),
        duration=beat(8),
    )
    keys.chord(beat(1, 2), beat(1, 2), notes=3)
    keys.chord(beat(11, 4), beat(1, 4), notes=2)
    keys.chord(beat(4), beat(3, 4), notes=4, omit_root=False)
    keys.chord(beat(13, 2), beat(1, 2), notes=3)
    keys.end()

    lead = section.segment(
        "seg_lead",
        "Question and answer",
        track="trk_lead",
        functions=["foreground"],
        start=beat(1, 3),
        duration=beat(22, 3),
    )
    lead.note(beat(1, 3), beat(2, 3), chord(3), contour="up", motif="q")
    lead.note(beat(4, 3), beat(1, 3), scale(4), contour="up", motif="q")
    lead.note(beat(2), beat(1), chord(5), contour="up", motif="q")
    lead.note(beat(13, 3), beat(1, 3), chord(3), contour="down", motif="a")
    lead.note(beat(5), beat(1, 2), scale(2), contour="down", motif="a")
    lead.note(beat(6), beat(3, 2), chord(1), contour="down", importance=0.9)
    lead.end()

    section.end()
    song.play("occ_a", "sec_a")
    song.interaction(
        "int_lead_pulse",
        "sec_a",
        source="foreground",
        target="pulse",
        minimum=0.0,
        maximum=0.7,
        description="The line may meet the pulse, but should not trace it.",
    )
    return song.build()


def continuous_two_voice_composition() -> Composition:
    song = SongBuilder(
        "Continuous Two Voice Texture",
        intent="Exercise shared-release and density diagnostics.",
        bpm=108,
        tonic="D",
        mode="minor",
        meter=(4, 4),
    )
    song.track(
        "trk_upper",
        "Upper",
        program=0,
        monophonic=True,
        low=60,
        center=69,
        high=84,
    )
    song.track(
        "trk_lower",
        "Lower",
        program=0,
        monophonic=True,
        low=36,
        center=50,
        high=62,
    )
    section = song.section("sec_continuous", "Continuous", bars=8, energy=0.7)
    upper = section.segment(
        "seg_upper",
        "Upper line",
        track="trk_upper",
        functions=["foreground"],
        start=beat(0),
        duration=beat(32),
    )
    lower = section.segment(
        "seg_lower",
        "Lower line",
        track="trk_lower",
        functions=["counterline"],
        start=beat(0),
        duration=beat(32),
    )
    for onset in range(32):
        upper.note(beat(onset), beat(1), midi(69 + onset % 3))
        lower.note(beat(onset), beat(1), midi(50 - onset % 3))
    upper.end()
    lower.end()
    section.end()
    song.play("occ_continuous", "sec_continuous")
    return song.build()


def arranged_composition() -> Composition:
    song = SongBuilder(
        "Arrangement Test",
        intent="Reuse one section with a distinct final occurrence.",
        bpm=120,
        tonic="C",
        mode="major",
        target_duration_seconds=8,
    )
    song.track(
        "trk_lead",
        "Lead",
        program=0,
        monophonic=True,
        low=48,
        center=64,
        high=84,
    )
    song.track(
        "trk_drums",
        "Drums",
        percussion=True,
        channel=9,
        performance="percussive",
    )
    section = song.section("sec_hook", "Hook", bars=2, energy=0.45)
    section.chord_bar(1, "C").chord_bar(2, "G7")
    base = section.segment(
        "seg_base",
        "Base line",
        track="trk_lead",
        functions=["foreground"],
        start=beat(0),
        duration=beat(8),
    )
    base.note(beat(0), beat(1), chord(1))
    base.note(beat(2), beat(1), chord(3), contour="up")
    base.note(beat(4), beat(1), chord(5), contour="up")
    base.note(beat(6), beat(1), chord(3), contour="down")
    base.end()
    final = section.segment(
        "seg_final",
        "Final alternative",
        track="trk_lead",
        functions=["foreground"],
        start=beat(0),
        duration=beat(8),
        default_enabled=False,
    )
    final.note(beat(0), beat(1, 2), chord(3))
    final.note(beat(1), beat(1, 2), chord(5), contour="up")
    final.note(beat(2), beat(2), chord(1), contour="up")
    final.note(beat(5), beat(2), chord(1), contour="down")
    final.end()
    drums = section.segment(
        "seg_drums",
        "Pulse",
        track="trk_drums",
        functions=["pulse"],
        start=beat(0),
        duration=beat(8),
    )
    drums.drums("closed_hat", [beat(index) for index in range(8)], velocities=60)
    drums.end()
    section.end()
    song.play(
        "occ_first",
        "sec_hook",
        development="statement",
        energy=0.35,
    )
    song.play(
        "occ_final",
        "sec_hook",
        development="climax",
        energy=0.9,
        intent="Use the alternate line in a higher register.",
    )
    song.arrange("occ_final", "seg_base", enabled=False)
    song.arrange(
        "occ_final",
        "seg_final",
        enabled=True,
        octave=1,
        velocity=1.2,
        gate=0.75,
    )
    return song.build()


def foreground_stress_composition() -> Composition:
    song = SongBuilder(
        "Foreground Stress",
        intent="Expose a copied one-bar line competing with a designed chord top voice.",
        bpm=100,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_keys",
        "Keys",
        program=4,
        performance="percussive",
        low=48,
        center=64,
        high=84,
    )
    song.track(
        "trk_lead",
        "Lead",
        program=0,
        monophonic=True,
        low=60,
        center=72,
        high=88,
    )
    section = song.section("sec_stress", "Stress", bars=8, energy=0.5)
    for bar in range(1, 9):
        section.chord_bar(bar, "CM7")
    keys = section.segment(
        "seg_keys",
        "Top voice",
        track="trk_keys",
        functions=["harmony"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        keys.chord(
            beat(bar * 4),
            beat(3),
            notes=4,
            omit_root=True,
            top_target=scale(5),
        )
    keys.end()
    lead = section.segment(
        "seg_lead",
        "Copied cell",
        track="trk_lead",
        functions=["foreground"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        base = bar * 4
        lead.note(beat(base), beat(1, 2), scale(1), motif="copied")
        lead.note(beat(base * 2 + 2, 2), beat(1, 2), scale(4), motif="copied")
        lead.note(beat(base * 2 + 4, 2), beat(1), scale(2), motif="copied")
    lead.end()
    section.end()
    song.play("occ_stress", "sec_stress")
    return song.build()


def foreground_handoff_composition() -> Composition:
    song = SongBuilder(
        "Foreground Handoff",
        intent="Let piano answers alternate with a designed chord top voice.",
        bpm=84,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_keys",
        "Keys",
        program=4,
        performance="percussive",
        low=48,
        center=64,
        high=84,
    )
    song.track(
        "trk_piano",
        "Piano",
        program=0,
        low=60,
        center=72,
        high=88,
    )
    section = song.section("sec_handoff", "Handoff", bars=8, energy=0.5)
    for bar in range(1, 9):
        section.chord_bar(bar, "CM7")
    keys = section.segment(
        "seg_handoff_keys",
        "Top voice",
        track="trk_keys",
        functions=["harmony"],
        start=beat(0),
        duration=beat(32),
    )
    piano = section.segment(
        "seg_handoff_piano",
        "Answers",
        track="trk_piano",
        functions=["foreground"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        base = bar * 4
        keys.chord(
            beat(base),
            beat(3, 2),
            notes=4,
            omit_root=True,
            top_target=scale(5),
        )
        piano.note(beat(base * 2 + 4, 2), beat(1, 2), scale(3))
        piano.note(beat(base * 2 + 6, 2), beat(1, 2), scale(2))
    keys.end()
    piano.end()
    section.end()
    song.play("occ_handoff", "sec_handoff")
    return song.build()


def diffuse_pulse_composition() -> Composition:
    song = SongBuilder(
        "Diffuse Pulse",
        intent="Expose a percussion layer with too many independent beat phases.",
        bpm=90,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_drums",
        "Drums",
        percussion=True,
        channel=9,
        performance="percussive",
    )
    section = song.section("sec_pulse", "Pulse", bars=8, energy=0.4)
    pulse = section.segment(
        "seg_pulse",
        "Diffuse timing",
        track="trk_drums",
        functions=["pulse"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        for phase in range(9):
            pulse.drum(
                beat((bar * 48) + phase, 12),
                beat(1, 24),
                "closed_hat",
                velocity=54,
            )
    pulse.end()
    section.end()
    song.play("occ_pulse", "sec_pulse")
    return song.build()


def unanchored_foreground_composition() -> Composition:
    song = SongBuilder(
        "Unanchored Foreground",
        intent="Expose a dense foreground that obscures the beat without an anchor.",
        bpm=96,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_lead",
        "Lead",
        program=0,
        monophonic=True,
        low=60,
        center=72,
        high=88,
    )
    section = song.section("sec_unanchored", "Unanchored", bars=8, energy=0.5)
    for bar in range(1, 9):
        section.chord_bar(bar, "CM7")
    lead = section.segment(
        "seg_unanchored",
        "Quarter-beat offsets",
        track="trk_lead",
        functions=["foreground"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        base = bar * 4
        lead.note(beat(base * 4 + 1, 4), beat(1, 2), scale(1))
        lead.note(beat(base * 4 + 7, 4), beat(1, 2), scale(4))
        lead.note(beat(base * 4 + 13, 4), beat(1, 2), scale(2))
    lead.end()
    section.end()
    song.play("occ_unanchored", "sec_unanchored")
    return song.build()


def floating_harmony_composition() -> Composition:
    song = SongBuilder(
        "Floating Harmony",
        intent="Expose harmony attacks that rarely establish a primary beat.",
        bpm=92,
        tonic="C",
        mode="major",
    )
    song.track("trk_keys", "Keys", program=4, low=48, center=64, high=84)
    section = song.section("sec_float", "Float", bars=8, energy=0.5)
    for bar in range(1, 9):
        section.chord_bar(bar, "CM7")
    keys = section.segment(
        "seg_float",
        "Late comping",
        track="trk_keys",
        functions=["harmony"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        keys.chord(beat(bar * 16 + 1, 4), beat(3, 4), notes=4)
        keys.chord(beat(bar * 16 + 9, 4), beat(1, 2), notes=3)
    keys.end()
    section.end()
    song.play("occ_float", "sec_float")
    return song.build()


def reused_harmony_rhythm_composition() -> Composition:
    song = SongBuilder(
        "Reused Harmony Rhythm",
        intent="Expose one comping rhythm copied into every formal section.",
        bpm=96,
        tonic="C",
        mode="major",
    )
    song.track("trk_keys", "Keys", program=4, low=48, center=64, high=84)
    for index in range(4):
        section = song.section(
            f"sec_{index}",
            f"Section {index}",
            bars=4,
            energy=0.3 + index * 0.1,
        )
        for bar in range(1, 5):
            section.chord_bar(bar, "CM7")
        keys = section.segment(
            f"seg_{index}",
            "Copied comping",
            track="trk_keys",
            functions=["harmony"],
            start=beat(0),
            duration=beat(16),
        )
        for bar in range(4):
            keys.chord(beat(bar * 4), beat(2), notes=4)
            keys.chord(beat(bar * 4 + 2), beat(1), notes=3)
        keys.end()
        section.end()
        song.play(f"occ_{index}", f"sec_{index}")
    return song.build()


def unresolved_structural_tones_composition() -> Composition:
    song = SongBuilder(
        "Unresolved Structural Tones",
        intent="Expose non-chord tones on primary beats without stepwise resolution.",
        bpm=88,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_lead",
        "Lead",
        program=0,
        monophonic=True,
        low=60,
        center=72,
        high=88,
    )
    section = song.section("sec_tones", "Tones", bars=8, energy=0.5)
    for bar in range(1, 9):
        section.chord_bar(bar, "CM7")
    lead = section.segment(
        "seg_tones",
        "Unresolved line",
        track="trk_lead",
        functions=["foreground"],
        start=beat(0),
        duration=beat(32),
    )
    for bar in range(8):
        lead.note(beat(bar * 4), beat(1), midi(61))
        lead.note(beat(bar * 4 + 2), beat(1), midi(66))
    lead.end()
    section.end()
    song.play("occ_tones", "sec_tones")
    return song.build()


class BeatFlowCompositionTests(unittest.TestCase):
    def test_compound_meter_at_uses_the_dotted_quarter_tactus(self) -> None:
        song = SongBuilder(
            "Compound Meter",
            intent="Test meter-aware beat addressing.",
            bpm=90,
            tonic="C",
            mode="major",
            meter=(6, 8),
        )
        self.assertEqual(song.at(1, 2).fraction, Fraction(3, 2))
        self.assertEqual(song.at(2, 1).fraction, Fraction(3))

    def test_meter_aware_duration_helpers(self) -> None:
        song = SongBuilder(
            "Meter Durations",
            intent="Exercise perceptual duration helpers.",
            bpm=108,
            tonic="D",
            mode="minor",
            meter=(6, 8),
        )
        self.assertEqual(song.tactus(1).fraction, Fraction(3, 2))
        self.assertEqual(song.tactus(5, 2).fraction, Fraction(15, 4))
        self.assertEqual(song.bars(2).fraction, Fraction(6))

    def test_phrase_grouping_and_structural_stage_are_validated(self) -> None:
        payload = small_composition().model_dump(mode="json")
        phrase = payload["sections"][0]["phrases"][0]
        phrase["grouping"] = "regular"
        phrase["subphrase_bars"] = [1, 1]
        stage = payload["sections"][0]["phrase_stages"][0]
        stage["metric_role"] = "structural"
        stage["entry_anchor"] = "bar_downbeat"
        report = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "structural_stage_off_subphrase_boundary",
            {issue.code for issue in report.issues},
        )

        payload = small_composition().model_dump(mode="json")
        phrase = payload["sections"][0]["phrases"][0]
        phrase["grouping"] = "regular"
        phrase["subphrase_bars"] = [1]
        report = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "phrase_grouping_duration_mismatch",
            {issue.code for issue in report.issues},
        )

        payload = small_composition().model_dump(mode="json")
        phrase = payload["sections"][0]["phrases"][0]
        phrase["grouping"] = "regular"
        phrase["subphrase_bars"] = [1, 2]
        with self.assertRaises(ValueError):
            Composition.model_validate(payload)

    def test_regular_phrase_reports_repeated_subtractive_activity(self) -> None:
        song = SongBuilder(
            "Subtractive Six Eight",
            intent="Expose a repeated seven-active-beat habit.",
            bpm=108,
            tonic="D",
            mode="minor",
            meter=(6, 8),
        )
        song.track(
            "trk_line",
            "Line",
            monophonic=True,
            low=60,
            center=69,
            high=84,
        )
        section = song.section("sec_a", "A", bars=8, energy=0.6)
        for index, bar in enumerate([1, 5], start=1):
            section.phrase(
                f"phr_{index}",
                song.at(bar),
                song.bars(4),
                functions=["foreground"],
                attention="foreground",
                boundary_strength=0.0,
                grouping="regular",
                subphrase_bars=[2, 2],
                goal="Exercise a regular four-bar grouping.",
            )
        line = section.segment(
            "seg_line",
            "Repeated subtractive phrase rhythm",
            track="trk_line",
            functions=["foreground"],
            start=song.at(1),
            duration=song.bars(8),
        )
        for phrase_start in [Fraction(0), Fraction(12)]:
            for tactus_index in [0, 1, 2, 4, 5, 6, 7]:
                onset = phrase_start + Fraction(3, 2) * tactus_index
                line.note(
                    song.time(onset),
                    song.tactus(1),
                    midi(67 + tactus_index % 4),
                )
        line.end()
        section.end()
        song.play("occ_a", "sec_a")
        report = diagnose_composition(song.build())
        self.assertIn(
            "repeated_subtractive_phrase_activity",
            {issue.code for issue in report.issues},
        )
        metrics = report.metrics["sections"]["sec_a"]["phrases"]["phr_1"]
        self.assertEqual(metrics["duration_bars"], 4.0)
        self.assertEqual(metrics["duration_tactus"], 8.0)
        self.assertEqual(metrics["subphrase_boundary_tactus"], [4])
        self.assertEqual(metrics["tactus_activity_pattern"], "11101111")
        self.assertEqual(metrics["active_tactus_runs"], [3, 4])
        self.assertEqual(metrics["full_tactus_rest_positions"], [4])

    def test_regular_phrase_detects_unplanned_hypermetric_split(self) -> None:
        song = SongBuilder(
            "Unplanned Split",
            intent="Expose a restart away from the declared subphrase boundary.",
            bpm=108,
            tonic="D",
            mode="minor",
            meter=(6, 8),
        )
        song.track(
            "trk_line",
            "Line",
            monophonic=True,
            low=60,
            center=69,
            high=84,
        )
        section = song.section("sec_a", "A", bars=4, energy=0.6)
        section.phrase(
            "phr_main",
            song.at(1),
            song.bars(4),
            functions=["foreground"],
            boundary_strength=0.0,
            grouping="regular",
            subphrase_bars=[2, 2],
        )
        line = section.segment(
            "seg_line",
            "Off-boundary restart",
            track="trk_line",
            functions=["foreground"],
            start=song.at(1),
            duration=song.bars(4),
        )
        for tactus_index in [0, 1, 3, 4, 5, 6, 7]:
            line.note(
                song.tactus(tactus_index),
                song.tactus(1),
                midi(67 + tactus_index % 4),
            )
        line.end()
        section.end()
        song.play("occ_a", "sec_a")
        report = diagnose_composition(song.build())
        self.assertIn(
            "unplanned_hypermetric_split",
            {issue.code for issue in report.issues},
        )

    def test_occurrence_arrangement_reuses_material_with_a_real_variant(self) -> None:
        composition = arranged_composition()
        report = validate_composition(composition)
        self.assertTrue(report.valid, report.model_dump_json(indent=2))
        self.assertEqual(report.stats["seconds"], 8.0)
        project = compile_composition(composition)
        clip_ids = {clip.id for clip in project.clips}
        self.assertIn("c1c_occ_first_seg_base", clip_ids)
        self.assertNotIn("c1c_occ_first_seg_final", clip_ids)
        self.assertIn("c1c_occ_final_seg_final", clip_ids)
        self.assertNotIn("c1c_occ_final_seg_base", clip_ids)
        first = next(
            clip for clip in project.clips if clip.id == "c1c_occ_first_seg_base"
        )
        final = next(
            clip for clip in project.clips if clip.id == "c1c_occ_final_seg_final"
        )
        self.assertGreater(min(note.pitch for note in final.notes), min(note.pitch for note in first.notes))
        self.assertEqual([section.energy for section in project.sections], [0.35, 0.9])

    def test_alternative_monophonic_segments_may_overlap_when_not_coactive(self) -> None:
        report = validate_composition(arranged_composition())
        self.assertTrue(report.valid, report.model_dump_json(indent=2))

    def test_coactive_alternatives_are_rejected(self) -> None:
        payload = arranged_composition().model_dump(mode="json")
        final_occurrence = payload["timeline"][1]
        final_occurrence["treatments"] = [
            item
            for item in final_occurrence["treatments"]
            if item["segment_id"] != "seg_base"
        ]
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "overlapping_monophonic_events",
            {issue.code for issue in report.issues},
        )

    def test_missing_treatment_segment_is_rejected(self) -> None:
        payload = arranged_composition().model_dump(mode="json")
        payload["timeline"][0]["treatments"].append(
            {
                "segment_id": "seg_missing",
                "enabled": False,
                "transpose_semitones": 0,
                "octave_shift": 0,
                "velocity_scale": 1.0,
                "gate_scale": 1.0,
            }
        )
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "missing_treatment_segment",
            {issue.code for issue in report.issues},
        )

    def test_target_duration_and_declared_development_are_diagnosed(self) -> None:
        payload = arranged_composition().model_dump(mode="json")
        payload["target_duration_seconds"] = 20
        payload["timeline"][1]["energy"] = 0.35
        payload["timeline"][1]["treatments"] = []
        payload["sections"][0]["segments"][1]["default_enabled"] = True
        payload["sections"][0]["segments"][0]["default_enabled"] = False
        composition = Composition.model_validate(payload)
        report = diagnose_composition(composition)
        codes = {issue.code for issue in report.issues}
        self.assertIn("duration_outside_target", codes)
        self.assertIn("development_without_arrangement_change", codes)

    def test_percussion_pitch_treatment_is_rejected(self) -> None:
        payload = arranged_composition().model_dump(mode="json")
        payload["timeline"][0]["treatments"].append(
            {
                "segment_id": "seg_drums",
                "enabled": None,
                "transpose_semitones": 2,
                "octave_shift": 0,
                "velocity_scale": 1.0,
                "gate_scale": 1.0,
            }
        )
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "percussion_pitch_treatment",
            {issue.code for issue in report.issues},
        )

    def test_gate_treatment_cannot_escape_segment_boundary(self) -> None:
        payload = arranged_composition().model_dump(mode="json")
        treatment = next(
            item
            for item in payload["timeline"][1]["treatments"]
            if item["segment_id"] == "seg_final"
        )
        treatment["gate_scale"] = 2.0
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "treated_event_outside_segment",
            {issue.code for issue in report.issues},
        )

    def test_candidate_comparison_includes_occurrence_arrangement(self) -> None:
        original = arranged_composition()
        payload = original.model_dump(mode="json")
        payload["title"] = "Arrangement Variant"
        payload["timeline"][1]["energy"] = 0.7
        variant = Composition.model_validate(payload)
        report = compare_compositions([original, variant])
        self.assertLess(
            report["pairs"][0]["function_similarity"]["form"],
            1.0,
        )

    def test_style_neutral_composition_validates_compiles_and_renders(self) -> None:
        composition = small_composition()
        report = validate_composition(composition)
        self.assertTrue(report.valid, report.model_dump_json(indent=2))
        project = compile_composition(composition)
        self.assertTrue(validate_project(project).valid)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "small.mid"
            summary = render_project(project, destination)
            inspection = inspect_midi(destination)
        self.assertEqual(summary.notes, inspection["notes"])
        self.assertEqual(inspection["musical_tracks"], 4)

    def test_chord_top_target_controls_the_highest_voice(self) -> None:
        payload = small_composition().model_dump(mode="json")
        keys_segment = next(
            segment
            for segment in payload["sections"][0]["segments"]
            if segment["id"] == "seg_keys"
        )
        first_chord = next(
            event for event in keys_segment["events"] if event["type"] == "chord"
        )
        first_chord["top_target"] = {
            "basis": "scale",
            "degree": 2,
            "alter": 0,
            "midi": None,
            "semitones": None,
        }
        composition = Composition.model_validate(payload)
        report = validate_composition(composition)
        self.assertTrue(report.valid, report.model_dump_json(indent=2))
        project = compile_composition(composition)
        clip = next(clip for clip in project.clips if clip.id.endswith("_seg_keys"))
        first_onset = min(note.start for note in clip.notes)
        voicing = [note.pitch for note in clip.notes if note.start == first_onset]
        self.assertEqual(max(voicing) % 12, 2)
        self.assertIn(2, {pitch % 12 for pitch in voicing})

        absolute_payload = small_composition().model_dump(mode="json")
        absolute_keys = next(
            segment
            for segment in absolute_payload["sections"][0]["segments"]
            if segment["id"] == "seg_keys"
        )
        absolute_first = next(
            event for event in absolute_keys["events"] if event["type"] == "chord"
        )
        absolute_first["top_target"] = {
            "basis": "absolute",
            "degree": None,
            "alter": 0,
            "midi": 73,
            "semitones": None,
        }
        absolute = Composition.model_validate(absolute_payload)
        absolute_project = compile_composition(absolute)
        absolute_clip = next(
            clip for clip in absolute_project.clips if clip.id.endswith("_seg_keys")
        )
        absolute_onset = min(note.start for note in absolute_clip.notes)
        absolute_voicing = [
            note.pitch
            for note in absolute_clip.notes
            if note.start == absolute_onset
        ]
        self.assertEqual(max(absolute_voicing), 73)

    def test_absolute_chord_top_target_must_fit_the_voicing_range(self) -> None:
        payload = small_composition().model_dump(mode="json")
        keys_segment = next(
            segment
            for segment in payload["sections"][0]["segments"]
            if segment["id"] == "seg_keys"
        )
        first_chord = next(
            event for event in keys_segment["events"] if event["type"] == "chord"
        )
        first_chord["top_target"] = {
            "basis": "absolute",
            "degree": None,
            "alter": 0,
            "midi": 100,
            "semitones": None,
        }
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "chord_top_target_outside_range",
            {issue.code for issue in report.issues},
        )

    def test_rational_triplets_survive_compilation(self) -> None:
        project = compile_composition(small_composition())
        clip = next(item for item in project.clips if item.id.endswith("seg_lead"))
        self.assertIn(round(1 / 3, 6), {round(note.start, 6) for note in clip.notes})
        self.assertIn(round(2 / 3, 6), {round(note.duration, 6) for note in clip.notes})

    def test_explicit_duration_is_not_derived_from_next_onset(self) -> None:
        project = compile_composition(small_composition())
        clip = next(item for item in project.clips if item.id.endswith("seg_lead"))
        first = min(clip.notes, key=lambda note: note.start)
        self.assertAlmostEqual(first.duration, 2 / 3)

    def test_schema_has_no_swing_or_genre_template_fields(self) -> None:
        schema = json.dumps(Composition.model_json_schema()).lower()
        self.assertNotIn('"swing"', schema)
        self.assertNotIn("groove_template", schema)
        self.assertNotIn("acid_jazz", schema)

    def test_no_cadence_or_drum_pattern_is_required(self) -> None:
        composition = small_composition()
        payload = composition.model_dump(mode="json")
        payload["sections"][0]["segments"] = [
            segment
            for segment in payload["sections"][0]["segments"]
            if "pulse" not in segment["functions"]
        ]
        payload["tracks"] = [
            track for track in payload["tracks"] if track["id"] != "trk_drums"
        ]
        payload["interactions"] = []
        report = validate_composition(Composition.model_validate(payload))
        self.assertTrue(report.valid, report.model_dump_json(indent=2))

    def test_monophonic_overlap_is_rejected(self) -> None:
        payload = small_composition().model_dump(mode="json")
        lead = next(
            item
            for item in payload["sections"][0]["segments"]
            if item["id"] == "seg_lead"
        )
        lead["events"][0]["duration"] = {"numerator": 4, "denominator": 1}
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "overlapping_monophonic_events",
            {issue.code for issue in report.issues},
        )

    def test_same_monophonic_track_in_different_sections_does_not_overlap(self) -> None:
        payload = small_composition().model_dump(mode="json")
        second = dict(payload["sections"][0])
        second["id"] = "sec_b"
        second["name"] = "B"
        second["segments"] = [
            {**segment, "id": f"{segment['id']}_b"}
            for segment in payload["sections"][0]["segments"]
        ]
        payload["sections"].append(second)
        payload["timeline"].append(
            {"id": "occ_b", "section_id": "sec_b", "label": ""}
        )
        report = validate_composition(Composition.model_validate(payload))
        self.assertTrue(report.valid, report.model_dump_json(indent=2))

    def test_unrepresentable_fraction_is_rejected(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["segments"][0]["events"][0]["onset"] = {
            "numerator": 1,
            "denominator": 7,
        }
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "time_not_representable_at_ppq",
            {issue.code for issue in report.issues},
        )

    def test_diagnostics_warn_but_do_not_reject_declared_interaction(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["interactions"][0]["minimum_overlap"] = 0.9
        payload["interactions"][0]["maximum_overlap"] = 1.0
        composition = Composition.model_validate(payload)
        report = diagnose_composition(composition)
        self.assertTrue(report.structurally_valid)
        self.assertIn(
            "interaction_outside_declared_range",
            {issue.code for issue in report.issues},
        )

    def test_declared_silence_is_validated_and_diagnosed(self) -> None:
        composition = small_composition()
        clean_report = diagnose_composition(composition)
        self.assertNotIn(
            "declared_silence_occupied",
            {issue.code for issue in clean_report.issues},
        )
        clean_metrics = clean_report.metrics["sections"]["sec_a"][
            "declared_silences"
        ]["sil_lead_breath"]
        self.assertEqual(clean_metrics["overlapping_events"], 0)

        payload = composition.model_dump(mode="json")
        payload["sections"][0]["silences"][0]["onset"] = {
            "numerator": 2,
            "denominator": 1,
        }
        occupied_report = diagnose_composition(Composition.model_validate(payload))
        self.assertIn(
            "declared_silence_occupied",
            {issue.code for issue in occupied_report.issues},
        )

    def test_silence_outside_section_is_rejected(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["silences"][0]["onset"] = {
            "numerator": 8,
            "denominator": 1,
        }
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "silence_out_of_bounds",
            {issue.code for issue in report.issues},
        )

    def test_declared_phrase_reports_boundary_and_continuity(self) -> None:
        report = diagnose_composition(small_composition())
        codes = {issue.code for issue in report.issues}
        self.assertNotIn("weak_declared_phrase_boundary", codes)
        self.assertNotIn("phrase_continuity_exceeds_declared_limit", codes)
        metrics = report.metrics["sections"]["sec_a"]["phrases"][
            "phr_question_answer"
        ]
        self.assertEqual(metrics["attention"], "foreground")
        self.assertGreater(metrics["boundary_gap_beats"], 0.0)
        self.assertLessEqual(metrics["longest_continuous_beats"], 4.0)
        self.assertEqual(
            metrics["intended_tension"],
            {"start": 0.2, "peak": 0.65, "end": 0.25},
        )
        arrival = report.metrics["sections"]["sec_a"]["arrivals"]["arr_answer"]
        self.assertEqual(arrival["attacks_at_arrival"], 1)
        self.assertEqual(arrival["post_attacks"], 0)
        self.assertGreaterEqual(arrival["anchor_hold_beats"], 1.0)
        self.assertEqual(arrival["harmonic_support_ratio"], 1.0)
        stages = report.metrics["sections"]["sec_a"]["phrase_stages"]
        self.assertEqual(stages["stg_question"]["attacks"], 3)
        self.assertEqual(stages["stg_answer"]["attacks"], 3)
        self.assertEqual(stages["stg_question"]["exit_behavior"], "breathe")
        self.assertGreaterEqual(stages["stg_question"]["exit_gap_beats"], 1.0)
        self.assertGreater(
            stages["stg_answer"]["maximum_duration_beats"],
            stages["stg_question"]["maximum_duration_beats"],
        )
        self.assertNotIn("phrase_focus_not_realized", codes)

    def test_phrase_boundary_and_continuity_failures_are_diagnosed(self) -> None:
        payload = continuous_two_voice_composition().model_dump(mode="json")
        payload["sections"][0]["phrases"] = [
            {
                "id": "phr_unbroken",
                "onset": {"numerator": 0, "denominator": 1},
                "duration": {"numerator": 32, "denominator": 1},
                "functions": ["foreground", "counterline"],
                "attention": "foreground",
                "boundary_strength": 1.0,
                "max_continuous_beats": {
                    "numerator": 4,
                    "denominator": 1,
                },
                "tension": {"start": 0.2, "peak": 0.8, "end": 0.2},
                "goal": "Expose an intentionally breathless phrase.",
            }
        ]
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("weak_declared_phrase_boundary", codes)
        self.assertIn("phrase_continuity_exceeds_declared_limit", codes)
        self.assertIn("phrase_release_not_reflected_in_density", codes)

    def test_empty_declared_phrase_has_no_boundary_credit(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"] = []
        payload["sections"][0]["phrase_stages"] = []
        payload["sections"][0]["phrases"][0]["onset"] = {
            "numerator": 3,
            "denominator": 1,
        }
        payload["sections"][0]["phrases"][0]["duration"] = {
            "numerator": 1,
            "denominator": 1,
        }
        payload["sections"][0]["phrases"][0]["max_continuous_beats"] = {
            "numerator": 1,
            "denominator": 1,
        }
        report = diagnose_composition(Composition.model_validate(payload))
        self.assertIn(
            "empty_declared_phrase",
            {issue.code for issue in report.issues},
        )
        metrics = report.metrics["sections"]["sec_a"]["phrases"][
            "phr_question_answer"
        ]
        self.assertEqual(metrics["attacks"], 0)
        self.assertEqual(metrics["boundary_evidence"], 0.0)

    def test_phrase_stage_references_bounds_and_overlap_are_validated(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0]["phrase_id"] = "phr_missing"
        missing = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "missing_phrase_stage_phrase",
            {issue.code for issue in missing.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0]["onset"] = {
            "numerator": 7,
            "denominator": 1,
        }
        outside = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "phrase_stage_outside_phrase",
            {issue.code for issue in outside.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][1]["onset"] = {
            "numerator": 2,
            "denominator": 1,
        }
        overlap = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "overlapping_phrase_stages",
            {issue.code for issue in overlap.issues},
        )

    def test_phrase_stage_has_one_focus_and_valid_attack_budget(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0]["focus"] = True
        payload["sections"][0]["phrase_stages"][0]["focus_cue"] = "salience"
        report = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "multiple_phrase_focus_stages",
            {issue.code for issue in report.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0]["min_attacks"] = 4
        payload["sections"][0]["phrase_stages"][0]["max_attacks"] = 3
        with self.assertRaises(ValueError):
            Composition.model_validate(payload)

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0][
            "min_polyphonic_attacks"
        ] = 2
        payload["sections"][0]["phrase_stages"][0][
            "max_polyphonic_attacks"
        ] = 1
        with self.assertRaises(ValueError):
            Composition.model_validate(payload)

    def test_phrase_stage_budget_and_focus_are_diagnosed(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0]["min_attacks"] = 0
        payload["sections"][0]["phrase_stages"][0]["max_attacks"] = 2
        payload["sections"][0]["phrase_stages"][1]["focus_cue"] = "density"
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("phrase_stage_attack_budget_missed", codes)
        self.assertIn("phrase_focus_not_realized", codes)

    def test_phrase_stage_exit_behavior_is_diagnosed(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0][
            "exit_behavior"
        ] = "continue"
        payload["sections"][0]["phrase_stages"][1][
            "exit_behavior"
        ] = "breathe"
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("phrase_stage_continuation_interrupted", codes)
        self.assertIn("phrase_stage_breath_missing", codes)

    def test_phrase_stage_internal_connection_is_diagnosed(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrase_stages"][0][
            "min_connected_ratio"
        ] = 0.5
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("phrase_stage_internal_connection_missed", codes)
        metrics = report.metrics["sections"]["sec_a"]["phrase_stages"][
            "stg_question"
        ]
        self.assertEqual(metrics["transition_pairs"], 2)
        self.assertEqual(metrics["connected_pairs"], 0)
        self.assertEqual(metrics["connected_pair_ratio"], 0.0)
        self.assertGreater(metrics["micro_gap_pairs"], 0)

    def test_phrase_stage_metric_coordination_is_diagnosed(self) -> None:
        payload = small_composition().model_dump(mode="json")
        stage = payload["sections"][0]["phrase_stages"][0]
        stage["entry_anchor"] = "tactus"
        stage["min_tactus_attack_ratio"] = 0.5
        stage["max_off_tactus_bridge_ratio"] = 0.25
        payload["sections"][0]["segments"][3]["events"][0]["duration"] = {
            "numerator": 1,
            "denominator": 1,
        }
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("phrase_stage_entry_anchor_missed", codes)
        self.assertIn("phrase_stage_tactus_alignment_missed", codes)
        self.assertIn("phrase_stage_displaced_holds_exceeded", codes)
        metrics = report.metrics["sections"]["sec_a"]["phrase_stages"][
            "stg_question"
        ]
        self.assertEqual(metrics["entry_anchor"], "tactus")
        self.assertFalse(metrics["entry_anchor_met"])
        self.assertEqual(metrics["first_attack_onset"], "1/3")
        self.assertEqual(metrics["tactus_attack_ratio"], 0.3333)
        self.assertEqual(metrics["off_tactus_bridge_ratio"], 0.5)

    def test_phrase_stage_gesture_and_polyphonic_budgets_are_diagnosed(
        self,
    ) -> None:
        payload = small_composition().model_dump(mode="json")
        stage = payload["sections"][0]["phrase_stages"][0]
        stage["max_gesture_beats"] = {
            "numerator": 2,
            "denominator": 1,
        }
        stage["min_polyphonic_attacks"] = 1
        stage["max_polyphonic_attacks"] = 2
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("phrase_stage_gesture_span_exceeded", codes)
        self.assertIn("phrase_stage_polyphonic_attack_budget_missed", codes)
        metrics = report.metrics["sections"]["sec_a"]["phrase_stages"][
            "stg_question"
        ]
        self.assertEqual(metrics["gesture_count"], 1)
        self.assertGreater(metrics["longest_gesture_beats"], 2.0)
        self.assertEqual(metrics["polyphonic_attacks"], 0)
        self.assertEqual(metrics["single_note_attacks"], 3)

    def test_uniform_long_phrase_gestures_are_diagnosed(self) -> None:
        song = SongBuilder(
            "Long Uniform Gestures",
            intent="Exercise phrase gesture-length diagnostics.",
            bpm=108,
            tonic="C",
            mode="minor",
            meter=(4, 4),
        )
        song.track(
            "trk_lead",
            "Lead",
            monophonic=True,
            low=60,
            center=69,
            high=84,
        )
        section = song.section("sec_long", "Long", bars=4, energy=0.6)
        section.phrase(
            "phr_long",
            beat(0),
            beat(14),
            functions=["foreground"],
            attention="foreground",
            boundary_strength=0.0,
            goal="Expose two equally long continuous gestures.",
        )
        lead = section.segment(
            "seg_long",
            "Two long gestures",
            track="trk_lead",
            functions=["foreground"],
            start=beat(0),
            duration=beat(14),
        )
        for onset in [0, 1, 2, 3, 4, 5, 7, 8, 9, 10, 11, 12]:
            lead.note(beat(onset), beat(1), midi(67 + onset % 3))
        lead.end()
        section.end()
        song.play("occ_long", "sec_long")
        report = diagnose_composition(song.build())
        self.assertIn(
            "uniform_long_phrase_gestures",
            {issue.code for issue in report.issues},
        )
        spans = report.metrics["sections"]["sec_long"]["phrases"]["phr_long"][
            "continuous_spans_beats"
        ]
        self.assertEqual(spans, [6.0, 6.0])

    def test_dense_displaced_foreground_reports_metric_anchor_conflict(self) -> None:
        song = SongBuilder(
            "Displaced Foreground",
            intent="Exercise shared-clock diagnostics.",
            bpm=108,
            tonic="C",
            mode="minor",
            meter=(4, 4),
        )
        song.track(
            "trk_lead",
            "Lead",
            monophonic=True,
            low=60,
            center=69,
            high=84,
        )
        section = song.section("sec_shifted", "Shifted", bars=8, energy=0.6)
        lead = section.segment(
            "seg_shifted",
            "Permanently displaced line",
            track="trk_lead",
            functions=["foreground"],
            start=beat(0),
            duration=beat(32),
        )
        for bar in range(8):
            for offset_halves, pitch in [(1, 67), (3, 69), (5, 72)]:
                lead.note(
                    beat(bar * 8 + offset_halves, 2),
                    beat(3, 4),
                    midi(pitch),
                )
        lead.end()
        section.end()
        song.play("occ_shifted", "sec_shifted")
        report = diagnose_composition(song.build())
        codes = {issue.code for issue in report.issues}
        self.assertIn("foreground_metric_anchor_conflict", codes)
        metrics = report.metrics["segments"]["seg_shifted"]
        self.assertEqual(metrics["tactus_alignment_ratio"], 0.0)
        self.assertEqual(metrics["bar_downbeat_coverage"], 0.0)
        self.assertEqual(metrics["off_tactus_bridge_ratio"], 1.0)

    def test_tension_peak_must_be_the_high_point(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrases"][0]["tension"] = {
            "start": 0.6,
            "peak": 0.5,
            "end": 0.2,
        }
        with self.assertRaises(ValueError):
            Composition.model_validate(payload)

    def test_phrase_outside_section_is_rejected(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["phrases"][0]["duration"] = {
            "numerator": 9,
            "denominator": 1,
        }
        report = validate_composition(Composition.model_validate(payload))
        self.assertFalse(report.valid)
        self.assertIn(
            "phrase_out_of_bounds",
            {issue.code for issue in report.issues},
        )

    def test_arrival_reference_bounds_and_hold_are_validated(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["phrase_id"] = "phr_missing"
        missing = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "missing_arrival_phrase",
            {issue.code for issue in missing.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["onset"] = {
            "numerator": 8,
            "denominator": 1,
        }
        outside = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "arrival_outside_phrase",
            {issue.code for issue in outside.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["min_hold"] = {
            "numerator": 3,
            "denominator": 1,
        }
        excessive = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "arrival_hold_exceeds_phrase",
            {issue.code for issue in excessive.issues},
        )

    def test_arrival_stop_has_no_post_attack_budget(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["max_post_attacks"] = 1
        with self.assertRaises(ValueError):
            Composition.model_validate(payload)

    def test_arrival_detects_missing_and_unarticulated_completion(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["onset"] = {
            "numerator": 3,
            "denominator": 1,
        }
        payload["sections"][0]["arrivals"][0]["min_hold"] = None
        missing = diagnose_composition(Composition.model_validate(payload))
        self.assertIn(
            "arrival_missing",
            {issue.code for issue in missing.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["onset"] = {
            "numerator": 7,
            "denominator": 1,
        }
        payload["sections"][0]["arrivals"][0]["min_hold"] = None
        sustained = diagnose_composition(Composition.model_validate(payload))
        self.assertIn(
            "arrival_not_articulated",
            {issue.code for issue in sustained.issues},
        )

    def test_arrival_detects_short_hold_and_post_arrival_overrun(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["arrivals"][0]["onset"] = {
            "numerator": 2,
            "denominator": 1,
        }
        payload["sections"][0]["arrivals"][0]["min_hold"] = {
            "numerator": 2,
            "denominator": 1,
        }
        report = diagnose_composition(Composition.model_validate(payload))
        codes = {issue.code for issue in report.issues}
        self.assertIn("arrival_hold_too_short", codes)
        self.assertIn("post_arrival_overrun", codes)

    def test_arrival_detects_missed_harmonic_support(self) -> None:
        payload = small_composition().model_dump(mode="json")
        final_note = payload["sections"][0]["segments"][3]["events"][-1]
        final_note["target"] = {
            "basis": "absolute",
            "degree": None,
            "alter": 0,
            "midi": 61,
            "semitones": None,
        }
        report = diagnose_composition(Composition.model_validate(payload))
        self.assertIn(
            "arrival_harmonic_support_missed",
            {issue.code for issue in report.issues},
        )

    def test_diagnostics_report_shared_release_and_bar_density(self) -> None:
        report = diagnose_composition(continuous_two_voice_composition())
        self.assertIn(
            "continuous_pitched_texture",
            {issue.code for issue in report.issues},
        )
        metrics = report.metrics["sections"]["sec_continuous"]
        self.assertEqual(
            metrics["pitched_texture_silence"]["longest_silence_beats"],
            0.0,
        )
        self.assertEqual(
            metrics["pitched_attack_density"]["per_bar"],
            [8] * 8,
        )

    def test_diagnostics_detect_foreground_loop_and_attention_competition(self) -> None:
        report = diagnose_composition(foreground_stress_composition())
        codes = {issue.code for issue in report.issues}
        self.assertIn("competing_attention_lines", codes)
        self.assertIn("transposition_equivalent_foreground_loop", codes)
        attention = report.metrics["sections"]["sec_stress"]["attention"]
        self.assertEqual(attention["designed_top_voice_attacks"], 8)
        self.assertEqual(attention["explicit_foreground_attacks"], 24)
        self.assertEqual(attention["shared_attack_onsets"], 8)
        self.assertEqual(attention["shared_smaller_line_ratio"], 1.0)

    def test_diagnostics_allow_alternating_foreground_handoff(self) -> None:
        report = diagnose_composition(foreground_handoff_composition())
        self.assertNotIn(
            "competing_attention_lines",
            {issue.code for issue in report.issues},
        )
        attention = report.metrics["sections"]["sec_handoff"]["attention"]
        self.assertEqual(attention["shared_attack_onsets"], 0)
        self.assertEqual(attention["shared_smaller_line_ratio"], 0.0)

    def test_diagnostics_detect_diffuse_pulse_phase(self) -> None:
        report = diagnose_composition(diffuse_pulse_composition())
        self.assertIn(
            "diffuse_pulse_phase",
            {issue.code for issue in report.issues},
        )
        phases = report.metrics["sections"]["sec_pulse"]["pulse_phase"]
        self.assertEqual(phases["quarter_phase_count"], 9)

    def test_diagnostics_detect_unanchored_foreground_subdivision(self) -> None:
        report = diagnose_composition(unanchored_foreground_composition())
        self.assertIn(
            "unanchored_foreground_subdivision",
            {issue.code for issue in report.issues},
        )
        metrics = report.metrics["segments"]["seg_unanchored"]
        self.assertEqual(metrics["pitched_off_eighth_grid_ratio"], 1.0)

    def test_diagnostics_detect_floating_harmony_attacks(self) -> None:
        report = diagnose_composition(floating_harmony_composition())
        self.assertIn(
            "floating_harmony_attacks",
            {issue.code for issue in report.issues},
        )
        metrics = report.metrics["segments"]["seg_float"]
        self.assertEqual(metrics["tactus_alignment_ratio"], 0.0)
        self.assertEqual(metrics["bar_downbeat_coverage"], 0.0)

    def test_diagnostics_detect_reused_role_rhythm_across_sections(self) -> None:
        report = diagnose_composition(reused_harmony_rhythm_composition())
        self.assertIn(
            "reused_role_rhythm_across_sections",
            {issue.code for issue in report.issues},
        )

    def test_diagnostics_detect_unresolved_structural_nonchord_tones(self) -> None:
        report = diagnose_composition(unresolved_structural_tones_composition())
        self.assertIn(
            "unresolved_structural_nonchord_tones",
            {issue.code for issue in report.issues},
        )

    def test_candidate_comparison_finds_clone_and_distinct_rhythm(self) -> None:
        original = small_composition("Original")
        clone = Composition.model_validate(
            {**original.model_dump(mode="json"), "title": "Clone"}
        )
        cloned_report = compare_compositions([original, clone])
        self.assertFalse(cloned_report["distinct"])
        self.assertTrue(cloned_report["pairs"][0]["too_similar"])

        changed_payload = original.model_dump(mode="json")
        changed_payload["title"] = "Changed"
        for segment in changed_payload["sections"][0]["segments"]:
            for event in segment["events"]:
                event["duration"]["denominator"] *= 2
        changed = Composition.model_validate(changed_payload)
        changed_report = compare_compositions([original, changed])
        self.assertTrue(changed_report["distinct"])

    def test_variable_chord_sizes_are_realized(self) -> None:
        project = compile_composition(small_composition())
        clip = next(item for item in project.clips if item.id.endswith("seg_keys"))
        counts = {}
        for note in clip.notes:
            counts[note.start] = counts.get(note.start, 0) + 1
        self.assertEqual(sorted(counts.values()), [2, 3, 3, 4])

    def test_sustained_performance_emits_expression_and_modulation(self) -> None:
        project = compile_composition(small_composition())
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "expression.mid"
            render_project(project, destination)
            inspection = inspect_midi(destination)
        lead = next(
            item for item in inspection["track_summaries"] if item["name"] == "Lead"
        )
        self.assertGreater(lead["control_changes"].get("11", 0), 0)
        self.assertGreater(lead["control_changes"].get("1", 0), 0)

    def test_flat_chord_symbols_are_normalized(self) -> None:
        self.assertEqual(normalize_chord_symbol("Bb13"), "B-13")
        chord_value = parse_chord_symbol("Bb13")
        self.assertEqual(chord_value.root().pitchClass, 10)

    def test_harmony_validation_reports_invalid_and_missing_degrees(self) -> None:
        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["harmony"][0]["symbol"] = "not-a-chord"
        invalid = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "invalid_chord_symbol",
            {issue.code for issue in invalid.issues},
        )

        payload = small_composition().model_dump(mode="json")
        payload["sections"][0]["harmony"][0]["symbol"] = "C"
        bass = next(
            segment
            for segment in payload["sections"][0]["segments"]
            if segment["id"] == "seg_bass"
        )
        bass["events"][0]["target"]["degree"] = 7
        unavailable = validate_composition(Composition.model_validate(payload))
        self.assertIn(
            "unavailable_chord_degree",
            {issue.code for issue in unavailable.issues},
        )

    def test_compilation_is_deterministic(self) -> None:
        composition = small_composition()
        self.assertEqual(
            compile_composition(composition),
            compile_composition(composition),
        )


if __name__ == "__main__":
    unittest.main()
