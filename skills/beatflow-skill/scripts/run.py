#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Dependency-aware launcher for a self-contained BeatFlow skill installation."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import venv
from pathlib import Path


def _cache_root() -> Path:
    override = os.environ.get("BEATFLOW_CACHE_DIR")
    if override:
        return Path(override).expanduser().resolve()
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    return base / "beatflow-skill"


def _python_in(venv_path: Path) -> Path:
    if sys.platform == "win32":
        return venv_path / "Scripts" / "python.exe"
    return venv_path / "bin" / "python"


def _requirements_digest(requirements: Path) -> str:
    return hashlib.sha256(requirements.read_bytes()).hexdigest()


def _ensure_runtime(skill_root: Path, cache_root: Path | None = None) -> Path:
    requirements = skill_root / "requirements.txt"
    runtime = (cache_root or _cache_root()) / (
        f"runtime-py{sys.version_info.major}{sys.version_info.minor}-v1"
    )
    runtime_python = _python_in(runtime)
    stamp = runtime / ".requirements.sha256"
    digest = _requirements_digest(requirements)
    if runtime_python.exists() and stamp.exists() and stamp.read_text(encoding="utf-8").strip() == digest:
        return runtime_python

    runtime.parent.mkdir(parents=True, exist_ok=True)
    if not runtime_python.exists():
        venv.EnvBuilder(with_pip=True, clear=False).create(runtime)
    subprocess.run(
        [
            str(runtime_python),
            "-m",
            "pip",
            "install",
            "--disable-pip-version-check",
            "--quiet",
            "-r",
            str(requirements),
        ],
        check=True,
    )
    stamp.write_text(digest + "\n", encoding="utf-8")
    return runtime_python


def main() -> int:
    if sys.version_info < (3, 10):
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": "BeatFlow requires Python 3.10 or newer.",
                    "detected": sys.version.split()[0],
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    skill_root = Path(__file__).resolve().parent.parent
    try:
        try:
            runtime_python = _ensure_runtime(skill_root)
        except PermissionError:
            fallback = Path(tempfile.gettempdir()) / "beatflow-skill"
            runtime_python = _ensure_runtime(skill_root, fallback)
    except (OSError, subprocess.CalledProcessError) as error:
        print(
            json.dumps(
                {
                    "ok": False,
                    "error": f"Could not prepare BeatFlow Python runtime: {error}",
                    "hint": "Check network access and write permission for BEATFLOW_CACHE_DIR.",
                },
                indent=2,
            ),
            file=sys.stderr,
        )
        return 1
    completed = subprocess.run(
        [str(runtime_python), str(skill_root / "scripts" / "beatflow.py"), *sys.argv[1:]],
        check=False,
    )
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
