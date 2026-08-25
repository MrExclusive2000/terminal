# Argus

Design plan for a single-user Windows research terminal — equities and FX,
information only, no order execution and no broker connectivity.

**Status: plan only. Nothing is built.**

The distinguishing lens is *incentives*: insider transactions, ownership,
compensation structure and positioning treated as the primary surface rather
than a bolt-on screener, sitting on a knowledge base that is authored,
versioned and signed on a schedule.

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
