"""
Local backend for the desktop window.

Binds to 127.0.0.1 on an ephemeral port and is reachable only from this
machine. Serves the UI and a small JSON API over the deterministic engines.
No external listener, no remote access - the no-distribution invariant is
structural, not a promise.
"""
from __future__ import annotations

import json
import threading
import traceback
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Callable
from urllib.parse import parse_qs, urlparse

def _ui_path() -> Path:
    """The UI file, in both source and frozen layouts."""
    from argus.config import resource
    return resource("app", "ui.html")

_cache: dict[str, tuple[float, Any]] = {}
_lock = threading.Lock()


def cached(key: str, ttl: float, fn: Callable[[], Any]) -> Any:
    """Time-boxed memo so the UI can poll without hammering providers."""
    import time
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < ttl:
            return hit[1]
    value = fn()
    with _lock:
        _cache[key] = (now, value)
    return value


# ---------------------------------------------------------------- endpoints

def ep_status() -> dict[str, Any]:
    from argus.bridge import mt5_bridge
    mt5_ok, mt5_msg = False, "not connected"
    try:
        mt5_bridge._require_mt5()
        mt5_ok, mt5_msg = True, "package present"
    except Exception as exc:  # noqa: BLE001
        mt5_msg = str(exc)
    return {
        "utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "mt5": {"ok": mt5_ok, "detail": mt5_msg},
    }


def ep_positioning(symbol: str) -> dict[str, Any]:
    from argus.data.cot import CONTRACTS, CotError, snapshot
    if symbol not in CONTRACTS:
        return {"error": f"no COT contract mapped for {symbol}"}
    try:
        s = cached(f"cot:{symbol}", 3600, lambda: snapshot(symbol, weeks=260))
    except CotError as exc:
        return {"error": str(exc)}
    return {
        "as_of": s.as_of.isoformat(), "age_days": s.age_days,
        "staleness": s.staleness, "open_interest": s.open_interest,
        "cohorts": [{
            "name": n, "net": c.net, "change": c.change_net,
            "percentile": c.percentile, "flag": c.crowded,
        } for n, c in s.cohorts.items()],
    }


def ep_macro() -> dict[str, Any]:
    from argus.data.fred import FredError, named
    out: dict[str, Any] = {}
    for key in ("real_yield_10y", "dollar_broad", "breakeven_10y", "nominal_10y"):
        try:
            series = cached(f"fred:{key}", 3600, lambda k=key: named(k))
        except FredError as exc:
            out[key] = {"error": str(exc)}
            continue
        days = sorted(series)
        cur = series[days[-1]]
        def delta(n: int) -> float | None:
            past = [v for d, v in series.items() if (days[-1] - d).days <= n]
            return round(cur - past[0], 3) if past else None
        out[key] = {"value": cur, "as_of": days[-1].isoformat(),
                    "d30": delta(30), "d90": delta(90)}
    return out


def ep_quote(symbol: str) -> dict[str, Any]:
    """Live price and spread. Degrades honestly when MT5 is absent."""
    from argus.bridge import mt5_bridge
    try:
        return {"ok": True, **mt5_bridge.spread_now(symbol)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc),
                "hint": "Open MT5, log in, and make sure the symbol is in Market Watch."}


