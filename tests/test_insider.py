"""
Insider engine tests. No network, no terminal - every case runs offline.

Two fixtures are real SEC documents, kept precisely because synthetic XML
never contains the things that actually break parsers: a price that exists
only as a footnote, a document-level plan flag, an exchange-prefixed ticker,
and a feed that returns the wrong form types twice each.
"""
from __future__ import annotations

import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, "src")

from argus.data import edgar
from argus.insider import cluster as cl
from argus.insider.codes import CODES, describe, is_discretionary
from argus.insider.conviction import classify_filer, score
from argus.insider.form4 import (Form4, Owner, ParseError, Transaction, normalise_ticker,
                                 parse)
from argus.insider.pipeline import build

FIX = Path(__file__).parent / "fixtures"
PASS = FAIL = 0


def check(label: str, cond: bool) -> bool:
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
    print(f"  {'PASS' if cond else 'FAIL'}  {label}")
    return cond


def mk_form(owners, txns, *, plan=False, ticker="EXA", cik="9"):
    return Form4(accession="t", form_type="4", period=date(2026, 8, 1),
                 issuer_cik=cik, issuer_name="Example Inc", ticker=ticker,
                 owners=tuple(owners), transactions=tuple(txns), plan_flagged=plan)


def mk_txn(code="P", d=date(2026, 8, 1), shares=1000.0, price=10.0,
           acquired=True, after=5000.0, direct=True):
    return Transaction(security="Common", code=code, txn_date=d, shares=shares,
                       price=price, acquired=acquired, shares_after=after,
                       direct=direct, derivative=False)


