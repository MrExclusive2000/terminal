"""FRED series fetch. No API key: the public CSV endpoint serves full history."""
from __future__ import annotations

import csv
import io
from datetime import date, datetime

from .http import FetchError, get

FREDGRAPH = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={sid}"

SERIES = {
    "real_yield_10y": "DFII10",     # 10y TIPS - the classic gold driver
    "breakeven_10y":  "T10YIE",
    "nominal_10y":    "DGS10",
    "dollar_broad":   "DTWEXBGS",
    "sofr":           "SOFR",       # funding leg of the implied gold lease rate
}


class FredError(RuntimeError):
    pass


def fetch(series_id: str, timeout: float = 90.0) -> dict[date, float]:
    """Full history as {date: value}. FRED marks missing observations '.'."""
    try:
        body = get(FREDGRAPH.format(sid=series_id), timeout=timeout, user_agent=None)
    except FetchError as exc:
        raise FredError(str(exc)) from exc

    if body.lstrip().startswith("<"):
        raise FredError(f"FRED returned HTML for {series_id} - series id is probably wrong")

    out: dict[date, float] = {}
    for row in csv.DictReader(io.StringIO(body)):
        cols = list(row.keys())
        raw = row[cols[1]]
        if raw in (".", "", None):
            continue
        out[datetime.fromisoformat(row[cols[0]]).date()] = float(raw)
    if not out:
        raise FredError(f"FRED returned no usable observations for {series_id}")
    return out


def named(name: str) -> dict[date, float]:
    if name not in SERIES:
        raise FredError(f"unknown series {name!r}; known: {sorted(SERIES)}")
    return fetch(SERIES[name])
