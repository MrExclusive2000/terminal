"""
Stop placement and entry levels.

A stop has two jobs that pull against each other: sit beyond routine noise so
the market does not take it out at random, and sit close enough that the trade
is worth taking. This module computes candidate stops from three independent
methods and reports what each costs, so the choice is made on evidence rather
than on where the number looks tidy.

The metric that matters most and is almost never shown: **spread as a
percentage of stop distance**. A 4-point spread against a 20-point stop means
20% of the risk is paid to the broker at the moment of entry. That single
number kills more short-horizon trades than direction ever does.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

Direction = Literal["long", "short"]


@dataclass(frozen=True)
class Bar:
    t: str
    o: float
    h: float
    l: float
    c: float


@dataclass(frozen=True)
class StopCandidate:
    method: str
    price: float
    distance: float
    rationale: str
    atr_multiple: float | None = None
    inside_noise: bool = False

    @property
    def verdict(self) -> str:
        if self.inside_noise:
            return "inside normal noise - likely to be hit at random"
        return "beyond normal noise"


def true_range(prev_close: float, bar: Bar) -> float:
    return max(bar.h - bar.l, abs(bar.h - prev_close), abs(bar.l - prev_close))


def atr(bars: Sequence[Bar], period: int = 14) -> float | None:
    """Wilder's ATR. Needs period+1 bars to have a prior close for the first TR."""
    if len(bars) < period + 1:
        return None
    trs = [true_range(bars[i - 1].c, bars[i]) for i in range(1, len(bars))]
    seed = sum(trs[:period]) / period
    val = seed
    for tr in trs[period:]:
        val = (val * (period - 1) + tr) / period
    return val


def swing_low(bars: Sequence[Bar], lookback: int = 20, strength: int = 2,
              below: float | None = None) -> float | None:
    """Most recent pivot low: a bar whose low is under `strength` bars each side.

    `below` constrains the result to sit under a reference price. Without it a
    long trade can be handed a "swing low" above its own entry - a stop that is
    already triggered. Falls back to progressively older pivots, then to the
    window minimum.
    """
    window = bars[-lookback:] if len(bars) > lookback else list(bars)
    for i in range(len(window) - strength - 1, strength - 1, -1):
        lo = window[i].l
        if all(lo <= window[j].l for j in range(i - strength, i + strength + 1) if j != i):
            if below is None or lo < below:
                return lo
    lows = [b.l for b in window if below is None or b.l < below]
    return min(lows, default=None)


def swing_high(bars: Sequence[Bar], lookback: int = 20, strength: int = 2,
               above: float | None = None) -> float | None:
    """Mirror of `swing_low`; `above` keeps the pivot over a reference price."""
    window = bars[-lookback:] if len(bars) > lookback else list(bars)
    for i in range(len(window) - strength - 1, strength - 1, -1):
        hi = window[i].h
        if all(hi >= window[j].h for j in range(i - strength, i + strength + 1) if j != i):
            if above is None or hi > above:
                return hi
    highs = [b.h for b in window if above is None or b.h > above]
    return max(highs, default=None)


def stop_candidates(
    *,
    bars: Sequence[Bar],
    entry: float,
    direction: Direction,
    spread: float = 0.0,
    atr_period: int = 14,
    atr_mult: float = 1.5,
    digits: int = 2,
) -> list[StopCandidate]:
    """Three independent stops, each with what it costs and whether it is safe."""
    a = atr(bars, atr_period)
    out: list[StopCandidate] = []
    sign = -1 if direction == "long" else 1

    def add(method: str, price: float, rationale: str) -> None:
        # A stop must clear the spread, or it is inside the cost of entry itself.
        price = round(price + sign * spread, digits)
        dist = abs(entry - price)
        out.append(StopCandidate(
            method=method, price=price, distance=round(dist, digits), rationale=rationale,
            atr_multiple=round(dist / a, 2) if a else None,
            inside_noise=bool(a and dist < a),
        ))

    if a:
        add("atr", entry + sign * atr_mult * a,
            f"{atr_mult}x ATR({atr_period}) = {atr_mult * a:.{digits}f}, sized to routine volatility")

    pivot = (swing_low(bars, below=entry) if direction == "long"
             else swing_high(bars, above=entry))
    if pivot is not None:
        add("structure", pivot,
            f"beyond the most recent swing {'low' if direction == 'long' else 'high'} "
            f"- the level whose break says the idea is wrong")

    session = bars[-24:] if len(bars) >= 24 else list(bars)
    if session:
        edge = min(b.l for b in session) if direction == "long" else max(b.h for b in session)
        # Entry can sit outside the recent range (a breakout). Guard rather
        # than emit a stop on the wrong side.
        if (direction == "long" and edge < entry) or (direction == "short" and edge > entry):
            add("session", edge, "outside the recent session range")

    out.sort(key=lambda c: c.distance)
    return out


@dataclass(frozen=True)
class CostRead:
    spread: float
    stop_distance: float
    spread_pct_of_risk: float
    swap_per_lot_per_night: float | None
    verdict: str


def cost_of_entry(*, spread: float, stop_distance: float,
                  swap_per_lot: float | None = None) -> CostRead:
    """What entering costs relative to what you are risking."""
    pct = (spread / stop_distance * 100.0) if stop_distance else float("inf")
    if pct >= 25:
        v = "prohibitive - a quarter or more of your risk is paid on entry"
    elif pct >= 10:
        v = "expensive - consider a wider stop or waiting for spread to normalise"
    elif pct >= 5:
        v = "acceptable"
    else:
        v = "cheap"
    return CostRead(spread=spread, stop_distance=stop_distance,
                    spread_pct_of_risk=round(pct, 1),
                    swap_per_lot_per_night=swap_per_lot, verdict=v)
