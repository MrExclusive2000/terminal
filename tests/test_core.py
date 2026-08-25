"""Tests that need no network and no MetaTrader terminal."""
import io
import json
import math
import sys
from datetime import date, timedelta

sys.path.insert(0, "src")

from argus.analysis.regime import RegimeRead, _aligned_changes, _pearson, assess
from argus.bridge import mt5_bridge
from argus.data.cot import _percentile, _release_datetime


def check(label, cond):
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    return cond


def main() -> int:
    ok = True
    print("\n[bridge] read-only enforcement")
    ok &= check("no mutating method in dispatch table",
                not ({"order_send", "order_check", "positions_modify"} & mt5_bridge.METHODS.keys()))
    ok &= check("dispatch table is exactly the five read methods",
                set(mt5_bridge.METHODS) == {"initialize", "symbol_info", "bars", "ticks", "spread_now"})

    out = io.StringIO()
    mt5_bridge.serve(io.StringIO(json.dumps({"id": 1, "method": "order_send",
                                             "params": {"symbol": "XAUUSD"}}) + "\n"), out)
    resp = json.loads(out.getvalue())
    ok &= check("serve() refuses order_send", resp["ok"] is False and "non-permitted" in resp["error"])

    out = io.StringIO()
    mt5_bridge.serve(io.StringIO('{"id":2,"method":"bars","params":{"symbol":"XAUUSD","timeframe":"H1"}}\n'), out)
    resp = json.loads(out.getvalue())
    ok &= check("read method fails cleanly without a terminal (no crash)",
                resp["ok"] is False and "MetaTrader5" in resp["error"])

    out = io.StringIO()
    mt5_bridge.serve(io.StringIO("not json\n"), out)
    ok &= check("malformed input does not kill the loop", json.loads(out.getvalue())["ok"] is False)

    print("\n[regime] correlation maths")
    xs = [1.0, 2, 3, 4, 5, 6, 7, 8, 9, 10] * 3
    ok &= check("perfect positive correlation == 1.0", _pearson(xs, xs) == 1.0)
    ok &= check("perfect negative correlation == -1.0", _pearson(xs, [-x for x in xs]) == -1.0)
    ok &= check("flat series returns None (no spurious correlation)",
                _pearson(xs, [5.0] * len(xs)) is None)
    ok &= check("under-sampled window returns None", _pearson([1.0, 2, 3], [1.0, 2, 3]) is None)

    print("\n[regime] uses changes, not levels")
    d0 = date(2020, 1, 1)
    trend_a = {d0 + timedelta(days=i): 100 + i for i in range(300)}
    trend_b = {d0 + timedelta(days=i): 500 + i * 3 for i in range(300)}
    ca, cb = _aligned_changes(trend_a, trend_b)
    ok &= check("two rising trends do not manufacture correlation from levels",
                len(set(ca)) == 1 and len(set(cb)) == 1)

    print("\n[regime] detects an injected sign flip")
    base = {d0 + timedelta(days=i): math.sin(i / 11) for i in range(3000)}
    flipped = {}
    keys = sorted(base)
    for i, d in enumerate(keys):
        sign = -1 if i < len(keys) * 0.9 else 1
        flipped[d] = 100 + sign * base[d] * 10
    r = assess(flipped, base, driver_name="synthetic", window_days=252, baseline_days=5040)
    ok &= check(f"sign flip detected (cur {r.current_corr:+.2f} vs base {r.baseline_corr:+.2f})",
                r.sign_flipped and r.status == "SIGN FLIPPED")

    stable = {d: 100 + base[d] * 10 for d in keys}
    r2 = assess(stable, base, driver_name="synthetic", window_days=252, baseline_days=5040)
    ok &= check(f"stable relationship reads as holding ({r2.status})", r2.status == "holding")

    print("\n[cot] percentile bands")
    hist = list(range(100))
    ok &= check("median value ~ 50th percentile", 49 <= _percentile(hist, 50) <= 51)
    ok &= check("max value >= 99th percentile", _percentile(hist, 99) >= 99)
    ok &= check("min value <= 1st percentile", _percentile(hist, 0) <= 1)
    ok &= check("short history returns None rather than a fake percentile",
                _percentile([1, 2, 3], 2) is None)

    print("\n[cot] release-date derivation")
    rel = _release_datetime(date(2026, 8, 18))   # a Tuesday
    ok &= check(f"Tue 18 Aug -> Fri 21 Aug ({rel:%a %d %b})",
                rel.date() == date(2026, 8, 21) and rel.weekday() == 4)

    print("\n[regime] guard rails")
    empty = RegimeRead("x", None, None, 252, 5040, 0, 0)
    ok &= check("missing data reports insufficient, not a number",
                empty.status == "insufficient data" and empty.delta is None)
    ok &= check("every status has actionable guidance", bool(empty.actionable))

    print("\n" + ("ALL TESTS PASSED" if ok else "FAILURES PRESENT"))
    return 0 if ok else 1


