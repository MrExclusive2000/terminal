"""
Conviction scoring for insider transactions, with its working shown.

The score is deliberately a *decomposition*, not a number. Every panel in the
plan that shows a conviction figure can expand it into the factors below, with
the reason each one fired. An unexplainable score in a research tool is worse
than no score: you cannot argue with it, so you either believe it or ignore it,
and both are wrong.

Two design commitments that cost points and are worth it:

  * **Mechanical rows score zero and say so.** Not a low score - zero, with the
    reason attached. A vesting-withholding row is not weak evidence of selling;
    it is no evidence of anything.

  * **Purchases and sales are not symmetric.** Open-market buying is the
    best-documented anomaly in this literature. Selling is mostly liquidity,
    tax and diversification, so a sale has to clear a much higher bar before it
    scores at all - size, off-plan, and unusual against the filer's own history.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Sequence

from .codes import is_discretionary
from .form4 import Form4, Owner, Transaction


@dataclass(frozen=True)
class Factor:
    name: str
    points: float
    why: str


@dataclass(frozen=True)
class Conviction:
    score: float                      # 0-100
    direction: str                    # "buy" | "sell" | "none"
    factors: tuple[Factor, ...]
    caveats: tuple[str, ...] = ()

    @property
    def band(self) -> str:
        if self.direction == "none":
            return "no signal"
        if self.score >= 70:
            return "high"
        if self.score >= 40:
            return "moderate"
        if self.score >= 15:
            return "low"
        return "negligible"

    def explain(self) -> str:
        lines = [f"{self.direction.upper()} conviction {self.score:.0f}/100 ({self.band})"]
        for f in self.factors:
            sign = "+" if f.points >= 0 else ""
            lines.append(f"  {sign}{f.points:5.1f}  {f.name} - {f.why}")
        for c in self.caveats:
            lines.append(f"   note   {c}")
        return "\n".join(lines)


# Officer titles that move markets when they buy, in rough order of how much
# non-public information the role implies. Matched case-insensitively on
# substrings because the free-text officerTitle field is not a controlled
# vocabulary - "CEO", "Chief Executive Officer" and "President & CEO" all occur.
_SENIORITY: tuple[tuple[str, float, str], ...] = (
    ("chief executive", 12, "CEO - sees everything first"),
    ("ceo", 12, "CEO - sees everything first"),
    ("chief financial", 12, "CFO - closest to the numbers"),
    ("cfo", 12, "CFO - closest to the numbers"),
    ("chief operating", 8, "COO - operational visibility"),
    ("coo", 8, "COO - operational visibility"),
    ("president", 8, "President"),
    ("chief", 6, "C-suite"),
    ("vice president", 4, "VP"),
    ("evp", 4, "EVP"),
    ("svp", 4, "SVP"),
)


def _seniority(owner: Owner) -> Factor | None:
    title = (owner.officer_title or "").lower()
    if owner.is_officer and title:
        for needle, pts, why in _SENIORITY:
            if needle in title:
                return Factor("Role", pts, f"{owner.officer_title.strip()} - {why}")
        return Factor("Role", 3, f"{owner.officer_title.strip()} - officer")
    if owner.is_officer:
        return Factor("Role", 3, "Officer, title not stated")
    if owner.is_director:
        return Factor("Role", 5,
                      "Director - board sight of strategy, but less operational detail")
    if owner.is_ten_percent:
        return Factor("Role", 2,
                      "10% holder - may be trading for portfolio reasons unrelated to the company")
    return None


def _size_factors(txn: Transaction) -> list[Factor]:
    out: list[Factor] = []
    value = txn.value
    if value is not None and value > 0:
        # Log-ish banding. A $50k director buy and a $5m CEO buy are different
        # events; a linear scale would let one megacap trade drown everything.
        for floor, pts in ((5_000_000, 22), (1_000_000, 17), (250_000, 12),
                           (100_000, 8), (25_000, 4)):
            if value >= floor:
                out.append(Factor("Size", pts, f"${value:,.0f} committed"))
                break
        else:
            out.append(Factor("Size", 1, f"${value:,.0f} - small enough to be noise"))
    elif txn.shares:
        out.append(Factor("Size", 0,
                          "Price not stated in the filing, so notional is unknown"))

    # Conviction is better measured against what they already had than in
    # dollars. Doubling your own stake says more than a big number does.
    if txn.shares and txn.shares_after:
        prior = txn.shares_after - txn.shares if txn.acquired else txn.shares_after + txn.shares
        if prior > 0:
            pct = txn.shares / prior
            for floor, pts, label in ((1.0, 20, "more than doubled"),
                                      (0.5, 15, "increased by over half"),
                                      (0.25, 11, "increased by over a quarter"),
                                      (0.10, 7, "increased by over a tenth")):
                if pct >= floor:
                    out.append(Factor("Stake change", pts,
                                      f"Position {label} ({pct:.0%} of prior holding)"))
                    break
    return out


def score(form: Form4, txn: Transaction, *,
          owner: Owner | None = None,
          routine_filer: bool = False,
          cluster_size: int = 1) -> Conviction:
    """Score one transaction from one filing.

    `routine_filer` comes from `classify_filer` - a filer who trades the same
    month every year carries little information regardless of size.
    `cluster_size` is the number of distinct insiders trading the same issuer
    in the same direction inside the cluster window.
    """
    owner = owner or (form.owners[0] if form.owners else Owner(cik="", name=""))
    factors: list[Factor] = []
    caveats: list[str] = []

    meta = txn.meta
    if not is_discretionary(txn.code, plan_flagged=form.plan_flagged):
        why = meta.note
        if form.plan_flagged and meta.discretion == "conditional":
            why = ("Filing carries the document-level 10b5-1 flag, so the timing "
                   "was set when the plan was adopted, not when the trade printed.")
        return Conviction(0.0, "none",
                          (Factor(f"Code {txn.code or '?'}", 0.0, why),),
                          ("Scored zero because nobody chose the timing. This is "
                           "not weak evidence - it is evidence of nothing.",))

    buying = bool(txn.acquired)
    direction = "buy" if buying else "sell"

    if txn.code == "P":
        factors.append(Factor("Code P", 30,
                              "Open-market purchase - cash out of pocket at a price "
                              "they did not have to pay"))
    elif txn.code == "S":
        factors.append(Factor("Code S", 8,
                              "Open-market sale, not under a flagged plan. Sales carry "
                              "far less information than purchases - liquidity, tax and "
                              "diversification explain most of them"))
        caveats.append("Absence of a 10b5-1 flag is not proof of absence of a plan: "
                       "the flag became mandatory only for filings after the 2023 "
                       "amendments, and older or sloppy filings under-report it.")
    else:
        factors.append(Factor(f"Code {txn.code}", 5,
                              f"{meta.label} - discretionary but not a plain "
                              f"open-market trade"))

    if (f := _seniority(owner)) is not None:
        factors.append(f)
    factors.extend(_size_factors(txn))

    if cluster_size > 1:
        pts = min(20.0, 6.0 * (cluster_size - 1))
        factors.append(Factor("Cluster", pts,
                              f"{cluster_size} insiders trading the same way in the "
                              f"same window - the single strongest amplifier in the "
                              f"literature"))

    if routine_filer:
        factors.append(Factor("Routine filer", -25,
                              "This filer trades on a near-annual calendar. Routine "
                              "filers' trades carry close to no predictive content"))

    if txn.direct is False:
        factors.append(Factor("Indirect", -4,
                              "Held indirectly (trust, fund, family). The filer may not "
                              "be the decision-maker"))

    if not buying:
        caveats.append("Sales are scored on a deliberately harsher scale than "
                       "purchases. Most insider selling is not informative.")

    raw = sum(f.points for f in factors)
    # Sales are capped below purchases by design - even a perfect-looking sale
    # should not present as a high-conviction signal.
    ceiling = 100.0 if buying else 55.0
    return Conviction(max(0.0, min(ceiling, raw)), direction,
                      tuple(factors), tuple(caveats))


# --------------------------------------------------------------------------
# Cohen-Malloy-Pomorski routine / opportunistic split
# --------------------------------------------------------------------------

def classify_filer(trade_dates: Sequence[date], *, min_years: int = 3) -> bool:
    """True if this filer looks *routine*.

    The Cohen-Malloy-Pomorski test: a filer who traded in the same calendar
    month for at least `min_years` consecutive years is trading a calendar, not
    a view. Their trades are stripped of predictive content in the paper, and
    separating them is most of what makes insider data work.

    Deliberately conservative - it needs consecutive years, not merely a
    repeated month, so an insider who happens to have traded two Novembers is
    not written off.
    """
    if len(trade_dates) < min_years:
        return False
    by_month: dict[int, set[int]] = {}
    for d in trade_dates:
        by_month.setdefault(d.month, set()).add(d.year)
    for years in by_month.values():
        if len(years) < min_years:
            continue
        run = 1
        ordered = sorted(years)
        for a, b in zip(ordered, ordered[1:]):
            run = run + 1 if b == a + 1 else 1
            if run >= min_years:
                return True
    return False
