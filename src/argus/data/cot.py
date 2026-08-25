"""
CFTC Commitments of Traders ingest and percentile engine.

The positioning lens: cohort net positioning with historical percentile bands.
Two CFTC report families are needed because they classify traders differently:

  Disaggregated (commodities)  -> producer/merchant, swap dealer, managed money
  TFF (financial futures)      -> dealer, asset manager, leveraged funds

Vintage discipline: COT describes the *Tuesday* of its report week and is
released the following Friday at 15:30 ET. Every record therefore carries an
as-of date distinct from its availability date, and callers are expected to
surface both. Nothing here pretends the data is current.
"""
from __future__ import annotations

import json
import urllib.parse
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from typing import Literal, Sequence

from .http import FetchError, get

SOCRATA = "https://publicreporting.cftc.gov/resource/{dataset}.json"

DISAGGREGATED = "72hh-3qpy"   # commodities: prod/merc, swap, managed money
TFF = "gpe5-46if"             # financial futures: dealer, asset mgr, leveraged

ReportFamily = Literal["disaggregated", "tff"]

# CFTC contract market codes. Verified live against the Socrata endpoints.
CONTRACTS: dict[str, tuple[str, ReportFamily]] = {
    "XAUUSD": ("088691", "disaggregated"),   # GOLD - COMMODITY EXCHANGE INC.
    "XAGUSD": ("084691", "disaggregated"),   # SILVER
    "EURUSD": ("099741", "tff"),
    "GBPUSD": ("096742", "tff"),
    "USDJPY": ("097741", "tff"),             # JPY contract; sign flips vs USDJPY
    "AUDUSD": ("232741", "tff"),
    "DXY":    ("098662", "tff"),
}

# Instruments quoted USD-per-X where a long futures position is short the USD
# pair as conventionally written. USDJPY is the classic trap: the CME contract
# is JPY/USD, so a long JPY future is *short* USDJPY.
INVERTED = {"USDJPY"}

COHORTS: dict[ReportFamily, dict[str, tuple[str, str]]] = {
    "disaggregated": {
        "producer_merchant": ("prod_merc_positions_long", "prod_merc_positions_short"),
        "swap_dealer":       ("swap_positions_long_all", "swap_positions_short_all"),
        "managed_money":     ("m_money_positions_long_all", "m_money_positions_short_all"),
        "other_reportable":  ("other_rept_positions_long", "other_rept_positions_short"),
    },
    "tff": {
        "dealer":          ("dealer_positions_long_all", "dealer_positions_short_all"),
        "asset_manager":   ("asset_mgr_positions_long", "asset_mgr_positions_short"),
        "leveraged_funds": ("lev_money_positions_long", "lev_money_positions_short"),
        "other_reportable": ("other_rept_positions_long", "other_rept_positions_short"),
    },
}


class CotError(RuntimeError):
    pass


@dataclass(frozen=True)
class CohortReading:
    """One cohort's net position for one report week, with its percentile context."""
    cohort: str
    long: int
    short: int
    net: int
    change_net: int | None
    percentile: float | None          # 0-100 over the lookback window
    lookback_weeks: int

    @property
    def crowded(self) -> str | None:
        """Plain-language extremity flag. None when not notable."""
        if self.percentile is None:
            return None
        if self.percentile >= 95:
            return "extreme long"
        if self.percentile >= 85:
            return "stretched long"
        if self.percentile <= 5:
            return "extreme short"
        if self.percentile <= 15:
            return "stretched short"
        return None


@dataclass(frozen=True)
class CotSnapshot:
    instrument: str
    contract_code: str
    family: ReportFamily
    as_of: date                 # the Tuesday the data describes
    released_at: datetime       # when CFTC published it (Friday 15:30 ET)
    open_interest: int
    cohorts: dict[str, CohortReading]
    inverted: bool = False

    @property
    def age_days(self) -> int:
        return (datetime.now(timezone.utc).date() - self.as_of).days

    @property
    def staleness(self) -> str:
        return f"COT as of {self.as_of.isoformat()} ({self.age_days}d old)"


