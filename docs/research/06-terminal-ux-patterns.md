# UX / UI / Interaction Design patterns of professional financial terminals — senior-designer specification for a read-only Windows equities+FX intelligence terminal

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

Professional terminals are not "badly designed"; they are optimised for a different objective function than consumer apps: glances-per-minute and keystrokes-to-answer, not first-run delight. Bloomberg's defensibility is a *grammar* (object-then-verb: `AAPL US Equity OWN <GO>`) plus muscle memory, plus four independent command contexts on screen at once — verified: the core Terminal is four "Panels", each running a separate command instance, with F2–F12 hard-coded to asset classes (GOVT/CORP/MTGE/M-Mkt/MUNI/PFD/EQUITY/COMDTY/INDEX/CURNCY/CLIENT) and a green GO key (Wikipedia, fetched 2026-08-24). The modern equivalent of that grammar is the fuzzy command palette with sigil prefixes (VS Code: `>` commands, `@` symbols, `#` workspace symbols, `:` line, `?` help — verified). The correct answer for this product is *both*, with the mnemonic line primary and the palette as the discoverability escape hatch.

Three design pillars dominate. (1) **Density is the feature.** Compact 20–24px rows, hairline rules, tabular figures, no cards, no shadows. Whitespace in a blotter is a cost paid in scroll events. (2) **Trust UX is legally and practically load-bearing.** Every number needs an as-of stamp, a provenance click-through, and an entitlement/delay badge; 13F is 45 days stale, US short interest is bi-monthly with a lag, and non-US insider disclosure is MAR Art.19 RNS not Form 4 — a naive "global ownership" panel is quietly wrong. (3) **Accessibility constrains the live-update aesthetic.** WCAG 2.2 SC 2.3.1 caps flashing at three per second (verified thresholds), SC 2.2.2 requires a pause mechanism for auto-updating content lasting >5s — so a global Freeze key is mandatory, not a nicety. Red/green defaults fail ~1 in 12 men (verified, Colour Blind Awareness); ship Okabe-Ito blue `#0072B2` / vermilion `#D55E00` as the *default* and classic red/green as opt-in. Screen readers need UIA `UiaRaiseNotificationEvent` with `NotificationProcessing_MostRecent`, never a live region on the tape.

The differentiating surfaces — incentives/insiders forensics and a Claude-authored knowledge base — both live or die on provenance affordances and staleness honesty rather than on layout novelty.

## Findings

### 1. Bloomberg's interaction model, verified: four independent command contexts, hard-keyed asset classes, object-then-verb grammar  
`confidence: high`

Verified from Wikipedia (fetched 2026-08-24): 'Core Terminal' is typically four windows called Panels, each running a separate command instance simultaneously, on one or multiple monitors. The keyboard hard-codes asset class to function keys: F2 GOVT, F3 CORP, F4 MTGE, F5 M-Mkt, F6 MUNI, F7 PFD, F8 EQUITY, F9 COMDTY, F10 INDEX, F11 CURNCY, F12 CLIENT/ALPHA. Green GO key executes (named after Monopoly); red CANCEL aborts; MENU goes back up the function stack; HISTORY retrieves prior commands chronologically. Command notation convention: angle brackets for keys, curly braces for whole commands, e.g. {VOD LN Equity GO}. Launchpad provides small always-on 'components' pinned outside the four-panel model. ~325,000 subscribers as of 2022; ~$24,000–$27,000/user/year; >85% of Bloomberg L.P. revenue. Current Starboard keyboard weighs 1.08 kg.

**Why it matters.** The four-panel model is the architectural decision, not the yellow keys. Each panel is a *command context with its own history*, which is why power users navigate faster than in any tab/tile system where one address bar drives everything. Our product should replicate 'each tile owns a command context' even though we render a modern tiled grid.

- https://en.wikipedia.org/wiki/Bloomberg_Terminal

### 2. Bloomberg mnemonic vocabulary and its grammatical shape (object-then-verb) — meanings from model prior knowledge, NOT verified in this session  
`confidence: medium`

Grammar: [identifier] [market-sector key] [function mnemonic] <GO>. Commonly used equity mnemonics and their meanings: DES = security description; GP = graph price (line/bar chart); GIP = graph intraday price; HP = historical price table; COMP = comparative total returns; EQS = equity screening; FA = financial analysis (statements); RV = relative valuation / comps; ANR = analyst recommendations; EE = earnings estimates; ERN = earnings summary/surprise history; OWN = ownership summary; HDS = holders detail; SI = short interest; CACS = corporate actions; DVD = dividends; BI = Bloomberg Intelligence (industry research); TOP = top news; NI = news by topic code (e.g. NI OIL); WEI = world equity indices; FXC = FX cross-rate matrix; MOST = most active; PORT = portfolio analytics; BQ = Bloomberg Query; HELP HELP = live analyst chat. NOTE: I could not fetch a corroborating public mnemonic list this session (Yale, Brown, Harvard, MIT and USC library guides returned 404 or contained no mnemonics; Investopedia is blocked to this fetch tool). Treat individual mnemonic definitions as medium confidence; treat the *grammar shape* as high confidence.

**Why it matters.** Our command catalogue should be Bloomberg-adjacent so a professional's existing muscle memory transfers on day one (OWN, SI, DES, GP, EQS, CACS are near-universal in the industry). Inventing a fresh vocabulary is a gratuitous tax.

- https://en.wikipedia.org/wiki/Bloomberg_Terminal
- model prior knowledge — unverified this session

### 3. Why the 'dated' look is defended — and what actually must be preserved  
`confidence: medium`

The defensible properties are: (a) zero-chrome density — no cards, no shadows, no 16px padding, so 60+ rows are visible at 1080p; (b) determinism — the same keystrokes always produce the same screen, so the interface is memorisable rather than explorable; (c) four simultaneous command contexts; (d) an amber-on-black legacy palette that is really a *high-luminance-contrast, low-saturation-area* palette, which is the same conclusion modern dark-theme guidance reaches; (e) no animation, therefore no perceived latency. The properties that are genuinely obsolete: 8-colour palette, no font scaling, bitmap-era type metrics, no keyboard-map discoverability outside HELP, and no accessible-name plumbing. Design conclusion: keep density/determinism/multi-context, replace the rendering and the discoverability. Confidence medium on the causal claim (this is synthesis, not a fetched study).

**Why it matters.** A 'clean redesign' of a terminal fails because it trades information per glance for aesthetics. The correct brief is 'Tufte-dense and 2026-rendered', not 'Bloomberg but pretty'.

- https://en.wikipedia.org/wiki/Bloomberg_Terminal
- synthesis

### 4. Command palette state of the art: sigil-prefixed fuzzy search (VS Code model), verified  
`confidence: high`

Verified from VS Code docs (fetched 2026-08-24): Command Palette on Ctrl+Shift+P; prefix grammar within one input — '>' editor commands, '@' symbols in file, '#' symbols across workspace, ':' go to line number, '?' lists all available command options. Ctrl+P is Quick Open (files by name), Ctrl+Tab cycles recents. Fuzzy matching on partial names; recently-used commands are surfaced first. Workbench layout is six regions (Activity Bar, Primary Side Bar, Secondary Side Bar, Editor with vertical+horizontal editor groups, Panel, Status Bar), all repositionable/hideable.

**Why it matters.** This gives us a proven answer to the mnemonic discoverability problem: one input, sigils to disambiguate namespaces, '?' to enumerate. We adopt sigils for symbol vs function vs layout vs alert vs AI-question, so the *same* box serves the expert (types 'AAPL US EQ OWN') and the learner (types 'who owns').

- https://code.visualstudio.com/docs/getstarted/userinterface

### 5. Workspace models across the competitive set — four distinct paradigms, each with a named failure mode  
`confidence: high`

(1) Chartbook model — Sierra Chart: a Chartbook is 'like a desktop/layout/workspace', contains charts, Time & Sales, Market Depth windows; saved as .cht in the Data Files Folder; File>Save / Save As; multiple chartbooks can be open but 'only 1 can be visible at a time' per instance, switched by tabs, the CB menu, or F7/F8; showing two concurrently requires two program instances; Window >> Window Always Visible shares a chart across chartbooks (verified). (2) Tab/layout model — TradingView: charts-per-tab quota by plan, saved layouts quota by plan (verified numbers below). (3) Profiles+Templates model — MetaTrader 5: a Profile stores the set of open charts; a Template stores one chart's appearance; the Status Bar shows the active template/profile names; main window = Market Watch + Navigator + Toolbox + chart area + Chart Switch Bar + Depth of Market; 21 timeframes M1→MN1 (verified). (4) Free-floating MDI — IBKR TWS Classic (and the reason Mosaic exists). Failure modes: chartbook = can't see two workspaces side by side; tabs = no true multi-monitor; profiles = chart-only, no research panels; free-floating = window management becomes the user's job and layouts break on monitor change.

**Why it matters.** Our answer must be a tiled grid of command-owning panels + named layouts + genuine tear-off that survives monitor disconnect. Sierra's 'Window Always Visible' is the pattern for a pinned always-on panel (our equivalent of Launchpad).

- https://www.sierrachart.com/index.php?page=doc/Chartbooks.php
- https://www.metatrader5.com/en/terminal/help/startworking/interface
- https://www.tradingview.com/pricing/

### 6. TradingView plan limits are the industry's de-facto benchmark for quotas — exact numbers as of 2026-08-24  
`confidence: high`

Verified from tradingview.com/pricing (fetched 2026-08-24): Basic free; Essential $12.95/mo; Plus $29.95/mo; Premium $59.95/mo; Ultimate $199.95/mo. Charts per tab: 1 / 2 / 4 / 8 / 16. Indicators per chart: 2 / 5 / 10 / 25 / 50. Price alerts: 3 / 20 / 100 / 400 / 1,000. Technical alerts: 0 / 20 / 100 / 400 / 1,000. Saved layouts: 1 / 5 / 10 / 10 / 10. Bar Replay: absent on Basic, present on all paid. Historical bars: 5K / 10K / 10K / 20K / 40K. Chart connections (concurrent devices/streams): 2 / 10 / 20 / 50 / 200. Ultimate adds a 100-second indicator calculation time limit and first-priority support.

**Why it matters.** For a single-user local product these are ceilings we should simply not impose — 'unlimited alerts, unlimited layouts, unlimited panels' is a genuine differentiator and costs us nothing but engineering discipline. But note the *shape*: even the $199.95 tier caps saved layouts at 10, implying real users converge on <10 named workspaces. Design for 6–10 curated layouts, not 100.

- https://www.tradingview.com/pricing/

### 7. Alert UX benchmark — TradingView's channel set and semantics, verified  
`confidence: high`

Verified from TradingView help (fetched 2026-08-24): alerts can be attached to 'data series, indicator plots, strategy orders and drawing objects'. Data-series alerts are timeframe-independent; study/strategy/drawing alerts depend on the interval used for calculation — a crucial and commonly-missed semantic. Frequency setting controls once vs repeated. A Timer/expiration setting auto-disables the alert. Six delivery channels: Notify on App (mobile push), Show Pop-up (desktop notification), Send Email, Webhook URL (POST), Play Sound, Send plain text to alternative email. Alert names and messages support placeholders that interpolate variable values into the message.

**Why it matters.** Two transferable rules: (1) the alert UI must *state its evaluation clock* (tick / bar-close / data-refresh) or the user cannot reason about a non-firing alert; (2) message templating with placeholders is what makes an alert actionable rather than a bare 'AAPL alert triggered'. Our equivalent: `{{symbol}} {{field}} crossed {{threshold}} — now {{value}} (as of {{asof}})`.

- https://www.tradingview.com/support/solutions/43000595315-about-alerts/

### 8. Screener UX benchmark — Finviz's tabbed view-sets and signal library, verified  
`confidence: high`

Verified from finviz.com/help/screener (fetched 2026-08-24): expandable filter panel with categorised filters, saveable as presets; view tabs include Overview, Snapshot, Fundamental, Financial, Ownership, Performance, Technical. Most filters carry per-filter capability flags 'Sorting: Yes; Export: Yes'; a few (Exchange, Index, Pattern, Candlestick) support neither. A Signals library provides pre-built one-click screens: Top Gainers/Losers, New Highs/Lows, Most Active, Unusual Volume, RSI Overbought/Oversold, Earnings, Analyst upgrades/downgrades, News. Signal results are capped (Top 200, Top 100, etc.). Universe: NASDAQ, NYSE, AMEX; quotes delayed one minute.

**Why it matters.** The 'view-set' concept — same result rows, swappable column packs — is the single highest-value screener pattern and is cheap to build. It beats a column-chooser dialog because it is one keystroke. Stock Rover calls the identical concept 'Views' (verified separately). We should ship view-sets named Overview / Ownership / Incentives / Shorts / Estimates / Technicals / Custom.

- https://finviz.com/help/screener.ashx
- https://www.stockrover.com/features/

### 9. The incentives/insiders competitive landscape defines the feature vocabulary and the price anchor — verified prices as of 2026-08-24  
`confidence: high`

