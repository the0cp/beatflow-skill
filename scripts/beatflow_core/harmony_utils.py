# SPDX-License-Identifier: GPL-3.0-only
"""Chord-symbol normalization at the music21 boundary."""

from __future__ import annotations

import re

from music21 import harmony


def normalize_chord_symbol(symbol: str) -> str:
    """Accept common lead-sheet flat roots while preserving altered extensions."""
    normalized = symbol.strip()
    normalized = re.sub(r"^([A-G])b(?=[0-9mM+#s-]|$)", r"\1-", normalized)
    normalized = re.sub(r"/([A-G])b(?=$)", r"/\1-", normalized)
    return normalized


def parse_chord_symbol(symbol: str) -> harmony.ChordSymbol:
    return harmony.ChordSymbol(normalize_chord_symbol(symbol))