def trade_tests() -> bool:
    """Sizing and stop-placement arithmetic. Money bugs live here."""
    from argus.trade.levels import (Bar, atr, cost_of_entry, stop_candidates,
                                    swing_high, swing_low, true_range)
    from argus.trade.sizing import INSTRUMENTS, SizingError, size_position

    ok = True
    GBP = 0.79
    print("\n[sizing] hand-checkable arithmetic")
    t = size_position(instrument=INSTRUMENTS["XAUUSD"], entry=3962.40, stop=3944.00,
                      account_balance=25_000, risk_pct=1.0, account_currency="GBP",
                      quote_to_account=GBP)
    ok &= check("XAUUSD 18.4pt stop, £25k, 1% -> 0.17 lots", t.lots == 0.17)
    ok &= check("realised risk <= target", t.risk_actual <= t.risk_target)
    ok &= check("2R target computes correctly", t.reward_at(3999.20) == 2.0)

    print("\n[sizing] quantisation never overshoots risk")
    worst = True
    for pts in range(5, 400):
        s = size_position(instrument=INSTRUMENTS["XAUUSD"], entry=3962.40,
                          stop=3962.40 - pts * 0.1, account_balance=25_000,
                          risk_pct=1.0, account_currency="GBP", quote_to_account=GBP)
        if s.lots and s.risk_actual > s.risk_target + 1e-6:
            worst = False
            break
    ok &= check("395 stop distances: risk never exceeds target", worst)

    print("\n[sizing] refuses rather than silently over-risking")
    s = size_position(instrument=INSTRUMENTS["XAUUSD"], entry=3962.40, stop=3762.40,
                      account_balance=500, risk_pct=0.5, account_currency="GBP",
                      quote_to_account=GBP)
    ok &= check("below broker minimum -> 0 lots + warning", s.lots == 0.0 and bool(s.warnings))

    s2 = size_position(instrument=INSTRUMENTS["EURUSD"], entry=1.09146, stop=1.08900,
                       account_balance=25_000, risk_pct=1.0, account_currency="GBP")
    ok &= check("missing FX conversion warns", bool(s2.warnings))

    s3 = size_position(instrument=INSTRUMENTS["USDJPY"], entry=154.28, stop=154.90,
                       account_balance=25_000, risk_pct=1.0, account_currency="GBP",
                       quote_to_account=0.0051)
    ok &= check("stop above entry -> short inferred", s3.direction == "short")

    for why, kw in [("stop == entry", dict(entry=100.0, stop=100.0, risk_pct=1)),
                    ("zero risk", dict(entry=100.0, stop=99.0, risk_pct=0)),
                    ("risk > 100%", dict(entry=100.0, stop=99.0, risk_pct=101))]:
        try:
            size_position(instrument=INSTRUMENTS["XAUUSD"], account_balance=1000, **kw)
            ok &= check(f"rejects {why}", False)
        except SizingError:
            ok &= check(f"rejects {why}", True)

    print("\n[levels] volatility maths")
    flat = [Bar(f"t{i}", 100, 105, 95, 100) for i in range(40)]
    ok &= check("constant 10pt ranges -> ATR 10.0", abs(atr(flat, 14) - 10.0) < 1e-9)
    ok &= check("true range includes gaps",
                true_range(80, Bar("x", 100, 105, 95, 100)) == 25)
    ok &= check("too few bars -> None, not a wrong number", atr(flat[:5], 14) is None)

    print("\n[levels] pivots respect the reference price")
    seq = [100, 101, 102, 101, 100, 98, 96, 98, 100, 102,
           104, 103, 102, 104, 106, 105, 104, 106, 108, 107]
    sw = [Bar(f"t{i}", v, v + 1, v - 1, v) for i, v in enumerate(seq)]
    ok &= check("swing low below reference", swing_low(sw, below=100) < 100)
    ok &= check("swing high above reference", swing_high(sw, above=106) > 106)

    print("\n[levels] stops land on the correct side of entry")
    long_side = all(c.price < 120.0 for c in
                    stop_candidates(bars=sw, entry=120.0, direction="long", spread=0.1))
    short_side = all(c.price > 80.0 for c in
                     stop_candidates(bars=sw, entry=80.0, direction="short", spread=0.1))
    ok &= check("breakout long: every stop below entry", long_side)
    ok &= check("breakdown short: every stop above entry", short_side)

    print("\n[levels] entry cost relative to risk")
    ok &= check("4pt spread on 20pt stop -> 20% of risk",
                cost_of_entry(spread=4.0, stop_distance=20.0).spread_pct_of_risk == 20.0)
    ok &= check("prohibitive verdict at >=25%",
                "prohibitive" in cost_of_entry(spread=5.0, stop_distance=20.0).verdict)
    ok &= check("cheap verdict at <5%",
                cost_of_entry(spread=0.35, stop_distance=20.0).verdict == "cheap")

    tight = stop_candidates(bars=flat, entry=100.0, direction="long",
                            spread=0.0, atr_mult=0.3)
    ok &= check("sub-ATR stop flagged as inside noise",
                any(c.inside_noise for c in tight))
    return ok


if __name__ == "__main__":
    core_ok = main() == 0
    trade_ok = trade_tests()
    print("\n" + ("=" * 40))
    print("ALL SUITES PASSED" if (core_ok and trade_ok) else "FAILURES PRESENT")
    raise SystemExit(0 if (core_ok and trade_ok) else 1)