def ep_card(q: dict[str, list[str]]) -> dict[str, Any]:
    """Stops, size and cost. Uses live bars when MT5 is up, inputs when not."""
    from argus.bridge import mt5_bridge
    from argus.trade.levels import Bar, atr, cost_of_entry, stop_candidates
    from argus.trade.sizing import INSTRUMENTS, SizingError, size_position

    def g(k: str, d: str = "") -> str:
        return (q.get(k) or [d])[0]

    symbol = g("symbol", "XAUUSD")
    inst = INSTRUMENTS.get(symbol)
    if inst is None:
        return {"error": f"unknown instrument {symbol}"}
    direction = g("direction", "long")
    bal, risk = float(g("balance", "25000")), float(g("risk", "1"))
    fx, lev = float(g("fx", "0.79")), int(g("leverage", "30"))
    ccy = g("currency", "GBP")

    entry = float(g("entry") or 0) or None
    spread = float(g("spread") or 0)
    a = float(g("atr") or 0) or None
    bars: list[Bar] = []

    try:
        raw = mt5_bridge.bars(symbol, "H1", 200)
        bars = [Bar(r["t"], r["o"], r["h"], r["l"], r["c"]) for r in raw]
        live = mt5_bridge.spread_now(symbol)
        entry = entry or live["ask" if direction == "long" else "bid"]
        spread = spread or (live.get("spread_price") or 0)
        a = a or atr(bars, 14)
        source = "MT5 live"
    except Exception:  # noqa: BLE001 - absent terminal is a normal state
        source = "manual inputs (MT5 not connected)"

    if not entry or not a:
        return {"error": "need an entry price and an ATR (or a live MT5 connection)",
                "source": source}

    if bars:
        cands = stop_candidates(bars=bars, entry=entry, direction=direction,
                                spread=spread, digits=inst.digits)
    else:
        sign = -1 if direction == "long" else 1
        from argus.trade.levels import StopCandidate
        cands = []
        for label, mult in (("ATR x1.0", 1.0), ("ATR x1.5", 1.5), ("ATR x2.5", 2.5)):
            p = round(entry + sign * mult * a + sign * spread, inst.digits)
            dist = abs(entry - p)
            cands.append(StopCandidate(method=label, price=p, distance=round(dist, inst.digits),
                                       rationale=f"{mult}x ATR", atr_multiple=round(dist / a, 2),
                                       inside_noise=dist < a))

    rows = []
    for c in cands:
        try:
            s = size_position(instrument=inst, entry=entry, stop=c.price,
                              account_balance=bal, risk_pct=risk,
                              account_currency=ccy, quote_to_account=fx, leverage=lev)
        except SizingError as exc:
            rows.append({"method": c.method, "error": str(exc)})
            continue
        cost = cost_of_entry(spread=spread, stop_distance=c.distance)
        rows.append({
            "method": c.method, "stop": c.price, "distance": c.distance,
            "atr_multiple": c.atr_multiple, "inside_noise": c.inside_noise,
            "lots": s.lots, "risk_actual": s.risk_actual, "risk_target": s.risk_target,
            "margin": s.margin_required, "warnings": list(s.warnings),
            "spread_pct_of_risk": cost.spread_pct_of_risk, "cost_verdict": cost.verdict,
            "targets": [{"r": r, "price": round(entry + (r * c.distance if direction == "long"
                                                         else -r * c.distance), inst.digits),
                         "profit": round(r * s.risk_actual, 2)} for r in (1, 2, 3)],
        })
    return {"symbol": symbol, "direction": direction, "entry": entry, "spread": spread,
            "atr": round(a, inst.digits), "source": source, "currency": ccy, "stops": rows}


def ep_desk(q: dict[str, list[str]]) -> dict[str, Any]:
    """The FX and metals desk: session state, what is scheduled, and the bias board.

    Assembled from whatever is actually available. A provider that is down
    removes its evidence from the board and says so, rather than the board
    quietly presenting a thinner case as though it were the whole picture.
    """
    from datetime import datetime, timezone

    from argus.analysis import bias
    from argus.analysis import calendar as cal
    from argus.analysis import sessions as sess

    symbol = (q.get("symbol") or ["XAUUSD"])[0].upper()
    now = datetime.now(timezone.utc)
    gold = symbol.startswith("XAU") or symbol.startswith("XAG")

    state = sess.state(now, gold=gold)
    releases = cal.upcoming(now, days=21, symbols=(symbol,))
    reads: list[Any] = [bias.from_session(state.liquidity, state.note)]

    if releases:
        nxt = releases[0]
        reads.append(bias.from_event(nxt.name, nxt.minutes_from(now), nxt.impact))

    sources: dict[str, str] = {}

    # Positioning. Cached hard - COT moves once a week, so polling it is waste.
    try:
        from argus.data.cot import snapshot
        snap = cached(f"cot:{symbol}", 3600.0, lambda: snapshot(symbol))
        # cohorts is a dict keyed by cohort name. The speculative cohort is
        # named differently by report family: commodities report managed money,
        # financial futures report leveraged funds.
        reading = (snap.cohorts.get("managed_money")
                   or snap.cohorts.get("leveraged_funds"))
        if reading is not None:
            pct = reading.percentile
            # USDJPY and friends: the CME contract is JPY/USD, so a crowded long
            # in the future is a crowded SHORT in the pair as conventionally
            # written. Flipping the percentile keeps the board in pair terms;
            # not flipping it points the read at the wrong side of the market.
            if snap.inverted and pct is not None:
                pct = 100.0 - pct
            reads.append(bias.from_positioning(
                reading.cohort.replace("_", " ").title(), float(reading.net),
                pct, snap.as_of))
        sources["positioning"] = snap.staleness + (
            " [inverted to pair terms]" if snap.inverted else "")
    except Exception as exc:  # noqa: BLE001
        sources["positioning"] = f"unavailable ({type(exc).__name__})"

    board = bias.build(symbol, reads, now=now)
    if any("unavailable" in v for v in sources.values()):
        board.warnings.append(
            "Some evidence could not be loaded, so this board is thinner than "
            "usual. Read the strength accordingly.")

    return {"symbol": symbol, "session": state.as_dict(),
            "calendar": [r.as_dict(now) for r in releases[:8]],
            "board": board.as_dict(), "sources": sources}


