# Argus

A Windows desktop app that sits **next to MT5** and helps you decide: direction,
entry, stop, size, and what the trade actually costs. It never places an order.

Built for one person trading **FX and XAUUSD on IC Markets MT5** from the UK.

## Run it

Double-click **`run_argus.bat`**. First run makes a virtualenv and installs
dependencies; after that it just opens.

Or manually:

```
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python argus.py
```

Opens a native window. If `pywebview` isn't installed it falls back to your
browser, so it always runs.

### For live prices

Open MT5, log in, and put your symbols in Market Watch. Argus reads it through
MetaQuotes' official Python API. Without MT5 running, everything else still
works — you just type the entry, ATR and spread yourself.

### For the AI analyst

Set an Anthropic API key:

```
setx ANTHROPIC_API_KEY sk-ant-...
```

Uses `claude-opus-5`. Cost is shown after each answer — typically a few pence.

## What each panel does

| Panel | Answers |
|---|---|
| **Trade** | Your setup. Blank fields pull live from MT5. |
| **Stops & size** | Three stops with lot size, risk, and **spread as a % of your risk** — the number that decides short-horizon trades. Flags stops sitting inside normal noise. |
| **Targets** | 1R/2R/3R prices and profit. |
| **Positioning** | Live CFTC cohort positioning with 5-year percentiles. Who's crowded. |
| **Macro** | Real yields, dollar, breakevens — live from FRED. |
| **Analyst** | Claude, given exactly the numbers on screen. Direction and timing, with what would prove it wrong. |

## Safety properties

These are structural, not promises:

- **The bridge cannot trade.** `mt5_bridge.METHODS` holds five read functions.
  `order_send` is not reachable, and a test asserts it. A logged-in MT5 terminal
  is itself a trading path for any local process — Argus doesn't widen that, but
  it can't remove it either.
- **The AI never touches the broker.** It receives computed numbers and returns
  prose. No credentials, no filesystem write, no bridge access. News and filing
  text is wrapped as untrusted and cannot issue instructions.
- **Local only.** The backend binds 127.0.0.1 on an ephemeral port. No external
  listener, no telemetry, nothing leaves the machine except your Claude queries.

## Status

| Component | State |
|---|---|
| COT positioning engine | **Verified live** — gold, silver, 5 FX majors, DXY |
| FRED macro | **Verified live** — identity-checked to 0.0000 error |
| Regime detection | **Verified** — live data + synthetic control |
| Sizing / stops / cost | **Verified** — 42 tests, hand-checked arithmetic |
| Backend + UI | **Verified** — every endpoint exercised |
| MT5 bridge | **UNVERIFIED** — needs Windows + a running terminal |
| Claude analyst | **UNVERIFIED** — needs an API key |

The two unverified pieces are unverifiable without your machine. Expect the
first MT5 run to need a fix: symbol suffixes, timezone, or the max-bars cap.

## Tests

```
python tests/test_core.py
```

## Docs

`docs/plan/` — the full design plan. `docs/research/` — nine research dossiers
and four adversarial reviews behind it.
