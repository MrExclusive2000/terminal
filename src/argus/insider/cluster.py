"""
Cluster detection: several insiders at one issuer, moving the same way, close together.

Cluster buying is the strongest effect in the insider literature and the one
retail screens systematically miss, because they present filings as a
chronological tape. A tape shows you six rows; it does not tell you that the
six rows are six *different people* at the same company inside three weeks,
which is the entire point.

What counts as a cluster here is deliberately strict:

  * **Distinct people.** One insider filing six times is not a cluster, it is
    an execution schedule. Counting rows instead of filers is the classic way
    to manufacture a signal that is not there.
  * **Distinct *parties*, not co-filers.** A single Form 4 routinely carries
    several reporting owners - a venture fund, its general partner and its
    management company all sign one filing. Observed live: eight Sequoia
    entities on one accession, which a naive count reports as "8 insiders
    selling" when it is one decision by one investor. The decision unit here is
    therefore the *filing party*, and co-filers on one accession count once.
  * **Discretionary rows only.** Six executives vesting on the same day is a
    payroll calendar, not a consensus.
  * **Same direction.** Mixed buying and selling is not a cluster; it is a
    disagreement, and it is reported as one.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from .codes import is_discretionary
from .form4 import Form4, Owner, Transaction


@dataclass(frozen=True)
class Member:
    owner: Owner                   # representative filer for the party
    txn: Transaction
    form: Form4
    co_filers: int = 0             # additional reporting owners on the same filing

    @property
    def party(self) -> str:
        """Stable identity for the filing party.

        Joint filers share one identity: their economic decision was made once.
        Falls back through owner CIK, owner name, then accession so a filing
        with no usable owner id still groups sensibly instead of colliding with
        every other anonymous filing.
        """
        ciks = sorted(o.cik for o in self.form.owners if o.cik)
        if ciks:
            return "|".join(ciks)
        names = sorted(o.name for o in self.form.owners if o.name)
        return "|".join(names) or self.form.accession


@dataclass(frozen=True)
class Cluster:
    ticker: str
    issuer_name: str
    direction: str                 # "buy" | "sell"
    members: tuple[Member, ...]
    first: date
    last: date

    @property
    def people(self) -> int:
        """Distinct filing parties, so joint filers count once."""
        return len({m.party for m in self.members})

    @property
    def notional(self) -> float | None:
        """Total dollars, or None if any leg lacked a stated price.

        Returns None rather than a partial sum. A total that silently omits the
        legs with no price reads as complete and is not.
        """
        vals = [m.txn.value for m in self.members]
        if any(v is None for v in vals):
            return None
        return sum(v for v in vals if v is not None)

    @property
    def span_days(self) -> int:
        return (self.last - self.first).days

    def summary(self) -> str:
        n = self.notional
        money = f"${n:,.0f}" if n is not None else "notional incomplete"
        return (f"{self.ticker or self.issuer_name}: {self.people} "
                f"{'party' if self.people == 1 else 'parties'} "
                f"{self.direction}ing over {self.span_days}d - {money}")


def find(forms: list[Form4], *, window_days: int = 45,
         min_people: int = 2) -> list[Cluster]:
    """Group discretionary transactions into clusters per issuer and direction.

    `window_days` is the maximum gap between consecutive trades in a cluster,
    not the total span - a rolling campaign of buying should stay one cluster
    rather than fragmenting at an arbitrary boundary.
    """
    buckets: dict[tuple[str, str], list[Member]] = defaultdict(list)

    for form in forms:
        for txn in form.transactions:
            if txn.txn_date is None or txn.acquired is None:
                continue
            if not is_discretionary(txn.code, plan_flagged=form.plan_flagged):
                continue
            direction = "buy" if txn.acquired else "sell"
            key = (form.issuer_cik or form.ticker or form.issuer_name, direction)
            owners = form.owners or (Owner(cik="", name="unknown"),)
            # One member per transaction, not one per co-filer.
            buckets[key].append(Member(owner=owners[0], txn=txn, form=form,
                                       co_filers=len(owners) - 1))

    clusters: list[Cluster] = []
    for (_issuer, direction), members in buckets.items():
        members.sort(key=lambda m: m.txn.txn_date)      # type: ignore[arg-type]
        run: list[Member] = []

        def flush(run: list[Member]) -> None:
            if not run:
                return
            if len({m.party for m in run}) < min_people:
                return
            head = run[0].form
            clusters.append(Cluster(
                ticker=head.ticker, issuer_name=head.issuer_name,
                direction=direction, members=tuple(run),
                first=run[0].txn.txn_date,                 # type: ignore[arg-type]
                last=run[-1].txn.txn_date,                 # type: ignore[arg-type]
            ))

        for m in members:
            if run and (m.txn.txn_date - run[-1].txn.txn_date).days > window_days:  # type: ignore[operator]
                flush(run)
                run = []
            run.append(m)
        flush(run)

    clusters.sort(key=lambda c: (c.people, c.notional or 0), reverse=True)
    return clusters
