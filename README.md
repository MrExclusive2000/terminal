# Argus

Design plan for a single-user Windows trading terminal — **equities and forex**,
information only, no order execution and no broker connectivity.

**Status: plan complete (v2). The insider & incentives engine is built and
running against live SEC EDGAR, packaged as an installable Windows desktop app.**
Built in Python rather than the WPF stack the plan specifies — see
[Why Python, not WPF](#why-python-not-wpf).

The organising lens is **incentives**: insider transactions, ownership,
compensation structure and cohort positioning treated as the primary surface
rather than a bolt-on screener — applied to equities via SEC filings and to FX
and metals via CFTC positioning, official-sector flows and physical stocks.
Underneath sits a knowledge base authored, versioned and signed on a schedule.

24 modules · 182 features · 9 rendered mockups.

## Contents

| Path | What it is |
|---|---|
| `docs/plan/argus-build-plan-v2.html` | **The plan (current).** Written from the desk: what the job is, where the edge is and isn't, the screens, what it must know, the knowledge layer, how it's made, what breaks it, how it looks, money and time, what I'd cut. |
| `docs/plan/argus-design-plan.html` | The earlier v1.0 draft, kept for history. Superseded by v2. |
| `docs/plan/src/`, `assemble.py` | The v2 plan's sections and its assembly script — `python3 docs/plan/assemble.py` rebuilds the single-file HTML. |
| `docs/plan/validate.py`, `crosscheck.py` | Build gates. `validate.py` checks tag nesting, dangling anchors, duplicate ids, rail/section parity, CSS variable and dark-theme token integrity, table column counts and superseded figures. `crosscheck.py` reconciles the arithmetic — feature totals, the module map, phase weeks, the effort multiplier. Both exit non-zero on failure. |
| `docs/mockups/` | The nine screens as standalone HTML fragments. |
| `docs/research/` | Nine domain dossiers (201 findings) and four adversarial reviews (121 gaps, 42 corrections). |
| `docs/plan/*.css` | Design tokens. Every text token solved numerically to clear WCAG AA on all four surfaces in both themes. |
| `src/argus/insider/` | **The insider & incentives engine — built and working.** Form 4 parser, transaction-code decoder, conviction scoring, cluster detection, and the end-to-end pipeline. See below. |
| `src/argus/data/edgar.py` | SEC EDGAR client: rate limiting inside fair access, exact form-type filtering, per-accession dedup. |
| `insider.py` | Command line for the insider desk. |
| `src/`, `tests/`, `knowledge/`, `run.py` | The rest of the working code: MT5 bridge (read-only), COT positioning, FRED macro, regime analysis, trade sizing, local app. |

## Reading order

The plan document, top to bottom. It opens with the brief restated as an
auditable checklist so scope can be checked against what was asked for.

## Caveats

Prices, regulations and API terms were live-verified on 2026-08-24 and are
time-sensitive. Claims that adversarial review could not corroborate against a
primary source are marked in the text.

Mockups use real tickers with illustrative data. No filing, price, holder or
person shown is a record of an actual transaction.


## The insider engine (built)

Phase 1 of the plan — the flagship — is implemented and runs against live SEC
EDGAR. It is the piece the plan argues nobody else sells.

### Install on Windows

Download the installer from [Releases](https://github.com/MrExclusive2000/terminal/releases)
and run it. No administrator rights, no Python, no command line. It installs
per-user and puts Argus on your desktop and Start menu.

On first launch it asks for one thing: **a name and an email address**. The SEC
refuses anonymous traffic to EDGAR outright — a 403 on every request — so this
is required rather than optional. Nothing else needs configuring.

### Run from source

```bash
python3 run.py                                # the app
python3 insider.py --limit 40 --min-score 25  # ranked feed on the command line
python3 insider.py --file some-form4.xml      # score one filing, offline
python3 insider.py --json                     # machine-readable
```

The CLI takes `--contact` or `$ARGUS_SEC_CONTACT`; the app stores it in settings.

### What it actually does

It decodes filings rather than listing them. On live pulls it measures
**~71–81% of Form 4 rows as non-discretionary** and **code P (open-market
purchase) at ~5%** — independently reproducing the figures the plan is built
on. Those rows score exactly zero, with the reason attached, instead of being
padded into a tape.

| Piece | What it decides |
|---|---|
| `codes.py` | Whether the filer chose the timing. Tax withholding, grants and option mechanics are payroll, not decisions. |
| `form4.py` | Parses `ownershipDocument`. Distinguishes *no price stated* from *a stated price of zero* — a real filing in the fixtures has both. |
| `conviction.py` | Scores discretionary rows and shows every factor. Purchases and sales are deliberately asymmetric; sales cap at 55. Includes the Cohen–Malloy–Pomorski routine/opportunistic split. |
| `cluster.py` | Several **separate filers**, one issuer, one direction, inside a window. |
| `pipeline.py` | Detect → fetch → parse → decode → score → cluster, deterministic throughout. No model in this path. |

### Bugs this found in real data

Each of these was observed live, not anticipated, and each has a regression test:

- **`type=4` on the EDGAR feed is a prefix match** — it returns 424B2, 425 and
  40-33. Measured at 14 of 40 entries on one pull.
- **The feed caps at 40 entries** whatever `count` you ask for.
- **Every filing appears twice**, once per party (reporting owner and issuer).
  Undeduplicated, that double-counts insiders.
- **Joint filings are one decision, not many insiders.** Eight Sequoia entities
  co-signed a single Form 4; counting reporting owners reported it as an
  "8-insider cluster". The decision unit is the filing party.
- **Prices can exist only as a footnote.** Coercing that to `0.0` invents a
  free trade.
- **Tickers arrive dirty** — `NYSE: VTEX`, `[[Ticker]]`, `N/A` — and fragment
  per-issuer grouping if not normalised.

### Verification

```bash
python3 tests/test_insider.py    # 85 checks, offline, real SEC fixtures
python3 tests/test_core.py       # the pre-existing suite
```

## The FX & metals desk

You trade FX and gold, so this is the half of the plan aimed at that. Three
engines, all deterministic and all testable offline.

| Module | What it answers |
|---|---|
| `analysis/sessions.py` | Which desks are open, how deep the book is, and what changes next. |
| `analysis/calendar.py` | What is scheduled that could hurt a position. |
| `analysis/bias.py` | **Long or short here — and what agrees.** |

### Sessions are defined in local exchange time, never fixed UTC offsets

This is the whole reason the module exists. London and New York shift on
different weekends, Tokyo never shifts, and Sydney moves the other way. Any
hardcoded UTC window is wrong for several weeks a year — and wrong exactly
where the London/New York overlap changes length.

Proof, from the test suite: **12:30 UTC** has New York open in August (08:30
EDT) and closed in January (07:30 EST). **16:30 UTC** has London closed in
August (17:30 BST) and open in January (16:30 GMT). A fixed window gets one of
those wrong.

The practical payoff is the **rollover warning**. At 17:00 New York the
interbank day rolls, liquidity briefly evaporates, and gold spreads can go from
0.30 to several dollars. Traders get stopped out by a spread spike rather than a
move, at an entirely predictable minute.

### The calendar is built from rules, not scraped dates

Each source declares three things that are routinely conflated: the
**publication rule**, the **as-of rule**, and the **expected lag**. The COT is
the clean case — released Friday 15:30 New York, describing the *Tuesday three
days earlier*. Stamping it with the release date tells you positioning is
current when it is already three days old.

Because the rule is expressed in New York time, the COT resolves to 19:30 UTC in
summer and 20:30 UTC in winter, automatically.

**Only genuinely rule-based releases are included.** NFP is the first Friday of
the month; the CFTC reports follow fixed weekly rules. CPI and FOMC dates are
*published schedules*, not rules — so they are absent rather than approximated.
A calendar that quietly guesses the CPI date is worse than one that admits it
does not know, because you would plan a position around it.

### The bias board answers the original question

It will not break three rules:

- **It is never a signal.** There is no BUY — there is a lean, a strength, and
  every input that produced them, each of which you can argue with.
- **Disagreement is surfaced, not netted away.** Two strong opposing reads and
  two weak aligned ones average identically. They are not the same situation, so
  conflict is reported separately and caps the strength at *weak*.
- **Confidence needs evidence, not just agreement.** A single input agrees with
  itself perfectly and scores ±1.00 — so strength is gated on evidence *mass*
  too, and the bar is scaled by it. A full-width bar next to the word "weak"
  is the graphic contradicting the label.

Positioning is deliberately contrarian and weight-capped at 0.25: it marks
fuel, not timing, and the copy says *crowded*, never *due*. A driver whose
correlation has broken from its long-run value returns a **warning instead of a
direction** — gold against real yields is the standing example. USDJPY
positioning is inverted into pair terms, because the CME contract is JPY/USD.

## The desktop app

| Piece | What it does |
|---|---|
| `run.py` | Native window via pywebview, single-instance lock, window geometry remembered. |
| `src/argus/config.py` | Settings in `%LOCALAPPDATA%\Argus`, written atomically, tolerant of a corrupt file. |
| `src/argus/update.py` | Checks GitHub Releases and **tells you**. Never downloads or runs anything. |
| `packaging/argus.spec` | PyInstaller, onedir, no console window. |
| `packaging/make_icon.py` | Generates the 7-size ICO from `zlib` and `struct` — no image library. |
| `packaging/argus.iss` | Per-user Inno Setup installer. No admin prompt. |
| `.github/workflows/build-windows.yml` | Tests on Linux, builds the exe and installer on Windows. |

### Two deliberate refusals

**Secrets are not stored in settings.** That file is plaintext JSON in a
user-readable directory. The plan requires OS-level key isolation (CNG/TPM with
a passphrase) before a key touches disk, and is explicit that DPAPI alone is not
protection against the realistic adversary. Until that exists, the Claude API
key is read from `ANTHROPIC_API_KEY` at the moment it is used and never
persisted. POSTing a key to the settings endpoint is *refused with an
explanation*, not silently dropped.

**The updater does not update.** It checks for a newer release and links to it.
There is no code signing yet, so nothing could verify a downloaded binary — and
an updater that cannot verify what it fetched is a remote code execution path,
not a feature. When signing exists this becomes verify-then-apply.

## Why Python, not WPF

The plan specifies .NET 10 + WPF, and that remains the right answer for a native
Windows terminal — real docking, tear-off, and a mature charting ecosystem.

It was not built that way because this was developed on Linux, where WPF cannot
be compiled or run. Writing several thousand lines of C# that had never once
executed would have produced an impressive diff and an unverifiable product,
in a plan whose own UX section insists keyboard operation is *"audited as a
release gate, not asserted."*

So the engine — the hard, portable, differentiating part — is Python, and the
shell is a local web UI in a native window. The trade is real: no native
docking, no tear-off to a second monitor, no SciChart. The engine is a clean
HTTP API, so a WPF front end over it remains open.

### Known limits — stated, not hidden

- **The Windows build is produced by CI, not on this machine.** PyInstaller
  cannot cross-compile. The `.exe` and installer are built and smoke-tested on
  a `windows-latest` runner.
- **No code signing.** Windows SmartScreen will warn on first run, and the
  updater is check-only for exactly this reason.
- **Multiple purchases by one filer occupy several ranked rows** rather than
  aggregating into a single position-building event. Each row is a genuine
  distinct transaction, but aggregating per party would rank better.
- **No local store yet.** Every run re-fetches; there is no Parquet lake, so
  no history, no backtest and no filer trade-history, which means
  `classify_filer` is implemented and tested but not yet fed real history.
- **US only.** No non-US insider regimes.
