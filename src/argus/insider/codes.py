"""
SEC Form 3/4/5 transaction-code taxonomy, and the discretion question.

This module exists because of one measured fact: **most Form 4 activity is
not a decision**. On a recent full quarter of filings, 67% of transaction
rows were non-discretionary - tax withholding, scheduled vesting, option
mechanics - and open-market purchases (code P) were only 5.5% of rows.

A terminal that lists "insider selling" without decoding the code is
therefore wrong roughly two times in three, and wrong in the direction that
costs money: it reports payroll as though it were conviction.

Codes are from the SEC's Table I / Table II instructions to Forms 3, 4 and 5.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Discretion = Literal["discretionary", "mechanical", "conditional"]


@dataclass(frozen=True)
class Code:
    code: str
    label: str
    discretion: Discretion
    note: str


#: Discretion classification, and why each call was made.
#:
#:   discretionary - the filer chose to do this, at this price, on this day.
#:   mechanical    - the filer did not choose the timing; a plan, a grant
#:                   schedule, a tax rule or an expiry chose it.
#:   conditional   - depends on facts outside the code. The 10b5-1 flag and
#:                   the footnotes decide it, so it is never scored blind.
CODES: dict[str, Code] = {
    # -- general transactions -------------------------------------------
    "P": Code("P", "Open-market or private purchase", "discretionary",
              "The highest-signal row on the form. Somebody paid cash for "
              "their own company's stock at a price they did not have to pay."),
    "S": Code("S", "Open-market or private sale", "conditional",
              "The headline generator, and usually noise. Scheduled 10b5-1 "
              "sales look identical to conviction sales at code level - only "
              "the plan flag and adoption date separate them."),
    "V": Code("V", "Voluntarily reported early", "conditional",
              "A reporting choice, not a transaction type; the underlying "
              "code still decides."),

    # -- Rule 16b-3 exempt transactions with the issuer ------------------
    "A": Code("A", "Grant, award or other acquisition", "mechanical",
              "Compensation. Being granted stock is not buying stock, and "
              "presenting it as an insider 'acquisition' is the single most "
              "common way this data is misreported."),
    "D": Code("D", "Disposition to the issuer", "mechanical",
              "Back to the company, typically on forfeiture or a buyback "
              "mechanism. Not a market decision."),
    "F": Code("F", "Shares withheld for exercise price or tax", "mechanical",
              "Pure payroll. The filer never had the choice; the shares were "
              "withheld to settle a tax bill on vesting. Reported as a "
              "disposition, which is why naive tools read vesting as selling."),
    "I": Code("I", "Discretionary transaction with the issuer", "conditional",
              "Plan-level discretion inside an issuer plan."),
    "M": Code("M", "Exercise or conversion of an exempt derivative", "mechanical",
              "Option exercise. Almost always paired with an F or an S in the "
              "same filing; the pair is the event, not either leg alone."),

    # -- derivative securities -------------------------------------------
    "C": Code("C", "Conversion of a derivative security", "mechanical",
              "Instrument mechanics."),
    "E": Code("E", "Expiration of a short derivative position", "mechanical",
              "The calendar acted, not the filer."),
    "H": Code("H", "Expiration or cancellation of a long position, value received",
              "mechanical", "The calendar acted, not the filer."),
    "O": Code("O", "Exercise of an out-of-the-money derivative", "conditional",
              "Unusual enough to be worth a look - exercising OTM is rarely "
              "economic on its face."),
    "X": Code("X", "Exercise of an in- or at-the-money derivative", "mechanical",
              "Expiry-driven in the overwhelming majority of cases."),

    # -- other --------------------------------------------------------------
    "G": Code("G", "Bona fide gift", "mechanical",
              "No price and no market. Carries estate-planning information at "
              "most, and is not a directional view."),
    "L": Code("L", "Small acquisition under Rule 16a-6", "mechanical",
              "De minimis by definition."),
    "W": Code("W", "Acquisition or disposition by will or descent", "mechanical",
              "Somebody died. Not a signal."),
    "Z": Code("Z", "Deposit into or withdrawal from a voting trust", "mechanical",
              "Custodial."),
    "J": Code("J", "Other acquisition or disposition", "conditional",
              "Requires a footnote by rule, so the footnote is the data. Never "
              "score a J without reading it."),
    "K": Code("K", "Equity swap or similar instrument", "conditional",
              "Economic exposure changed without an obvious share movement."),
    "U": Code("U", "Disposition in a change-of-control tender", "mechanical",
              "The deal decided this, not the filer."),
}

#: The only code that means an insider spent their own money on the open
#: market. Kept as a named constant because it is the backbone of every
#: credible insider study, and because it is easy to widen by accident.
OPEN_MARKET_PURCHASE = "P"


def describe(code: str) -> Code:
    """Return the taxonomy entry for `code`, or an explicit unknown.

    Unknown codes are surfaced, never silently dropped: the SEC has amended
    this table before and a quarantined row that says "I do not know what
    this is" is worth more than a row that guessed.
    """
    code = (code or "").strip().upper()
    if code in CODES:
        return CODES[code]
    return Code(code or "?", f"Unrecognised code {code!r}", "conditional",
                "Not in the Table I/II taxonomy this build knows about. "
                "Quarantined for review rather than scored.")


def is_discretionary(code: str, *, plan_flagged: bool = False) -> bool:
    """Did the filer choose the timing of this trade?

    `plan_flagged` is the document-level `aff10b5One` flag. A conditional code
    under a 10b5-1 plan is scheduled, so it is not discretionary - that single
    check is what separates a real sale from a calendar entry.
    """
    d = describe(code).discretion
    if d == "mechanical":
        return False
    if d == "conditional":
        return not plan_flagged
    return True
