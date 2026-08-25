"""
A release calendar built from publication *rules*, not a scraped list of dates.

This is the design the plan argues for, and the reason is DST. A hardcoded cron
string like "Friday 20:30 UTC" for the COT release is correct for part of the
year and an hour wrong for the rest, and it fails silently - the fetch simply
runs at the wrong time and the data looks stale for an hour every week from
March. Expressing the rule as "Friday 15:30 America/New_York" and letting the
timezone database resolve it removes the entire class of bug.

Each source declares three separate things, which are routinely conflated:

  * **the publication rule** - when it is released,
  * **the as-of rule**       - what date the data actually describes,
  * **the expected lag**     - how stale it is the moment it lands.

The COT is the clean example: released Friday afternoon, describing the
*Tuesday* three days earlier. A terminal that stamps it with the release date is
telling you the positioning is current when it is already three days old, and
that is a lie of exactly the kind the whole plan is built to avoid.

**Scope, stated plainly.** Only genuinely rule-based releases are here. NFP is
the first Friday of the month by long-standing convention, and the CFTC reports
follow fixed weekly rules. CPI and FOMC dates are *published schedules*, not
rules - they move, and there is no formula that yields them. They are therefore
absent rather than approximated: an economic calendar that quietly guesses the
CPI date is worse than one that admits it does not know, because you would plan
a position around it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Callable, Literal
from zoneinfo import ZoneInfo

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")

Impact = Literal["high", "medium", "low"]


@dataclass(frozen=True)
class Release:
    name: str
    at: datetime                  # publication instant, UTC
    as_of: date | None            # what the data describes
    impact: Impact
    affects: tuple[str, ...]
    note: str

    @property
    def lag_days(self) -> int | None:
        """How old the data already is when it is published."""
        if self.as_of is None:
            return None
        return (self.at.astimezone(UTC).date() - self.as_of).days

    def minutes_from(self, now: datetime) -> float:
        return (self.at - now).total_seconds() / 60.0

    def as_dict(self, now: datetime) -> dict:
        return {"name": self.name, "at": self.at.isoformat(),
                "as_of": self.as_of.isoformat() if self.as_of else None,
                "lag_days": self.lag_days, "impact": self.impact,
                "affects": list(self.affects), "note": self.note,
                "in_minutes": round(self.minutes_from(now), 1)}


# --------------------------------------------------------------------------
# date rules
# --------------------------------------------------------------------------

def nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The nth `weekday` of a month (Monday=0). n=1 is the first."""
    d = date(year, month, 1)
    offset = (weekday - d.weekday()) % 7
    return d + timedelta(days=offset + 7 * (n - 1))


def last_business_day(year: int, month: int) -> date:
    """Last weekday of the month - month-end FX rebalancing flow lands here."""
    d = (date(year + (month == 12), (month % 12) + 1, 1) - timedelta(days=1))
    while d.weekday() >= 5:
        d -= timedelta(days=1)
    return d


def _at(d: date, t: time, tz: ZoneInfo) -> datetime:
    """Localise a wall-clock time, then convert to UTC.

    Built this way round so the intended local time survives a DST changeover;
    adding a fixed offset to UTC does not.
    """
    return datetime.combine(d, t, tzinfo=tz).astimezone(UTC)


def _months(start: date, count: int):
    y, m = start.year, start.month
    for _ in range(count):
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


# --------------------------------------------------------------------------
# the rules themselves
# --------------------------------------------------------------------------

def _nfp(now: datetime, horizon: int) -> list[Release]:
    out = []
    for y, m in _months(now.astimezone(NY).date(), horizon):
        d = nth_weekday(y, m, 4, 1)                        # first Friday
        out.append(Release(
            "US Non-Farm Payrolls", _at(d, time(8, 30), NY),
            date(y, m, 1) - timedelta(days=1), "high",
            ("USD", "XAUUSD", "EURUSD", "GBPUSD", "USDJPY"),
            "The single largest scheduled FX event of the month. Spreads widen "
            "for minutes either side and stops inside the initial range are "
            "routinely taken by noise before the real move."))
    return out


def _cot(now: datetime, horizon_weeks: int) -> list[Release]:
    """CFTC Commitments of Traders: Friday 15:30 ET, describing Tuesday."""
    out = []
    d = now.astimezone(NY).date()
    d += timedelta(days=(4 - d.weekday()) % 7)             # next Friday
    for _ in range(horizon_weeks):
        out.append(Release(
            "CFTC Commitments of Traders", _at(d, time(15, 30), NY),
            d - timedelta(days=3), "medium",
            ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY", "AUDUSD"),
            "Cohort positioning. Describes the Tuesday three days earlier - "
            "read it as fuel, never as timing."))
        d += timedelta(days=7)
    return out


def _bpr(now: datetime, horizon: int) -> list[Release]:
    """Bank Participation Report: released with the first COT of the month."""
    out = []
    for y, m in _months(now.astimezone(NY).date(), horizon):
        d = nth_weekday(y, m, 4, 1)
        out.append(Release(
            "CFTC Bank Participation Report", _at(d, time(15, 30), NY),
            nth_weekday(y, m, 1, 1), "medium", ("XAUUSD", "XAGUSD"),
            "Bullion bank positioning in gold and silver. Monthly, and the "
            "closest free view of the dealer side of the metals market."))
    return out


def _month_end(now: datetime, horizon: int) -> list[Release]:
    out = []
    for y, m in _months(now.astimezone(NY).date(), horizon):
        d = last_business_day(y, m)
        out.append(Release(
            "Month-end FX fix", _at(d, time(16, 0), LONDON), d,
            "medium" if m % 3 else "high",
            ("EURUSD", "GBPUSD", "USDJPY", "XAUUSD"),
            "The 16:00 London fix on the last business day. Rebalancing flow is "
            "price-insensitive by mandate - it happens regardless of level, and "
            "quarter-ends are materially larger."))
    return out


RULES: tuple[Callable[[datetime, int], list[Release]], ...] = (
    _nfp, _cot, _bpr, _month_end,
)


def upcoming(now: datetime | None = None, *, days: int = 30,
             symbols: tuple[str, ...] | None = None,
             min_impact: Impact | None = None) -> list[Release]:
    """Scheduled releases in the next `days`, soonest first.

    Filtering by symbol is a substring-free exact match against the `affects`
    tuple, so asking for XAUUSD never quietly includes an unrelated USD event
    that merely mentions the dollar.
    """
    now = now or datetime.now(UTC)
    if now.tzinfo is None:
        raise ValueError("calendar needs a timezone-aware datetime")
    now = now.astimezone(UTC)
    horizon = now + timedelta(days=days)

    span_months = max(2, days // 28 + 2)
    span_weeks = max(2, days // 7 + 2)

    out: list[Release] = []
    for rule in RULES:
        count = span_weeks if rule is _cot else span_months
        out.extend(rule(now, count))

    out = [r for r in out if now < r.at <= horizon]
    if symbols:
        want = set(symbols)
        out = [r for r in out if want & set(r.affects)]
    if min_impact:
        rank = {"low": 0, "medium": 1, "high": 2}
        out = [r for r in out if rank[r.impact] >= rank[min_impact]]

    out.sort(key=lambda r: r.at)
    return out


def next_high_impact(now: datetime | None = None,
                     symbols: tuple[str, ...] | None = None) -> Release | None:
    """The next event big enough to be worth flattening or sizing down into."""
    hits = upcoming(now, days=45, symbols=symbols, min_impact="high")
    return hits[0] if hits else None
