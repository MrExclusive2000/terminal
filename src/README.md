# Argus — working code

Built and verified in one session. Status of each piece is stated honestly
below, because "written" and "verified" are different things.

| Module | What it does | Status |
|---|---|---|
| `argus/data/http.py` | Shared GET with jittered backoff, per-adapter User-Agent | **Verified** against live hosts |
| `argus/data/cot.py` | CFTC COT ingest, cohort netting, percentile bands, vintage stamps | **Verified live** — gold, silver, 5 FX majors, DXY |
| `argus/data/fred.py` | FRED series fetch, no API key | **Verified live** — 4 series, identity-checked |
| `argus/analysis/regime.py` | Rolling vs long-run correlation; regime-break detection | **Verified** — live data + synthetic control |
| `argus/bridge/mt5_bridge.py` | Read-only MT5 bridge over stdio JSON | **UNVERIFIED** — needs Windows + running MT5 |

## Run

    PYTHONPATH=src python3 -m argus.cli            # once a CLI exists
    python3 tests/test_core.py                     # 18 offline tests

## Verification notes

- **COT** returns live cohort positioning for all seven instruments. USDJPY is
  sign-flipped because the CME contract is JPY/USD — a long JPY future is short
  USDJPY. Getting this wrong inverts every reading.
- **FRED** parsing is checked against the accounting identity
  `nominal = real + breakeven`, which came back with 0.0000 max error over 750
  observations. That validates parsing, date alignment and float handling in one
  assertion rather than by eyeball.
- **Regime engine** correlates daily *changes*, never levels: two rising series
  correlate on levels regardless of any real relationship. A test asserts this.
- **MT5 bridge** cannot be run here. It is written against the documented API and
  must be treated as unverified until it runs on the target machine.

## The read-only property

`mt5_bridge.METHODS` contains exactly five read functions. There is no code path
from the application to an order, and a test asserts that no mutating method is
reachable. This does not make the host safe — a logged-in MT5 terminal is itself
a trading capability available to any local process — but this application never
widens that exposure, and the AI layer has no route to the broker.
