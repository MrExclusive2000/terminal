"""
Position sizing and risk arithmetic.

Given an entry, a stop and how much of the account you are willing to lose,
the lot size is *determined*. There is no judgement in it - only arithmetic
that is easy to get wrong and expensive when you do.

The traps this handles explicitly:

  * Contract size differs by instrument. XAUUSD is 100 oz/lot, FX majors are
    100,000 units/lot. A stop that risks GBP 200 on EURUSD risks a very
    different amount on gold for the same price distance.
  * The currency the P&L lands in is the QUOTE currency, not the account
    currency. EURUSD pays in USD, USDJPY pays in JPY, XAUUSD pays in USD.
    A GBP account needs a conversion on every one of them.
  * Brokers quantise volume. 0.137 lots is not orderable; it must be floored
    to the volume step, which makes realised risk slightly *under* target -
    never over.
  * Leverage caps size independently of risk. Under the EU retail rules the
    IC Markets (EU) entity applies 1:30, so a position can be affordable in
    risk terms and still be unavailable in margin terms.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import floor


@dataclass(frozen=True)
class Instrument:
    symbol: str
    contract_size: float      # units of base per lot: 100 oz gold, 100_000 FX
    quote_currency: str       # currency the P&L is realised in
    digits: int               # price decimals
    volume_min: float = 0.01
    volume_step: float = 0.01
    volume_max: float = 100.0

    @property
    def point(self) -> float:
        return 10 ** -self.digits


# Defaults matching typical IC Markets contract specs. Override at runtime from
# the bridge's symbol_info rather than trusting these - broker specs change and
# symbols carry account-type suffixes.
INSTRUMENTS: dict[str, Instrument] = {
    "XAUUSD": Instrument("XAUUSD", 100, "USD", 2),
    "XAGUSD": Instrument("XAGUSD", 5_000, "USD", 3),
    "EURUSD": Instrument("EURUSD", 100_000, "USD", 5),
    "GBPUSD": Instrument("GBPUSD", 100_000, "USD", 5),
    "AUDUSD": Instrument("AUDUSD", 100_000, "USD", 5),
    "USDJPY": Instrument("USDJPY", 100_000, "JPY", 3),
}


class SizingError(ValueError):
    pass


@dataclass(frozen=True)
class SizedTrade:
    symbol: str
    direction: str                 # "long" | "short"
    entry: float
    stop: float
    stop_distance: float
    lots: float                    # broker-orderable, floored to volume step
    risk_target: float             # account currency
    risk_actual: float             # after quantisation - always <= target
    account_currency: str
    notional: float                # account currency
    margin_required: float | None
    warnings: tuple[str, ...] = ()

    @property
    def risk_per_lot(self) -> float:
        return self.risk_actual / self.lots if self.lots else 0.0

    def reward_at(self, target: float) -> float:
        """R-multiple if price reaches `target`."""
        if self.stop_distance == 0:
            return 0.0
        move = (target - self.entry) if self.direction == "long" else (self.entry - target)
        return round(move / self.stop_distance, 2)


def size_position(
    *,
    instrument: Instrument,
    entry: float,
    stop: float,
    account_balance: float,
    risk_pct: float,
    account_currency: str = "GBP",
    quote_to_account: float = 1.0,
    leverage: int | None = 30,
    free_margin: float | None = None,
) -> SizedTrade:
    """Lots to risk `risk_pct` of `account_balance` between `entry` and `stop`.

    `quote_to_account` converts one unit of the instrument's quote currency
    into the account currency (e.g. USD->GBP ~ 0.79). Passing 1.0 when they
    differ is the classic silent error, so a mismatch without a rate warns.
    """
    if entry <= 0 or stop <= 0:
        raise SizingError("entry and stop must be positive prices")
    if entry == stop:
        raise SizingError("stop cannot equal entry: risk would be undefined")
    if not 0 < risk_pct <= 100:
        raise SizingError("risk_pct must be between 0 and 100")
    if account_balance <= 0:
        raise SizingError("account_balance must be positive")

    direction = "long" if stop < entry else "short"
    stop_distance = abs(entry - stop)

    warnings: list[str] = []
    if account_currency != instrument.quote_currency and quote_to_account == 1.0:
        warnings.append(
            f"quote currency is {instrument.quote_currency} but account is "
            f"{account_currency} and no conversion rate was supplied - size assumes 1.0")

    risk_target = account_balance * (risk_pct / 100.0)

    # Loss for one lot at the stop, expressed in the account currency.
    loss_per_lot = stop_distance * instrument.contract_size * quote_to_account
    if loss_per_lot <= 0:
        raise SizingError("computed zero loss per lot - check contract size and conversion")

    raw_lots = risk_target / loss_per_lot

    # Floor to the broker's volume step: realised risk lands at or under target.
    steps = floor(raw_lots / instrument.volume_step)
    lots = round(steps * instrument.volume_step, 8)

    if lots < instrument.volume_min:
        warnings.append(
            f"required size {raw_lots:.4f} lots is below the broker minimum "
            f"{instrument.volume_min} - taking this trade at minimum size would risk "
            f"{instrument.volume_min * loss_per_lot:,.2f} {account_currency}, "
            f"which is {instrument.volume_min * loss_per_lot / risk_target:.1f}x your limit")
        lots = 0.0
    if lots > instrument.volume_max:
        warnings.append(f"size capped at broker maximum {instrument.volume_max} lots")
        lots = instrument.volume_max

    risk_actual = lots * loss_per_lot
    notional = lots * instrument.contract_size * entry * quote_to_account
    margin_required = (notional / leverage) if leverage else None

    if margin_required is not None and free_margin is not None and margin_required > free_margin:
        warnings.append(
            f"margin required {margin_required:,.2f} exceeds free margin "
            f"{free_margin:,.2f} at 1:{leverage} - position is not affordable")

    return SizedTrade(
        symbol=instrument.symbol, direction=direction, entry=entry, stop=stop,
        stop_distance=round(stop_distance, instrument.digits), lots=lots,
        risk_target=round(risk_target, 2), risk_actual=round(risk_actual, 2),
        account_currency=account_currency, notional=round(notional, 2),
        margin_required=round(margin_required, 2) if margin_required is not None else None,
        warnings=tuple(warnings),
    )
