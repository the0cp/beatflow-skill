# SPDX-License-Identifier: GPL-3.0-only
"""Meter-aware tactus and position helpers."""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction

from .models import TimeSignature


@dataclass(frozen=True)
class MeterProfile:
    numerator: int
    denominator: int
    kind: str
    pulses_per_bar: int
    tactus: Fraction
    measure: Fraction
    division: Fraction

    def within_bar(self, onset: Fraction) -> Fraction:
        return onset % self.measure

    def is_bar_downbeat(self, onset: Fraction) -> bool:
        return self.within_bar(onset) == 0

    def is_tactus(self, onset: Fraction) -> bool:
        return self.within_bar(onset) % self.tactus == 0

    def position(self, onset: Fraction) -> str:
        within = self.within_bar(onset)
        if within == 0:
            return "bar_downbeat"
        if within % self.tactus == 0:
            pulse = int(within / self.tactus)
            if self.pulses_per_bar == 4 and pulse == 2:
                return "secondary_strong"
            return "beat"
        if within % self.division == 0:
            return "division"
        return "subdivision"


def meter_profile(time_signature: TimeSignature) -> MeterProfile:
    numerator = time_signature.numerator
    denominator = time_signature.denominator
    written_unit = Fraction(4, denominator)
    measure = numerator * written_unit
    compound = numerator >= 6 and numerator % 3 == 0
    if compound:
        pulses = numerator // 3
        tactus = written_unit * 3
        division = written_unit
        kind = "compound"
    else:
        pulses = numerator
        tactus = written_unit
        division = written_unit / 2
        kind = "simple" if numerator in {2, 3, 4} else "irregular"
    return MeterProfile(
        numerator=numerator,
        denominator=denominator,
        kind=kind,
        pulses_per_bar=pulses,
        tactus=tactus,
        measure=measure,
        division=division,
    )
