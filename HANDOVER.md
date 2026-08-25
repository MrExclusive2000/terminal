# Handover

State of this repo as of 2026-08-25. Written so someone else can pick it up.

## Works, verified against live data

| Thing | Where | Evidence |
|---|---|---|
| CFTC COT ingest + percentile bands | `src/argus/data/cot.py` | Live for gold, silver, 5 FX majors, DXY. Handles both report families. USDJPY sign-flipped (CME contract is JPY/USD). |
| FRED macro fetch | `src/argus/data/fred.py` | Live. Parsing validated against `nominal = real + breakeven`, 0.0000 error over 750 obs. |
| Regime detection | `src/argus/analysis/regime.py` | Correlates daily changes, not levels. Detects injected sign flips. |
| Position sizing | `src/argus/trade/sizing.py` | Hand-checked. Risk never exceeds target across 395 stop distances. Refuses sub-minimum sizes rather than rounding up. |
| Stop placement + entry cost | `src/argus/trade/levels.py` | ATR, structure, session. Surfaces spread as % of stop distance. |
| Local backend + UI | `src/argus/app/` | Every endpoint exercised live. Degrades honestly when MT5 is absent. |
| Knowledge packs | `knowledge/packs/`, `src/argus/knowledge/` | 15 claims, claim-level diff working. |
| Tests | `tests/test_core.py` | 42 checks, all passing. |

## Does not work / never built

- **MT5 bridge** (`src/argus/bridge/mt5_bridge.py`) — written against the documented
  API, **never run**. Needs Windows + a running terminal. Expect the first run to
  break on symbol suffixes (IC appends them by account type), UTC vs local time,
  or the terminal's "Max bars in chart" cap silently truncating requests.
- **Claude analyst** (`src/argus/ai/analyst.py`) — written, never called. Needs
  `ANTHROPIC_API_KEY`. Uses `claude-opus-5`, adaptive thinking, cached prefix.
- **Auto-updater** — not built. Was next.
- **Equities / insiders** — planned in detail (`docs/plan/`), not built. This was
  in the original brief and should not have been cut.
- **Stocks** — same.

## Run it

```
python -m venv .venv && .venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Worth keeping regardless of what you build next

Findings from the research that would cost you time to rediscover:

- Polygon.io is now Massive.com (Oct 2025).
- SEC Form SHO short-position data is **not live** — exemption runs to Jan 2028.
- `companyfacts` silently drops dimensional facts, so segment data is not in it.
- The UTP tape moves to 23×5 on 6 Dec 2026 — "trading day" ≠ "calendar date".
- Form 4 filings land 16:00–22:00 ET, not intraday.
- GOFO was discontinued Jan 2015; lease rates must be derived.
- Gold/real-yield correlation decoupled after 2024 when central banks displaced
  ETFs as marginal buyer.
- IC Markets: no FIX into MT4/MT5; cTrader splits FIX into separate price and
  trade credentials, which is a real security property if you ever use it.
- DPAPI does not protect against malware running as the user.

Full detail in `docs/research/` (9 dossiers, 4 adversarial reviews) and
`docs/plan/argus-build-plan-v2.html` (v1.0 kept alongside as `argus-design-plan.html`).
