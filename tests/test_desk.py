"""
FX and metals desk tests: sessions, release calendar, bias board.

Every case is offline and deterministic. Timezone behaviour is tested at real
DST boundaries rather than at a convenient midweek afternoon, because that is
the only place these break.
"""
from __future__ import annotations

import sys
from datetime import date, datetime, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, "src")

from argus.analysis import bias
from argus.analysis import calendar as cal
from argus.analysis import sessions as S

UTC = timezone.utc
NY = ZoneInfo("America/New_York")
PASS = FAIL = 0


def check(label: str, cond: bool) -> bool:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    return cond


def main() -> int:
    print("\n[sessions] market open/closed boundaries in New York local time")
    check("Saturday midday is closed", not S.market_open(datetime(2026, 8, 29, 12, tzinfo=UTC)))
    check("Friday 16:59 NY is open",
          S.market_open(datetime(2026, 8, 28, 16, 59, tzinfo=NY)))
    check("Friday 17:01 NY is closed",
          not S.market_open(datetime(2026, 8, 28, 17, 1, tzinfo=NY)))
    check("Sunday 16:59 NY is closed",
          not S.market_open(datetime(2026, 8, 30, 16, 59, tzinfo=NY)))
    check("Sunday 17:01 NY is open",
          S.market_open(datetime(2026, 8, 30, 17, 1, tzinfo=NY)))
    check("Wednesday midday is open", S.market_open(datetime(2026, 8, 26, 12, tzinfo=UTC)))

    print("\n[sessions] the same wall clock differs across DST, in both directions")
    # New York opens 08:00 local: 12:00 UTC on EDT, 13:00 UTC on EST.
    # London closes 17:00 local: 16:00 UTC on BST, 17:00 UTC on GMT.
    # So 12:30 and 16:30 UTC each land on opposite sides of a session boundary
    # depending on the season. A fixed UTC window is wrong at one of them.
    early_s = S.state(datetime(2026, 8, 25, 12, 30, tzinfo=UTC))
    early_w = S.state(datetime(2026, 1, 20, 12, 30, tzinfo=UTC))
    check("12:30 UTC in August: New York has opened (08:30 EDT)",
          "New York" in early_s.open_sessions and early_s.overlap)
    check("12:30 UTC in January: New York has NOT opened (07:30 EST)",
          "New York" not in early_w.open_sessions and not early_w.overlap)

    late_s = S.state(datetime(2026, 8, 25, 16, 30, tzinfo=UTC))
    late_w = S.state(datetime(2026, 1, 20, 16, 30, tzinfo=UTC))
    check("16:30 UTC in August: London has closed (17:30 BST)",
          "London" not in late_s.open_sessions)
    check("16:30 UTC in January: London still open (16:30 GMT)",
          "London" in late_w.open_sessions and late_w.overlap)
    check("an overlap is reported as deep liquidity", late_w.liquidity == "deep")

    print("\n[sessions] liquidity states")
    check("Saturday reports closed",
          S.state(datetime(2026, 8, 29, 12, tzinfo=UTC)).liquidity == "closed")
    check("Sunday reopen is very thin",
          S.state(datetime(2026, 8, 30, 22, tzinfo=UTC)).liquidity == "very thin")
    roll = S.state(datetime(2026, 8, 25, 21, 5, tzinfo=UTC))
    check("the rollover window is very thin", roll.liquidity == "very thin")
    check("the rollover warning mentions spreads", "spread" in roll.note.lower())
    check("Tokyo-only is normal, not deep",
          S.state(datetime(2026, 8, 26, 2, tzinfo=UTC)).liquidity == "normal")

    print("\n[sessions] upcoming events")
    st = S.state(datetime(2026, 8, 25, 13, 0, tzinfo=UTC))
    check("events are returned", len(st.next_events) > 0)
    check("events are ordered soonest first",
          [e.at for e in st.next_events] == sorted(e.at for e in st.next_events))
    check("every event is in the future",
          all(e.minutes_from(st.at) > 0 for e in st.next_events))
    closed = S.state(datetime(2026, 8, 29, 12, tzinfo=UTC))
    check("when closed, the weekly open is listed",
          any("Weekly open" in e.name for e in closed.next_events))
    check("naive datetimes are rejected, not assumed",
          _raises(lambda: S.state(datetime(2026, 8, 25, 13, 0))))

    print("\n[calendar] date rules")
    check("first Friday of Sep 2026", cal.nth_weekday(2026, 9, 4, 1) == date(2026, 9, 4))
    check("first Friday of Aug 2026", cal.nth_weekday(2026, 8, 4, 1) == date(2026, 8, 7))
    check("first Monday of Feb 2027", cal.nth_weekday(2027, 2, 0, 1) == date(2027, 2, 1))
    check("last business day, Aug 2026 (Mon 31st)",
          cal.last_business_day(2026, 8) == date(2026, 8, 31))
    check("last business day skips a weekend (Jan 2027)",
          cal.last_business_day(2027, 1) == date(2027, 1, 29))
    check("last business day handles a December rollover",
          cal.last_business_day(2026, 12) == date(2026, 12, 31))

    print("\n[calendar] rules resolve to the right UTC instant either side of DST")
    aug = cal.upcoming(datetime(2026, 8, 25, tzinfo=UTC), days=14)
    jan = cal.upcoming(datetime(2026, 1, 20, tzinfo=UTC), days=14)
    cot_aug = next(r for r in aug if "Commitments" in r.name)
    cot_jan = next(r for r in jan if "Commitments" in r.name)
    check("COT is 19:30 UTC on EDT (15:30 New York)", cot_aug.at.hour == 19)
    check("COT is 20:30 UTC on EST (15:30 New York)", cot_jan.at.hour == 20)
    check("both are a Friday",
          cot_aug.at.astimezone(NY).weekday() == 4
          and cot_jan.at.astimezone(NY).weekday() == 4)

    print("\n[calendar] vintage is separate from release time")
    check("COT describes the Tuesday three days earlier", cot_aug.lag_days == 3)
    check("as_of is a real date", isinstance(cot_aug.as_of, date))

    print("\n[calendar] filtering and ordering")
    now = datetime(2026, 8, 25, 14, tzinfo=UTC)
    all_ev = cal.upcoming(now, days=30)
    check("results are in chronological order",
          [r.at for r in all_ev] == sorted(r.at for r in all_ev))
    check("every result is in the future", all(r.at > now for r in all_ev))
    check("every result is inside the horizon",
          all((r.at - now).days <= 30 for r in all_ev))
    gold = cal.upcoming(now, days=30, symbols=("XAUUSD",))
    check("symbol filter matches exactly, never by substring",
          all("XAUUSD" in r.affects for r in gold))
    high = cal.upcoming(now, days=45, min_impact="high")
    check("impact filter works", all(r.impact == "high" for r in high))
    check("NFP is found as the next high-impact event",
          "Payrolls" in cal.next_high_impact(now).name)
    check("a zero-day horizon returns nothing", cal.upcoming(now, days=0) == [])
    check("naive datetimes are rejected", _raises(lambda: cal.upcoming(datetime(2026, 8, 25))))

    print("\n[bias] a single weak read must not read as conviction")
    one = bias.build("XAUUSD", [bias.from_positioning("MM", 1, 92, date(2026, 8, 18))],
                     now=now)
    check("score is saturated by normalisation", abs(one.score) == 1.0)
    check("...but strength stays weak", one.strength == "weak")
    check("and the headline says the evidence is thin", "thin evidence" in one.headline())
    check("singular grammar for one input", "1 input)" in one.headline()
          or "1 input," in one.headline())

    print("\n[bias] conflict is surfaced, not netted away")
    opposed = bias.build("XAUUSD", [
        bias.from_regime("10y real", -0.80, -0.73, +0.30),
        bias.from_regime("DXY", -0.75, -0.70, -0.25)], now=now)
    check("opposing reads net to about zero", abs(opposed.score) < 0.05)
    check("conflict is reported high", opposed.conflict > 0.9)
    check("strength is capped at weak", opposed.strength == "weak")
    check("the headline says it is split", "split" in opposed.headline())

    aligned = bias.build("XAUUSD", [
        bias.from_regime("10y real", -0.80, -0.73, +0.30),
        bias.from_regime("DXY", -0.75, -0.70, +0.25)], now=now)
    check("aligned strong reads reach strong", aligned.strength == "strong")
    check("aligned reads have no conflict", aligned.conflict < 0.05)
    check("agree() and against() partition correctly",
          len(aligned.agree()) == 2 and aligned.against() == [])

    print("\n[bias] a broken model is a warning, never a direction")
    broken = bias.from_regime("10y real yield", +0.15, -0.73, +0.20)
    check("a flipped correlation returns neutral", broken.direction == "neutral")
    check("and says the relationship has broken", "broken" in broken.detail)
    check("with a caveat against trading it", "not currently working" in broken.caveat)
    held = bias.from_regime("10y real yield", -0.70, -0.73, +0.20)
    check("an intact correlation does give a direction", held.direction == "short")

    print("\n[bias] positioning is contrarian, capped, and never called 'due'")
    hot = bias.from_positioning("MM", 1, 93, date(2026, 8, 18))
    check("a crowded long reads short", hot.direction == "short")
    check("weight is capped low", hot.weight <= 0.25)
    check("the wording says stretched, not due",
          "crowded" in hot.detail and "due" not in hot.detail.lower())
    check("mid-range positioning is neutral",
          bias.from_positioning("MM", 1, 50, date(2026, 8, 18)).direction == "neutral")
    check("a missing percentile yields no read",
          bias.from_positioning("MM", 1, None, date(2026, 8, 18)) is None)

    print("\n[bias] gates and hygiene")
    ev = bias.from_event("US Non-Farm Payrolls", 45, "high")
    check("a high-impact event ahead has zero weight", ev.weight == 0.0)
    check("it carries a sizing caveat", "leveraged" in ev.caveat)
    check("a distant event produces nothing",
          bias.from_event("NFP", 60 * 24 * 3, "high") is None)
    check("a low-impact event produces nothing",
          bias.from_event("Something", 30, "low") is None)
    gated = bias.build("XAUUSD", [ev, bias.from_session("very thin", "Rollover")],
                       now=now)
    check("zero-weight reads become warnings, not evidence",
          gated.reads == [] and len(gated.warnings) == 2)

    stale = bias.build("XAUUSD",
                       [bias.from_positioning("MM", 1, 92, date(2026, 8, 1))], now=now)
    check("a stale input raises a warning", any("days old" in w for w in stale.warnings))
    empty = bias.build("XAUUSD", [None, None], now=now)
    check("an empty board does not divide by zero",
          empty.score == 0.0 and empty.strength == "none")
    check("an empty board says so", "no evidence" in empty.headline())

    import json
    json.dumps(aligned.as_dict(), default=str)
    check("boards serialise to JSON", True)

    print(f"\n{'-' * 60}\n  {PASS} passed, {FAIL} failed\n")
    return 1 if FAIL else 0


def _raises(fn) -> bool:
    try:
        fn()
    except Exception:  # noqa: BLE001
        return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