Quiver Quantitative (fetched 2026-08-24): Premium $25/mo or $300/yr (7-day trial monthly, 30-day annual); free 'Visitor' tier carries live Congress Trading, Insider Trading, Government Contracts, Corporate Lobbying, CNBC Stock Picks, Google Search Trends. Full dataset list: Congress Trading, Politician Stock Portfolios, Election Fundraising, 2026 Midterm Elections, Legislation Search, Government Spending, Congress Live Net Worth, Corporate Lobbying, Government Contracts, DC Insider Score, Insider Trading, Executive Compensation, Revenue Breakdowns, Institutional Holdings (13F), Risk Factors, Whale Moves (13D), Stock Splits, ETF Holdings, Analyst Ratings, CNBC Stock Picks, Jim Cramer Tracker, Google Trends, App Ratings, Patents, Corporate Flights, Social Media Trends. UI surfaces: Quiver Strategies (backtested), Quiver Alerts, Stock Screener across the alt datasets, Congress Backtester, Institutional Backtester, watchlists, politician leaderboards. Unusual Whales (fetched 2026-08-24): Retail Basic $50/mo — includes 25 custom alerts, 5 watchlists, 5 dashboards, GEX heatmap, SPX MMX at 10-min updates, insider trades, politician trades, options+dark-pool daily downloads, screener; Retail Pro $75/mo — unlimited alerts/watchlists/dashboards, unlimited saveable filters; Retail Max $120/mo — 1-minute SPX MMX; annual up to 30% off; separate API plans (REST, WebSocket, or MCP), Discord bot, Predictions, Whale Bundle.

**Why it matters.** Two things to steal: 'Backtester attached to the dataset' (turns a curiosity into a decision input) and 'unlimited alerts/dashboards as the upgrade lever' (i.e. quotas are the pain point users pay to remove — so give ours none). Also note Unusual Whales' Mr. Whale AI is metered by usage tier, which is the pricing shape an AI knowledge layer converges on.

- https://www.quiverquant.com/
- https://unusualwhales.com/pricing

### 10. Research-terminal price ladder and feature gating — Koyfin, TIKR, AlphaSense (verified 2026-08-24)  
`confidence: high`

Koyfin: Free $0 (2y financials, 1y estimates, 2 watchlists, 2 screens, 2 dashboards); Plus $39/mo ($468/yr, up to 30% saving) — 10y financials, 10y estimates, unlimited watchlists/screens/dashboards, 100K+ global company snapshots, press releases + filings + transcripts + premium news, stock & ETF screener, ETF holdings; Premium $79/mo — portfolio analytics, unlimited custom data, unlimited custom formulas, custom financial templates, ETF valuation; Advisor Core $209/mo; Advisor Pro $299/mo. TIKR: Free $0 (US only, 5Y/8Q, 90-day transcripts); Plus $24.95/mo (global, 10Y/20Q, 1y transcripts, top-40 fund data, 5 custom newsfeeds); Pro $54.95/mo (10Y/40Q, 10y transcripts, top-150 fund data, unlimited newsfeeds); Ultimate $119.95/mo (30Y/40Q, full transcript history, 10,000+ funds). AlphaSense: '500+ million premium financial and business documents', '7,000+ of the world's largest enterprises'; Smart Synonyms semantic expansion, Deep Research agentic report generation, sentence-level citations, PowerPoint and Excel add-ins, real-time alerts, earnings-call sentiment indices, Tegus expert transcripts and expert call services.

**Why it matters.** AlphaSense's 'sentence-level citations, no hallucinations' is the exact UX contract our AI knowledge layer must copy — the citation is a first-class UI object, not a footnote. Koyfin/TIKR show that history depth (years of financials, years of transcripts) is what buyers actually gate on, so our data-freshness/depth badge should be prominent.

- https://www.koyfin.com/pricing/
- https://www.tikr.com/pricing
- https://www.alpha-sense.com/

### 11. Colour vision deficiency: prevalence and the specific palette answer — verified  
`confidence: high`

Prevalence (Colour Blind Awareness, fetched 2026-08-24): approximately 1 in 12 men (8%) and 1 in 200 women; ~3 million in the UK (~4.5% of population); ~300 million worldwide. Okabe & Ito / Color Universal Design (jfly.uni-koeln.de, fetched 2026-08-24): red-green CVD affects ~8% of Caucasian males, ~5% of Asian males, ~4% of African males; tritanopia ~0.001%. Explicit guidance: 'Use magenta (purple) and green instead' of red and green; for red use vermilion (yellowish-red) RGB 100%,32%,0% = #FF2000 rather than pure red; light red #FF1414; prefer bluish-green over yellow-green; reddish-purple over violet. The canonical Okabe-Ito 8-colour palette (widely cited, values confirmed against a secondary source in this session): black #000000, orange #E69F00, sky blue #56B4E9, bluish green #009E73, yellow #F0E442, blue #0072B2, vermilion #D55E00, reddish purple #CC79A7.

