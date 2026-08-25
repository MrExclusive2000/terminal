"""
Driver-regime detection.

The idea the gold desk hangs on: a correlation shown alone is nearly useless,
because you cannot tell a normal reading from a broken one. Shown *beside its
own long-run value*, a regime break becomes the first thing you see rather
than something you infer months late.

Concretely, gold traded inversely to 10y real yields for roughly two decades
and then decoupled once central banks displaced ETFs as the marginal buyer.
Anything still plotting gold against TIPS and stopping there is presenting a
dead model with a straight face.

Series are injected rather than fetched: in production the price leg comes
from the MT5 bridge, the macro leg from FRED.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RegimeRead:
    driver: str
    current_corr: float | None
    baseline_corr: float | None
    window_days: int
    baseline_days: int
    n_current: int
    n_baseline: int

    @property
    def delta(self) -> float | None:
        if self.current_corr is None or self.baseline_corr is None:
            return None
        return round(self.current_corr - self.baseline_corr, 3)

    @property
    def sign_flipped(self) -> bool:
        if self.current_corr is None or self.baseline_corr is None:
            return False
        return (self.baseline_corr < -0.2 and self.current_corr > 0.1) or \
               (self.baseline_corr > 0.2 and self.current_corr < -0.1)

    @property
    def status(self) -> str:
        if self.current_corr is None or self.baseline_corr is None:
            return "insufficient data"
        if self.sign_flipped:
            return "SIGN FLIPPED"
        d = abs(self.delta or 0.0)
        if d >= 0.40:
            return "broken"
        if d >= 0.25:
            return "weakening"
        return "holding"

    @property
    def actionable(self) -> str:
        """What this means for someone about to place a trade."""
        return {
            "SIGN FLIPPED": "This driver now moves opposite to its history. Any thesis "
                            "resting on the textbook relationship is unsupported.",
            "broken": "The historical relationship is not operating. Do not lean on it.",
            "weakening": "The relationship is degrading. Weak evidence, not a reason.",
            "holding": "Behaving as history suggests.",
            "insufficient data": "Not enough overlapping observations to judge.",
        }[self.status]


def _pearson(xs: Sequence[float], ys: Sequence[float]) -> float | None:
    n = len(xs)
    if n < 20:
        return None
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return round(sxy / math.sqrt(sxx * syy), 3)


def _aligned_changes(a: Mapping[date, float], b: Mapping[date, float],
                     since: date | None = None) -> tuple[list[float], list[float]]:
    """Daily changes on dates both series observe.

    Correlating the *levels* of two trending series manufactures correlation;
    changes are the honest input.
    """
    common = sorted(set(a) & set(b))
    if since:
        common = [d for d in common if d >= since]
    ra: list[float] = []
    rb: list[float] = []
    for prev, cur in zip(common, common[1:]):
        ra.append(a[cur] - a[prev])
        rb.append(b[cur] - b[prev])
    return ra, rb


def assess(price: Mapping[date, float], driver: Mapping[date, float], *,
           driver_name: str, window_days: int = 252,
           baseline_days: int = 5040) -> RegimeRead:
    """Compare the recent correlation against the long-run one."""
    dates = sorted(set(price) & set(driver))
    if len(dates) < 40:
        return RegimeRead(driver_name, None, None, window_days, baseline_days, 0, 0)

    cur_start = dates[max(0, len(dates) - window_days)]
    base_start = dates[max(0, len(dates) - baseline_days)]

    ca, cb = _aligned_changes(price, driver, since=cur_start)
    ba, bb = _aligned_changes(price, driver, since=base_start)

    return RegimeRead(
        driver=driver_name,
        current_corr=_pearson(ca, cb),
        baseline_corr=_pearson(ba, bb),
        window_days=window_days, baseline_days=baseline_days,
        n_current=len(ca), n_baseline=len(ba),
    )