def _get(dataset: str, params: dict[str, str], timeout: float = 60.0) -> list[dict]:
    url = SOCRATA.format(dataset=dataset) + "?" + urllib.parse.urlencode(params)
    try:
        return json.loads(get(url, timeout=timeout))
    except FetchError as exc:
        raise CotError(str(exc)) from exc


def _to_int(v) -> int:
    if v in (None, ""):
        return 0
    return int(float(v))


def _release_datetime(as_of: date) -> datetime:
    """COT for Tuesday `as_of` is released the following Friday at 15:30 ET."""
    friday = as_of + timedelta(days=(4 - as_of.weekday()) % 7 or 3)
    # 15:30 ET; ET is UTC-4 in summer, -5 in winter. Approximated as -4 between
    # mid-March and early November. Exactness here is cosmetic - it only drives
    # the "released at" label, never a calculation.
    offset = 4 if 3 <= friday.month <= 10 else 5
    return datetime(friday.year, friday.month, friday.day, 15 + offset, 30, tzinfo=timezone.utc)


def _percentile(series: Sequence[float], value: float) -> float | None:
    """Rank of `value` within `series`, 0-100. Needs a meaningful sample."""
    clean = [x for x in series if x is not None]
    if len(clean) < 26:            # under six months of weeks: not a percentile
        return None
    below = sum(1 for x in clean if x < value)
    equal = sum(1 for x in clean if x == value)
    return round(100.0 * (below + 0.5 * equal) / len(clean), 1)


def fetch_history(instrument: str, weeks: int = 260) -> list[dict]:
    """Raw weekly rows, newest first. 260 weeks ~ five years."""
    if instrument not in CONTRACTS:
        raise CotError(f"unknown instrument {instrument!r}; known: {sorted(CONTRACTS)}")
    code, family = CONTRACTS[instrument]
    dataset = DISAGGREGATED if family == "disaggregated" else TFF
    rows = _get(dataset, {
        "$where": f"cftc_contract_market_code='{code}'",
        "$order": "report_date_as_yyyy_mm_dd DESC",
        "$limit": str(weeks),
    })
    if not rows:
        raise CotError(f"no COT rows for {instrument} (code {code}, {family})")
    return rows


def snapshot(instrument: str, weeks: int = 260) -> CotSnapshot:
    """Latest reading for `instrument`, with percentiles over the lookback."""
    rows = fetch_history(instrument, weeks)
    code, family = CONTRACTS[instrument]
    spec = COHORTS[family]
    latest, prior = rows[0], (rows[1] if len(rows) > 1 else None)

    as_of = datetime.fromisoformat(latest["report_date_as_yyyy_mm_dd"]).date()
    inverted = instrument in INVERTED
    sign = -1 if inverted else 1

    cohorts: dict[str, CohortReading] = {}
    for name, (lf, sf) in spec.items():
        if lf not in latest:
            continue
        lng, sht = _to_int(latest.get(lf)), _to_int(latest.get(sf))
        net = sign * (lng - sht)
        hist = [sign * (_to_int(r.get(lf)) - _to_int(r.get(sf))) for r in rows]
        prev = sign * (_to_int(prior.get(lf)) - _to_int(prior.get(sf))) if prior else None
        cohorts[name] = CohortReading(
            cohort=name, long=lng, short=sht, net=net,
            change_net=(net - prev) if prev is not None else None,
            percentile=_percentile(hist, net), lookback_weeks=len(hist),
        )

    return CotSnapshot(
        instrument=instrument, contract_code=code, family=family, as_of=as_of,
        released_at=_release_datetime(as_of),
        open_interest=_to_int(latest.get("open_interest_all")),
        cohorts=cohorts, inverted=inverted,
    )
