"""
Parser for the SEC `ownershipDocument` XML behind Forms 3, 4 and 5.

Three things in this schema bite people, and all three are handled here:

  1. **Values are nested, and optional.** Almost every field is
     `<field><value>x</value></field>`, but `<value>` can be *absent* with only
     a `<footnoteId>` in its place - a real filing in the test corpus reports a
     sale whose price lives solely in a footnote. Reading `.text` off the outer
     element yields whitespace, and coercing that to 0.0 invents a free trade.
     Missing stays `None` here, all the way to the surface.

  2. **The 10b5-1 flag is document-level, not row-level.** `aff10b5One` sits
     beside the tables, so a row-by-row parse loses it, and losing it means a
     scheduled sale is indistinguishable from a conviction sale.

  3. **A filing can have several reporting owners.** Joint filings by funds
     and their principals are common, and collapsing them to the first owner
     silently drops co-filers from cluster detection.
"""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from datetime import date
from typing import Iterator

from .codes import Code, describe, is_discretionary


class ParseError(ValueError):
    """The document is not an ownership document we understand.

    Raised rather than returning a half-built object: a partially parsed Form 4
    is worse than none, because it looks usable.
    """


@dataclass(frozen=True)
class Owner:
    cik: str
    name: str
    is_director: bool = False
    is_officer: bool = False
    is_ten_percent: bool = False
    is_other: bool = False
    officer_title: str = ""

    @property
    def role(self) -> str:
        bits = []
        if self.is_officer:
            bits.append(self.officer_title.strip() or "Officer")
        if self.is_director:
            bits.append("Director")
        if self.is_ten_percent:
            bits.append("10% owner")
        if self.is_other and not bits:
            bits.append("Other")
        return ", ".join(bits) or "Unspecified"


@dataclass(frozen=True)
class Transaction:
    security: str
    code: str
    txn_date: date | None
    shares: float | None
    price: float | None
    acquired: bool | None          # True=A (acquired), False=D (disposed)
    shares_after: float | None
    direct: bool | None            # True=D (direct), False=I (indirect)
    derivative: bool
    footnotes: tuple[str, ...] = ()

    @property
    def meta(self) -> Code:
        return describe(self.code)

    @property
    def value(self) -> float | None:
        """Notional in dollars, or None when the filing did not state a price.

        Never defaults a missing price to zero. A gift and a $4m purchase both
        have "no price" in the naive reading; only one of them is free.
        """
        if self.shares is None or self.price is None:
            return None
        return self.shares * self.price


@dataclass(frozen=True)
class Form4:
    accession: str
    form_type: str
    period: date | None
    issuer_cik: str
    issuer_name: str
    ticker: str
    owners: tuple[Owner, ...]
    transactions: tuple[Transaction, ...]
    plan_flagged: bool             # document-level aff10b5One
    footnotes: dict[str, str] = field(default_factory=dict)

    @property
    def is_amendment(self) -> bool:
        return self.form_type.endswith("/A")

    def discretionary(self) -> tuple[Transaction, ...]:
        """Rows where the filer actually chose the timing."""
        return tuple(t for t in self.transactions
                     if is_discretionary(t.code, plan_flagged=self.plan_flagged))

    def open_market_purchases(self) -> tuple[Transaction, ...]:
        return tuple(t for t in self.transactions if t.code == "P")


# --------------------------------------------------------------------------
# element helpers
# --------------------------------------------------------------------------

def _txt(node: ET.Element | None) -> str | None:
    """Text of `node/value`, or None.

    Returns None - not "" and not 0 - when the element is missing or carries
    only a footnote reference. Callers must decide what absence means; this
    layer refuses to guess.
    """
    if node is None:
        return None
    v = node.find("value")
    if v is None or v.text is None:
        return None
    s = v.text.strip()
    return s or None


def _num(node: ET.Element | None) -> float | None:
    s = _txt(node)
    if s is None:
        return None
    try:
        return float(s.replace(",", "").replace("$", ""))
    except ValueError:
        return None


def _date(node: ET.Element | None) -> date | None:
    s = _txt(node)
    if not s:
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None


def _flag(node: ET.Element | None, tag: str) -> bool:
    """A 0/1/true/false flag that may be bare text or wrapped in <value>."""
    if node is None:
        return False
    el = node.find(tag)
    if el is None:
        return False
    raw = _txt(el)
    if raw is None:
        raw = (el.text or "").strip()
    return raw.lower() in {"1", "true", "y", "yes"}


def _footnote_ids(node: ET.Element) -> tuple[str, ...]:
    return tuple(f.get("id", "") for f in node.iter("footnoteId") if f.get("id"))


# --------------------------------------------------------------------------
# parse
# --------------------------------------------------------------------------