**Why it matters.** Our user is one man; 1-in-12 odds are not negligible and the cost of asking is a 10-second first-run question with live preview. Ship three directional palettes: Classic (green/red), CVD-Safe Blue/Orange (#0072B2 up / #D55E00 down), CVD-Safe Cyan/Magenta (#56B4E9 up / #CC79A7 down), plus a Luminance-only mode for greyscale printing. Crucially, direction must ALWAYS be triple-coded: hue + glyph (▲▼) + explicit sign, so the palette choice is a comfort setting, never a correctness dependency.

- https://www.colourblindawareness.org/colour-blindness/
- https://jfly.uni-koeln.de/color/

### 12. WCAG 2.2 SC 2.3.1 flash thresholds — exact numbers, and what they mean for tick flashing  
`confidence: high`

Verified from W3C Understanding SC 2.3.1 (fetched 2026-08-24): content must not flash more than three times in any one second period, OR the flash must be below the general and red flash thresholds. General flash = 'a pair of opposing changes in relative luminance of 10% or more of the maximum relative luminance (1.0) where the relative luminance of the darker image is below 0.80'. Area exemption: combined flashing area no more than 0.006 steradians within any 10-degree visual field (25% of a 10-degree field); the reference measurement is a 341 x 256 pixel rectangle at standard viewing distance. Red flash = a pair of opposing transitions involving saturated red (transition to/from a state where R/(R+G+B) >= 0.8 with chromaticity difference > 0.2). Exception: fine balanced patterns (white noise, alternating checkerboard) with squares smaller than 0.1 degree.

**Why it matters.** A liquid FX pair updates far more than 3x/second. A naive uptick/downtick cell flash therefore violates 2.3.1 AND is nauseating. Required design: a per-cell FLASH GOVERNOR — flash budget of 3/sec; above that rate, degrade to a persistent 2px left edge-bar whose opacity encodes update intensity (no luminance oscillation at all). Also keep the total simultaneously-flashing area under the 341x256px equivalent by never flashing whole rows, only the changed cell's background at low alpha. The red-flash clause is an independent reason to avoid saturated red as the down colour.

- https://www.w3.org/WAI/WCAG22/Understanding/three-flashes-or-below-threshold.html

### 13. WCAG 2.2 SC 2.2.2 forces a global Freeze control on any live terminal — and it is also a great feature  
`confidence: high`

Verified (w3.org/TR/WCAG22, fetched 2026-08-24): 'For moving, blinking, scrolling, or auto-updating information that starts automatically and lasts more than five seconds or updates in parallel with other content, a mechanism exists for users to pause, stop, or hide it.' Other verified 2.2 criteria that bind here: 1.4.3 Contrast (Minimum) 4.5:1 normal text, 3:1 large text (>=18pt or 14pt bold, ~24px / ~18.5px); 1.4.11 Non-text Contrast 3:1 for UI components and graphical objects (this covers chart lines, sparklines, heatmap cell borders, focus rings); 1.4.12 Text Spacing (line-height 1.5x, paragraph spacing 2x, letter spacing 0.12x, word spacing 0.16x with no loss of content); 1.4.4 Resize Text to 200% without loss of content or function; 2.4.11 Focus Not Obscured (Minimum) AA — focused component must not be entirely hidden by author content; 2.5.8 Target Size (Minimum) AA — 24x24 CSS px with five exceptions (Spacing: a 24px-diameter circle centred on each undersized target must not intersect another target's circle; Equivalent; Inline; User Agent Control; Essential); 2.4.13 Focus Appearance AAA — indicator area >= a 2 CSS px perimeter (4h+4w for a w x h rect) AND >= 3:1 contrast between the same pixels in focused vs unfocused states.

**Why it matters.** Three hard product requirements fall out: (a) Alt+P Freeze that halts all animation and pins every value with its freeze timestamp; (b) a Density mode ladder that still satisfies 24x24 targets — at 18px dense rows, row-level click targets rely on the *Spacing* exception, so inter-target spacing must be audited, and any icon button in a dense row needs a 24px hit box even with a 14px glyph; (c) 200% font scaling must reflow the panel grid to single-column stacking rather than clipping — which means the grid engine needs a breakpoint model, not fixed pixel tiles.

- https://www.w3.org/TR/WCAG22/
- https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html

### 14. Screen-reader strategy for live prices: UIA notifications, not live regions — with the exact enum to use  
`confidence: high`

Verified Microsoft Learn (fetched 2026-08-24): UiaRaiseNotificationEvent(provider, NotificationKind, NotificationProcessing, displayString, activityId), Windows 10 1709+ / Server 2016+, uiautomationcoreapi.h, Uiautomationcore.dll. NotificationKind: ItemAdded=0, ItemRemoved=1, ActionCompleted=2, ActionAborted=3, Other=4. NotificationProcessing: ImportantAll=0 ('presented as soon as possible... all notifications delivered' — documentation carries an explicit warning that this 'could cause a flooding of information'); ImportantMostRecent=1; All=2; MostRecent=3 ('presented when possible... the most recent supersedes all others'); CurrentThenMostRecent=4 (don't interrupt the current announcement; keep only the most recent arrival and discard the rest, then promote it); ImportantCurrentThenMostRecent=5 (added in Windows build 26100). Note: WS_POPUP windows must also implement the Window Control Pattern and handle WM_GETOBJECT. Web-equivalent guidance (MDN, fetched 2026-08-24) is explicit that stock tickers and real-time dashboards must NOT use aria-live='assertive', and that even 'polite' is annoying when updates are frequent; roles carry implicit liveness (status=polite, alert=assertive, log=polite, timer=off, marquee=off); aria-atomic=true for short self-contained status; create the live region empty first, then populate.

**Why it matters.** Concrete rules: (1) the tape/quote grid is NEVER a live region and NEVER raises notifications on tick; (2) price is announced only on demand via an 'announce focused cell' hotkey, or when the user has explicitly subscribed a cell to spoken monitoring; (3) alert firings use NotificationKind_Other with NotificationProcessing_ImportantMostRecent for P1 and NotificationProcessing_CurrentThenMostRecent for P2, so a burst of alerts collapses to the latest instead of flooding; (4) connection state changes use ActionAborted/ActionCompleted. This is the single most-missed accessibility detail in trading software.

- https://learn.microsoft.com/en-us/windows/win32/api/uiautomationcoreapi/nf-uiautomationcoreapi-uiaraisenotificationevent
- https://learn.microsoft.com/en-us/windows/win32/api/uiautomationcore/ne-uiautomationcore-notificationprocessing
- https://learn.microsoft.com/en-us/windows/win32/api/uiautomationcore/ne-uiautomationcore-notificationkind
- https://developer.mozilla.org/en-US/docs/Web/Accessibility/ARIA/Guides/Live_regions

### 15. Numeric typography spec: tabular figures beat monospace; the exact OpenType features to force  
`confidence: high`

Verified MDN (fetched 2026-08-24): font-variant-numeric values map to OpenType features — lining-nums->lnum (all digits on the baseline), oldstyle-nums->onum, proportional-nums->pnum, tabular-nums->tnum (equal digit advance width; 'essential for alignment in tables and financial data... enables numbers to stack vertically without shifting'), diagonal-fractions->frac, stacked-fractions->afrc, slashed-zero->zero. Design spec derived: every numeric cell in the product sets tnum + lnum + zero. Use a proportional UI face with tabular digits (Inter, Segoe UI Variable, IBM Plex Sans, Source Sans) rather than a monospace face — monospace forces the *letters* to full-width too, costing roughly 12–18% horizontal space in mixed alphanumeric columns like 'Holder name' (that percentage is my estimate, low-medium confidence; measure in the chosen face). Reserve true monospace for code/expression editors and the raw filing viewer. Negative numbers: use U+2212 MINUS SIGN, not U+002D HYPHEN, because hyphen renders at a different width and vertical position in most faces and breaks decimal alignment. Convention split: P&L and market data use signed minus + colour + glyph; financial statements use accounting parentheses (1,234) because that is what the filing itself uses and the user is cross-checking against the source. Thousands separator: U+2009 THIN SPACE in dense grids to reclaim ~3px per group, full locale separator in reports and exports.

**Why it matters.** Decimal misalignment is the highest-frequency, lowest-cost bug in financial UI. It destroys the pre-attentive scan of magnitude down a column, which is the entire reason a grid exists. Getting tnum + a real minus sign + right-alignment-on-decimal correct is worth more than any chart feature.

- https://developer.mozilla.org/en-US/docs/Web/CSS/font-variant-numeric

### 16. FX price rendering: the three-tier big-figure / pip / pipette convention (spec, medium confidence on convention details)  
`confidence: medium`

Standard FX quoting: most pairs 5 decimals (e.g. EURUSD 1.08543) where digits 1-2 after the point are the 'big figure', digit 4 is the pip, digit 5 is the 'pipette' (1/10 pip). JPY pairs quote to 3 decimals (e.g. USDJPY 147.235) where digit 2 is the pip and digit 3 the pipette. Rendering spec: render as three type sizes within one baseline — big figure at 1.0em / 65% opacity (it rarely changes and is visual noise), pip digits at 1.35em / 700 weight / full opacity (this is what the eye tracks), pipette at 0.75em raised toward the cap line at 55% opacity. Spread displayed in pips to one decimal (e.g. '0.6'), never in price units. Bid and ask stacked or side-by-side with the changing digits aligned on a shared decimal grid so the pip digits sit in a fixed x-position across all rows regardless of big figure length — this requires per-instrument column templates, not a single number formatter. Confidence: the quoting convention is high confidence; the specific opacity/size ratios are my design recommendation, not an industry standard.

**Why it matters.** A generic number formatter applied to FX makes an FX board unreadable to an FX trader — this is the fastest way to signal 'built by someone who has not traded FX'. It is also a genuine speed feature: the eye locks to a fixed pip column and reads change without parsing the whole number.

- model prior knowledge; convention widely documented by FX brokers

### 17. Dark theme is not free: the evidence says light mode wins for sustained reading, so dark must be engineered  
`confidence: high`

Verified NN/g (fetched 2026-08-24): for users with normal or corrected vision, light mode consistently outperforms dark mode; positive contrast polarity (dark text on light) yields better visual acuity and proofreading results, and the advantage grows as font size shrinks; for glanceable tasks light mode was superior, and 'during nighttime, light mode led to better performance'. Mechanism: light backgrounds contract the pupil, reducing spherical aberration and increasing depth of field. Users with cataracts/cloudy ocular media read better in dark mode. NN/g: 'At this point we don't recommend switching to dark mode by default' for general audiences, but do provide the toggle. Long-term counterpoint noted: sustained light-mode exposure is associated with choroid thinning, a marker linked to myopia.

**Why it matters.** Adversarial conclusion a naive plan misses: dark theme is right for the *live monitoring* surfaces (glance, low ambient light, long sessions, less eyestrain from a wall of bright panels) and wrong for the *reading* surfaces (filings, transcripts, AI long-form answers, research notes). The correct design is a per-surface theme: dark chrome and dark grids, but a light 'paper' reading pane for documents and AI prose — and a light print/PDF export. Also: because dark mode degrades small-text acuity, dark-theme body text must be larger or higher-contrast than its light-theme equivalent, not merely inverted.

- https://www.nngroup.com/articles/dark-mode/

### 18. Trading-journal products define the behavioural-design vocabulary we should adopt wholesale  
`confidence: high`

TraderVue (fetched 2026-08-24): 80+ platform integrations (TradeStation, Ameritrade, Interactive Brokers, Lightspeed); notes system to 'record past trading habits'; setup tagging ('breakouts, VWAP bounces, hammer candlestick entries — and see which ones actually pay you'); MFE/MAE analysis expressed as 'Exit Performance as a % vs your Best potential exit P&L'; auto-generated price charts per trade from weekly down to 1-minute with entry/exit marked; surfaces are Dashboard, Trades, Reports, Analytics, Calendar, Journal, Filters, Automatic reports. Edgewonk (fetched 2026-08-24): '50+ unique data reports' in a Chart Lab; a Psychology Lab containing mistake tracking, trade checklists, review cards and an integrated diary; an 'Edge Finder' that 'scans your journal to uncover strengths, weaknesses, and the biggest opportunities to improve'; a Strategy Lab/simulator for testing exit strategy, trade duration and management variations; 200+ broker imports; 14-day refund.

**Why it matters.** Three transferable primitives: (1) TAGS AS THE ANALYTIC UNIT — the journal only produces insight if setups are tagged, so tagging must be one keystroke at capture time, not a form; (2) MFE/MAE as the exit-quality lens — 'you left 62% of the move on the table on your breakout trades' is the single most behaviour-changing statistic a journal produces; (3) an automated 'Edge Finder' pass — the user will not run their own analysis, so the system must volunteer the finding. Our AI layer is the natural Edge Finder.

- https://www.tradervue.com/
- https://edgewonk.com/

### 19. PROPOSED COMMAND GRAMMAR (design deliverable)  
`confidence: high`

PRIMARY LINE (always focused on Ctrl+Space or when no panel claims the key): object-first, whitespace-delimited, case-insensitive.
FORM: <identifier> [<class>] <function> [<args>] ⏎
  identifier: ticker | ticker+MIC (RIO LN, 7203 JT) | ISIN | SEDOL | FIGI | CUSIP | FX pair (EURUSD, EUR/USD, EURJPY) | index (SPX, UKX) | free text -> resolver
  class (optional, inferred if unambiguous, hard-set by function keys): EQ | FX | IDX | ETF | FUT | RATE
  function: 2-5 char mnemonic from the catalogue
  args: function-specific, e.g. `AAPL EQ GP 5Y W` or `AAPL EQ INS 24M CODE=P`
EXAMPLES: `AAPL EQ OWN` · `RIO LN EQ SI` · `EURUSD FX GP 1H` · `AAPL EQ PAY` · `SPX IDX MAP` · `NI CENTRALBANK`
REVERSE ORDER ACCEPTED: `OWN AAPL` parses and normalises, with a ghost-text rewrite shown before ⏎ ('→ AAPL US EQ OWN') so the user learns the canonical order without being punished. This is the single biggest fix to Bloomberg's learning cliff.
PALETTE (Ctrl+K) — one input, sigil namespaces:
  (none)  symbol resolver / recents
  >       verb commands ('>save layout', '>export csv', '>toggle CVD palette')
  @       function mnemonics with descriptions ('@own', '@si') — the discoverable form of the mnemonic catalogue
  #       named layouts and workspaces ('#premarket')
  /       screener / query DSL ('/mktcap>2e9 and short_pct_float>0.15')
  !       alert authoring ('!AAPL px < 180')
  ~       natural-language question to the AI layer ('~who has been selling AAPL and why')
  ?       command catalogue / help, and lists every sigil
  :       jump to row N in the focused grid
AFFORDANCES: (a) inline ghost-text completion of the next token only, never the whole line; (b) a persistent 20px GRAMMAR BAR under the input rendering the parse as chips [AAPL]·[US]·[EQ]·[OWN] with the ambiguous token highlighted; (c) did-you-mean via Levenshtein<=2 over the mnemonic catalogue PLUS a hand-authored synonym table (holders/shareholders/13f -> OWN; shorts/borrow/squeeze -> SI; insiders/form4/pdmr -> INS; pay/comp/proxy/def14a -> PAY; buybacks/dilution -> DIL); (d) user aliases with a leading dot ('.pm' -> open Pre-Market layout; '.a' -> AAPL US EQ); (e) history on Ctrl+Up/Down within the line, `HIST` for the last 200 commands as a searchable grid; (f) EVERY panel header shows the exact command string that produced it, and clicking it copies the command — this is how mnemonics become learnable by osmosis.
MNEMONIC CATALOGUE (initial): DES GP GIP HP RV COMP EQS MAP FA EE ANR ERN CAL — OWN HDS 13F INS INSX SI SBL PAY EXEC GOV DIL BUYB CACS DVD SPLT LOCK POL LOB — CF NI TOP BI — FXC FXP CARRY COT ECO WEI — ALRT W LAY CAT DIAG SET — AI KB JRNL PM LOG RVW BIAS.

**Why it matters.** This resolves the central tension in the brief: professional speed (mnemonic, object-first, no mouse) versus discoverability (fuzzy, described, forgiving). Both live in one input with distinct namespaces, and the ghost-rewrite converts every wrong-order attempt into a lesson rather than an error.

- https://en.wikipedia.org/wiki/Bloomberg_Terminal
- https://code.visualstudio.com/docs/getstarted/userinterface
- design synthesis

### 20. PROPOSED KEYBOARD MAP (design deliverable) — global chords, panel-context single keys, no-mouse audit  
`confidence: high`

MODES: NORMAL (default; single keys act on the focused panel) and INSERT (any text field). Optional VIM mode toggled in settings — off by default, because chord memory is already the tax and vim bindings collide with j/k row nav expectations.
GLOBAL (Ctrl-based, work from anywhere):
 Ctrl+Space focus command line · Enter = GO · Esc clear line · Esc Esc return focus to panel
 Ctrl+K fuzzy palette · Ctrl+G go-to-symbol only · Ctrl+Shift+F global document search
 Ctrl+1..9 focus panel N · Ctrl+Tab / Ctrl+Shift+Tab cycle panels · Alt+1..9 switch named layout
 Alt+Left / Alt+Right navigate panel history back/forward (per-panel command stack, Bloomberg MENU equivalent)
 Ctrl+N new panel · Ctrl+D duplicate panel with same symbol · Ctrl+W close · Ctrl+Shift+T reopen closed
 Ctrl+Shift+S save layout · Ctrl+Shift+O open layout · Ctrl+Shift+P pin panel always-on-top (Launchpad equivalent)
 Ctrl+Alt+0..6 assign link channel (0 = unlinked; 1-6 = channel colours) · Ctrl+L toggle link on/off
 F11 maximise/restore focused panel · Ctrl+Shift+Enter tear panel off to its own window
 Alt+P FREEZE all live updates (WCAG 2.2.2) — status rail turns amber and shows the freeze timestamp
 Ctrl+M mute all sound instantly (panic key, single keystroke, no confirm) · Ctrl+Shift+M DND 15 min
 Ctrl+Shift+A new alert from current context · Ctrl+Shift+N alerts centre
 Ctrl+J journal quick-capture (captures symbol, panel command, chart snapshot, timestamp) · Ctrl+Shift+J full journal
 Ctrl+/ toggle PROVENANCE MODE (every number gains a dotted underline; click or Enter opens the source)
 Ctrl+E export focused grid · Ctrl+Shift+C copy with provenance footnote · Ctrl+P print-preview in light theme
 F5 refresh focused panel · Shift+F5 refresh all · Ctrl+Shift+D cycle density (Comfortable/Compact/Dense)
 Ctrl+= / Ctrl+- / Ctrl+0 font scale up/down/reset (must reach 200%) · Ctrl+, settings
 F1 context help · F1 F1 CHEAT-SHEET OVERLAY (context-aware: shows the focused panel's keys) · Ctrl+Shift+K full keyboard map
 Ctrl+Shift+V announce focused cell to screen reader (explicit, on-demand speech)
CHART PANEL (single keys, NORMAL mode): type an interval directly ('5m','1h','1D','1W' then ⏎) · ←/→ pan, Shift+←/→ fast pan · +/- zoom time · Home/End first/last bar · L log/linear · % percent scale · C compare symbol · I indicator palette · T measure tool · H horizontal line at cursor · V vertical line · F fib · N text note · Ctrl+Z/Ctrl+Y undo/redo drawings · A alert at cursor price · R enter REPLAY (then Space play/pause, . step forward, , step back, 1-5 speed, Esc exit)
GRID / BLOTTER: ↑↓ or j/k row · PgUp/PgDn page · Home/End first/last row · Enter push row to linked detail panel · Space multi-select · / filter-as-you-type on focused column · s sort asc/desc, Shift+s add to multi-sort · Ctrl+Shift+C column chooser · Alt+←/→ move column · g group by focused column · b add row to watchlist · x expand row detail inline
OWNERSHIP/INSIDER PANELS: 1-4 switch view-set · f cycle transaction-code filter (All / Open-market only / Exclude 10b5-1 / Exclude tax-withholding) · c toggle cluster-buy overlay · Enter open the underlying filing
ALERTS LIST: e edit · d disable · x delete · s snooze then 5/1/6/d for 5m/15m/60m/rest-of-day · a acknowledge · Shift+A acknowledge all visible
NO-MOUSE AUDIT (acceptance criterion): every screen in the inventory must be fully operable with the above map; the test script is 'from a cold start, reach and read each of the 40 screens, author one alert, log one journal entry, run one screen and export it, without touching the pointer'. Any screen failing this is a defect, not a backlog item.
CONFLICT RULES: Ctrl+chords are global and are never overridden by a panel; single keys belong to the focused panel; Alt+ is reserved for layout/session-level actions; F-keys are reserved for help/refresh/maximise and are NOT used for asset class (unlike Bloomberg) because a Windows app cannot own F2-F12 reliably across screen readers and IMEs — asset class is instead a command-line token.

**Why it matters.** A keyboard map is a contract, and its two failure modes are collisions and invisibility. The three-tier discipline (Ctrl = global, single = panel, Alt = session) makes collisions structurally impossible, and F1-F1 makes the map visible exactly where it is needed.

- design synthesis grounded in the Bloomberg/VS Code/TradingView/NinjaTrader patterns above

### 21. PROPOSED SCREEN INVENTORY (design deliverable) — 40 screens in 8 groups  
`confidence: high`

SHELL: 1 Frame (command bar, context ribbon, panel grid, status rail) · 2 Today/Home (session brief, calendar, map, AI overnight note) · 3 Layout Manager (LAY) · 4 Command Catalogue (CAT) · 5 Cheat-Sheet Overlay · 6 Settings (Data & entitlements / Colour & theme / Keyboard / Accessibility / Privacy) · 7 Data Health & Diagnostics (DIAG) · 8 Provenance Drill-Through Overlay.
MARKET DATA & CHARTING: 9 Chart (GP) · 10 Intraday + Tape (GIP) · 11 Historical Price Table (HP) · 12 Relative Value / Comps (RV) · 13 Comparative Returns (COMP) · 14 Heatmap (MAP) · 15 Watchlist/Monitor (W) · 16 Screener (EQS) · 17 Depth/Liquidity view (read-only ladder, if L2 entitled).
COMPANY CORE: 18 Overview/Description (DES) · 19 Fundamentals (FA) · 20 Estimates & Revisions (EE) · 21 Analyst Recommendations (ANR) · 22 Earnings Cockpit (ERN) · 23 Filings Browser (CF) · 24 News & Sentiment (NI/TOP) · 25 Industry Primer (BI).
INCENTIVES & INSIDERS (the pillar): 26 Ownership Summary (OWN) · 27 Holders Detail & 13F Flow (HDS) · 28 Insider Transactions (INS) · 29 Insider Signals / Cluster Detector (INSX) · 30 Executive Compensation & Pay-for-Metric Map (PAY) · 31 Governance & Board (GOV) · 32 Short Interest & Borrow (SI/SBL) · 33 Dilution, Buybacks & Share Count (DIL) · 34 Corporate Actions (CACS) · 35 Politician / Lobbying / Gov Contracts (POL).
FX: 36 FX Session Board (FXC) · 37 FX Pair Deep Dive (rate differential, carry, COT positioning, session ranges).
AI KNOWLEDGE LAYER: 38 Ask (AI) with mandatory Sources pane · 39 Knowledge Base Browser & Diff (KB).
DECISION DISCIPLINE: 40 Journal / Thesis (JRNL) · 41 Pre-Mortem & Checklist (PM) · 42 Decision Log (LOG) · 43 Post-Trade Review (RVW) · 44 Bias Dashboard (BIAS) · 45 Position Ledger (manual, no broker link).
ALERTING: 46 Alerts Centre (feed + rules) · 47 Alert Author (three-lane).
STATE KIT: 48 Empty/Error/Degraded state library (nine named states, see separate finding).
(Numbering exceeds 40 because the pillar group is deliberately over-specified; screens 26-35 and 38-44 are where the product differentiates and each deserves its own comp.)

**Why it matters.** The inventory makes explicit that this is not 'a charting app with extras'. Ten of the screens are ownership/incentive forensics and seven are decision discipline — that ratio is the product thesis expressed as information architecture, and it should drive the default layout set.

- design synthesis

### 22. MOCKUP SPEC — Shell / Frame (pixel-level, drawable without further questions)  
`confidence: high`

Target: 2560x1440 primary at 100% scale as the design baseline; must survive 1920x1080@100%, 3840x2160@150%, and per-monitor DPI v2 mixed-DPI setups. Minimum window 1440x900.
ROW 0 — COMMAND BAR, height 32px, background #171B22, 1px bottom hairline #2A313B. Left 8px pad, 16px app glyph, 12px gap. COMMAND INPUT: 560px wide, 24px tall, background #0E1116, 1px border #2A313B, 4px radius, 13px text with tnum/lnum/zero, caret 2px #E6EAF0, ghost completion text at 40% opacity. Immediately right, 12px gap, GRAMMAR BAR: parsed chips, each 20px tall, 6px horizontal pad, 3px radius, background rgba(255,255,255,0.06), 11px uppercase text, 4px gaps, with the currently-editing token carrying a 2px bottom border in accent #7AA2F7; a trailing '⏎' glyph at 40%. Right cluster, right-aligned with 8px pad: global-search glyph (16px), bell glyph with a 14px circular unread badge (badge background = P1 colour, text 10px), DND toggle (moon glyph, amber when active), CLOCKS as two stacked 10px lines 'NY 14:32:07' / 'LON 19:32:07' with tnum, CONNECTION PILL (56x18px, 3px radius: green dot + 'LIVE' | amber dot + 'DEGRADED' | grey dot + 'FROZEN').
ROW 1 — CONTEXT RIBBON, height 26px, background #12151A, shown only when a symbol is in scope. Contents left to right, all vertically centred, 8px gaps: ticker 14px/700; venue chip 10px ('US','LN','JT'); company name 12px at 65% opacity, truncating with ellipsis; LAST PRICE 18px/700 tabular, coloured by direction, preceded by a 8px ▲/▼ glyph; change absolute and percent, 12px tabular, same colour, percent in parentheses; SESSION CHIP (PRE / OPEN / POST / CLOSED / HALTED) 10px uppercase on a 16px pill; DATA-QUALITY CHIP (RT / D15 / D20 / EOD) 10px on a 16px pill, amber when delayed, with the exact as-of appended '· 14:31:58'; currency code; 64x16 sparkline (session, baseline at prior close as a 1px 30%-opacity line, last point a 3px dot); far right an 'i' glyph opening provenance.
BODY — PANEL GRID. Default 2x2 tiles, 1px gutters #2A313B, resizable by dragging the gutter (8px hit zone, cursor changes, 24px min drag target per SC 2.5.8 spacing exception). Layouts may declare arbitrary splits (2x2, 3x2, 1+3, 4x1, 60/40 vertical). Each TILE: header 24px, background #1E232B; left 6px pad; LINK-CHANNEL CHIP 8x8px square with 1px radius (channel colours below) or an empty 8x8 outline if unlinked; 6px gap; MNEMONIC BADGE 11px/700 uppercase on rgba(255,255,255,0.08), 4px pad, 3px radius; 6px gap; title 12px; flexible spacer; AS-OF STAMP 10px tabular at 55% opacity ('as of 14:31:58'); 8px gap; overflow '⋯' 16px button in a 24x24 hit box. Tile body has zero padding — content owns its own gutters, because every 8px of padding is a row lost.
STATUS RAIL — bottom, height 22px, background #171B22, 1px top hairline. Left: provider health as fixed-width segments, each 'NAME ● latency-or-age', e.g. 'EQ ● 42ms  FX ● 18ms  FILINGS ● 3m  KB ● 06:00Z'; each is a 24px-tall click target opening DIAG. Centre: TOAST DOCK — transient messages render here (not floating over content) as a single 18px line, max 1 at a time, 4s dwell, with a 2px left bar in the priority colour. Right: layout name, density mode glyph, keyboard mode ('NORM'/'VIM'), and a 40x8px CPU/frame micro-gauge.
LINK CHANNEL COLOURS (must be perceptually distinct from every directional colour and from each other under deuteranopia): C1 #E5C07B amber, C2 #C678DD purple, C3 #56B6C2 teal, C4 #E06C75 rose, C5 #98C379 sage, C6 #ABB2BF slate. Directional colours are drawn from the CVD-safe pair and never reused as channel colours.
DENSITY LADDER: Comfortable = 28px rows / 13px text / 8px cell pad; Compact (DEFAULT) = 22px rows / 12px text / 6px pad; Dense = 18px rows / 11px text / 4px pad. All row heights even so 1px hairlines land on device pixels at 100% and 200%.

**Why it matters.** This is the frame every other comp inherits. The two non-obvious decisions: as-of stamp lives in the tile header (not a tooltip) so staleness is never hidden, and the toast dock is in the status rail rather than floating, because floating toasts over a blotter occlude exactly the rows you were reading — and would also violate SC 2.4.11 if they covered a focused element.

- design synthesis; WCAG 2.2 constraints as cited

### 23. MOCKUP SPEC — Ownership (OWN) and Holders Detail (HDS)  
`confidence: high`

OWN, three columns in a 1200x700 tile.
LEFT RAIL 280px: 'CONCENTRATION'. No donut. A single 100%-width horizontal stacked bar, 14px tall, 2px radius, segments in fixed order: Insiders / Strategic & corporate / Index & passive / Active institutions / Other float; each segment labelled below in a 5-row list, each row = 8x8 colour chip + label 11px + percentage 11px/700 tabular right-aligned at 100px + share count 11px tabular right-aligned at 180px. Beneath, a 3-row KPI stack: 'Institutional ownership 71.4% (Q2 2026)', 'Top-10 concentration 34.2%', 'Float 15.28bn'. Beneath that a 'Concentration risk' callout box only when top-10 > 40% or a single holder > 10%.
CENTRE (flex) 'HOLDERS': virtualised grid, 22px rows, ~26 rows visible. Columns with fixed widths: Holder (220, left, frozen) | Type (72) | Shares (96, right, tabular) | Δ Shares QoQ (120, right, with an inline diverging bar occupying the left 44px of the cell, zero-centred, CVD-safe blue/orange) | % O/S (64, right) | Δ % O/S (64, right) | % of holder's AUM (80, right) | Value (96, right, 3 sig figs + unit) | Filed (76, date) | Src (32, filing-type glyph, click opens the 13F). Sticky pinned first row = 'TOTAL 13F' aggregate. Right-click header = column chooser; view-set tabs above the grid: [Summary] [Flow] [Activists] [Index vs Active] [Custom].
RIGHT RAIL 320px 'FLOW': (a) 8-quarter stacked column chart, 140px tall, net institutional buys above axis / sells below, x-labels 'Q3-24 … Q2-26'; (b) two lists side by side, 'NEW POSITIONS' and 'EXITED', 6 rows each, holder name + share count; (c) 'ACTIVIST & 13D/G' list of any Schedule 13D/G filers with filing date and stated purpose snippet.
FOOTER STRIP, full width, 26px, background rgba(255,180,0,0.08), amber 2px left bar: '13F positions are filed up to 45 days after quarter end and cover only long US-listed equity positions of managers with >$100m in 13(f) securities. Latest complete quarter: Q2 2026 (deadline 2026-08-14). 4,812 filers processed. Short positions, swaps, derivatives and non-US holdings are NOT represented.' This strip is structural and non-dismissible — it is the single most important honesty affordance in the product.
HDS is the same grid at full tile width with the left and right rails collapsed, plus a holder-detail flyout (Enter on a row): the holder's full portfolio, their history in this name across 12 quarters as a small multiples sparkline row, and their turnover/concentration stats.

**Why it matters.** Ownership panels in retail tools present 13F as if it were live ownership. Making the 45-day lag and the long-only US-equity-only scope permanently visible is both an accuracy requirement and, for this user, a competitive advantage: it is the difference between a data display and an analyst's tool.

- design synthesis; scope/lag facts are widely documented SEC 13F rules — medium confidence on the exact $100m threshold wording, verify before shipping copy

### 24. MOCKUP SPEC — Insider Transactions (INS) and Insider Signals (INSX): the transaction-code intelligence that makes or breaks the panel  
`confidence: high`

TOP STRIP 130px 'PEOPLE TIMELINE': x-axis = trailing 24 months (or the selected window), y-axis = one 16px row per insider, sorted by total net value. Each transaction is a mark centred on its date: FILLED SQUARE = open-market purchase (code P); HOLLOW SQUARE = open-market sale (code S); TRIANGLE-UP = option exercise (M); DIAMOND = award/grant (A); SMALL BAR = tax withholding (F); CIRCLE = gift (G). Mark width scales with log10(value), clamped 4-14px. Colour: purchases in the up-colour, disposals in the down-colour, non-discretionary codes (A, F, M-without-sale) in neutral #6C7887 — this neutral treatment is the whole point. Vertical guide lines mark earnings dates (1px, 25% opacity, labelled 'Q2' etc.). Hover shows a 200px tooltip with the accession number.
MAIN GRID (22px rows): Date | Filer | Role (CEO/CFO/Dir/10%) | Code | Shares | Price | Value | Post-txn holding | Δ% of holding (with inline diverging bar) | Days from earnings (signed) | 10b5-1? (Y/N/date adopted) | Filing lag (days, amber if >2 business days) | Accession (link glyph). Default filter EXCLUDES codes A, F and M-without-disposition, and the filter state is rendered as a removable chip above the grid ('Excluding: awards, tax withholding' ×) — never a hidden default.
RIGHT RAIL 300px 'SIGNALS' (this is INSX inline): stacked cards, each 88px — (1) CLUSTER BUY: '3 insiders bought within 21 days · combined $4.2m · last cluster 2024-11' with a mini timeline; (2) CONVICTION: CEO/CFO open-market purchases as a % of their holding and as a multiple of their annual salary; (3) 10b5-1 CONTEXT: plan adoption dates plotted against subsequent price, flagging adoptions within 30 days of a material event; (4) SALE CLASSIFICATION: donut-free 100% bar splitting the trailing-12m disposal value into Discretionary / Plan / Tax-withholding / Gift; (5) FILING-LAG ANOMALY: any filing beyond the 2-business-day Section 16 deadline.
JURISDICTION ROUTER: when the symbol is non-US the panel header swaps the badge and the copy — for a UK issuer it reads 'PDMR notifications, MAR Article 19 (RNS)' with columns Date | PDMR | Nature of transaction | Volume | Price | Venue | Notification date; for Japan, the applicable disclosure regime; and where no equivalent disclosure exists, the empty state names the regime rather than showing 'no data'.

**Why it matters.** Naive insider panels are a false-signal machine because ~most reported disposals are automatic (10b5-1 plans, code F tax withholding on vesting, code M exercises). Neutral-colouring non-discretionary codes, defaulting the filter to exclude them, and surfacing 10b5-1 adoption dates is the entire alpha of the panel — and the jurisdiction router is what makes 'global equities' a truthful claim rather than a US product with foreign tickers.

- design synthesis; Section 16 / Form 4 transaction codes and MAR Art.19 PDMR regime are standard — medium confidence on the 2-business-day deadline wording, verify before shipping copy

### 25. MOCKUP SPEC — Executive Compensation & Pay-for-Metric Map (PAY): 'who is paid to make the number'  
`confidence: high`

TOP 200px 'PACKAGE WATERFALL': horizontal waterfall for the named executive (selector chip row above: CEO | CFO | COO | +3), bars in fixed order Salary → Cash bonus (with a ghost bar behind showing target) → PSU (target) → PSU (actual earned) → RSU → Options (Black-Scholes as reported) → All other. Each bar 24px tall, value label right of the bar in tabular figures, percent-of-total below in 10px at 55%. A second, thinner ghost series behind each bar shows the prior year for instant YoY read.
MIDDLE 'METRIC MAP' — the differentiating table. Columns: Metric | Weight % | Definition (GAAP / Adjusted / Non-financial) | Threshold | Target | Maximum | Actual | Payout % | 3y trend sparkline | Link. One row per plan metric (typical: Adjusted EPS, Revenue growth, ROIC, FCF, relative TSR, ESG/strategic). The 'Definition' cell is a chip: green-neutral 'GAAP', amber 'ADJUSTED', grey 'QUALITATIVE'. Every 'ADJUSTED' chip expands to show the reconciliation bridge from the GAAP figure with the size of each add-back — and flags in amber when total add-backs as a % of GAAP earnings have grown for 3+ consecutive years. The 'Link' cell jumps the FA panel to the same line item so the user can verify against the statements in one keystroke. Below the table, a one-line verdict strip: 'Payout is 78% driven by metrics management can adjust.' (computed as the weight-sum of ADJUSTED + QUALITATIVE metrics).
RIGHT RAIL 300px: (a) PEER GROUP list from the proxy, with a red flag icon on any constituent added or removed versus the prior proxy, and a computed 'peer group median pay percentile'; (b) VESTING CLIFF CALENDAR — next 8 quarters, one 12px bar per executive per quarter showing shares scheduled to vest, overlaid with a 1px marker line at each historical post-vest sale so the user can see 'this person always sells on vest'; (c) ALIGNMENT card: shares owned outright vs unvested awards vs options, and ownership as a multiple of salary against the company's stated guideline.
FOOTER: 'Source: DEF 14A filed 2026-04-11 (accession 0000320193-26-000045). Compensation figures are Summary Compensation Table as-reported; equity valued at grant-date fair value, not realised value.'

**Why it matters.** This screen has no direct retail equivalent and is the sharpest expression of the product thesis. The two insights that make it more than a proxy-statement viewer are (1) classifying each plan metric as GAAP vs Adjusted vs Qualitative and computing the 'manipulable share' of the payout, and (2) the vesting-cliff-versus-historical-sale-behaviour overlay, which converts compensation disclosure into a forward-looking supply forecast.

- design synthesis; Quiver Quantitative confirms Executive Compensation as a saleable dataset

### 26. MOCKUP SPEC — Screener (EQS), AI Ask (AI), and Alerts Author  
`confidence: high`

SCREENER. Left rail 300px, criteria stack: each criterion a 28px row = [field combobox 130px][operator 56px][value 90px][× 24px]; a 'ƒx' toggle at the rail top swaps the whole rail for a monospace expression editor showing the equivalent DSL with syntax highlighting and inline error underlining: `mktcap > 2e9 and insider_net_buy_90d > 0 and short_pct_float > 0.15 and pay_adjusted_weight > 0.5`. The two views round-trip losslessly; anything expressible in the builder is expressible in the DSL and vice-versa. Top bar 32px: universe chips (US · DM · EM · S&P500 · FTSE350 · MyList) with an editable count, a live result counter animating '1,284 → 37', view-set dropdown, Save, Share (exports the DSL as text, not a link), Export. Grid: virtualised, 22px rows, first two columns (Ticker, Name) frozen; per-column conditional formatting configured from the header menu with three modes — Data bar (in-cell, left-anchored, single hue), Colour scale (must use a CVD-safe sequential ramp AND pass a greyscale check, which the picker enforces by showing a desaturated preview), Icon set (▲▬▼). Bottom strip 26px: SCREEN PROVENANCE — 'Fundamentals as of 2026-08-23 21:00Z · Short interest as of 2026-08-15 settlement, published 2026-08-25 · Insider: live Form 4 feed · Effective as-of: 2026-08-15' — the effective as-of is always the SLOWEST input, stated explicitly.
AI ASK. Vertical split 62/38. TOP: conversation, user turns right-aligned in a 70%-width bubble, assistant turns full-width on a LIGHT 'paper' surface (#F7F8FA background, #1A1D23 text) because this is a reading surface (see dark-mode finding). Every number in assistant prose renders as a CITATION CHIP: the number, then a superscript source index in a 14px rounded chip; hovering highlights the corresponding source card; clicking navigates the linked panel to the underlying row. Any number the model emits without a resolvable source gets a dotted red underline and a ⚠ glyph, and the composer shows a persistent 'N unsourced figures' counter. BOTTOM 'SOURCES' pane: never collapsible while an answer is on screen; horizontally scrolling row of 260x120px cards, each = doc-type glyph + title + date + the exact quoted span (2 lines, monospace, on a tinted background) + actions [Open] [Pin to journal]. ABOVE THE COMPOSER: KB FRESHNESS BAR, 22px — 'Knowledge base authored by Claude · last run 2026-08-24 06:00Z · 1,842 notes · 37 updated in 24h · 512 tickers covered · next run 06:00Z' with a 'diff' link to the KB browser. COMPOSER: mode chips [Ask] [Explain this screen] [Devil's advocate] [Pre-mortem] [Summarise filing] [Find the disconfirming evidence].
ALERT AUTHOR. Three lanes, all visible simultaneously in one 720x480 modal. Lane 1 (top, 80px): natural-language box, placeholder 'e.g. any officer of a company on my watchlist sells more than 20% of their stake'. Lane 2 (middle, 240px): the COMPILED RULE TREE rendered as an indented, editable outline — WHEN [entity: insider transaction] / WHERE [role ∈ {CEO,CFO,Officer}] AND [symbol ∈ Watchlist:Core] AND [Δ% of holding < -20%] AND [code ∉ {A,F,M}] / EVALUATE [on filing arrival] / THROTTLE [max 5 per day]. Lane 3 (bottom, 80px): the expression form, monospace, editable. Editing any lane recompiles the other two; a lane that cannot represent the current rule is greyed with a reason. Right rail 200px: PRIORITY selector (P1 Critical / P2 Attention / P3 Log) with a plain-English consequence line under each ('P1 interrupts: modal toast + sound + Windows notification'), CHANNELS checklist, QUIET HOURS, SESSION SCOPE (pre / regular / post / closed), EXPIRY, and a live 'BACKTEST' readout: 'This rule would have fired 11 times in the last 90 days' — the single best fatigue-prevention affordance, because it makes noise visible before it happens.

**Why it matters.** Three patterns generalise: (1) builder↔expression round-tripping means the tool never traps a power user behind a UI; (2) the mandatory Sources pane plus unsourced-number warnings is the only way an AI layer earns and keeps trust in a domain where a wrong number is expensive; (3) alert backtest-before-save converts alert fatigue from a support problem into a design-time decision.

- design synthesis; grounded in Finviz view-sets, TradingView alert channels, AlphaSense sentence-level citations

### 27. MOCKUP SPEC — FX Session Board (FXC) and FX pair deep dive  
`confidence: medium`

FXC BOARD: a matrix grid, majors down the rows and a fixed column set across: Pair | Bid | Ask | Spread(pips) | Δ pips today | Δ% | Session range bar | ATR(14) | Position in 20-day range | Next event. The BID and ASK cells use the three-tier renderer: big figure 12px/65% opacity, pip digits 16px/700, pipette 9px raised/55%; critically, the PIP DIGITS OF EVERY ROW ARE X-ALIGNED because each instrument has its own column template — EURUSD (5dp) and USDJPY (3dp) must place their pip digit at the same x. SESSION RANGE BAR: 120x14px, showing the day's low-high as a track with a 2px marker at current, plus 1px ghost markers at Tokyo/London/NY session opens and a 30% band showing the 20-day average range for scale. Row background carries a 2px left edge-bar whose opacity encodes tick intensity (the flash-governor degradation) rather than flashing.
SESSION RIBBON above the grid, 20px: a 24-hour horizontal timeline with Sydney/Tokyo/London/New York bands as overlapping translucent blocks, a 'now' playhead, and the 17:00 New York day-boundary marked with a labelled 1px line — because FX has no single close and 'today' is otherwise a lie.
PAIR DEEP DIVE: 2x2 — (top-left) chart; (top-right) INTEREST RATE DIFFERENTIAL: two policy-rate step lines plus the differential as a filled area, with the implied carry in pips/day and annualised %; (bottom-left) POSITIONING: CFTC COT non-commercial net as a 3-year z-score histogram with the current bar highlighted, plus its as-of date and the 'reported Friday for Tuesday' lag stated in the footer; (bottom-right) EVENT LADDER: the next 10 scheduled releases for both currencies with consensus, prior, and the historical average absolute pip move in the 15 minutes after that release type.

**Why it matters.** Everything on this screen is a thing generic tools get wrong: pip alignment across differing decimal conventions, the absence of a real 'day' in FX, and COT's two-stage lag. Getting these right is what makes an FX trader believe the rest of the terminal.

- design synthesis; FX quoting and COT release conventions from prior knowledge — verify COT release timing before shipping copy

### 28. MOCKUP SPEC — Decision discipline suite (JRNL / PM / RVW / BIAS): designing against the user's own biases  
`confidence: high`

QUICK CAPTURE (Ctrl+J from anywhere), 480x320 modal, opens with focus in the note field and auto-captures: symbol in context, the exact command string of the focused panel, a PNG snapshot of that panel, UTC + venue-local timestamp, and the current price with its as-of. Fields: note (multiline), TAGS (token input with autocomplete over the user's tag vocabulary — one keystroke per tag, this is the analytic unit), and a 1-5 conviction stepper bound to keys 1-5. Ctrl+Enter saves; total interaction target under 6 seconds.
THESIS CARD (full JRNL): Symbol · Direction · Conviction 1-5 · Horizon · ENTRY CONDITIONS · INVALIDATION CONDITIONS (MANDATORY — the Save button is disabled with the inline reason 'A thesis without an invalidation condition is a hope') · Size rationale · Expected value / asymmetry · 'What would make me wrong'. Each condition row can be promoted to an ALERT with one click, which is the mechanism that makes the discipline self-enforcing rather than aspirational.
PRE-MORTEM (PM): a single forced prompt — 'It is [today + horizon]. This position is down 30%. Write the story of how that happened.' Free text, soft minimum 200 characters shown as a filling progress bar rather than a hard block. Beneath, three AI-assisted prompts from the KB: 'Three things the bears say', 'The last three times this setup failed in your journal', 'The disconfirming filing you have not read'. Then a CHECKLIST pane: user-authored per-setup checklists in two Gawande modes — READ-DO (each item must be ticked in order, for execution) and DO-CONFIRM (tick at the end, for research). Checklist items support a 'hard stop' flag that blocks the thesis from being marked Active.
POST-TRADE REVIEW (RVW): triggered automatically 72h after a position is closed in the manual ledger; cannot be dismissed, only deferred twice. Layout: left = the chart with entry/exit/invalidation-level annotations and the MFE/MAE shading; right = the original thesis text rendered read-only beside a 'what actually happened' composer. Bottom: the RESULTING 2x2 — a 240x240 grid with axes Process (poor↔good) and Outcome (bad↔good); the user places a single marker; the four quadrants are labelled 'Deserved loss', 'Bad luck', 'Dumb luck', 'Deserved win'. This one control does more to break outcome bias than any amount of statistics.
BIAS DASHBOARD: six computed metrics as 180x120 cards, each with a 90-day sparkline and a plain-English definition on hover — RECENCY (correlation between conviction score and the symbol's trailing 5-day return at time of entry), CONFIRMATION (share of sources opened in the AI panel whose stance agreed with the thesis, requires the AI layer to tag stance), OVERTRADING (entries per week vs the user's own 12-month baseline), REVENGE (entries opened within 60 minutes of realising a loss), DISPOSITION (median holding period of winners vs losers), CHECKLIST ADHERENCE (% of theses with all hard-stop items ticked). Each card links to the underlying journal entries. Framing rule: cards are never scored or graded — they state a number and a comparison to the user's own baseline, because a self-directed sophisticated user rejects moralising instantly.

**Why it matters.** This is where the product stops being an information display and becomes an instrument of discipline. The three enforcement mechanisms that actually work are: a mandatory invalidation field, one-click promotion of invalidation to an alert, and an undismissable post-trade review with the process/outcome 2x2. Everything else is decoration.

- https://www.tradervue.com/
- https://edgewonk.com/
- design synthesis

### 29. MOCKUP SPEC — Empty, error and degraded states: a nine-state library with exact copy  
`confidence: high`

Every data-dependent panel must implement all nine. Shared anatomy: a 16px glyph, a 13px headline, an 11px explanation at 70%, one primary action, and — where relevant — a secondary 'Show sample data' action that renders the panel populated with clearly-watermarked example data so the user can evaluate the panel before buying an entitlement.
1 NO ENTITLEMENT — 'Level 2 depth is not in your data plan.' / 'Nasdaq TotalView is required for this panel. Your current plan provides Level 1 consolidated quotes.' Actions: [See what this needs] [Show sample data].
2 RATE LIMITED — 'Provider limit reached — 5 calls/minute.' / 'Next slot in 00:41.' Render a determinate countdown ring, never an indeterminate spinner; queue position if applicable. The panel keeps showing the last good values, greyed, with their timestamps.
3 MARKET CLOSED — NOT an error state. Show the last session's summary and a countdown to next open in exchange-local time with the venue named ('NASDAQ opens in 14h 22m · 09:30 America/New_York').
4 NO FILINGS / NO DISCLOSURE — jurisdiction-aware: 'No Form 4 filings — BHP is a UK/AU issuer.' / 'UK issuers disclose director dealings as PDMR notifications under MAR Article 19 via RNS. Showing RNS instead.' Action: [Show RNS notifications].
5 SYMBOL NOT FOUND — fuzzy suggestions list (max 6) plus 'Identifier types that resolve here: ticker, ticker+MIC (RIO LN), ISIN, SEDOL, FIGI, CUSIP.'
6 PROVIDER DOWN — full-tile diagonal 4px hatch at 6% opacity, last values frozen and desaturated with their as-of stamps in amber, a banner naming the provider and the incident start time, and the global connection pill switches to DEGRADED. Never render a stale number in live styling.
7 PARTIAL DATA — per-cell '◌' glyph (never a blank, never a zero) with a hover reason; a tile-header chip '12 of 214 fields unavailable'.
8 TOO MANY RESULTS — 'Screen matched 8,412 rows; showing the first 2,000 sorted by market cap.' with the truncation rule stated and a [Refine] action; never silently truncate.
9 STALE BUT VALID — the normal state for slow data (13F, proxy, short interest). A 2px amber left bar on the tile plus 'as of' in the header; NOT an error, and must be visually distinct from state 6.
GLOBAL RULE: no spinner may run longer than 800ms without becoming a determinate, named progress state that says what it is waiting for and which provider.

**Why it matters.** In a data-dependent terminal the error states ARE the product for a meaningful fraction of runtime, and they are where trust is won or destroyed. Distinguishing 'stale but valid' from 'provider down' from 'no entitlement' — three states that most tools collapse into one grey box — is the difference between a user who trusts the numbers and one who checks them elsewhere.

- design synthesis

### 30. Onboarding a dense tool without dumbing it down: curated workspaces, not wizards  
`confidence: high`

Pattern set: (1) SIX SHIPPED LAYOUTS, each a real populated workspace rather than a template — Pre-Market (07:00), Earnings Day, FX London Session, Research Deep Dive, Ownership Forensics, Post-Trade Review; the user's first run opens Pre-Market with their first watchlist symbol already in scope. (2) COMMAND CATALOGUE (CAT): a searchable grid of every mnemonic — Mnemonic | Name | What it answers (one sentence in the user's language, e.g. OWN = 'Who owns this and who has been buying') | Example command | Keyboard | [Run] [Pin]. This is the answer to the mnemonic discoverability problem and it costs one screen. (3) CHEAT-SHEET OVERLAY on F1-F1, context-aware — a translucent full-window sheet showing the focused panel's single-key map plus the global chords, dismissed on any key; modelled on Figma's '?' overlay. (4) GHOST-TEACHING: after the third mouse-driven use of a function, a one-line, non-modal, permanently-dismissible hint in the status rail — 'OWN also opens with: AAPL EQ OWN ⏎'. (5) PROGRESSIVE DISCLOSURE in panels via view-sets rather than settings dialogs: every panel opens on 'Summary' and the deeper column packs are one keystroke away, so the surface area grows with the user. (6) TELEMETRY-FREE USABILITY: because this is a single-user product handling position data, ship ZERO network telemetry; instead keep a local, user-readable usage log (opt-in, viewable and deletable in Settings) that powers self-directed prompts — 'You have not opened 14 of 46 panels in 90 days. Hide them from the catalogue?' and 'This alert rule fired 63 times this week. Tighten it?'. Nielsen's information-scent guidance applies directly to the catalogue and palette: link labels must be 'succinct yet accurate' and in plain language rather than jargon, which is why every mnemonic row carries a 'what it answers' sentence alongside the jargon name.

**Why it matters.** The standard onboarding failure in professional tools is a coach-mark tour that teaches nothing and a settings-heavy first run. Curated populated workspaces teach by example, the catalogue makes the vocabulary browsable, and the ghost-teaching converts mouse habits into keyboard habits over weeks — which is the only mechanism that has ever produced Bloomberg-grade speed.

- https://www.nngroup.com/articles/information-scent/
- design synthesis

### 31. ADVERSARIAL: eleven things a naive UX plan for this product will miss  
`confidence: medium`

1. TIME IS NOT SCALAR. Every timestamp needs a venue and a zone; FX has no close, and the market 'day' rolls at 17:00 America/New_York; equity sessions differ per venue; a single 'Today' filter silently mixes them. 2. CORPORATE ACTIONS RETROACTIVELY FALSIFY THE UI. A split invalidates saved alerts, journal entries, chart drawings and screen thresholds. Required: an adjustment reconciler that rewrites affected objects and shows a diff — 'AAPL 4:1 split on 2026-06-01: 3 alerts and 2 drawings adjusted'. 3. 'READ-ONLY' STILL NEEDS A POSITION LEDGER. Ownership and incentive intelligence is contextless without knowing what the user holds; but a manual/CSV ledger must be visually and structurally distinct from anything resembling brokerage connectivity, with no order affordances anywhere in the app. 4. LINK-CHANNEL COLOURS COLLIDE WITH P&L COLOURS. Reserve two hue families exclusively for direction and never reuse them for channels, selection, or status. 5. THE COMMAND LINE BELONGS AT THE TOP. Terminal instinct says bottom; Bloomberg puts it top and results render below in reading order. (Medium confidence — reasoned from reading-order and from Bloomberg's precedent, not from an eye-tracking study.) 6. WINDOWS-SPECIFIC LAYOUT FRAGILITY. Per-monitor DPI v2, mixed-DPI setups, and monitor disconnect: torn-off windows must persist with monitor GUIDs and fall back to the primary display rather than restoring off-screen. Test the 3-monitor→1-monitor→3-monitor cycle explicitly. 7. FOCUS RINGS VANISH IN DARK THEMES. The Windows default focus rectangle is invisible on #12151A; implement a 2px ring meeting SC 2.4.13's 3:1 focused-vs-unfocused change, in a hue reserved for focus alone. 8. 200% FONT SCALING BREAKS TILED GRIDS. The grid needs breakpoints that collapse 2x2 to 1x4 with a panel switcher, not clipping. 9. PRINT AND PDF ARE REAL. Research deep-dives get printed; heatmaps and conditional formatting must survive greyscale, which means every sequential ramp must be monotonic in luminance, not just in hue. 10. AI KNOWLEDGE MUST BE VERSIONED AND DIFFABLE. A KB the user cannot audit is a KB they will abandon after one bad answer; ship a diff browser showing what Claude changed at each scheduled run, with the source that caused the change. 11. ALERT EVALUATION SEMANTICS MUST BE VISIBLE. TradingView's docs already show the trap: study/strategy alerts depend on the calculation interval while data-series alerts do not. Every alert row must display its evaluation clock (on tick / on bar close / on data refresh / on filing arrival) or the user cannot debug a non-firing alert.

**Why it matters.** Each of these is cheap to design in and expensive to retrofit. Items 2, 3, 6 and 11 in particular are architectural — they constrain the data model and the window manager, not just the visual design.

- https://www.tradingview.com/support/solutions/43000595315-about-alerts/
- https://www.w3.org/WAI/WCAG22/Understanding/focus-appearance.html
- design synthesis

### 32. Tufte applied concretely to blotters, ladders and heatmaps  
`confidence: medium`

Operational rules derived from data-ink discipline (classic principles, high confidence; the specific numbers are my design targets): (1) DELETE ALL VERTICAL GRID LINES in tables — column alignment carries the structure; use 1px horizontal hairlines at 8% opacity every 5 rows only, or zebra at 3% opacity, never both. (2) THE CELL BORDER BUDGET is zero: use whitespace and alignment, reserving borders for the focus ring and for the flash-governor edge bar. (3) IN-CELL GRAPHICS BEAT SEPARATE CHARTS: a 44px data bar inside the Δ column and a 64x16 sparkline in the row deliver more decisions per pixel than a linked chart panel. (4) HEATMAP: cell colour must encode ONE variable (change), area must encode ONE variable (weight), and the label must state the number — never rely on colour alone to convey magnitude; the palette must be monotonic in luminance so it survives greyscale, and must be diverging around zero with a neutral (not white) midpoint on a dark surface. (5) NO CHARTJUNK IN THE LADDER: a depth ladder's ink is the size bars and the price column; the price column must be fixed-position with the inside market marked by a 2px rule rather than by a colour fill. (6) AXES: y-axis labels only at the visible extremes plus the last price; a full tick ladder is noise. (7) LEGENDS ARE A FAILURE: label series in place, at the line, in the series colour. Target metric for the design review: on a 1920x1080 tile at Compact density, a holders grid should show >=26 data rows with <=12% of tile pixels spent on chrome.

**Why it matters.** 'Clean' in finance means high data-ink ratio, not high whitespace. Naming a numeric target (26 rows, <=12% chrome) turns a philosophical argument into a reviewable acceptance criterion, which is the only way density survives contact with a visual designer's instincts.

- Tufte, The Visual Display of Quantitative Information — classic principles, not fetched this session; numeric targets are design recommendations

### 33. Latency and trust: what must be on screen at all times, and the regulatory hook  
`confidence: low`

ALWAYS-VISIBLE TRUST FURNITURE: (a) connection pill in the command bar with three states LIVE / DEGRADED / FROZEN; (b) per-provider health segments in the status rail with latency for streaming feeds and age for polled feeds ('FILINGS ● 3m'); (c) an as-of stamp in EVERY tile header, not on hover; (d) a data-quality chip on the context ribbon (RT / D15 / D20 / EOD) with its exact as-of; (e) provenance mode on Ctrl+/ that dotted-underlines every number in the app and makes it activatable to its source document, row, or API response. REGULATORY HOOK: US consolidated market data display by vendors is governed by Reg NMS Rule 603(c), the 'Vendor Display Rule' (17 CFR 242.603(c)), which constrains how quotation and transaction data may be displayed in a context of order entry/execution; exchanges additionally impose contractual display and attribution requirements including identification of delayed data and per-exchange attribution. I was NOT able to fetch the operative text this session (SEC and eCFR both returned index pages or redirects), so treat the precise obligations as UNVERIFIED and requiring counsel review before launch copy is finalised. What is safe to assert as a design requirement regardless: delayed data must be labelled with both the delay and the as-of, exchange attribution must be displayable, and a read-only product with no order entry sits in a materially lighter position than an execution venue — but the vendor agreements, not the SEC rule, will be the binding constraint on badging.

**Why it matters.** Delay badging is simultaneously a licensing obligation, a legal risk control, and the single cheapest trust signal in the product. Designing it as a first-class, always-visible chip rather than a footnote costs nothing and pre-empts a late-stage compliance rewrite of every panel.

- https://www.sec.gov/rule-release/34-42208 (index only, text not retrieved)
- https://www.ecfr.gov/current/title-17/chapter-II/part-242/section-242.603 (redirected, not retrieved)

## Recommended decisions

### Primary navigation model: mnemonic command line, fuzzy palette, or both?

**Recommendation.** Both, with the object-first mnemonic command line as the ALWAYS-FOCUSED primary (Ctrl+Space) and the sigil-prefixed fuzzy palette as the secondary (Ctrl+K). Accept reverse-order input and normalise it with a visible ghost rewrite. Every panel header displays the exact command that produced it, and clicking copies it.

**Rationale.** Bloomberg's verified model gives speed and determinism; VS Code's verified sigil grammar gives discoverability. Neither alone serves a user who is both an institutional analyst and a day trader. The ghost rewrite is the specific mechanism that removes Bloomberg's learning cliff without slowing the expert path, and command-echo in panel headers teaches the vocabulary passively over weeks.

**Rejected.** Palette-only (Koyfin/Atom model) — caps out at maybe 60% of Bloomberg keystroke efficiency and never builds muscle memory. Mnemonic-only — an unacceptable discoverability cliff for a 46-screen product with no support desk.

**Cost.** L — parser, resolver, catalogue, synonym table, ghost-rewrite engine, per-panel command stack

### Workspace paradigm: tabs, tiles, chartbooks, or free-floating MDI?

**Recommendation.** Tiled panel grid where each tile owns its own command context and history, plus named saved layouts, pinned always-on-top panels, and genuine tear-off windows persisted against monitor GUIDs. Ship six curated populated layouts.

**Rationale.** The verified Bloomberg insight is not four windows but four independent command contexts. Sierra Chart's verified chartbook model proves saved workspaces are the right unit of persistence but shows the limitation (only one visible per instance). IBKR TWS's classic free-floating MDI is the canonical criticism case: window management becomes the user's unpaid job and layouts break on monitor change. TradingView's verified plan data — even the $199.95 tier caps saved layouts at 10 — indicates real users converge on well under ten named workspaces, so optimise for six excellent ones rather than infinite flexibility.

**Rejected.** Tabs-only (insufficient for simultaneous research contexts); free-floating MDI (TWS's known failure mode); chartbook-only (cannot see two workspaces side by side)

**Cost.** L — grid engine, layout serialisation with monitor GUIDs, tear-off window manager, per-monitor DPI v2 handling

### Default directional colour scheme: classic red/green or a CVD-safe pair?

**Recommendation.** Ship Okabe-Ito Blue #0072B2 (up) / Vermilion #D55E00 (down) as the DEFAULT, with Classic green/red and Cyan/Magenta #56B4E9/#CC79A7 as one-click alternatives, and a first-run one-question screen with live preview. Direction must additionally be encoded by a ▲▼ glyph and an explicit sign so the palette is a comfort setting and never a correctness dependency.

**Rationale.** Verified prevalence is ~1 in 12 men; the user is one man and the cost of asking is ten seconds. Vermilion is specifically recommended over pure red by the Color Universal Design source, and pure saturated red also brushes against WCAG 2.3.1's separate red-flash threshold when used as a flash colour. Triple-coding means we never have to be right about which palette they chose.

**Rejected.** Red/green default with CVD as a buried accessibility option — the standard industry choice, and the reason CVD users mis-read financial UIs daily.

**Cost.** S for tokens and the first-run screen; M including the contrast auditor

### Visual density and theme posture

**Recommendation.** Compact default (22px rows, 12px text, 6px cell padding), zero cards, zero shadows, 1px hairlines, tabular figures everywhere, three-mode density ladder. Dark shell (#12151A base, never pure black) for all live/monitoring surfaces; a LIGHT 'paper' reading surface for documents, transcripts and AI long-form prose inside the dark shell; a full light theme for print/PDF. Acceptance criterion: >=26 data rows visible in a holders grid on a 1920x1080 tile with <=12% of tile pixels spent on chrome.

**Rationale.** Density is the product. But the verified NN/g evidence is that light mode outperforms dark for sustained reading with normal vision, and the advantage grows as text shrinks — so a uniformly dark app is optimising the wrong surface for the reading tasks. Per-surface polarity is the honest synthesis. The numeric acceptance criterion is what stops density being negotiated away in visual design review.

**Rejected.** Uniform dark theme (degrades the reading surfaces); 'modern clean' card UI with generous whitespace (halves rows-per-glance and is the standard way fintech redesigns fail); pure-black OLED theme (halation on dense text, and no elevation vocabulary)

**Cost.** M — token system, three density modes, dual-polarity surface system, print stylesheet

### How should alerts be authored?

**Recommendation.** Three lanes visible at once — natural language, an editable compiled rule tree, and an expression — all round-tripping, with a mandatory backtest readout ('this rule would have fired 11 times in the last 90 days') before Save is enabled.

**Rationale.** NL-only is unauditable, and in this domain an alert the user cannot verify is an alert they will not trust when it fires at 3am. Builder-only traps the power user. The compiled tree is the contract between the two. The backtest readout is the highest-leverage anti-fatigue mechanism available because it moves the noise decision to design time, when the user still cares.

**Rejected.** NL-only (unauditable); rule-builder-only (TradingView/Stock Rover model — hits a ceiling fast); expression-only (unusable for ad-hoc alerts mid-session)

**Cost.** XL — bidirectional NL↔AST↔DSL compiler plus a historical evaluation engine

### How to handle live-update animation given WCAG 2.3.1

**Recommendation.** A per-cell flash governor with a hard 3-flashes-per-second budget that degrades to a persistent opacity-encoded edge bar above that rate; low-alpha (12–18%) tint for 180–250ms with eased decay rather than a blink; only the changed cell flashes, never the row, keeping total flashing area under the 341×256px reference; OS reduced-motion substitutes a static direction glyph; and a global Alt+P Freeze.

**Rationale.** Verified: 2.3.1 caps flashing at three per second and defines a general flash as a ≥10% relative-luminance opposing change with the darker state below 0.80 — which a naive cell flash on a liquid FX pair violates continuously. 2.2.2 independently requires a pause mechanism for auto-updating content lasting over five seconds. The degradation-to-edge-bar design satisfies both while actually conveying MORE information (update intensity) than a flash does.

**Rejected.** Conventional uptick/downtick flashing (non-conformant and fatiguing); no update indication at all (loses the pre-attentive signal that is the whole point)

**Cost.** M — render-layer rate limiter and a second visual encoding

### Screen-reader strategy for a continuously updating terminal

**Recommendation.** No live regions on any market-data surface. Use UIA notifications: alert firings raise UiaRaiseNotificationEvent with NotificationKind_Other and NotificationProcessing_ImportantMostRecent (P1) or NotificationProcessing_CurrentThenMostRecent (P2); connection-state changes use ActionCompleted/ActionAborted; price is spoken only on demand via Ctrl+Shift+V on the focused cell, or for cells the user explicitly subscribes to spoken monitoring.

**Rationale.** Verified from Microsoft's own documentation: ImportantAll carries an explicit flooding warning, and CurrentThenMostRecent exists precisely to collapse bursts from one source. Verified MDN guidance is equally explicit that stock tickers must not use assertive live regions and that even polite is annoying at high frequency. On-demand speech plus burst-collapsing notifications is the only design that makes a live terminal usable with a screen reader.

**Rejected.** aria-live/LiveSetting on the quote grid (unusable — continuous speech); no accessibility plumbing at all (fails WCAG and makes the product unusable in a low-vision future)

**Cost.** M — hand-written UIA providers for custom-drawn grid and chart content

### Keyboard binding scheme and whether to offer vim mode

**Recommendation.** Three-tier discipline: Ctrl+chords are global and never overridable by a panel; bare single keys belong to the focused panel; Alt+ is reserved for layout/session actions. F-keys reserved for help/refresh/maximise only — NOT for asset class as Bloomberg does. Optional vim mode, off by default. Enforce with a Keyboard-Only Audit Mode in CI.

**Rationale.** The tiering makes binding collisions structurally impossible rather than a maintenance chore. Bloomberg's F2–F12 asset-class mapping depends on a bespoke keyboard; a Windows app cannot reliably own F2–F12 across screen readers and IMEs, so asset class becomes a command-line token instead. Vim-by-default would collide with the j/k row navigation expectation and taxes an already substantial chord vocabulary.

**Rejected.** Bloomberg-style dedicated F-key asset classes (hardware-dependent, conflicts with AT); vim-by-default (adds a second grammar to learn on top of the mnemonics)

**Cost.** M for the map and mode system; S for the audit mode

### Is the decision journal a feature or a pillar?

**Recommendation.** A pillar. Ctrl+J is reachable from every screen, capture completes in under six seconds with automatic context (symbol, panel command, snapshot, dual timestamps, price with as-of), the thesis card refuses to save without an invalidation condition, and each condition promotes to a live alert in one click.

**Rationale.** Verified from TraderVue and Edgewonk that the analytic unit is the TAG and the behaviour-changing statistic is exit quality (MFE/MAE) — both of which require capture to be frictionless or they never happen. The mandatory-invalidation rule plus one-click promotion to an alert is the mechanism that closes the loop: the terminal, not the P&L, tells the user they were wrong.

**Rejected.** A journal tab the user must remember to visit (the universal failure mode of journalling products); free-form notes with no structure (produces no analytics)

**Cost.** M for capture and thesis card; L including the bias dashboard

### Telemetry posture

**Recommendation.** Zero network telemetry. Ship an opt-in, entirely local, user-readable and user-deletable usage log, and use it only to power self-directed prompts (hide unused panels, tighten noisy alert rules).

**Rationale.** This is a single-user tool sitting adjacent to position data. Any outbound analytics is a trust liability that will eventually be discovered and will contaminate the user's trust in the AI layer as well. The local log gives us every usability benefit we would actually act on for a single user, with none of the exposure — and 'no telemetry' is itself a marketable property for this buyer.

**Rejected.** Standard product analytics (Amplitude/Mixpanel class) — the default choice, and wrong here; no usage data at all — loses the self-tuning prompts for free

**Cost.** S

### Where does the command line sit — top or bottom?

**Recommendation.** Top, in a 32px command bar, with results rendering below it in reading order and a grammar bar directly beneath the input.

**Rationale.** Bloomberg's verified placement is top, and the reading-order argument is straightforward: the parse feedback and the results both flow downward from the input, so the eye never reverses. A bottom-mounted command line borrowed from terminal emulators would force an upward saccade to read results. Marked medium confidence — this is reasoned from precedent and reading order, not from an eye-tracking study.

**Rejected.** Bottom-mounted (terminal-emulator instinct); a floating palette as the only input (no persistent home for the grammar bar, and no always-available focus target)

**Cost.** S

### UI technology stack for a dense, custom-drawn Windows terminal

**Recommendation.** WPF or WinUI 3 with a fully custom-drawn virtualised grid and custom-drawn charts, and hand-written UIA providers for both. Budget the accessibility plumbing explicitly as a first-class workstream rather than assuming it from the framework. Confidence medium — this is an inference from the requirements, not a verified benchmark.

**Rationale.** Off-the-shelf grids will not hit 22px rows at 60fps with per-cell flash governing, tabular-figure decimal alignment, in-cell data bars and sparklines, and 200% scaling reflow. Custom drawing is therefore forced. The consequence that teams routinely miss is that custom-drawn content is invisible to screen readers unless UIA providers are written by hand — which is exactly why the UIA notification design must be decided now rather than retrofitted.

**Rejected.** Electron/web stack (fights the Windows accessibility and multi-monitor DPI story, and adds latency to a latency-sensitive product); off-the-shelf commercial data grid (loses control of density, flash governing and numeric typography)

**Cost.** XL — and the UIA provider work is a significant, commonly under-budgeted slice of it

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | L | Mnemonic Command Bar with GO | Top-mounted, always-addressable command line implementing object-first grammar `<identifier> [<class>] <function> [args] ⏎`, with a live grammar bar rendering the parse as chips, inline ghost completion of the next token only, and a normalising rewrite for reverse-order input (`OWN AAPL` → `AAPL US EQ OWN`). | Internal command catalogue + symbol resolver |
| P0 | M | Ctrl+K Fuzzy Palette with Sigil Namespaces | Single input with namespaces: (none) symbols, `>` verbs, `@` function mnemonics, `#` layouts, `/` screener DSL, `!` alert authoring, `~` AI question, `?` catalogue, `:` grid row. Fuzzy matching, recents first, did-you-mean over a hand-authored synonym table. | Internal |
| P0 | S | Command Catalogue & Context Cheat-Sheet Overlay | Searchable grid of every mnemonic with a plain-language 'what it answers' sentence, example command and keyboard binding; plus an F1-F1 translucent overlay showing the focused panel's single-key map alongside global chords. | Internal |
| P0 | M | Six-Channel Panel Linking | Assign any panel to one of six colour channels (Ctrl+Alt+1..6); changing the symbol in one linked panel propagates to all panels on that channel. Channel hues drawn from a palette that excludes every directional and status hue. | Internal |
| P0 | L | Named Workspaces with True Tear-Off | Tiled panel grid with arbitrary splits, named saved layouts (Alt+1..9), per-panel command history (Alt+Left/Right), pinned always-on-top panels, and tear-off windows persisted against monitor GUIDs with safe fallback on monitor disconnect. | Internal |
| P0 | M | Density Engine + 200% Font Scaling | Three density modes (28/22/18px rows) on Ctrl+Shift+D, with even row heights for crisp hairlines, and Ctrl+=/-/0 scaling to 200% that reflows the tile grid to a stacked single column with a panel switcher rather than clipping. | Internal |
| P0 | M | CVD-Safe Palette System with Built-In Contrast Auditor | Three directional palettes (Classic green/red, Blue/Orange #0072B2/#D55E00, Cyan/Magenta #56B4E9/#CC79A7) plus a luminance-only mode; direction always triple-coded as hue + ▲▼ glyph + explicit sign; a settings-page auditor measures every token pair against 4.5:1 / 3:1 and flags failures. | Okabe-Ito palette; WCAG 1.4.3/1.4.11 |
| P0 | M | Tick Flash Governor | Per-cell update animation with a hard budget of 3 flashes/second (WCAG 2.3.1); above that rate the cell degrades to a persistent 2px left edge-bar whose opacity encodes update intensity. Low-alpha (12–18%) 180–250ms tint with eased decay, never a hard blink. Honours the OS reduced-motion setting by substituting a static 500ms direction glyph. | Internal render layer |
| P0 | S | Global Freeze (Pause Live Updates) | Alt+P halts all animation and streaming updates, pins every visible value with its freeze timestamp, and turns the connection pill and status rail amber until released. | Internal |
| P0 | XL | Provenance Layer ('Cite Everything') | Ctrl+/ toggles a mode in which every number in the application gains a dotted underline and becomes activatable to its source — the filing and accession number, the API response with its request timestamp, or the calculation with its inputs. Ctrl+Shift+C copies a value with a provenance footnote. | All providers, filing archives |
| P0 | M | Staleness, Entitlement & Delay Badging System | Every tile header carries an as-of stamp; the context ribbon carries an RT/D15/D20/EOD chip with exact as-of; slow-data panels (13F, proxy, short interest) carry a 2px amber bar; screens display the effective as-of of their slowest input. | Provider metadata |
| P0 | M | Connection Health Rail & Degraded Mode | Per-provider status segments with latency (streaming) or age (polled) in the status rail; on provider failure the affected tiles gain a diagonal hatch, freeze and desaturate their last values with amber timestamps, and a banner names the provider and incident start. | Provider health endpoints |
| P0 | L | Ownership Forensics Panel (OWN/HDS) | Concentration stacked bar, virtualised holders grid with QoQ delta bars and %-of-holder's-AUM, 8-quarter net institutional flow, new/exited lists, 13D/G activist list, and a permanent non-dismissible strip stating the 45-day 13F lag and its long-only US-equity scope. | SEC 13F/13D/13G; commercial ownership vendor |
| P0 | L | Insider Signal Panel with Transaction-Code Intelligence | People-timeline strip with glyph-coded transaction types, a grid carrying the non-obvious columns (days-from-earnings, 10b5-1 flag and adoption date, filing lag, Δ% of holding), non-discretionary codes rendered neutral, a default filter excluding awards/tax-withholding shown as a removable chip, and a signals rail (cluster-buy detector, conviction score, sale classifier, filing-lag anomaly). | SEC Form 4 feed; MAR Art.19 RNS for UK/EU |
| P0 | XL | Pay-for-Metric Map (Executive Incentive Decomposition) | Compensation waterfall with prior-year ghost bars, plus a metric table classifying every plan metric as GAAP / Adjusted / Qualitative, with threshold-target-max-actual-payout, an add-back reconciliation expander that flags multi-year growth in adjustments, a peer-group change detector, and a vesting-cliff calendar overlaid with each executive's historical post-vest sale behaviour. | DEF 14A proxy statements; Form 4 vesting history |
| P1 | M | Short Interest & Borrow Panel | Bi-monthly settlement short interest with its publication lag stated, days-to-cover, short % of float, plus daily FINRA short volume as an explicitly separate and differently-labelled series, and borrow rate/utilisation where entitled. | FINRA; exchange short interest; securities-lending vendor |
| P0 | L | Screener with View-Sets and Round-Tripping Expression Mode | Criteria rail and a monospace DSL editor that round-trip losslessly; universe chips with live result counting; swappable column packs (Overview / Ownership / Incentives / Shorts / Estimates / Technicals / Custom); per-column conditional formatting whose colour-scale picker enforces a greyscale-safe preview; a provenance strip stating the effective as-of. | Fundamentals + ownership + insider + short data |
| P1 | M | Greyscale-Safe Heatmap | Treemap where area encodes weight and colour encodes change on a diverging ramp that is monotonic in luminance with a neutral (not white) midpoint on dark surfaces, with the numeric value always printed in-cell. | Market data + index constituents |
| P0 | XL | Three-Lane Alert Compiler | Natural language → editable compiled rule tree → expression, all three visible simultaneously and round-tripping; priority tiers with plain-English consequence lines; session scope; expiry; throttle; and a live 'this rule would have fired N times in the last 90 days' backtest readout before saving. | Historical data for the backtest readout |
| P0 | M | Alert Fatigue Governor and Audit Trail | Per-rule rate limits, automatic noisy-rule detection with a 'tighten this?' card, quiet hours, session-aware suppression, Ctrl+M instant global mute, and an immutable log of every firing recording the timestamp, the exact values that satisfied the condition, and a snapshot link. | Internal |
| P0 | XL | AI Ask Panel with Mandatory Sources Pane | Conversation on a light 'paper' reading surface with every emitted number rendered as a citation chip that navigates the linked panel to its underlying row; a never-collapsible Sources pane of quoted-span cards; unsourced numbers dotted-underlined with a persistent counter; mode chips including Devil's Advocate and Find-the-Disconfirming-Evidence. | Claude-authored KB + live panels |
| P0 | M | Knowledge Base Freshness Bar & Diff Browser | Persistent bar showing last authoring run (UTC), note count, notes changed in 24h, tickers covered and next scheduled run; a diff browser showing what Claude changed at each run and which source caused each change. | KB versioning store |
| P0 | M | Journal Quick-Capture (Ctrl+J) | Sub-six-second modal that auto-captures symbol, the focused panel's command string, a panel snapshot, UTC + venue-local timestamps and the current price with its as-of; fields are note, tags (one keystroke each) and a 1-5 conviction stepper on keys 1-5. | Internal |
| P0 | M | Thesis Card with Mandatory Invalidation and One-Click Alerting | Structured thesis requiring an invalidation condition before it can be saved, where each entry and invalidation condition can be promoted to a live alert in one click. | Internal + alert engine |
| P1 | M | Pre-Mortem Engine with Checklists | Forced prospective-hindsight prompt ('it is horizon-from-now and this is down 30% — write the story'), AI-assisted disconfirming prompts drawn from the KB and from the user's own past failures, plus user-authored per-setup checklists in Gawande READ-DO and DO-CONFIRM modes with hard-stop items. | KB + journal history |
| P1 | M | Post-Trade Review with the Process×Outcome 2×2 | Auto-triggered 72h after a close, deferrable only twice: chart with entry/exit/invalidation and MFE/MAE shading beside the original thesis, and a single 240×240 grid where the user places one marker across Process (poor↔good) and Outcome (bad↔good). | Position ledger + journal |
| P1 | L | Bias Dashboard | Six computed, non-judgemental metrics against the user's own baseline — recency, confirmation (via AI-panel source stance tagging), overtrading, revenge entries, disposition effect, checklist adherence — each with a 90-day sparkline and a drill-through to the underlying journal entries. | Journal + ledger + AI panel logs |
| P0 | L | FX Session Board with Big-Figure/Pip/Pipette Rendering | Matrix board where bid/ask use three-tier type (big figure de-emphasised, pip digits large and bold, pipette small and raised) with pip digits x-aligned across instruments of differing decimal conventions; session range bars with Tokyo/London/NY open markers; a 24-hour session ribbon with the 17:00 New York day boundary drawn explicitly. | FX quote feed |
| P1 | L | Corporate Action Reconciler | Detects splits, consolidations, spin-offs and symbol changes, rewrites affected alerts, chart drawings, screen thresholds and journal price references, and presents a reviewable diff of every object it changed. | Corporate actions feed |
| P1 | XL | Jurisdiction-Aware Disclosure Router | Insider, ownership and filing panels detect issuer domicile and switch data model, columns, copy and empty states accordingly (US Form 4 / 13F versus UK-EU MAR Article 19 PDMR via RNS, and other regimes), naming the applicable regime in every empty state. | Per-jurisdiction regulatory feeds |
| P1 | M | Light Reading Surface and Print/PDF Theme | Documents, transcripts and AI long-form prose render on a light 'paper' surface inside the dark shell; a dedicated light print stylesheet inverts the whole app for PDF export with luminance-monotonic heatmap ramps. | Internal |
| P1 | M | Manual Position Ledger | CSV/manual entry of positions with cost basis, currency and open date, structurally and visually distinct from anything resembling brokerage connectivity, with no order affordances anywhere. | User entry / CSV import |
| P2 | XL | Chart Replay | R enters replay on any chart; Space play/pause, comma/period step back/forward, 1–5 speed, Esc exit — with all linked panels time-warping to the replay cursor so ownership, news and filings shown are as-of the replayed moment. | Historical market data + point-in-time fundamentals |
| P1 | S | Keyboard-Only Audit Mode | A built-in developer/QA mode that disables the pointer and logs any interaction that cannot be completed by keyboard, producing a pass/fail report per screen against the shipped keyboard map. | Internal |
| P1 | S | Local, Telemetry-Free Usage Log | Opt-in, entirely local, user-readable and user-deletable interaction log with zero network transmission, powering self-directed prompts such as hiding never-used panels and flagging noisy alert rules. | Internal |

## Risks

- DENSITY EROSION IN DESIGN REVIEW. The single most likely failure: a visual designer or the user's own aesthetic instinct progressively adds padding, cards and shadows until rows-per-glance halves. Mitigation: the numeric acceptance criterion (>=26 rows, <=12% chrome on a 1920x1080 tile at Compact) is a review gate, not a guideline.
- KEYBOARD MAP COLLISION AND DRIFT. A 100+ binding map accretes conflicts. Mitigation: the three-tier discipline (Ctrl global / bare-key panel / Alt session) plus an automated collision test in CI, plus the Keyboard-Only Audit Mode as a per-screen pass/fail.
- ACCESSIBILITY RETROFIT COST. Custom-drawn grids and charts are invisible to UIA unless providers are hand-written. If this is deferred, it becomes an XL rewrite rather than an M workstream, and the WCAG 2.2 AA claim becomes unachievable. Mitigation: budget UIA providers alongside the render layer from day one.
- FALSE-SIGNAL GENERATION IN THE INSIDER PANEL. If transaction codes are not classified and non-discretionary activity is not neutralised, the panel will produce a stream of confident-looking noise (mostly 10b5-1 plan sales and code-F tax withholding) and will actively make the user's decisions worse. This is the highest-consequence correctness risk in the product.
- 13F STALENESS MISREAD. Presenting 45-day-old, long-only, US-equity-only data as 'ownership' invites exactly the error the product exists to prevent. Mitigation: the non-dismissible footer strip and the effective-as-of on every derived screen.
- ALERT FATIGUE COLLAPSE. Once the user starts ignoring alerts, every alert in the system loses value simultaneously and the failure is not recoverable by adding features. Mitigation: the pre-save backtest readout, per-rule throttles, noisy-rule detection, and priority tiers with honest consequence copy.
- AI TRUST COLLAPSE FROM ONE UNCITED WRONG NUMBER. A professional will discard an AI layer permanently after a single confident fabrication. Mitigation: mandatory Sources pane, citation chips on every emitted number, dotted-underline plus a persistent counter for unsourced figures, and a KB diff browser so the knowledge base is auditable.
- WCAG 2.3.1 NON-CONFORMANCE FROM TICK FLASHING. Conventional uptick/downtick flashing on liquid instruments breaches the three-flashes-per-second limit continuously, and a saturated-red down colour additionally engages the separate red-flash threshold. This is a real accessibility and, in some jurisdictions, legal exposure — and it is the industry default.
- MULTI-MONITOR LAYOUT LOSS. Torn-off windows restoring off-screen after a monitor disconnect is a classic Windows defect that destroys user trust in saved layouts. Mitigation: persist monitor GUIDs with a primary-display fallback, and explicitly test the 3→1→3 monitor cycle.
- MARKET-DATA LICENSING SURPRISE. Display, attribution and delay-badging terms live in exchange and vendor agreements rather than in SEC rules, and can force late, invasive UI changes across every panel. Mitigation: design the badging system as a first-class, configurable, always-visible component now so the eventual constraint is a configuration change rather than a redesign.
- JURISDICTION GAPS PRESENTED AS EMPTY DATA. If a non-US symbol shows 'no insider filings' rather than 'this regime discloses differently', the product is silently wrong for most of its claimed universe. Mitigation: the jurisdiction router must ship with named 'regime not supported' states before any global coverage is claimed.
- SCOPE GRAVITY FROM THE PILLAR SCREENS. Ten ownership/incentive screens and seven decision-discipline screens are each individually justified and collectively an enormous build. The realistic failure is shipping all of them shallowly. Mitigation: sequence OWN, INS and PAY to full depth first — they are the differentiator — and stub the rest behind honest 'not yet built' states.

## Open questions

- Bloomberg mnemonic definitions could not be corroborated from a public source this session (Yale, Brown, Harvard, MIT and USC library guides returned 404 or contained no mnemonics; Investopedia is blocked to the fetch tool; Bloomberg's own product page returns 403). Before publishing a command catalogue that claims Bloomberg parity, verify the meaning of each mnemonic (DES, GP, GIP, HP, RV, COMP, EQS, FA, EE, ANR, ERN, OWN, HDS, SI, CACS, DVD, BI, TOP, NI, WEI, FXC, MOST, PORT, BQ) against a terminal or a current library guide.
- The exact obligations of the Reg NMS Vendor Display Rule (17 CFR 242.603(c)) could not be retrieved (SEC returned an index page, eCFR redirected). Confirm with counsel whether a read-only, no-execution product triggers any consolidated-display obligation at all, and separately confirm the display, attribution and delay-labelling terms in each exchange's and each vendor's data agreement — the vendor contracts, not the SEC rule, are likely the binding constraint on badging.
- Confirm the current 13F filing threshold wording and deadline (commonly cited as $100m in Section 13(f) securities, 45 days after quarter end) before it appears in the non-dismissible OWN footer strip, since that copy is the product's central honesty claim.
- Confirm the Section 16 Form 4 filing deadline (two business days) and the MAR Article 19 PDMR notification deadline before they appear in the filing-lag anomaly detector.
- Confirm CFTC Commitments of Traders release timing and the as-of/publication lag before the FX positioning panel states it in copy.
- Does the user actually have colour vision deficiency? This should be the first question the app asks, with a live preview — it changes the default palette and cannot be inferred.
- Monitor topology: how many monitors, what resolutions, what OS scaling? The tear-off design, the six curated layouts and the density default all depend on this and it is cheap to ask.
- Which jurisdictions must ship at v1? Full 'global equities' insider/ownership coverage is an XL data-modelling problem per regime; a defensible v1 might be US + UK + EU with explicit, named 'regime not supported' empty states elsewhere rather than silent gaps.
- Does the user want a manual position ledger at all, or is the product purely analytical? Several features (MFE/MAE, post-trade review, bias dashboard, personalised alerting) depend on it, but it introduces a data-entry burden and a superficial resemblance to a brokerage surface that the read-only positioning may not want.
- Should chart replay time-warp the linked fundamental, ownership and news panels? This requires point-in-time (bitemporal) storage of fundamentals and filings, which is a substantially larger data commitment than replaying prices alone. It may be the single most expensive feature in the inventory.
- How is the AI knowledge base scheduled and scoped — per ticker, per sector, per watchlist? The freshness bar's numbers ('512 tickers covered', 'next run 06:00Z') imply a coverage model that has not been defined, and coverage gaps must be visible in the UI or the bar becomes a lie.
- What is the acceptable end-to-end latency budget for market data at the UI, and does the chosen provider tier actually meet it? The connection pill's LIVE/DEGRADED thresholds cannot be specified without this number.
- Should the six shipped layouts be editable-in-place or forked-on-edit? Forking preserves a known-good reference state; editing in place is what users expect. Recommend forking with a visible 'reset to shipped layout' action, but confirm.
