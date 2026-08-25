"""
MT5 read-only bridge.

Runs as a separate child process next to the terminal. Exposes bars, ticks and
symbol metadata over stdio JSON-RPC and nothing else.

The read-only property is enforced structurally, not by convention:
`order_send` and every other mutating call is absent from the dispatch table,
so there is no code path from the application to an order. That is deliberate
and load-bearing - see the security section of the plan. It does not make the
host safe (a logged-in terminal is itself a trading capability available to any
local process), but it does mean this application never widens that exposure,
and in particular the AI layer has no route to the broker.

Cannot be tested in this environment: MetaTrader5 is Windows-only and needs a
running terminal. Everything here is written against the documented API and is
UNVERIFIED until run on the target machine.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, Callable

try:
    import MetaTrader5 as mt5  # type: ignore
except ImportError:  # pragma: no cover - absent off-Windows
    mt5 = None


TIMEFRAMES = {
    "M1": "TIMEFRAME_M1", "M5": "TIMEFRAME_M5", "M15": "TIMEFRAME_M15",
    "M30": "TIMEFRAME_M30", "H1": "TIMEFRAME_H1", "H4": "TIMEFRAME_H4",
    "D1": "TIMEFRAME_D1", "W1": "TIMEFRAME_W1",
}


class BridgeError(RuntimeError):
    pass


def _require_mt5():
    if mt5 is None:
        raise BridgeError("MetaTrader5 package unavailable (Windows-only, needs a running terminal)")


def _utc(ts: int) -> str:
    """MT5 timestamps are UTC. Python's datetime defaults to local time, which
    is the single most common bug in MT5 pipelines - it silently shifts every
    bar by the host's offset. Always construct explicitly."""
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


def initialize(**kw) -> dict[str, Any]:
    _require_mt5()
    if not mt5.initialize(**kw):
        raise BridgeError(f"initialize failed: {mt5.last_error()}")
    info = mt5.terminal_info()
    acct = mt5.account_info()
    return {
        "terminal": {"build": getattr(info, "build", None),
                     "connected": getattr(info, "connected", None),
                     "max_bars": getattr(info, "maxbars", None)},
        "account": {"server": getattr(acct, "server", None),
                    "currency": getattr(acct, "currency", None),
                    "leverage": getattr(acct, "leverage", None)},
    }


def symbol_info(symbol: str) -> dict[str, Any]:
    """Broker symbol metadata. IC suffixes symbols by account type, so the
    caller must resolve broker symbol -> canonical instrument rather than
    assuming 'XAUUSD' is a universal key."""
    _require_mt5()
    s = mt5.symbol_info(symbol)
    if s is None:
        raise BridgeError(f"unknown symbol {symbol!r}: {mt5.last_error()}")
    return {
        "name": s.name, "digits": s.digits, "point": s.point,
        "spread_points": s.spread,
        "contract_size": s.trade_contract_size,
        "volume_min": s.volume_min, "volume_step": s.volume_step,
        "swap_long": s.swap_long, "swap_short": s.swap_short,
        "swap_rollover3days": s.swap_rollover3days,  # the multiplied-swap weekday
        "currency_profit": s.currency_profit,
    }


def bars(symbol: str, timeframe: str, count: int = 500) -> list[dict[str, Any]]:
    _require_mt5()
    if timeframe not in TIMEFRAMES:
        raise BridgeError(f"unknown timeframe {timeframe!r}; known: {sorted(TIMEFRAMES)}")
    tf = getattr(mt5, TIMEFRAMES[timeframe])
    rows = mt5.copy_rates_from_pos(symbol, tf, 0, count)
    if rows is None:
        raise BridgeError(f"copy_rates_from_pos failed: {mt5.last_error()}")
    if len(rows) < count:
        # Bar history is silently capped by the terminal's "Max bars in chart"
        # setting - requests return short without raising. Surface it.
        sys.stderr.write(
            f"[bridge] warning: asked {count} bars of {symbol} {timeframe}, "
            f"got {len(rows)} - check Max bars in chart\n")
    return [{
        "t": _utc(int(r["time"])), "o": float(r["open"]), "h": float(r["high"]),
        "l": float(r["low"]), "c": float(r["close"]),
        "tick_volume": int(r["tick_volume"]), "spread": int(r["spread"]),
        # real_volume is 0 on FX and CFDs. Passed through unaltered so the UI
        # can refuse to render it as volume rather than quietly plotting a lie.
        "real_volume": int(r["real_volume"]),
    } for r in rows]


def ticks(symbol: str, start_iso: str, end_iso: str) -> list[dict[str, Any]]:
    """Historical ticks in [start, end). MT5 pulls these from the broker's
    server, which is why deep tick history is obtainable here and not through
    cTrader's one-week-per-request cap."""
    _require_mt5()
    start = datetime.fromisoformat(start_iso).astimezone(timezone.utc)
    end = datetime.fromisoformat(end_iso).astimezone(timezone.utc)
    rows = mt5.copy_ticks_range(symbol, start, end, mt5.COPY_TICKS_ALL)
    if rows is None:
        raise BridgeError(f"copy_ticks_range failed: {mt5.last_error()}")
    return [{
        "t": _utc(int(r["time"])), "bid": float(r["bid"]), "ask": float(r["ask"]),
        "last": float(r["last"]), "flags": int(r["flags"]),
    } for r in rows]


def spread_now(symbol: str) -> dict[str, Any]:
    """Live spread. The intraday panel that most directly saves money."""
    _require_mt5()
    t = mt5.symbol_info_tick(symbol)
    s = mt5.symbol_info(symbol)
    if t is None or s is None:
        raise BridgeError(f"no tick for {symbol!r}: {mt5.last_error()}")
    spread_price = t.ask - t.bid
    return {
        "t": _utc(int(t.time)), "bid": t.bid, "ask": t.ask,
        "spread_price": round(spread_price, s.digits),
        "spread_points": round(spread_price / s.point, 1) if s.point else None,
    }


# Read-only dispatch table. Adding a mutating entry here is the only way to
# make this process capable of trading; keep it that way.
METHODS: dict[str, Callable[..., Any]] = {
    "initialize": initialize,
    "symbol_info": symbol_info,
    "bars": bars,
    "ticks": ticks,
    "spread_now": spread_now,
}

FORBIDDEN = {"order_send", "order_check", "order_calc_margin", "positions_modify"}
assert not (FORBIDDEN & METHODS.keys()), "a mutating method reached the dispatch table"


def serve(stdin=sys.stdin, stdout=sys.stdout) -> None:
    """One JSON request per line; one JSON response per line."""
    for line in stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            if method not in METHODS:
                raise BridgeError(f"unknown or non-permitted method {method!r}")
            result = METHODS[method](**req.get("params", {}))
            resp = {"id": req.get("id"), "ok": True, "result": result}
        except Exception as exc:  # noqa: BLE001 - every failure is reported, never fatal
            resp = {"id": (req.get("id") if isinstance(locals().get("req"), dict) else None),
                    "ok": False, "error": str(exc)}
        stdout.write(json.dumps(resp) + "\n")
        stdout.flush()


if __name__ == "__main__":  # pragma: no cover
    serve()