def ep_settings() -> dict[str, Any]:
    """Current settings, secrets excluded by construction."""
    from argus import config
    return config.load().public()


def ep_secret_save(body: dict[str, Any]) -> dict[str, Any]:
    """Store the Claude API key in the protected secret store.

    Kept on its own endpoint, away from the settings whitelist, so a secret can
    never be written into settings.json by a field-name mistake. The value is
    never echoed back - only its masked status.
    """
    from argus.secrets import set_secret, status

    key = str(body.get("anthropic_api_key", "")).strip()
    if key and not key.startswith("sk-"):
        return {"ok": False,
                "error": "That does not look like an Anthropic API key - they "
                         "begin with 'sk-'. Nothing was saved."}
    try:
        set_secret("anthropic_api_key", key)
    except OSError as exc:
        return {"ok": False, "error": f"Could not write the secret store: {exc}"}
    return {"ok": True, "api_key": status("anthropic_api_key"),
            "cleared": not key}


def ep_test_ai() -> dict[str, Any]:
    """Prove the key works, with the cheapest call that can fail honestly."""
    from argus import config
    from argus.config import load

    key = config.Settings.api_key()
    if not key:
        return {"ok": False, "error": "No API key configured."}
    try:
        import anthropic
    except ImportError:
        return {"ok": False,
                "error": "The anthropic package is not installed in this build, "
                         "so AI features are unavailable. The key was saved."}
    try:
        client = anthropic.Anthropic(api_key=key)
        r = client.messages.create(
            model=load().ai_model, max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: ready"}])
        text = "".join(b.text for b in r.content if b.type == "text").strip()
        return {"ok": True, "model": r.model, "reply": text[:40],
                "tokens": {"in": r.usage.input_tokens, "out": r.usage.output_tokens}}
    except Exception as exc:  # noqa: BLE001 - report, never raise into the UI
        name = type(exc).__name__
        hint = ("The key was rejected." if "Authentication" in name else
                "Rate limited - the key works." if "RateLimit" in name else
                "Could not reach the API." if "Connection" in name else str(exc)[:160])
        return {"ok": "RateLimit" in name, "error": f"{name}: {hint}"}


def ep_test_mt5() -> dict[str, Any]:
    """Try to attach to the terminal and resolve the user's symbols.

    Reports the resolved broker symbol per instrument, because the suffix is the
    thing that actually goes wrong: IC Markets serves XAUUSD, XAUUSD.a and
    XAUUSD.r depending on account type, and the wrong one reads as "symbol not
    found" rather than as a settings problem.
    """
    from argus.config import load
    from argus.bridge import mt5_bridge

    cfg = load()
    if not cfg.mt5_enabled:
        return {"ok": False, "error": "The MT5 bridge is switched off in settings."}
    try:
        mt5_bridge._require_mt5()
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc),
                "hint": "MetaTrader5 is Windows-only and needs the terminal "
                        "installed. On other platforms this will always fail."}
    try:
        kw = {"path": cfg.mt5_path} if cfg.mt5_path else {}
        info = mt5_bridge.initialize(**kw)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc),
                "hint": "Is the MetaTrader 5 terminal running and logged in?"}

    resolved: list[dict[str, Any]] = []
    for base in ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY"):
        found = None
        for cand in ({base + cfg.mt5_suffix} if cfg.mt5_suffix else set()) | {
                base, base + ".a", base + ".r", base + "m", base + "#"}:
            try:
                mt5_bridge.symbol_info(cand)
                found = cand
                break
            except Exception:  # noqa: BLE001 - not this one, try the next
                continue
        resolved.append({"instrument": base, "broker_symbol": found})
    hits = [r for r in resolved if r["broker_symbol"]]
    suffix = ""
    if hits:
        s0 = hits[0]["broker_symbol"]
        suffix = s0[len(hits[0]["instrument"]):]
    return {"ok": True, "account": info.get("account"), "symbols": resolved,
            "detected_suffix": suffix,
            "note": (f"Detected symbol suffix {suffix!r}." if suffix
                     else "Symbols resolve with no suffix.")}