def main() -> int:
    print("\n[codes] discretion taxonomy")
    check("every code carries a discretion class",
          all(c.discretion in {"discretionary", "mechanical", "conditional"}
              for c in CODES.values()))
    check("P is discretionary", is_discretionary("P"))
    check("F (tax withholding) is never discretionary", not is_discretionary("F"))
    check("A (grant) is never discretionary", not is_discretionary("A"))
    check("M (option exercise) is never discretionary", not is_discretionary("M"))
    check("S is discretionary when off-plan", is_discretionary("S", plan_flagged=False))
    check("S is NOT discretionary under a 10b5-1 plan",
          not is_discretionary("S", plan_flagged=True))
    check("P stays discretionary even under a plan flag",
          is_discretionary("P", plan_flagged=True))
    check("unknown code is surfaced, not dropped",
          describe("QQ").label.startswith("Unrecognised"))
    check("empty code does not crash", describe("").code == "?")

    print("\n[form4] real filing: footnote-only price vs a stated zero")
    f = parse((FIX / "form4-rskd-10b51.xml").read_text(), accession="a")
    check("issuer parsed", f.issuer_name == "RISKIFIED LTD." and f.ticker == "RSKD")
    check("document-level aff10b5One flag read", f.plan_flagged is True)
    check("four transactions parsed", len(f.transactions) == 4)
    prices = [t.price for t in f.transactions]
    check("footnote-only price is None, not 0.0", prices[0] is None)
    check("a stated <value>0</value> parses as 0.0, not None", prices[3] == 0.0)
    check("value is None when price is unstated", f.transactions[0].value is None)
    check("value is 0.0 when price is genuinely zero", f.transactions[3].value == 0.0)
    check("real prices parse", abs(prices[1] - 5.8935) < 1e-9)
    check("owner and role parsed", f.owners[0].name == "Shachar Erez"
          and "Director" in f.owners[0].role)
    check("footnotes collected", len(f.footnotes) >= 5)
    check("plan-flagged filing yields no discretionary rows",
          len(f.discretionary()) == 0)

    print("\n[form4] malformed input fails loudly, never half-parsed")
    for label, bad in (("not XML", "<<<"), ("wrong root", "<foo><bar/></foo>"),
                       ("empty", "")):
        try:
            parse(bad)
            check(f"{label} raises ParseError", False)
        except ParseError:
            check(f"{label} raises ParseError", True)
        except Exception as exc:  # noqa: BLE001
            check(f"{label} raises ParseError (got {type(exc).__name__})", False)

    check("namespaced root is tolerated",
          parse('<ns:ownershipDocument xmlns:ns="http://x"><documentType>4'
                '</documentType></ns:ownershipDocument>').form_type == "4")

    print("\n[form4] ticker normalisation")
    for raw, want in (("NYSE: VTEX", "VTEX"), ("NASDAQ:ABCD", "ABCD"),
                      ("BRK.B", "BRK.B"), ("N/A", ""), ("", ""),
                      ("[[Ticker]]", ""), ("OTC MKTS: XYZ", "XYZ"),
                      ("toolongtickername", "")):
        check(f"{raw!r} -> {want!r}", normalise_ticker(raw) == want)

    print("\n[conviction] mechanical rows score zero, with a reason")
    for code in ("F", "A", "M", "G", "D"):
        c = score(mk_form([Owner("1", "X", is_officer=True)], [mk_txn(code=code)]),
                  mk_txn(code=code))
        if not check(f"code {code} scores exactly 0 and direction 'none'",
                     c.score == 0.0 and c.direction == "none"):
            break
    check("zero score still explains itself", bool(
        score(mk_form([Owner("1", "X")], [mk_txn(code="F")]), mk_txn(code="F")).factors))

    print("\n[conviction] plan flag neutralises an otherwise-scoring sale")
    sale = mk_txn(code="S", acquired=False)
    off = score(mk_form([Owner("1", "X", is_officer=True, officer_title="CEO")],
                        [sale]), sale)
    on = score(mk_form([Owner("1", "X", is_officer=True, officer_title="CEO")],
                       [sale], plan=True), sale)
    check("off-plan sale scores", off.score > 0)
    check("same sale under a plan scores zero", on.score == 0.0)

    print("\n[conviction] purchases and sales are not symmetric")
    ceo = Owner("1", "X", is_officer=True, officer_title="Chief Executive Officer")
    big_buy = mk_txn(code="P", shares=100000.0, price=100.0, acquired=True, after=200000.0)
    big_sell = mk_txn(code="S", shares=100000.0, price=100.0, acquired=False, after=100000.0)
    b = score(mk_form([ceo], [big_buy]), big_buy, owner=ceo)
    s = score(mk_form([ceo], [big_sell]), big_sell, owner=ceo)
    check("an identical-size buy outscores the sale", b.score > s.score)
    check("sales are capped below 60", s.score <= 55.0)
    check("buys can reach the high band", b.score >= 70)

    print("\n[conviction] modifiers")
    plain = score(mk_form([ceo], [big_buy]), big_buy, owner=ceo)
    clustered = score(mk_form([ceo], [big_buy]), big_buy, owner=ceo, cluster_size=4)
    routine = score(mk_form([ceo], [big_buy]), big_buy, owner=ceo, routine_filer=True)
    check("cluster raises or holds the score", clustered.score >= plain.score)
    check("routine filer lowers the score", routine.score < plain.score)
    check("score never exceeds 100", clustered.score <= 100.0)
    check("score never goes negative", routine.score >= 0.0)
    check("factors sum is shown for every scoring event",
          all(f.why for f in plain.factors))

    print("\n[conviction] routine/opportunistic classifier")
    check("3 consecutive same-month years is routine",
          classify_filer([date(2023, 11, 4), date(2024, 11, 6), date(2025, 11, 3)]))
    check("scattered months are opportunistic",
          not classify_filer([date(2023, 3, 4), date(2024, 7, 6), date(2025, 11, 3)]))
    check("a gap year breaks the run",
          not classify_filer([date(2021, 5, 4), date(2022, 5, 6),
                              date(2024, 5, 3), date(2025, 5, 3)]))
    check("too few trades is not routine", not classify_filer([date(2025, 1, 1)]))
    check("empty history does not crash", not classify_filer([]))

    print("\n[cluster] what counts as a cluster")
    a_, b_, c_ = (Owner("a", "Ann", is_officer=True, officer_title="CEO"),
                  Owner("b", "Bob", is_officer=True, officer_title="CFO"),
                  Owner("c", "Cat", is_officer=True, officer_title="COO"))
    three = [mk_form([o], [mk_txn(d=date(2026, 8, 3 + i * 8))])
             for i, o in enumerate((a_, b_, c_))]
    cs = cl.find(three)
    check("three distinct insiders buying form one cluster",
          len(cs) == 1 and cs[0].people == 3)
    one_person = [mk_form([a_], [mk_txn(d=date(2026, 8, 3 + i * 8))]) for i in range(3)]
    check("one insider filing three times is NOT a cluster", cl.find(one_person) == [])
    vesting = [mk_form([o], [mk_txn(code="A", d=date(2026, 8, 3))])
               for o in (a_, b_, c_)]
    check("three insiders vesting the same day is NOT a cluster", cl.find(vesting) == [])
    mixed = cl.find(three + [mk_form([Owner("d", "Dan")],
                                     [mk_txn(code="S", acquired=False,
                                             d=date(2026, 8, 4))]),
                             mk_form([Owner("e", "Eve")],
                                     [mk_txn(code="S", acquired=False,
                                             d=date(2026, 8, 5))])])
    check("buys and sells are separate clusters, never merged",
          {c.direction for c in mixed} == {"buy", "sell"})
    part = cl.find([mk_form([a_], [mk_txn()]),
                    mk_form([b_], [mk_txn(price=None)])])
    check("a leg with no price makes notional None, not a partial sum",
          part and part[0].notional is None)
    far = cl.find([mk_form([a_], [mk_txn(d=date(2026, 1, 1))]),
                   mk_form([b_], [mk_txn(d=date(2026, 12, 1))])])
    check("trades outside the window do not cluster", far == [])

    print("\n[cluster] joint filings are one party, not many insiders")
    # Observed live: eight Sequoia entities co-signing a single Form 4. Counting
    # reporting owners rather than filing parties reported it as an 8-insider
    # cluster - a manufactured signal from a single decision.
    joint = [Owner(f"c{i}", f"Fund {i}", is_ten_percent=True) for i in range(8)]
    one_filing = mk_form(joint, [mk_txn(code="S", acquired=False)])
    check("eight co-filers on one accession are NOT a cluster",
          cl.find([one_filing]) == [])
    seps = [mk_form([Owner(f"p{i}", f"Person {i}", is_officer=True,
                           officer_title="VP")],
                    [mk_txn(code="S", acquired=False, d=date(2026, 8, 3 + i))])
            for i in range(3)]
    got = cl.find(seps)
    check("three separately-filing insiders are a 3-party cluster",
          len(got) == 1 and got[0].people == 3)
    mixed2 = cl.find([one_filing] + seps[:2])
    check("a joint filing counts once alongside separate filers",
          len(mixed2) == 1 and mixed2[0].people == 3)
    check("member records how many co-filers were collapsed",
          cl.find([one_filing] + seps)[0].members[0].co_filers == 7)

    print("\n[edgar] feed parsing against a real captured feed")
    feed = (FIX / "current-feed.xml").read_text()
    entries = re.findall(r"<entry>(.*?)</entry>", feed, re.S)
    refs = [edgar._parse_entry(e) for e in entries]
    refs = [r for r in refs if r]
    check("every entry parses to a ref", len(refs) == len(entries))
    types = {r.form_type for r in refs}
    check("the captured type=4 feed really does contain non-Form-4 types",
          bool(types - {"4", "4/A"}))
    keep = [r for r in refs if r.form_type in {"4", "4/A"}]
    check("filtering removes them", all(r.form_type in {"4", "4/A"} for r in keep))
    check("accession numbers extracted",
          all(re.fullmatch(r"\d{10}-\d{2}-\d{6}", r.accession) for r in keep))
    accs = [r.accession for r in keep]
    check("the raw feed does duplicate accessions (one entry per party)",
          len(accs) != len(set(accs)))

    print("\n[edgar] rate limiter")
    import time
    lim = edgar.RateLimiter(per_second=20.0)
    t0 = time.monotonic()
    for _ in range(5):
        lim.wait()
    check("limiter spaces requests", time.monotonic() - t0 >= 4 / 20.0)

    print("\n[pipeline] offline build")
    d = build(three)
    check("digest counts rows", d.rows == 3)
    check("all three rows discretionary", d.discretionary == 3)
    check("events ranked descending",
          [e.conviction.score for e in d.events] ==
          sorted([e.conviction.score for e in d.events], reverse=True))
    check("cluster detected in digest", len(d.clusters) == 1)
    check("headline mentions the non-discretionary share", "%" in d.headline())
    payload = d.as_dict()
    check("digest serialises to JSON-safe types",
          isinstance(payload["events"], list) and isinstance(payload["clusters"], list))
    import json
    json.dumps(payload, default=str)
    check("digest survives json.dumps", True)

    joint_digest = build([mk_form(joint, [mk_txn(code="S", acquired=False)])])
    check("a joint filing yields ONE event, not one per co-filer",
          len(joint_digest.events) == 1)
    check("the event records the collapsed co-filers",
          joint_digest.events[0].co_filers == 7)

    print("\n[edgar] contact configuration")
    import os
    from argus.data.edgar import ContactNotConfigured
    saved = os.environ.pop(edgar.CONTACT_ENV, None)
    edgar.set_contact("")
    try:
        edgar._ua()
        check("an unconfigured contact raises before any request", False)
    except ContactNotConfigured:
        check("an unconfigured contact raises before any request", True)
    edgar.set_contact("no email here")
    try:
        edgar._ua()
        check("a contact without an email is rejected", False)
    except ContactNotConfigured:
        check("a contact without an email is rejected", True)
    edgar.set_contact("Jane Doe jane@example.com")
    check("a valid contact builds a declared User-Agent",
          "jane@example.com" in edgar._ua())
    edgar.set_contact("")
    os.environ[edgar.CONTACT_ENV] = "Env Person env@example.com"
    check("the environment variable is honoured", "env@example.com" in edgar._ua())
    if saved is not None:
        os.environ[edgar.CONTACT_ENV] = saved
    else:
        os.environ.pop(edgar.CONTACT_ENV, None)

    mech = build([mk_form([a_], [mk_txn(code="F", acquired=False)])])
    check("an all-mechanical window reports 100% non-discretionary",
          mech.mechanical_share == 1.0 and mech.events == [])
    check("empty input does not divide by zero",
          build([]).mechanical_share is None)

    print(f"\n{'-'*60}\n  {PASS} passed, {FAIL} failed\n")
    return 1 if FAIL else 0


if __name__ == "__main__":
    raise SystemExit(main())
