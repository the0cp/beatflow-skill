# SPDX-License-Identifier: GPL-3.0-only
"""BeatFlow's relational composition and MIDI rendering core."""

from .composition_compiler import compile_composition
from .composition_diagnostics import diagnose_composition
from .composition_models import Composition
from .composition_validation import validate_composition
from .models import Project
from .renderer import render_project
from .validation import ValidationReport, validate_project

__all__ = [
    "Composition",
    "Project",
    "ValidationReport",
    "__version__",
    "compile_composition",
    "diagnose_composition",
    "render_project",
    "validate_composition",
    "validate_project",
]
__version__ = "2.0"