def ep_settings_save(body: dict[str, Any]) -> dict[str, Any]:
    """Persist settings from the UI.

    Only whitelisted fields are writable, and any key that looks like a secret
    is refused rather than silently ignored - a caller trying to POST an API key
    to *this* endpoint should be told where it actually goes.
    """
    from argus import config

    banned = {"api_key", "anthropic_api_key", "token", "secret", "password"}
    offered = {k.lower() for k in body}
    if offered & banned:
        return {"ok": False,
                "error": "Secrets are not written to settings.json. Post the key "
                         "to /api/secret instead, where it is stored in the "
                         "protected secret store."}

    allowed = {"sec_contact", "professional", "account_currency", "risk_percent",
               "balance", "insider_limit", "update_check", "onboarded", "window",
               "mt5_path", "mt5_suffix", "mt5_enabled",
               "ai_enabled", "ai_model", "ai_effort", "ai_monthly_budget_usd"}
    changes = {k: v for k, v in body.items() if k in allowed}
    if not changes:
        return {"ok": False, "error": "Nothing recognised to save."}

    # Reject values the UI should never have offered, rather than storing a
    # model id or effort level this build has never been run against.
    if (m := changes.get("ai_model")) and m not in config.AI_MODELS:
        return {"ok": False, "error": f"Unknown model {m!r}."}
    if (e := changes.get("ai_effort")) and e not in config.AI_EFFORTS:
        return {"ok": False, "error": f"Unknown effort level {e!r}."}

    s = config.update(**changes)
    # Clear any cached insider pull: the contact may have changed, which changes
    # whether the request succeeds at all.
    if "sec_contact" in changes:
        with _lock:
            for k in [k for k in _cache if k.startswith("insider:")]:
                _cache.pop(k, None)
    return {"ok": True, "settings": s.public()}


def ep_insider(q: dict[str, list[str]]) -> dict[str, Any]:
    """Scored Form 4 feed.

    Cached hard: a full pull is a few dozen rate-limited SEC round trips, and
    the underlying feed only moves as filings arrive. Polling this endpoint must
    never turn into polling EDGAR.
    """
    from argus.insider.pipeline import run

    limit = 40
    try:
        limit = max(1, min(40, int((q.get("limit") or ["40"])[0])))
    except ValueError:
        pass
    contact = (q.get("contact") or [""])[0].strip()

    def pull() -> dict[str, Any]:
        from argus.data.edgar import ContactNotConfigured
        try:
            return run(limit=limit, contact=contact or None).as_dict()
        except ContactNotConfigured as exc:
            # A configuration problem, not an outage. Said plainly, with the fix,
            # because "HTTP 403" sends you debugging the wrong thing.
            return {"error": str(exc), "needs_contact": True, "events": [],
                    "clusters": [], "filings": 0, "rows": 0}
        except Exception as exc:  # noqa: BLE001
            # Surface the failure as data so the panel can render a real
            # provider-down state instead of an empty table that reads as
            # "no insider activity".
            return {"error": f"{type(exc).__name__}: {exc}", "events": [],
                    "clusters": [], "filings": 0, "rows": 0}

    return cached(f"insider:{limit}", 300.0, pull)