def _transactions(table: ET.Element | None, *, derivative: bool) -> Iterator[Transaction]:
    if table is None:
        return
    tag = "derivativeTransaction" if derivative else "nonDerivativeTransaction"
    for t in table.findall(tag):
        coding = t.find("transactionCoding")
        amounts = t.find("transactionAmounts")
        post = t.find("postTransactionAmounts")
        nature = t.find("ownershipNature")

        code = ""
        if coding is not None:
            el = coding.find("transactionCode")
            code = (el.text or "").strip() if el is not None and el.text else ""

        ad = _txt(amounts.find("transactionAcquiredDisposedCode")) if amounts is not None else None
        di = _txt(nature.find("directOrIndirectOwnership")) if nature is not None else None

        yield Transaction(
            security=_txt(t.find("securityTitle")) or "",
            code=code,
            txn_date=_date(t.find("transactionDate")),
            shares=_num(amounts.find("transactionShares")) if amounts is not None else None,
            price=_num(amounts.find("transactionPricePerShare")) if amounts is not None else None,
            acquired={"A": True, "D": False}.get((ad or "").upper()),
            shares_after=(_num(post.find("sharesOwnedFollowingTransaction"))
                          if post is not None else None),
            direct={"D": True, "I": False}.get((di or "").upper()),
            derivative=derivative,
            footnotes=_footnote_ids(t),
        )


def parse(xml: str, *, accession: str = "") -> Form4:
    """Parse an ownership document into a `Form4`.

    Raises `ParseError` on anything that is not an ownership document, so a
    schema change or a mis-routed filing quarantines loudly instead of
    producing an empty-but-plausible record.
    """
    try:
        root = ET.fromstring(xml.strip())
    except ET.ParseError as exc:
        raise ParseError(f"not well-formed XML: {exc}") from exc

    # Tolerate a namespace if the SEC ever adds one; match on local name.
    local = root.tag.rsplit("}", 1)[-1]
    if local != "ownershipDocument":
        raise ParseError(f"root element is <{local}>, expected <ownershipDocument>")

    issuer = root.find("issuer")
    doc_type = (root.findtext("documentType") or "").strip()

    owners: list[Owner] = []
    for o in root.findall("reportingOwner"):
        oid = o.find("reportingOwnerId")
        rel = o.find("reportingOwnerRelationship")
        owners.append(Owner(
            cik=(oid.findtext("rptOwnerCik") or "").strip() if oid is not None else "",
            name=(oid.findtext("rptOwnerName") or "").strip() if oid is not None else "",
            is_director=_flag(rel, "isDirector"),
            is_officer=_flag(rel, "isOfficer"),
            is_ten_percent=_flag(rel, "isTenPercentOwner"),
            is_other=_flag(rel, "isOther"),
            officer_title=(rel.findtext("officerTitle") or "").strip() if rel is not None else "",
        ))

    footnotes = {f.get("id", ""): "".join(f.itertext()).strip()
                 for f in root.iter("footnote") if f.get("id")}

    txns = list(_transactions(root.find("nonDerivativeTable"), derivative=False))
    txns += list(_transactions(root.find("derivativeTable"), derivative=True))

    return Form4(
        accession=accession,
        form_type=doc_type,
        period=_date_or_text(root, "periodOfReport"),
        issuer_cik=(issuer.findtext("issuerCik") or "").strip() if issuer is not None else "",
        issuer_name=(issuer.findtext("issuerName") or "").strip() if issuer is not None else "",
        ticker=normalise_ticker(issuer.findtext("issuerTradingSymbol") or "") if issuer is not None else "",
        owners=tuple(owners),
        transactions=tuple(txns),
        plan_flagged=_flag(root, "aff10b5One"),
        footnotes=footnotes,
    )


#: Issuers type the trading symbol by hand, so it arrives dirty: "NYSE: VTEX",
#: "NASDAQ:ABCD", "N/A", "None", "[[Ticker]]". Left unnormalised it fragments
#: every per-issuer grouping - the same company clusters under two keys and the
#: cluster never reaches its threshold.
_EXCHANGE_PREFIX = re.compile(
    r"^\s*(?:NYSE(?:\s*AMERICAN|\s*ARCA|\s*MKT)?|NASDAQ(?:\s*[A-Z]{2})?|AMEX|BATS|CBOE|"
    r"OTC(?:\s*(?:BB|QB|QX|MKTS))?|TSX(?:\s*-?\s*V)?|LSE|ASX|NEO|CSE)\s*[:\-]\s*",
    re.I)
_NOT_A_TICKER = {"", "N/A", "NA", "NONE", "N.A.", "-", "--", "TBD", "TICKER",
                 "SYMBOL", "XXX", "NOTAPPLICABLE"}
#: Filing-agent template markers that reached production unfilled.
_TEMPLATE = re.compile(r"\[\[|\]\]|\{\{|\}\}|<[^>]*>")


def normalise_ticker(raw: str) -> str:
    """Strip exchange prefixes and placeholder values from a trading symbol.

    Returns "" when the field carries no usable symbol, so callers fall back to
    the issuer name rather than grouping several companies under "N/A".
    """
    t = (raw or "").strip()
    if _TEMPLATE.search(t):
        return ""
    t = _EXCHANGE_PREFIX.sub("", t)
    t = t.strip().strip("[]() ").upper()
    t = re.sub(r"\s+", "", t)
    if t in _NOT_A_TICKER or not re.fullmatch(r"[A-Z0-9.\-]{1,12}", t):
        return ""
    return t


def _date_or_text(root: ET.Element, tag: str) -> date | None:
    """`periodOfReport` is bare text, unlike most fields which wrap in <value>."""
    s = (root.findtext(tag) or "").strip()
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", s)
    if not m:
        return None
    try:
        return date(int(m[1]), int(m[2]), int(m[3]))
    except ValueError:
        return None
