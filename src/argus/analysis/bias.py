"""
The bias board: assemble the evidence, show what agrees, show what does not.

This answers the question the whole terminal exists for - *long or short here,
and what backs that up* - and it answers it the only honest way, by laying out
each piece of evidence with its own direction, its own weight and its own age,
then reporting the balance including the parts that disagree.

Three rules it will not break:

  * **It is never a signal.** There is no BUY. There is a lean, a strength, and
    a list of what produced it, each line of which you can argue with. A single
    directional verdict with the reasoning hidden is how people end up in trades
    they cannot manage, because they cannot tell which leg broke.

  * **Disagreement is surfaced, not netted away.** Two strong opposing reads and
    two weak aligned ones are completely different situations that produce the
    same net number. The conflict is reported separately from the balance.

  * **Every input carries its own vintage.** Positioning is three days old by
    law; a correlation is a rolling window; price is live. Blending them into
    one undated view is the specific failure this design exists to prevent.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Literal, Sequence

UTC = timezone.utc

Direction = Literal["long", "short", "neutral"]
Strength = Literal["strong", "moderate", "weak", "none"]


def ordinal(n: float) -> str:
    """1st, 2nd, 3rd, 11th, 21st. Naive suffixing gets the teens wrong."""
    i = int(round(n))
    if 10 <= i % 100 <= 20:
        return f"{i}th"
    return f"{i}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(i % 10, 'th') }"


@dataclass(frozen=True)
class Read:
    """One piece of evidence."""
    source: str
    direction: Direction
    weight: float                 # 0-1, how much this deserves to count
    detail: str
    as_of: date | None = None     # what date this evidence describes
    caveat: str = ""

    @property
    def signed(self) -> float:
        return {"long": 1.0, "short": -1.0, "neutral": 0.0}[self.direction] * self.weight

    def age_days(self, now: datetime) -> int | None:
        if self.as_of is None:
            return None
        return (now.astimezone(UTC).date() - self.as_of).days

    def as_dict(self, now: datetime) -> dict:
        return {"source": self.source, "direction": self.direction,
                "weight": round(self.weight, 2), "detail": self.detail,
                "as_of": self.as_of.isoformat() if self.as_of else None,
                "age_days": self.age_days(now), "caveat": self.caveat}


@dataclass
class Board:
    symbol: str
    at: datetime
    reads: list[Read] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    # ---- aggregate -------------------------------------------------------
    @property
    def score(self) -> float:
        """Signed balance in [-1, 1]. Zero means balanced OR empty - never
        report it without also reporting `conflict` and the read count."""
        total = sum(r.weight for r in self.reads)
        if total <= 0:
            return 0.0
        return sum(r.signed for r in self.reads) / total

    @property
    def conflict(self) -> float:
        """How much the evidence disagrees, 0 (aligned) to 1 (evenly split).

        Reported alongside the score because a flat score from two strong
        opposing reads is a different world from a flat score from three weak
        neutral ones, and netting hides that completely.
        """
        longs = sum(r.weight for r in self.reads if r.direction == "long")
        shorts = sum(r.weight for r in self.reads if r.direction == "short")
        both = longs + shorts
        if both <= 0:
            return 0.0
        return 1.0 - abs(longs - shorts) / both

    @property
    def evidence(self) -> float:
        """Total weight of evidence, unnormalised.

        Separate from `score` on purpose. `score` is normalised by total weight,
        so a single low-weight read produces a score of exactly +/-1.0 and looks
        unanimous - which it is, trivially, because nothing else is in the room.
        Confidence has to be gated on how much evidence exists, not only on how
        well it agrees.
        """
        return sum(r.weight for r in self.reads)

    @property
    def lean(self) -> Direction:
        if abs(self.score) < 0.15:
            return "neutral"
        return "long" if self.score > 0 else "short"

    @property
    def strength(self) -> Strength:
        if not self.reads:
            return "none"
        a, mass = abs(self.score), self.evidence
        if self.conflict > 0.6:
            # Genuine disagreement caps how strongly anything can be stated,
            # regardless of which way the balance happens to fall.
            return "weak"
        # Both gates must clear: the evidence has to agree AND there has to be
        # enough of it. One 0.25-weight read agreeing with itself is not strong.
        if a >= 0.55 and mass >= 0.90:
            return "strong"
        if a >= 0.30 and mass >= 0.50:
            return "moderate"
        if a >= 0.15:
            return "weak"
        return "none"

    def headline(self) -> str:
        if not self.reads:
            return f"{self.symbol}: no evidence available."
        if self.lean == "neutral":
            return (f"{self.symbol}: no directional edge. "
                    f"{'Evidence is genuinely split.' if self.conflict > 0.5 else 'Nothing is pulling hard either way.'}")
        n = len(self.reads)
        thin = "" if self.evidence >= 0.50 else ", thin evidence"
        return (f"{self.symbol}: leans {self.lean}, {self.strength} "
                f"({n} input{'' if n == 1 else 's'}"
                f"{', in conflict' if self.conflict > 0.5 else ''}{thin}).")

    def agree(self) -> list[Read]:
        return [r for r in self.reads if r.direction == self.lean and r.direction != "neutral"]

    def against(self) -> list[Read]:
        other = {"long": "short", "short": "long"}.get(self.lean)
        return [r for r in self.reads if r.direction == other] if other else []

    def as_dict(self) -> dict:
        return {"symbol": self.symbol, "at": self.at.isoformat(),
                "lean": self.lean, "strength": self.strength,
                "score": round(self.score, 3), "conflict": round(self.conflict, 3),
                "evidence": round(self.evidence, 3),
                "headline": self.headline(),
                "reads": [r.as_dict(self.at) for r in self.reads],
                "agree": [r.as_dict(self.at) for r in self.agree()],
                "against": [r.as_dict(self.at) for r in self.against()],
                "warnings": list(self.warnings)}

    def explain(self) -> str:
        lines = [self.headline(), ""]
        for r in sorted(self.reads, key=lambda r: -r.weight):
            age = r.age_days(self.at)
            stamp = "live" if age is None else f"{age}d old"
            arrow = {"long": "^", "short": "v", "neutral": "-"}[r.direction]
            lines.append(f"  {arrow} {r.weight:.2f}  {r.source:<24} {r.detail}  [{stamp}]")
            if r.caveat:
                lines.append(f"           note: {r.caveat}")
        for w in self.warnings:
            lines.append(f"  ! {w}")
        return "\n".join(lines)


# --------------------------------------------------------------------------
# builders: turn each engine's output into a Read
# --------------------------------------------------------------------------

def from_positioning(cohort: str, net: float, percentile: float | None,
                     as_of: date, *, contrarian: bool = True) -> Read | None:
    """Positioning as a stretch reading.

    Deliberately *contrarian and weak*. Crowded gets more crowded, and the
    literature is clear that an extreme marks available fuel rather than a turn.
    Weight is capped low so this can colour a view but never carry one, and the
    wording says "stretched", never "due".
    """
    if percentile is None:
        return None
    if percentile >= 85:
        direction: Direction = "short" if contrarian else "long"
        detail = f"{cohort} net long at the {ordinal(percentile)} percentile - crowded"
    elif percentile <= 15:
        direction = "long" if contrarian else "short"
        detail = f"{cohort} net short at the {ordinal(percentile)} percentile - crowded"
    else:
        return Read("Positioning", "neutral", 0.15,
                    f"{cohort} at the {ordinal(percentile)} percentile - unremarkable",
                    as_of=as_of)
    return Read("Positioning", direction, 0.25, detail, as_of=as_of,
                caveat="Marks fuel, not timing. Never fade an extreme without a "
                       "price trigger - crowded positions get more crowded.")


def from_regime(driver: str, current: float | None, baseline: float | None,
                driver_change: float | None) -> Read | None:
    """A macro driver, but only while the relationship still holds.

    If the correlation has broken away from its own long-run value, this
    returns a *warning* rather than a direction. Trading a dead model with
    confidence is worse than having no model, and gold against real yields is
    the standing example.
    """
    if current is None or baseline is None:
        return None

    broken = abs(current - baseline) > 0.45 or (
        baseline != 0 and current * baseline < 0 and abs(current) > 0.2)
    if broken:
        return Read(f"Driver: {driver}", "neutral", 0.10,
                    f"correlation {current:+.2f} vs long-run {baseline:+.2f} - "
                    f"the relationship has broken",
                    caveat="This model is not currently working. It is shown so "
                           "the break is visible, not so it can be traded.")
    if driver_change is None or abs(current) < 0.25:
        return None

    implied = -driver_change if current < 0 else driver_change
    direction: Direction = "long" if implied > 0 else "short"
    return Read(f"Driver: {driver}", direction, min(0.45, abs(current)),
                f"correlation {current:+.2f} (long-run {baseline:+.2f}), "
                f"driver moved {driver_change:+.2f}")


def from_session(liquidity: str, note: str) -> Read | None:
    """Session state never has a direction - it gates size, not side."""
    if liquidity in ("very thin", "closed"):
        return Read("Session", "neutral", 0.0, f"liquidity {liquidity}",
                    caveat=note)
    return None


def from_event(name: str, minutes: float, impact: str) -> Read | None:
    """A scheduled binary ahead is a reason to size down, not a direction."""
    if impact != "high" or minutes > 60 * 24:
        return None
    when = f"{minutes/60:.1f}h" if minutes >= 60 else f"{minutes:.0f}m"
    return Read("Scheduled event", "neutral", 0.0, f"{name} in {when}",
                caveat="Holding a leveraged position through a scheduled binary "
                       "is the most reliable way to lose more than you planned.")


def build(symbol: str, reads: Sequence[Read | None], *,
          now: datetime | None = None) -> Board:
    """Assemble a board, dropping unavailable inputs rather than faking them."""
    now = (now or datetime.now(UTC)).astimezone(UTC)
    board = Board(symbol=symbol, at=now)
    for r in reads:
        if r is None:
            continue
        if r.weight <= 0 and r.caveat:
            board.warnings.append(f"{r.source}: {r.caveat}")
            continue
        if r.weight > 0:
            board.reads.append(r)

    stale = [r for r in board.reads
             if (a := r.age_days(now)) is not None and a > 10]
    for r in stale:
        board.warnings.append(
            f"{r.source} is {r.age_days(now)} days old - older than its usual "
            f"release cycle, so treat it as background rather than current.")
    return board