def ep_analyse(body: dict[str, Any]) -> dict[str, Any]:
    from argus.ai.analyst import AnalysisRequest, analyse
    try:
        return analyse(AnalysisRequest(
            instrument=body.get("instrument", "XAUUSD"),
            question=body.get("question", "Long or short here, and why?"),
            facts=body.get("facts", {}),
            external=body.get("external", ""),
            effort=body.get("effort", "high"),
        ))
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}",
                "hint": "Set ANTHROPIC_API_KEY, or run: ant auth login"}


ROUTES: dict[str, Callable[[dict[str, list[str]]], Any]] = {
    "/api/status": lambda q: ep_status(),
    "/api/positioning": lambda q: ep_positioning((q.get("symbol") or ["XAUUSD"])[0]),
    "/api/macro": lambda q: ep_macro(),
    "/api/quote": lambda q: ep_quote((q.get("symbol") or ["XAUUSD"])[0]),
    "/api/card": ep_card,
    "/api/insider": ep_insider,
    "/api/settings": lambda q: ep_settings(),
    "/api/desk": ep_desk,
    "/api/test/ai": lambda q: ep_test_ai(),
    "/api/test/mt5": lambda q: ep_test_mt5(),
}


def _startup_error(exc: Exception) -> bytes:
    """A diagnosable page for the one failure that has no UI to render into."""
    from argus import config
    return (f"""<!doctype html><meta charset=utf-8>
<title>Argus - could not start</title>
<style>body{{background:#0C1013;color:#DFE6E4;font:14px/1.6 system-ui,sans-serif;
padding:44px;max-width:760px}}code{{background:#12181A;padding:2px 6px;border-radius:2px;
font-family:Consolas,monospace}}h1{{font-size:19px}}.m{{color:#8B9996}}</style>
<h1>Argus could not load its interface</h1>
<p>The application started, but the bundled interface file is missing from this
install. This is a packaging fault, not something you have done wrong.</p>
<p class=m><code>{type(exc).__name__}: {exc}</code></p>
<p class=m>Looked in: <code>{_ui_path()}</code><br>
Version: <code>{config.version()}</code> &middot;
Frozen: <code>{config.frozen()}</code></p>
<p>Reinstalling from the latest release is the fix. If it persists, this text is
what to report.</p>""").encode()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # keep the console clean
        pass

    def _send(self, code: int, payload: Any, ctype="application/json") -> None:
        body = (json.dumps(payload, default=str).encode() if ctype == "application/json"
                else payload)
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        u = urlparse(self.path)
        if u.path in ("/", "/index.html"):
            # Guarded because an unhandled exception here sends *nothing*: the
            # handler thread dies mid-request and the browser reports
            # ERR_EMPTY_RESPONSE, which tells the user nothing at all. The first
            # shipped build failed exactly this way on a mislocated bundled
            # asset. A readable error page is the difference between a
            # five-minute fix and an afternoon.
            try:
                body = _ui_path().read_bytes()
            except OSError as exc:
                self._send(500, _startup_error(exc), "text/html; charset=utf-8")
                return
            self._send(200, body, "text/html; charset=utf-8"); return
        fn = ROUTES.get(u.path)
        if not fn:
            self._send(404, {"error": "no such endpoint"}); return
        try:
            self._send(200, fn(parse_qs(u.query)))
        except Exception as exc:  # noqa: BLE001
            self._send(500, {"error": str(exc), "trace": traceback.format_exc(limit=3)})

    def do_POST(self) -> None:
        u = urlparse(self.path)
        n = int(self.headers.get("Content-Length", "0"))
        try:
            body = json.loads(self.rfile.read(n) or b"{}")
        except json.JSONDecodeError:
            self._send(400, {"error": "invalid JSON"}); return
        if u.path == "/api/analyse":
            self._send(200, ep_analyse(body)); return
        if u.path == "/api/settings":
            self._send(200, ep_settings_save(body)); return
        if u.path == "/api/secret":
            self._send(200, ep_secret_save(body)); return
        self._send(404, {"error": "no such endpoint"})


def serve(port: int = 0) -> tuple[ThreadingHTTPServer, str]:
    """Start on localhost. Port 0 means the OS picks a free one."""
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}/"
