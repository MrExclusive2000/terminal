"""
FX and metals session state: which desks are open, how deep the book is, and
what is about to change.

Sessions are defined in **local exchange time with a real timezone**, never as
fixed UTC offsets. This is the whole reason the module exists. London and New
York shift on different weekends, Tokyo does not shift at all, and Sydney moves
in the opposite direction - so any hardcoded UTC window is wrong for several
weeks a year, and wrong in exactly the period where the London/New York overlap
either lengthens or shortens. The plan flags this as a 2-3x overrun area and it
is where "it works on my machine in July" comes from.

The practical payoff is the rollover warning. At 17:00 New York the interbank
day rolls, liquidity briefly evaporates and retail spreads on gold can go from
0.30 to several dollars. Traders get stopped out at that minute by a spread
spike rather than by a move, and it is entirely predictable.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Iterable, Literal
from zoneinfo import ZoneInfo

UTC = timezone.utc

Liquidity = Literal["deep", "normal", "thin", "very thin", "closed"]


@dataclass(frozen=True)
class Session:
    name: str
    tz: str
    open_local: time
    close_local: time

    def is_open(self, at: datetime) -> bool:
        """Open at instant `at`, evaluated in the desk's own local time.

        Weekends are excluded in local terms, which is not the same as excluding
        them in UTC: Sydney opens Monday morning while London is still on Sunday
        evening, and a UTC weekend test would wrongly call that market shut.
        """
        local = at.astimezone(ZoneInfo(self.tz))
        if local.weekday() >= 5:
            return False
        return self.open_local <= local.time() < self.close_local

    def local_now(self, at: datetime) -> datetime:
        return at.astimezone(ZoneInfo(self.tz))


#: The four majors, in local time so DST is handled by the tz database.
SESSIONS: tuple[Session, ...] = (
    Session("Sydney", "Australia/Sydney", time(8, 0), time(17, 0)),
    Session("Tokyo", "Asia/Tokyo", time(9, 0), time(18, 0)),
    Session("London", "Europe/London", time(8, 0), time(17, 0)),
    Session("New York", "America/New_York", time(8, 0), time(17, 0)),
)

NY = ZoneInfo("America/New_York")
LONDON = ZoneInfo("Europe/London")

#: Interbank rollover. Swap is applied and liquidity thins hard for a few
#: minutes either side.
ROLLOVER_LOCAL = time(17, 0)

#: LBMA gold price auctions - the twice-daily benchmark fixings. Physical
#: interest concentrates into these and XAUUSD frequently moves through them.
LBMA_AUCTIONS = (time(10, 30), time(15, 0))


@dataclass(frozen=True)
class Event:
    name: str
    at: datetime
    note: str

    def minutes_from(self, now: datetime) -> float:
        return (self.at - now).total_seconds() / 60.0


@dataclass(frozen=True)
class SessionState:
    at: datetime
    open_sessions: tuple[str, ...]
    liquidity: Liquidity
    overlap: bool
    market_open: bool
    next_events: tuple[Event, ...]
    note: str

    def as_dict(self) -> dict:
        return {
            "at": self.at.isoformat(),
            "open": list(self.open_sessions),
            "liquidity": self.liquidity,
            "overlap": self.overlap,
            "market_open": self.market_open,
            "note": self.note,
            "next": [{"name": e.name, "at": e.at.isoformat(),
                      "in_minutes": round(e.minutes_from(self.at), 1),
                      "note": e.note} for e in self.next_events],
        }


def market_open(at: datetime) -> bool:
    """Is the FX market open at all?

    The week runs Sunday 17:00 New York to Friday 17:00 New York. Expressed in
    NY local time deliberately: the UTC boundary moves twice a year, and a fixed
    "Friday 21:00 UTC" close is an hour wrong for half the year.
    """
    ny = at.astimezone(NY)
    wd, t = ny.weekday(), ny.time()
    if wd == 5:                                    # Saturday
        return False
    if wd == 6:                                    # Sunday: opens 17:00
        return t >= ROLLOVER_LOCAL
    if wd == 4 and t >= ROLLOVER_LOCAL:            # Friday: closes 17:00
        return False
    return True


def _next_weekday_at(now: datetime, tz: ZoneInfo, weekday: int,
                     at_time: time) -> datetime:
    """Next occurrence of `weekday` at `at_time` in `tz`, strictly after `now`.

    Built by localising a naive datetime rather than by adding a UTC offset, so
    a target that lands on a DST changeover keeps the intended wall-clock time.
    """
    local = now.astimezone(tz)
    days = (weekday - local.weekday()) % 7
    cand = datetime.combine(local.date() + timedelta(days=days), at_time, tzinfo=tz)
    if cand <= local:
        cand = datetime.combine(local.date() + timedelta(days=days + 7),
                                at_time, tzinfo=tz)
    return cand.astimezone(UTC)


def _next_daily(now: datetime, tz: ZoneInfo, at_time: time,
                skip_weekend: bool = True) -> datetime:
    local = now.astimezone(tz)
    cand = datetime.combine(local.date(), at_time, tzinfo=tz)
    while cand <= local or (skip_weekend and cand.weekday() >= 5):
        cand = datetime.combine(cand.date() + timedelta(days=1), at_time, tzinfo=tz)
    return cand.astimezone(UTC)


def upcoming(now: datetime, *, gold: bool = True, limit: int = 5) -> tuple[Event, ...]:
    """The scheduled liquidity events worth knowing about, soonest first."""
    events: list[Event] = []

    ny = now.astimezone(NY)
    if market_open(now):
        if ny.weekday() == 4:
            events.append(Event(
                "Weekend close",
                _next_weekday_at(now, NY, 4, ROLLOVER_LOCAL),
                "Market shuts until Sunday 17:00 New York. Gap risk over the break."))
        events.append(Event(
            "Daily rollover",
            _next_daily(now, NY, ROLLOVER_LOCAL),
            "Swap applied, liquidity thins. Spreads widen sharply for a few "
            "minutes - do not place a stop just beyond the spread here."))
    else:
        events.append(Event(
            "Weekly open",
            _next_weekday_at(now, NY, 6, ROLLOVER_LOCAL),
            "Sunday 17:00 New York. Thin book and gappy - the worst time to "
            "enter on a market order."))

    for s in SESSIONS:
        if not s.is_open(now):
            events.append(Event(
                f"{s.name} open",
                _next_daily(now, ZoneInfo(s.tz), s.open_local),
                f"{s.name} desks come in."))

    if gold:
        for t in LBMA_AUCTIONS:
            events.append(Event(
                f"LBMA {t:%H:%M} auction",
                _next_daily(now, LONDON, t),
                "Gold benchmark fixing. Physical interest concentrates here."))

    events.sort(key=lambda e: e.at)
    return tuple(events[:limit])


def state(now: datetime | None = None, *, gold: bool = True) -> SessionState:
    """Full session read for `now` (defaults to this instant, UTC)."""
    now = (now or datetime.now(UTC))
    if now.tzinfo is None:
        # A naive datetime here is a bug in the caller, but silently assuming
        # local time would make it a silent wrong answer instead of a loud one.
        raise ValueError("session state needs a timezone-aware datetime")
    now = now.astimezone(UTC)

    if not market_open(now):
        nxt = upcoming(now, gold=gold)
        return SessionState(now, (), "closed", False, False, nxt,
                            "FX market closed. Reopens Sunday 17:00 New York.")

    open_now = tuple(s.name for s in SESSIONS if s.is_open(now))
    overlap = "London" in open_now and "New York" in open_now

    if overlap:
        liq: Liquidity = "deep"
        note = ("London/New York overlap - the deepest book of the day. "
                "Tightest spreads and the cleanest fills.")
    elif "London" in open_now:
        liq, note = "deep", "London open. Deep liquidity, the main FX session."
    elif "New York" in open_now:
        liq, note = "normal", "New York session. Good liquidity, thinning after London goes."
    elif open_now:
        liq, note = "normal", f"{' + '.join(open_now)} open. Ranges tend to be tighter."
    else:
        liq = "thin"
        note = ("Between sessions. Wider spreads and less reliable levels - "
                "breakouts here fail more often than they hold.")

    ny = now.astimezone(NY)
    if ny.weekday() == 6:
        liq = "very thin"
        note = ("Sunday reopen. The book is thin and gaps are common - "
                "market orders can fill a long way from the screen.")
    else:
        mins = (datetime.combine(ny.date(), ROLLOVER_LOCAL, tzinfo=NY) - ny
                ).total_seconds() / 60.0
        if -10 <= mins <= 20:
            liq = "very thin"
            note = ("Rollover window. Spreads spike hard for a few minutes; "
                    "this is when a stop gets taken by the spread and not by price.")

    return SessionState(now, open_now, liq, overlap, True,
                        upcoming(now, gold=gold), note)
