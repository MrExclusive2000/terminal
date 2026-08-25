"""
The Form 4 path, end to end: detect -> fetch -> parse -> decode -> score -> cluster.

This is the pipeline the whole product exists for, so it is deliberately
boring: deterministic, no model in the loop, and every stage able to fail
without taking the others down.

The output is a *ranked* feed, not a chronological tape. A tape is what every
free filing viewer already gives you and it buries the one row that matters
under forty rows of payroll. Ranking by decoded conviction is the product.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ..data import edgar
from ..data.http import FetchError
from . import cluster as cluster_mod
from .codes import is_discretionary
from .conviction import Conviction, score
from .form4 import Form4, Owner, ParseError, Transaction  # noqa: F401


@dataclass(frozen=True)
class Event:
    """One scored transaction, with everything needed to justify it on screen.

    One event per transaction, attributed to the filing's primary reporting
    owner. Joint filings are one decision, so emitting an event per co-filer
    would show the same fact eight times and rank it eight times.
    """
    form: Form4
    owner: Owner
    txn: Transaction
    conviction: Conviction
    co_filers: int = 0

    @property
    def ticker(self) -> str:
        return self.form.ticker or self.form.issuer_name

    def as_row(self) -> dict:
        t = self.txn
        return {
            "ticker": self.ticker,
            "issuer": self.form.issuer_name,
            "person": self.owner.name,
            "role": self.owner.role,
            "co_filers": self.co_filers,
            "code": t.code,
            "code_label": t.meta.label,
            "discretion": t.meta.discretion,
            "date": t.txn_date.isoformat() if t.txn_date else None,
            "shares": t.shares,
            "price": t.price,
            "value": t.value,
            "direction": self.conviction.direction,
            "score": round(self.conviction.score, 1),
            "band": self.conviction.band,
            "plan_flagged": self.form.plan_flagged,
            "amendment": self.form.is_amendment,
            "accession": self.form.accession,
            "factors": [{"name": f.name, "points": f.points, "why": f.why}
                        for f in self.conviction.factors],
            "caveats": list(self.conviction.caveats),
        }


@dataclass
class Digest:
    fetched_at: datetime
    filings: int
    rows: int
    discretionary: int
    events: list[Event] = field(default_factory=list)
    clusters: list[cluster_mod.Cluster] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)

    @property
    def mechanical_share(self) -> float | None:
        if not self.rows:
            return None
        return (self.rows - self.discretionary) / self.rows

    def headline(self) -> str:
        if not self.rows:
            return "No transaction rows in this window."
        pct = self.mechanical_share or 0
        best = self.events[0] if self.events else None
        lead = (f"Top: {best.ticker} {best.owner.name} "
                f"{best.conviction.direction} {best.conviction.score:.0f}/100"
                if best else "Nothing discretionary in this window")
        return (f"{self.filings} filings, {self.rows} rows, "
                f"{pct:.0%} non-discretionary. {lead}")

    def as_dict(self) -> dict:
        return {
            "fetched_at": self.fetched_at.isoformat(),
            "filings": self.filings,
            "rows": self.rows,
            "discretionary": self.discretionary,
            "mechanical_share": self.mechanical_share,
            "headline": self.headline(),
            "events": [e.as_row() for e in self.events],
            "clusters": [
                {"ticker": c.ticker, "issuer": c.issuer_name,
                 "direction": c.direction, "people": c.people,
                 "notional": c.notional, "span_days": c.span_days,
                 "first": c.first.isoformat(), "last": c.last.isoformat(),
                 "summary": c.summary(),
                 "members": [{"person": m.owner.name, "role": m.owner.role,
                              "date": m.txn.txn_date.isoformat() if m.txn.txn_date else None,
                              "value": m.txn.value} for m in c.members]}
                for c in self.clusters
            ],
            "skipped": self.skipped,
        }



def build(forms: list[Form4], *,
          routine_ciks: set[str] | None = None,
          window_days: int = 45) -> Digest:
    """Score and rank an already-fetched set of filings.

    Split from fetching so the whole analytical path is testable offline with
    no network - which is what makes it verifiable at all.
    """
    routine_ciks = routine_ciks or set()
    clusters = cluster_mod.find(forms, window_days=window_days)

    # How many distinct insiders are moving the same way at each issuer, so a
    # single event can be credited for the cluster it belongs to.
    cluster_size: dict[tuple[str, str], int] = {}
    for c in clusters:
        key = (c.ticker or c.issuer_name, c.direction)
        cluster_size[key] = max(cluster_size.get(key, 0), c.people)

    rows = 0
    discretionary = 0
    events: list[Event] = []

    for form in forms:
        for txn in form.transactions:
            rows += 1
            if not is_discretionary(txn.code, plan_flagged=form.plan_flagged):
                continue
            discretionary += 1
            direction = "buy" if txn.acquired else "sell"
            size = cluster_size.get(
                (form.ticker or form.issuer_name, direction), 1)
            owners = form.owners or (Owner(cik="", name="unknown"),)
            primary = owners[0]
            conv = score(form, txn, owner=primary,
                         routine_filer=primary.cik in routine_ciks,
                         cluster_size=size)
            if conv.direction != "none":
                events.append(Event(form, primary, txn, conv,
                                    co_filers=len(owners) - 1))

    events.sort(key=lambda e: e.conviction.score, reverse=True)
    return Digest(fetched_at=datetime.now(timezone.utc), filings=len(forms),
                  rows=rows, discretionary=discretionary,
                  events=events, clusters=clusters)


def run(*, limit: int = 40, contact: str | None = None) -> Digest:
    """Fetch the newest filings and score them. Network required."""
    if contact:
        edgar.set_contact(contact)
    forms: list[Form4] = []
    skipped: list[str] = []
    for ref in edgar.current(count=edgar.FEED_MAX):
        if len(forms) >= limit:
            break
        try:
            form = edgar.fetch_form(ref)
        except FetchError as exc:
            skipped.append(f"{ref.accession}: fetch failed ({exc})")
            continue
        except ParseError as exc:
            # Loud on purpose. A schema change must not look like a quiet day.
            skipped.append(f"{ref.accession}: QUARANTINED - {exc}")
            continue
        if form is None:
            continue
        forms.append(form)

    digest = build(forms)
    digest.skipped = skipped
    return digest
