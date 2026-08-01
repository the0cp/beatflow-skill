# SPDX-License-Identifier: GPL-3.0-only
"""Compact CLI for Composition 1.1 validation, diagnostics, and MIDI export."""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from . import __version__
from .composition_compiler import CompositionCompileError, compile_composition
from .composition_diagnostics import compare_compositions, diagnose_composition
from .composition_models import Composition
from .composition_validation import validate_composition
from .inspect_midi import inspect_midi
from .models import Project
from .renderer import RenderError, render_project
from .validation import validate_project


def _write_json(
    payload: Any,
    output: str | None = None,
    *,
    summary_when_written: Any | None = None,
) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False)
    if output:
        destination = Path(output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(text + "\n", encoding="utf-8")
    visible = summary_when_written if output and summary_when_written is not None else payload
    print(json.dumps(visible, indent=2, ensure_ascii=False))


def _load_composition(path: str | Path) -> Composition:
    source = Path(path).expanduser().resolve()
    return Composition.model_validate_json(source.read_text(encoding="utf-8"))


def _load_project(path: str | Path) -> Project:
    source = Path(path).expanduser().resolve()
    return Project.model_validate_json(source.read_text(encoding="utf-8"))


def _load_composition_script(path: str | Path) -> Composition:
    source = Path(path).expanduser().resolve()
    spec = importlib.util.spec_from_file_location("beatflow_user_composition", source)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not load composition script: {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    build = getattr(module, "build", None)
    if not callable(build):
        raise TypeError("Composition script must define a callable build().")
    result = build()
    return result if isinstance(result, Composition) else Composition.model_validate(result)


def _schema_error(error: Exception, source: str) -> dict[str, Any]:
    if isinstance(error, ValidationError):
        issues = [
            {
                "severity": "error",
                "code": "schema_error",
                "path": ".".join(str(part) for part in item["loc"]),
                "message": item["msg"],
                "hint": None,
            }
            for item in error.errors(include_url=False)
        ]
    else:
        issues = [
            {
                "severity": "error",
                "code": "parse_error",
                "path": source,
                "message": str(error),
                "hint": "Ensure the input is readable UTF-8 JSON.",
            }
        ]
    return {
        "valid": False,
        "errors": len(issues),
        "warnings": 0,
        "issues": issues,
        "stats": {},
    }


def command_schema(args: argparse.Namespace) -> int:
    schema = Composition.model_json_schema()
    _write_json(
        schema,
        args.output,
        summary_when_written={
            "written": str(Path(args.output).expanduser().resolve()),
            "schema": "BeatFlow Composition 1.1",
        }
        if args.output
        else None,
    )
    return 0


def command_validate(args: argparse.Namespace) -> int:
    try:
        composition = _load_composition(args.composition)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as error:
        _write_json(_schema_error(error, args.composition), args.output)
        return 2
    report = validate_composition(composition)
    _write_json(
        report.model_dump(mode="json"),
        args.output,
        summary_when_written={
            "valid": report.valid,
            "errors": report.errors,
            "warnings": report.warnings,
            "issue_codes": [item.code for item in report.issues],
            "report": str(Path(args.output).expanduser().resolve())
            if args.output
            else None,
        },
    )
    return 0 if report.valid else 2


def command_diagnose(args: argparse.Namespace) -> int:
    try:
        composition = _load_composition(args.composition)
        report = diagnose_composition(composition)
    except (OSError, ValueError, ValidationError) as error:
        _write_json({"structurally_valid": False, "error": str(error)}, args.output)
        return 2
    _write_json(
        report.model_dump(mode="json"),
        args.output,
        summary_when_written={
            "structurally_valid": report.structurally_valid,
            "warnings": report.warnings,
            "infos": report.infos,
            "issue_codes": [item.code for item in report.issues],
            "report": str(Path(args.output).expanduser().resolve())
            if args.output
            else None,
        },
    )
    return 0 if report.structurally_valid else 2


def command_compare(args: argparse.Namespace) -> int:
    try:
        compositions = [_load_composition(path) for path in args.compositions]
        report = compare_compositions(compositions)
    except (OSError, ValueError, ValidationError) as error:
        _write_json({"compared": False, "error": str(error)}, args.output)
        return 2
    _write_json(report, args.output)
    return 0


def _compile_payload(
    composition: Composition,
    *,
    project_output: str | None = None,
) -> tuple[Project, dict[str, Any]]:
    validation = validate_composition(composition)
    if not validation.valid:
        raise CompositionCompileError("Composition has validation errors.", validation)
    diagnostics = diagnose_composition(composition)
    project = compile_composition(composition)
    project_validation = validate_project(project)
    if not project_validation.valid:
        raise CompositionCompileError(
            "Compiled Project has validation errors.",
            project_validation,
        )
    if project_output:
        destination = Path(project_output).expanduser().resolve()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(
            project.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
    return project, {
        "validation": validation.model_dump(mode="json"),
        "diagnostics": diagnostics.model_dump(mode="json"),
        "project_validation": project_validation.model_dump(mode="json"),
    }


def command_compile(args: argparse.Namespace) -> int:
    try:
        composition = _load_composition(args.composition)
        project, payload = _compile_payload(
            composition,
            project_output=args.output,
        )
    except (CompositionCompileError, OSError, ValueError, ValidationError) as error:
        report = (
            error.report.model_dump(mode="json")
            if isinstance(error, CompositionCompileError)
            and error.report is not None
            else {"compiled": False, "error": str(error)}
        )
        _write_json(report, args.report)
        return 2
    payload.update(
        {
            "compiled": True,
            "composition": str(Path(args.composition).expanduser().resolve()),
            "project": str(Path(args.output).expanduser().resolve()),
            "clips": len(project.clips),
        }
    )
    _write_json(payload, args.report)
    return 0


def _render_composition(
    composition: Composition,
    output: str,
    *,
    project_output: str | None = None,
) -> dict[str, Any]:
    project, payload = _compile_payload(
        composition,
        project_output=project_output,
    )
    summary = render_project(project, output)
    inspection = inspect_midi(output)
    return {
        **payload,
        "rendered": True,
        "midi": summary.model_dump(mode="json"),
        "inspection": inspection,
    }


def command_render(args: argparse.Namespace) -> int:
    try:
        composition = _load_composition(args.composition)
        payload = _render_composition(
            composition,
            args.output,
            project_output=args.project_output,
        )
    except (
        CompositionCompileError,
        RenderError,
        OSError,
        ValueError,
        ValidationError,
    ) as error:
        report = (
            error.report.model_dump(mode="json")
            if isinstance(error, (CompositionCompileError, RenderError))
            and error.report is not None
            else {"rendered": False, "error": str(error)}
        )
        _write_json(report, args.report)
        return 2
    _write_json(
        payload,
        args.report,
        summary_when_written={
            "rendered": True,
            "diagnostics": {
                "warnings": payload["diagnostics"]["warnings"],
                "infos": payload["diagnostics"]["infos"],
                "issue_codes": [
                    item["code"]
                    for item in payload["diagnostics"]["issues"]
                ],
            },
            "midi": payload["midi"],
            "report": str(Path(args.report).expanduser().resolve())
            if args.report
            else None,
        },
    )
    return 0


def command_compose(args: argparse.Namespace) -> int:
    try:
        composition = _load_composition_script(args.script)
        if args.composition_output:
            destination = Path(args.composition_output).expanduser().resolve()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(
                composition.model_dump_json(indent=2) + "\n",
                encoding="utf-8",
            )
        payload = _render_composition(
            composition,
            args.output,
            project_output=args.project_output,
        )
    except (
        CompositionCompileError,
        RenderError,
        OSError,
        ValueError,
        ValidationError,
    ) as error:
        report = (
            error.report.model_dump(mode="json")
            if isinstance(error, (CompositionCompileError, RenderError))
            and error.report is not None
            else {"rendered": False, "error": str(error)}
        )
        _write_json(report, args.report)
        return 2
    payload.update(
        {
            "script": str(Path(args.script).expanduser().resolve()),
            "composition": (
                str(Path(args.composition_output).expanduser().resolve())
                if args.composition_output
                else None
            ),
        }
    )
    _write_json(
        payload,
        args.report,
        summary_when_written={
            "rendered": True,
            "script": payload["script"],
            "composition": payload["composition"],
            "diagnostics": {
                "warnings": payload["diagnostics"]["warnings"],
                "infos": payload["diagnostics"]["infos"],
                "issue_codes": [
                    item["code"]
                    for item in payload["diagnostics"]["issues"]
                ],
            },
            "midi": payload["midi"],
            "report": str(Path(args.report).expanduser().resolve())
            if args.report
            else None,
        },
    )
    return 0


def command_project_schema(args: argparse.Namespace) -> int:
    _write_json(Project.model_json_schema(), args.output)
    return 0


def command_project_validate(args: argparse.Namespace) -> int:
    try:
        project = _load_project(args.project)
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as error:
        _write_json(_schema_error(error, args.project), args.output)
        return 2
    report = validate_project(project)
    _write_json(report.model_dump(mode="json"), args.output)
    return 0 if report.valid else 2


def command_render_project(args: argparse.Namespace) -> int:
    try:
        project = _load_project(args.project)
        summary = render_project(project, args.output)
        inspection = inspect_midi(args.output)
    except (RenderError, OSError, ValueError, ValidationError) as error:
        _write_json({"rendered": False, "error": str(error)}, args.report)
        return 2
    payload = {
        "rendered": True,
        "midi": summary.model_dump(mode="json"),
        "inspection": inspection,
    }
    _write_json(payload, args.report)
    return 0


def command_inspect(args: argparse.Namespace) -> int:
    try:
        payload = inspect_midi(args.midi)
    except (OSError, ValueError) as error:
        _write_json({"inspected": False, "error": str(error)}, args.output)
        return 2
    _write_json(payload, args.output)
    return 0


def command_self_check(_: argparse.Namespace) -> int:
    from .composer import SongBuilder, beat, chord, scale

    song = SongBuilder(
        "BeatFlow Self Check",
        intent="Verify explicit rational time, functional pitch, diagnostics, and MIDI.",
        bpm=96,
        tonic="C",
        mode="major",
    )
    song.track(
        "trk_pulse",
        "Pulse",
        percussion=True,
        channel=9,
        performance="percussive",
    )
    song.track(
        "trk_piano",
        "Piano",
        program=0,
        performance="percussive",
        monophonic=False,
        low=48,
        center=66,
        high=84,
    )
    section = song.section("sec_a", "Self Check", bars=2, energy=0.5)
    section.chord_bar(1, "CM7").chord_bar(2, "FM7")
    pulse = section.segment(
        "seg_pulse",
        "Pulse",
        track="trk_pulse",
        functions=["pulse"],
        start=beat(0),
        duration=beat(8),
    )
    for index in range(8):
        pulse.drum(beat(index), beat(1, 16), "closed_hat", velocity=62)
    pulse.end()
    harmony = section.segment(
        "seg_harmony",
        "Harmony",
        track="trk_piano",
        functions=["harmony"],
        start=beat(0),
        duration=beat(8),
    )
    harmony.chord(beat(0), beat(1), notes=3)
    harmony.chord(beat(4), beat(1), notes=2)
    harmony.end()
    line = section.segment(
        "seg_line",
        "Line",
        track="trk_piano",
        functions=["foreground"],
        start=beat(1),
        duration=beat(6),
    )
    line.note(beat(1), beat(1, 2), chord(3), motif="a")
    line.note(beat(5, 3), beat(1, 3), scale(4), motif="a")
    line.note(beat(2), beat(1), chord(5), contour="up", motif="a")
    line.note(beat(5), beat(1, 2), chord(3), contour="down")
    line.note(beat(6), beat(1), chord(1), importance=0.9)
    line.end()
    section.end()
    song.play("occ_a", "sec_a")
    composition = song.build()

    validation = validate_composition(composition)
    diagnostics = diagnose_composition(composition)
    project = compile_composition(composition)
    project_validation = validate_project(project)
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "self-check.mid"
        summary = render_project(project, output)
        inspection = inspect_midi(output)
    payload = {
        "ok": validation.valid and project_validation.valid,
        "schema_version": composition.schema_version,
        "validation": validation.model_dump(mode="json"),
        "diagnostics": diagnostics.model_dump(mode="json"),
        "project_validation": project_validation.model_dump(mode="json"),
        "midi": summary.model_dump(mode="json"),
        "inspection": inspection,
    }
    _write_json(payload)
    return 0 if payload["ok"] else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="beatflow",
        description="Compose explicit, style-neutral symbolic music and export MIDI.",
    )
    parser.add_argument("--version", action="version", version=f"BeatFlow {__version__}")
    subparsers = parser.add_subparsers(dest="command", required=True)

    schema = subparsers.add_parser("schema", help="Print Composition 1.1 JSON Schema.")
    schema.add_argument("--output")
    schema.set_defaults(function=command_schema)

    validate = subparsers.add_parser("validate", help="Validate a Composition.")
    validate.add_argument("composition")
    validate.add_argument("--output")
    validate.set_defaults(function=command_validate)

    diagnose = subparsers.add_parser(
        "diagnose",
        help="Report intent conflicts and style-neutral degeneration signals.",
    )
    diagnose.add_argument("composition")
    diagnose.add_argument("--output")
    diagnose.set_defaults(function=command_diagnose)

    compare = subparsers.add_parser(
        "compare",
        help="Compare candidate rhythm and duration fingerprints.",
    )
    compare.add_argument("compositions", nargs="+")
    compare.add_argument("--output")
    compare.set_defaults(function=command_compare)

    compile_parser = subparsers.add_parser(
        "compile",
        help="Compile a Composition to internal Project JSON.",
    )
    compile_parser.add_argument("composition")
    compile_parser.add_argument("output")
    compile_parser.add_argument("--report")
    compile_parser.set_defaults(function=command_compile)

    render = subparsers.add_parser(
        "render",
        help="Validate, diagnose, compile, render, and inspect a Composition.",
    )
    render.add_argument("composition")
    render.add_argument("output")
    render.add_argument("--project-output")
    render.add_argument("--report")
    render.set_defaults(function=command_render)

    compose = subparsers.add_parser(
        "compose",
        help="Run a trusted Python build() script and render its Composition.",
    )
    compose.add_argument("script")
    compose.add_argument("output")
    compose.add_argument("--composition-output")
    compose.add_argument("--project-output")
    compose.add_argument("--report")
    compose.set_defaults(function=command_compose)

    project_schema = subparsers.add_parser(
        "project-schema",
        help="Print the internal Project JSON Schema.",
    )
    project_schema.add_argument("--output")
    project_schema.set_defaults(function=command_project_schema)

    project_validate = subparsers.add_parser(
        "project-validate",
        help="Validate internal Project JSON.",
    )
    project_validate.add_argument("project")
    project_validate.add_argument("--output")
    project_validate.set_defaults(function=command_project_validate)

    render_project_parser = subparsers.add_parser(
        "render-project",
        help="Render validated internal Project JSON.",
    )
    render_project_parser.add_argument("project")
    render_project_parser.add_argument("output")
    render_project_parser.add_argument("--report")
    render_project_parser.set_defaults(function=command_render_project)

    inspect = subparsers.add_parser("inspect", help="Inspect a MIDI file.")
    inspect.add_argument("midi")
    inspect.add_argument("--output")
    inspect.set_defaults(function=command_inspect)

    self_check = subparsers.add_parser(
        "self-check",
        help="Run an end-to-end installation smoke test.",
    )
    self_check.set_defaults(function=command_self_check)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.function(args))
    except OSError as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": str(error),
                    "hint": "Choose readable inputs and writable output paths.",
                },
                indent=2,
                ensure_ascii=False,
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())
