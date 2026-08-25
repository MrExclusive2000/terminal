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


if __name__ == "__main__":
    raise SystemExit(main())
