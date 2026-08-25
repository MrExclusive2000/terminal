#!/usr/bin/env python3
"""
Argus insider desk - command line.

    python3 insider.py --contact "Your Name you@example.com"
    python3 insider.py --limit 25 --min-score 40
    python3 insider.py --file some-form4.xml

Reads SEC EDGAR. Information only: nothing here places, modifies or cancels
an order, and there is no broker credential anywhere in this path.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from argus.data.edgar import ContactNotConfigured    # noqa: E402
from argus.insider import parse                      # noqa: E402
from argus.insider.conviction import score           # noqa: E402
from argus.insider.pipeline import build, run        # noqa: E402

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
UP, DOWN, WARN = "\033[38;5;33m", "\033[38;5;166m", "\033[38;5;179m"


def colour(enabled: bool):
    if enabled:
        return BOLD, DIM, RESET, UP, DOWN, WARN
    return ("",) * 6


def main() -> int:
    ap = argparse.ArgumentParser(description="Argus insider desk")
    ap.add_argument("--contact", default="",
                    help="Name and email for the SEC User-Agent. Defaults to "
                         "$ARGUS_SEC_CONTACT. Required: EDGAR returns 403 without it.")
    ap.add_argument("--limit", type=int, default=40, help="filings to pull")
    ap.add_argument("--min-score", type=float, default=0.0)
    ap.add_argument("--file", help="score a local Form 4 XML instead of fetching")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--no-colour", action="store_true")
    a = ap.parse_args()

    b, d, r, up, dn, wn = colour(not a.no_colour and sys.stdout.isatty())

    if a.file:
        form = parse(Path(a.file).read_text(), accession=Path(a.file).stem)
        digest = build([form])
    else:
        try:
            digest = run(limit=a.limit, contact=a.contact or None)
        except ContactNotConfigured as exc:
            print(f"\n{wn}Not configured.{r} {exc}\n", file=sys.stderr)
            return 2

    if a.json:
        print(json.dumps(digest.as_dict(), indent=2, default=str))
        return 0

    print(f"\n{b}ARGUS INSIDER DESK{r}  {d}{digest.fetched_at:%Y-%m-%d %H:%M UTC}{r}")
    print(f"{d}{'-'*76}{r}")
    print(f"  {digest.headline()}")
    if digest.mechanical_share is not None:
        print(f"  {d}Rows the filer did not choose the timing of are excluded "
              f"from ranking.{r}")

    if digest.clusters:
        print(f"\n{b}CLUSTERS{r}  {d}separate filers · one issuer · same direction{r}")
        for c in digest.clusters[:8]:
            tint = up if c.direction == "buy" else dn
            print(f"  {tint}{c.summary()}{r}")
            for m in c.members[:6]:
                v = f"${m.txn.value:,.0f}" if m.txn.value is not None else "no price"
                print(f"      {d}{str(m.txn.txn_date):<12}{r} {m.owner.name[:26]:<26} "
                      f"{m.owner.role[:22]:<22} {v:>14}")

    shown = [e for e in digest.events if e.conviction.score >= a.min_score]
    print(f"\n{b}RANKED EVENTS{r}  {d}{len(shown)} of {len(digest.events)} "
          f"discretionary rows at or above score {a.min_score:g}{r}")
    if not shown:
        print(f"  {d}Nothing cleared the bar. That is a normal result, and it is "
              f"the answer - not an empty screen.{r}")
    for e in shown[:20]:
        c = e.conviction
        tint = up if c.direction == "buy" else dn
        v = f"${e.txn.value:,.0f}" if e.txn.value is not None else "price not stated"
        flag = f" {wn}[10b5-1]{r}" if e.form.plan_flagged else ""
        amd = f" {wn}[amended]{r}" if e.form.is_amendment else ""
        print(f"\n  {tint}{b}{c.score:5.1f}{r} {tint}{c.direction.upper():<4}{r} "
              f"{b}{e.ticker:<8}{r} {e.owner.name[:24]:<24} {d}{e.owner.role[:26]}{r}{flag}{amd}")
        print(f"        {e.txn.code} {e.txn.meta.label[:44]:<44} "
              f"{str(e.txn.txn_date):<12} {v:>18}")
        for f in c.factors:
            sign = "+" if f.points >= 0 else ""
            print(f"        {d}{sign}{f.points:5.1f}  {f.name}: {f.why[:78]}{r}")
        for cv in c.caveats:
            print(f"        {wn}note{r} {d}{cv[:88]}{r}")

    if digest.skipped:
        print(f"\n{wn}SKIPPED{r} {d}({len(digest.skipped)}){r}")
        for s in digest.skipped[:10]:
            print(f"  {d}{s[:100]}{r}")
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
