# Argus

Design plan for a single-user Windows trading terminal — **equities and forex**,
information only, no order execution and no broker connectivity.

**Status: plan only (v1.0). Nothing is built.**

The organising lens is **incentives**: insider transactions, ownership,
compensation structure and cohort positioning treated as the primary surface
rather than a bolt-on screener — applied to equities via SEC filings and to FX
and metals via CFTC positioning, official-sector flows and physical stocks.
Underneath sits a knowledge base authored, versioned and signed on a schedule.

24 modules · 209 features · 9 rendered mockups.

## Contents

| Path | What it is |
|---|---|
| `docs/plan/argus-design-plan.html` | **The plan.** Brief as a contract, concepts, mockups, exhaustive feature inventory, architecture, data economics, the AI knowledge layer, security, usability, roadmap, risks. |
| `docs/mockups/` | The nine screens as standalone HTML fragments. |
| `docs/research/` | Nine domain dossiers (201 findings) and four adversarial reviews (121 gaps, 42 corrections). |
| `docs/plan/*.css` | Design tokens. Every text token solved numerically to clear WCAG AA on all four surfaces in both themes. |
| `src/`, `tests/`, `knowledge/`, `run.py` | Exploratory code written earlier in the session, outside the plan-only brief. Working and tested where marked in `HANDOVER.md`, but **not part of this deliverable**. |

## Reading order

The plan document, top to bottom. It opens with the brief restated as an
auditable checklist so scope can be checked against what was asked for.

## Caveats

Prices, regulations and API terms were live-verified on 2026-08-24 and are
time-sensitive. Claims that adversarial review could not corroborate against a
primary source are marked in the text.

Mockups use real tickers with illustrative data. No filing, price, holder or
person shown is a record of an actual transaction.
