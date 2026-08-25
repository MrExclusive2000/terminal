# Argus

Design plan for a single-user Windows research terminal — **FX and XAUUSD**,
information only, no order execution and no broker connectivity.

**Status: plan only (v0.3). Nothing is built.**

The distinguishing lens is *incentives*, translated out of the equity world
into the markets actually traded: cohort positioning (CFTC COT), producer
hedging, bullion-bank books, official-sector accumulation, physical stocks and
flow — sitting on a knowledge base that is authored, versioned and signed on a
schedule.

Scope confirmed: single user, UK-resident, non-professional subscriber. That
combination means the exchange-licensing cliff and the EU AI Act both fall out
of scope, and the positioning and physical layer is free at origin — the only
recurring cost is the AI layer.

Scoped as a tool rather than a project: every feature must name the decision
it changes, or it does not ship. The full equity insider module is documented
but cut - roughly 70 engineer-weeks that would not change an XAUUSD decision.
A miner bridge (gold producer hedge books and insider transactions) is kept as
a later hook, since that is the only equity work that informs a gold view.

Three steps, 30 irreducible engineer-weeks to a complete tool:

1. **Desk** (10w) - MT5 bridge, local store, tick recorder, price, spread
   monitor, session clock, ATR and levels, release calendar, journal.
2. **Context** (10w) - COT cohort percentiles, physical stocks, official
   sector, four-venue price panel, driver regime panel, FX driver stacks.
3. **Brain** (10w) - knowledge packs, morning brief, pre-trade check,
   weekly review.

Data cost is zero for steps 1 and 2; the only recurring spend is the AI layer.

## Contents

| Path | What it is |
|---|---|
| `docs/plan/argus-design-plan.html` | The plan. Concepts, rendered mockups, feature inventory, architecture, data economics, AI knowledge layer, security, design system, roadmap. |
| `docs/mockups/` | The five UI mockups as standalone HTML fragments. |
| `docs/plan/*.css` | Design tokens and stylesheets. Every text token is solved to clear WCAG AA (4.5:1) on all four surface levels in both themes. |
| `docs/research/` | Eight domain research dossiers — 201 findings, 210 candidate features, with per-finding confidence labels and sources. |

## Reading order

Start with the plan document. The research dossiers are the evidence base
behind it, not a substitute for it.

## Caveats

Prices, regulations and API terms were live-verified on 2026-08-24 and are
time-sensitive. Anything a researcher marked medium or low confidence is
flagged in the dossiers and should be re-verified before being relied on.

Mockups use real tickers with illustrative data. No filing, price or person
shown is a record of an actual transaction.
