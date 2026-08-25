# Market Data & Feed Infrastructure for a single-user, read-only global equities + FX desktop terminal (Windows), as of 2026-08-24

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

The single most important architectural fact is that this product is a **single-user, own-use, read-only** terminal. That one property collapses the cost structure by 10–50x, because every expensive concept in market data licensing — redistribution, external distribution, non-display use, enterprise caps, per-subscriber multiplication — is triggered by *sharing data with someone else*, not by building software. A solo non-professional subscriber can legally see full-depth Nasdaq TotalView for **$15.00/subscriber/month** (2026 rate, verified in Nasdaq's own price list) while an external distributor of the same feed pays **$4,230/month** plus per-subscriber fees. The design must therefore be built so that the app *never* becomes a distributor, and the plan must state explicitly that the moment a second human sees the screen, the economics change by three orders of magnitude.

Three time-sensitive shocks land inside this build window. (1) **Polygon.io rebranded to Massive.com** (effective 2025-10-30); polygon.io/pricing now 301-redirects to massive.com/pricing — verified live today. (2) The **CT Plan** replaces the CTA/CQ/UTP SIP plans, with its fee schedule approved by the SEC in July 2026 and launch expected early 2027. It replaces status-based professional/non-professional tests with **use-based** ones: any use "by or on behalf of any entity… limited liability company…" is *Professional*. A trader who routes his own money through an LLC flips from ~$2.70/month of tape fees to ~$73/month plus device fees. (3) The **UTP SIP goes 23 hours a day, 5 days a week on 2026-12-06**, Sunday 20:00 ET to Friday 20:00 ET, with new overnight LULD band indicators "G" and "H". Any terminal whose data model assumes a 09:30–16:00 session and a calendar date equal to a trading day will be structurally wrong within four months of launch.

FX has no consolidated tape and no NBBO. "The price" is always a specific venue's or dealer's price. Verified evidence: Massive's FX quote schema carries a single `bid_exchange`/`ask_exchange` ID per tick — a contributor, not a consolidated best bid/offer. The terminal must label every FX quote with its source and quote type rather than pretending to a canonical price.

Recommended architecture: **Massive (Polygon) Stocks Advanced $199/mo** as the primary equities spine, **Databento** for depth/microstructure and survivorship-safe history, **IBKR non-professional entitlements (~$31/mo)** as an independent cross-check, **OANDA v20 + ECB Data Portal (free)** for dealable-vs-official FX, and **OpenFIGI (free)** as the symbology spine while deliberately staying under CUSIP's 500-identifier fee threshold. Realistic all-in: **~$310/mo lean, ~$660/mo full.**

## Findings

### 1. Polygon.io is now Massive.com — the rebrand is live and polygon.io redirects (verified today)  
`confidence: high`

polygon.io/pricing returns HTTP 301 Moved Permanently to massive.com/pricing (verified by direct fetch, 2026-08-24). Rebrand effective 2025-10-30 16:00 ET, announced 2025-11-03. API keys and logins remain valid; api.polygon.io remains supported in parallel with the new api.massive.com base. Invoices now read 'Massive.com, Inc.'; card statements show MASSIVE.COM. Current Stocks tiers verified on massive.com/pricing: Basic free (EOD, 5 calls/min, 2y history); Starter $29/mo (15-min delayed, unlimited calls, 5y history); Developer $79/mo (15-min delayed, unlimited calls, 10y history, second-level aggregates, WebSocket); Advanced $199/mo (real-time, unlimited calls, 20+y history, tick-level trades and quotes). Add-ons: Financials & Ratios $29/mo, NYSE Order Imbalances $49/mo; partner datasets (Benzinga, TMX, ETF Global) $99/mo each. All plans include up to 3 concurrent WebSocket connections plus one per data expansion. Note: several third-party 'review' sites incorrectly date the rebrand to 'early 2026' or 'July 2026' — the primary sources say 2025-10-30.

**Why it matters.** Every code sample, doc link, vendor comparison and invoice reference in the plan must use Massive, not Polygon, or the build will start with stale documentation and a confused procurement trail. This also demonstrates that secondary 'API pricing comparison' sites are unreliable on dates — the plan should cite vendor primary sources only.

- https://polygon.io/pricing (301 -> https://massive.com/pricing, verified 2026-08-24)
- https://massive.com/pricing
- https://massive.com/blog/polygon-is-now-massive
- https://fisd.net/polygon-io-is-now-massive/

### 2. Non-professional display use of full Nasdaq depth costs $15.00/month; redistributing the same feed costs $4,230/month  
`confidence: high`

From Nasdaq's own regulated price list (Nasdaq_US_Equities_Price_List_2025_2026_2027.pdf, extracted directly): Nasdaq TotalView, monthly fee effective 2026-01-01 — Professional/Corporate $84.00 per subscriber, Non-Professional $15.00 per subscriber (2027: $86.00 / $15.00). Nasdaq Depth Data distributor fees (2026): Internal Distribution $1,690/firm, External Distribution $4,230/firm, Direct Access $3,340/firm. Nasdaq Depth Non-Display (Direct Access only, 2026): 1–39 subscribers = $412 per subscriber; 250+ = $75,000/firm. Nasdaq Basic per-subscriber (2026): all-issues Pro $28.50, Non-Pro $1.00 each; itemised, Nasdaq Issues Pro $14.10 / Non-Pro $0.50, NYSE Issues Pro $7.20 / Non-Pro $0.25. Nasdaq Basic Internal Distributor Fee $1,680/firm/mo; External $2,140/firm/mo. Monthly Administrative Fees: Delayed Data Products $50/firm, Real-Time Data Products $100/firm, Web-Based $100/firm. Non-Professional Derived Data License $1,500/firm/mo (flat 2025–2027). Nasdaq TotalView Enterprise License $25,000/mo plus depth subscriber fees; Nasdaq Depth Display Enterprise (Broker Dealer) $500,000/mo.

**Why it matters.** This is the whole economic case for the product. Because it is a single-user own-use terminal with no redistribution, the licence cost of institutional-grade Level 2 is $15/month, not $4,230/month. The plan should make 'never become a distributor' an explicit, tested architectural invariant — and should note that adding even a second viewer, a hosted web view, or a public screenshot bot changes the category.

- https://www.nasdaqtrader.com/content/ProductsServices/PriceList/Nasdaq_US_Equities_Price_List_2025_2026_2027.pdf

### 3. The CT Plan replaces CTA/CQ/UTP and redefines 'Professional' by USE, not registration — trading through an LLC makes you professional  
`confidence: high`

SEC Release 34-105125 (File 4-757), March 31 2026, and the approval order published 2026-07-01: the CT Plan LLC fee schedule was filed 2025-12-11, amended 2026-03-30, and approved by the SEC with a Commission modification in July 2026; launch expected early 2027. Key change extracted verbatim from the order: Professional use is redefined as '(i) any use of market data by or on behalf of any entity (for example, a corporation, company, partnership, limited partnership, limited liability company, or association), except trusts not for compensation; or (ii) use of market data by an individual to provide a service to a third party for compensation.' Everything else is Non-Professional. A 'good faith' safe harbour protects redistributors relying on user representations. Fee changes: Tape A professional per-device tiers ($45/$27/$23/$19) collapse to a flat $26; Tape B stays $23, Tape C stays $24 (combined $73/professional/month). Non-Professional moves from a flat $1 per tape to a tax-bracket sliding scale per tape: 1–2,000 users $0.90; 2,001–50,000 $0.75; 50,001–250,000 $0.60; 250,001–1,000,000 $0.40; 1,000,001+ $0.25 — i.e. $2.70/month across all three tapes at the top bracket. Inflation adjustments: Real-Time Redistributor fee $1,000 -> $1,155 per tape; Non-Display (ETS) Tape A $2,000 -> $2,315, Tape C $3,500 -> $2,025; Direct Access Tape A Bid-Ask $1,750 -> $2,025. Enterprise caps: existing Tape A/B/C caps $686,400 / $520,000 / $648,000; Tape A cut ~$40,000 and Tape B cut ~$30,000, with Professionals removed from the cap.

**Why it matters.** This is the single most expensive detail a naive plan would miss. Under today's rules a sophisticated unregistered trader is non-professional. Under the CT Plan, if he trades through an LLC or family company — which sophisticated traders routinely do for liability and tax reasons — his terminal's *data* becomes Professional use, moving tape fees from ~$2.70 to ~$73/month plus triggering professional rates at every exchange and vendor (Nasdaq TotalView $15 -> $84, IBKR TotalView $16.50 -> $90). The entitlement/status model in the app must be a first-class configurable, and the user must be advised on the account-structure consequence before he incorporates.

- https://www.sec.gov/files/rules/sro/nms/2026/34-105125.pdf
- https://www.federalregister.gov/documents/2026/07/01/2026-13215/joint-industry-plan-order-approving-the-second-amendment-to-the-national-market-system-plan
- https://datact.com/
- https://thectplanllc.com/faqs/

### 4. The UTP SIP goes 23/5 on 2026-12-06 — the concept of a 'trading day' breaks four months after launch  
`confidence: high`

Nasdaq Trader UTP Vendor Alert #2026-24: effective 2026-12-06 the UTP SIP operates 23 hours a day, 5 days a week, from Sunday 21:00 ET through Friday 20:00 ET, with a nightly maintenance window approximately 20:00–21:00 ET. Protection Price Limits are distributed via the existing LULD Price Band Message, with a NEW overnight LULD indicator carrying two values for the 21:00–04:00 ET extended window: 'G' for initial/update values and 'H' for zeroing values. The overnight indicator has been available for testing since 2026-07-13. The evening test broadcast service ends 2026-12-06; firms must move to Saturday UAT sessions. Separately, 24X National Exchange — an SEC-approved 23/5 national securities exchange and a listed CT Plan member — began trading 2025-10-15 (currently 04:00–20:00 ET) and expects full 23/5 (Sunday 20:00 ET to Friday 20:00 ET) in H2 2026, targeting the same 2026-12-06 SIP date.

**Why it matters.** Almost every retail charting stack hard-codes: session = 09:30–16:00 ET, trading day = calendar date, daily bar = one date, 'previous close' = yesterday. All four assumptions break on 2026-12-06. Bars that span midnight, sessions that start on the prior calendar day, overnight LULD bands with a distinct indicator, and a Sunday-evening open all need first-class modelling in the schema NOW — retrofitting a session model into a bar store after launch is a rewrite, not a patch.

- https://www.nasdaqtrader.com/TraderNews.aspx?id=UTP2026-24
- https://www.prnewswire.com/news-releases/24x-national-exchange-opens-for-trading-as-first-sec-approved-235-stock-exchange-302581303.html
- https://equities.24exchange.com/overnight-trading-faqs
- https://www.sec.gov/files/rules/sro/nms/2026/34-105125.pdf

### 5. NYSE proprietary feed pricing (May 14 2026 guide): non-professional device fees are trivial, access and non-display fees are not  
`confidence: high`

Extracted from NYSE Proprietary Market Data Pricing Guide dated 2026-05-14. NYSE Integrated: Access Fee $8,400/mo; Redistribution Fee $4,400/mo; Non-Display Categories 1/2/3 each $22,400/mo (Cat 3 per platform, capped at 3 platforms / $67,200); Professional User $78.00/device; NON-PROFESSIONAL User $16.00/device; Late Non-Display Declaration $1,000. NYSE OpenBook: Ultra Access $5,000/mo, Aggregated Access $5,000/mo, Redistribution $3,000/mo, Non-Display $6,000/mo, Pro $60.00/device, Non-Pro $15.00/device. NYSE BBO: Access $1,500/mo, Per-User Access $100/mo, Non-Display $1,500/mo, Pro $4.00/device, Non-Pro $0.20/device, Enterprise $25,000/mo, Digital Media Enterprise $40,000/mo. NYSE Trades: Redistribution $1,000/mo, Non-Display $3,000/mo. NYSE BQT (Best Quotes and Trades): Per-User Access $850/mo, Access $6,250/mo, Redistribution $2,500/mo, Pro $18.00/device, Non-Pro $1.00/device, Enterprise $50,000/mo, Digital Media Enterprise $65,000/mo; Datafeed and Device Redistribution Credits of ($2,500) each.

**Why it matters.** Confirms the pattern across exchanges: the per-eyeball non-professional fee is $0.20–$16.00, while the fees for *being a pipe* are $1,500–$22,400. It also shows the trap in 'non-display': a $22,400/month Category charge attaches to using NYSE Integrated to drive automated logic rather than a screen. A read-only terminal that computes alerts, scans, or scores from real-time data is arguably non-display use — this must be checked with each vendor rather than assumed, because it is the largest single line item that a naive plan silently incurs.

- https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf

### 6. Cboe One Summary is the cheapest legitimate real-time consolidated-ish US equity feed: $0.25/non-pro user/month  
`confidence: high`

From Cboe's US Market Data Product Price List v2026-07-21 (extracted directly). Cboe One Summary: Internal Distribution $1,500/mo; External Distribution $5,000/mo; Pro User $10.00/mo; NON-PRO USER $0.25/mo; Digital Media $15,000/mo; Data Consolidation $1,000/mo; Enterprise $50,000/mo. Cboe One Premium: Internal $15,000, External $12,500, Pro $15.00, Non-Pro $0.50, Digital Media $25,000, Data Consolidation $1,000, Enterprise $100,000. Individual depth feeds: BZX Summary Depth $5,000 internal / $5,000 external / $5.00 pro / $0.15 non-pro / $7,500 digital media; BYX and EDGA Summary Depth $2,500/$2,500/$2.50/$0.10/$5,000; EDGX Summary Depth $5,000/$2,500/$5.00/$0.15/$7,500. Cboe One is a consolidation of Cboe's own four US equities exchanges (BZX, BYX, EDGX, EDGA), NOT the full SIP — it therefore reflects a material but partial share of consolidated volume.

**Why it matters.** Cboe One is why so many vendors advertise 'real-time, no exchange fees' — they are frequently serving Cboe One (often 15-minute delayed) rather than the SIP. The terminal must know and display WHICH consolidation a quote came from, because a Cboe-One 'last' can differ from the consolidated last, especially in NYSE-listed large caps where Cboe share is lower. Presenting Cboe One as 'the price' is the kind of quiet dishonesty that destroys an analyst's trust in a tool.

- https://cdn.cboe.com/resources/membership/US_Market_Data_Product_Price_List.pdf
- https://markets.cboe.com/us/equities/market_data_services/cboe_one/

### 7. Interactive Brokers is the cheapest path to real, exchange-licensed L1+L2 — about $31/month — but its API forbids redistribution  
`confidence: high`

From interactivebrokers.com/en/pricing/market-data-pricing.php (fetched 2026-08-24). Non-Professional / Professional monthly: US Securities Snapshot and Futures Value Bundle $10.00 (base waived for activity) + $0.01 per snapshot / Professional bundle $10.00; US Equity and Options Add-On Streaming Bundle $4.50 / $125.00; NASDAQ TotalView-OpenView (L1, L2) $16.50 / $90.00; NASDAQ TotalView-OpenView EDS $1.00 / $10.00; NASDAQ BX TotalView $3.50 / $48.00; NYSE (Network A/CTA) L1 $1.50 / $45.00; NYSE American, BATS, ARCA, IEX and Regional (Network B) L1 $1.50 / $25.00; Cboe BZX (L1, L2) $8.00 / $47.00; Cboe One (L1) $1.00 / $5.00; NYSE Arca Order Imbalances $1.00; IBKR Currencies (Global) FEE WAIVED. All accounts get 100 free snapshot quotes/month and a $1.00 monthly snapshot waiver; snapshots are US equities/ETF $0.01, other instruments $0.03, and auto-upgrade to streaming when snapshot spend equals the streaming price. IBKR retains 5–10% of market data fees as admin. Level 2 concurrency is rationed: every 100 lines of market data allowance = 1 unique L2 symbol, minimum 3, maximum 60. Subscriptions are NOT pro-rated — mid-month starts and stops are charged the full month. CRITICALLY: IBKR states that using the TWS API to disseminate market data or other licensed information to third parties or non-IB customers is strictly prohibited without prior written approval, the API licence is not for developers selling software to third parties, and the API code may only be used for non-commercial purposes.

**Why it matters.** For roughly $31/month a non-professional gets genuinely licensed NBBO plus Nasdaq TotalView depth — cheaper than any pure data vendor and legally clean, because he is the account holder consuming his own entitlements. This makes IBKR the ideal cross-check/failover leg. But it can never be the redistributable leg, and the 3–60 concurrent L2 symbol cap plus the no-proration rule are real product constraints (a 'watchlist of 200 with depth' feature is simply impossible on IBKR).

- https://www.interactivebrokers.com/en/pricing/market-data-pricing.php
- https://interactivebrokers.github.io/tws-api/third_party.html
- https://www.interactivebrokers.com/campus/glossary-terms/market-data-subscriber-status/

### 8. FX has no NBBO and no consolidated tape — verified in the data schema itself  
`confidence: high`

Massive's (Polygon's) FX quote flat-file schema, fetched from massive.com/docs/flat-files/forex/quotes.md, contains exactly: ask_exchange (integer), ask_price, bid_exchange (integer), bid_price, participant_timestamp (nanosecond), ticker. Example rows for X:EUR-USD all carry a single contributor ID (48) on both sides. There is no consolidated best bid/offer, no tape, no aggregation across venues in the record. Coverage is 1,750+ pairs described as 'Global foreign exchange rate quotes from major institutions.' Market structure context: the BIS Triennial Survey (April 2025, published 2025) put global FX turnover at ~USD 9.5–9.6 trillion/day, up ~28% on 2022, with spot at ~USD 2.577–3 trillion/day (~31% of turnover). CLSMarketData covers over 50% of global FX traded volume for the 18 CLS-settled currencies across four datasets (FX Volume, FX Flow, FX Pricing, FX Outstanding) at 17 delivery frequencies. The dominant benchmark is the WM/Refinitiv 4pm London fix, administered by FTSE International Limited (LSEG), regulated by the FCA and designated a Critical Benchmark under UK BMR since November 2024. Official reference rates: the ECB Data Portal publishes daily euro reference rates at 14:15 CET — verified live today with no authentication: GET https://data-api.ecb.europa.eu/service/data/EXR/D.USD+GBP+JPY.EUR.SP00.A?lastNObservations=2&format=csvdata returned EURUSD 1.1664, EURGBP 0.8555, EURJPY 185.6 for 2026-08-24. api.frankfurter.dev returned byte-identical values, confirming it is an ECB mirror.

**Why it matters.** An honest terminal cannot show 'EURUSD 1.1664' with no qualifier. There are at least four legitimate and materially different answers: a dealable streaming bid/ask from one liquidity provider (OANDA, LMAX), an aggregated composite from a data vendor (Massive, TraderMade), the official ECB reference rate at 14:15 CET, and the WMR 4pm London fix used for index and NAV valuation. They disagree, and the disagreement is the information. Every FX quote surface in the product should carry source, quote type, and timestamp — this is a differentiating honesty feature, not a footnote.

- https://massive.com/docs/flat-files/forex/quotes.md
- https://data-api.ecb.europa.eu/service/data/EXR/D.USD.EUR.SP00.A (live test 2026-08-24)
- https://api.frankfurter.dev/v1/latest (live test 2026-08-24)
- https://www.bis.org/statistics/rpfx25_fx.htm
- https://www.cls-group.com/products/data/clsmarketdata/
- https://www.lseg.com/en/ftse-russell/benchmarks/wmr-fx-benchmarks

### 9. 'No exchange fees' vendors are usually selling DERIVED prices, not exchange data — and they say so if you read closely  
`confidence: high`

Intrinio's pricing page (fetched 2026-08-24) offers: Individual $150/mo — 'AI-Ready, Personal use only', monthly billing, includes OptionsEdge (FMV Real-Time), EquitiesEdge (FMV Real-Time), US Fundamentals, US EOD & Historical for stocks and options, 15-min delayed stocks (CBOE ONE), tick-level market data; explicitly 'No redistribution or display', '1 seat license', 'No exchange fees or paperwork'. Startup $333/mo to start (6 months at $333, 6 at $666, $999 thereafter), billed quarterly, with 'Commercial Use and Display Rights' and business-wide licence. Enterprise $1,250/mo+. Intrinio's own documentation describes EquitiesEdge as using 'multiple sources of data to derive a highly accurate predicted bid, ask, and last price for all U.S. stocks' — i.e. FMV = a modelled fair-market-value estimate, not exchange-sourced quotes. That derivation is precisely why there are no exchange fees. Massive/Polygon likewise publishes an 'FMV' product alongside real quotes for FX and other classes.

**Why it matters.** $150/month for 'real-time all US stocks, no paperwork' looks like the obvious answer and is a trap for a serious discretionary trader. A modelled price is fine for a portfolio dashboard and unacceptable for reading the tape, sizing a limit order mentally, or judging whether a print traded at the offer. The plan must distinguish three price classes — exchange/SIP actual, single-venue actual, and modelled/derived — and never let a derived price occupy a field the user reads as a real quote.

- https://intrinio.com/pricing
- https://intrinio.com/financial-market-data/equitiesedge
- https://massive.com/docs/rest/forex/overview

### 10. Databento's model is metered bytes plus pass-through exchange fees — cheap for research, expensive to leave running  
`confidence: high`

From databento.com/pricing (fetched 2026-08-24): four tiers — Usage-based (pay-as-you-go, historical only, billed by GB, no upfront cost); Standard $199/month (monthly billing, live data, NO exchange licence fees, 16+ years of L0 history plus 1 year of L1); Plus $1,750/month (annual contract, external distribution rights, 16+ years L1, dedicated account manager and connectivity); Unlimited $4,500/month (annual contract, 16+ years across all schemas). Historical metering is by uncompressed binary size; CSV and JSON encodings cost no extra; compression choice does not change cost. Pricing was updated 2026-06-22 citing higher exchange licence fees. Databento US Equities (DBEQ) spans 15 US equities exchanges and 30 ATSs (40 venues initially), with L0/L1 12 months across 12 schemas, L2 (MBP-10) 1 month, L3 (MBO, Imbalance) 1 month, and 7 years of consolidated OHLCV; live data with no exchange licence fees. Where you take a real exchange feed the fees pass through undiscounted: Databento documents Nasdaq TotalView Internal Distribution at $1,500/mo plus a $100/mo Nasdaq admin fee plus a $76/subscriber/mo Depth Non-Display Usage fee (~$2,051/mo minimum for professional raw access), noting $375/non-display subscriber applies only to RAW delivery. Corporate actions is a separate product starting at $299/month, covering 215 exchanges, 310,000+ listed and delisted securities from 85,000+ issuers, 60+ event types, refreshed four times daily, with a companion Adjustment Factors dataset and a Security Master carrying FIGI, ISIN, CFI, FISN and CIK mappings back to 2005.

**Why it matters.** Databento is the right tool for depth, microstructure and clean survivorship-safe history, and the wrong tool for an always-on desktop tape if you are careless — metered bytes plus a live subscription plus $299 corporate actions plus pass-through Nasdaq fees can quietly become $2,000+/month. Budget it as a research and backfill leg with hard byte caps, not as the streaming spine.

- https://databento.com/pricing
- https://databento.com/blog/introducing-databento-us-equities
- https://databento.com/blog/understanding-exchange-fees
- https://databento.com/blog/corporate-actions
- https://databento.com/blog/updates-to-subscription-pricing

### 11. Free/regulatory data covers a surprising amount of the 'incentives' pillar at zero cost — and several endpoints were verified live today  
`confidence: high`

All verified working on 2026-08-24 with no API key: (1) NYSE trade halts CSV — https://www.nyse.com/api/trade-halts/current/download returns 'Halt Date,Halt Time,Symbol,Name,Exchange,Reason,Resume Date,NYSE Resume Time' including Nasdaq-listed names and LULD Pause reasons (live sample: DAIC halted 15:31:56 LULD Pause, resume 15:36:56). (2) Nasdaq Trader halts RSS — https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts returns 100 items with ndaq:HaltDate, ndaq:HaltTime (millisecond precision), ndaq:IssueSymbol, ndaq:IssueName, ndaq:Market, ndaq:ReasonCode. (3) FINRA Reg SHO daily short volume — https://cdn.finra.org/equity/regsho/daily/CNMSshvol{YYYYMMDD}.txt, pipe-delimited Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market. IMPORTANT GOTCHA: the volume fields are now FRACTIONAL, e.g. '20260821|A|509558.830081|0|997736.860442|B,Q,N' — a naive integer parser will crash or silently truncate. (4) OpenFIGI v3 mapping — POST https://api.openfigi.com/v3/mapping works unauthenticated and returned figi BBG000B9XRY4 / compositeFIGI BBG000B9XRY4 / shareClassFIGI BBG001S5N8V8 for AAPL US; response headers state ratelimit-policy: 25;w=60, ratelimit-limit: 25 — i.e. 25 requests per 60 seconds unauthenticated. (5) ECB Data Portal EXR series as described above.

**Why it matters.** The insider/incentives pillar leans on free regulatory sources, and these are the plumbing: halts and LULD pauses for 'something is happening now', Reg SHO short volume for 'who is pressing', OpenFIGI for identity. Verifying them live also surfaces the fractional-volume trap, which is exactly the kind of defect that produces a wrong number on screen with no error.

- https://www.nyse.com/api/trade-halts/current/download (live test 2026-08-24)
- https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts (live test 2026-08-24)
- https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260821.txt (live test 2026-08-24)
- https://api.openfigi.com/v3/mapping (live test 2026-08-24)

### 12. Stooq has gone behind a JavaScript proof-of-work bot wall — a commonly recommended free fallback is now dead for scripts  
`confidence: high`

Verified live 2026-08-24: GET https://stooq.com/q/d/l/?s=aapl.us&i=d no longer returns CSV. It returns an HTML challenge page containing a SHA-256 proof-of-work loop ('const c="AAAA...",d=4... while(1){digest(c+n)...}') that posts to /__verify before reloading. The legacy quote endpoint https://stooq.com/q/l/?s=eurusd&f=sd2t2ohlcv&h&e=csv returns a 'page does not exist' notice. By contrast, Yahoo Finance's unofficial endpoints still respond: https://query1.finance.yahoo.com/v8/finance/chart/AAPL?range=5d&interval=1d returned HTTP 200 with regularMarketPrice 310.34 for AAPL, and .../EURUSD=X returned HTTP 200. Yahoo's Terms of Service prohibit automated access without written permission; hiQ v. LinkedIn (2022) limited CFAA exposure for public data but does not override contract terms. The Yahoo API was formally deprecated in 2017 — yfinance and yahooquery scrape internal endpoints that Yahoo changes, rate-limits and blocks without notice.

**Why it matters.** Two of the three canonical 'free fallback' recommendations are now materially worse than the internet believes: Stooq is script-hostile as of today, and Yahoo is a ToS violation with no stability contract. A plan that lists them as the resilience layer has no resilience layer. Free sources belong in the product only as clearly-labelled, non-load-bearing enrichment, never as the failover for the price the user trades on.

- https://stooq.com/q/d/l/?s=aapl.us&i=d (live test 2026-08-24)
- https://query1.finance.yahoo.com/v8/finance/chart/AAPL (live test 2026-08-24)
- https://scrapfly.io/blog/posts/guide-to-yahoo-finance-api
- https://www.promptcloud.com/blog/scrape-yahoo-finance/

### 13. Delayed data is genuinely free from the SIPs — but only if you display the delay notice, and vendor 'delayed' tiers still charge  
`confidence: high`

UTP Plan Data Policies: the Delay Interval is 15 minutes; vendors may delay UTP Information and 'there is no charge for UTP Delayed Information distributed on Controlled Products' if delayed for the appropriate timeframe — fees may apply on an Uncontrolled product. The delay message must appear prominently on ALL displays containing delayed data, including wallboards, tickers, mobile devices and audio/voice response; on a ticker it must be interspersed at least every 90 seconds. CTA's Delayed Market Data policy requires 'Prices delayed 15 minutes' to be conspicuously displayed on all screens showing delayed data. Separately, Nasdaq's own PROPRIETARY delayed products are not free: the price list shows a Monthly Administrative Fee of $50.00 per firm for Delayed Data Products and $100.00 per firm for Real-Time Data Products (flat 2025–2027). Commercially, vendor 'delayed' tiers cost real money regardless: Massive Starter $29/mo and Developer $79/mo are both 15-minute delayed.

**Why it matters.** Two traps. First, the 15-minute exemption is conditional on a UI obligation — a terminal showing delayed prices must render a persistent, prominent delay banner, and a ticker must re-state it every 90 seconds. That is a design requirement, not legal boilerplate, and it should be built as a non-dismissible component bound to the entitlement state. Second, 'delayed = free' is false at the vendor layer; the saving from choosing delayed is $170/month against Massive Advanced, not the whole bill.

- https://www.utpplan.com/DOC/datapolicies.pdf
- https://www.ctaplan.com/publicdocs/ctaplan/notifications/trader-update/Policy%20-%20Delayed%20Market%20Data.pdf
- https://www.nasdaqtrader.com/content/ProductsServices/PriceList/Nasdaq_US_Equities_Price_List_2025_2026_2027.pdf
- https://massive.com/pricing

### 14. CUSIP/ISIN carry a licence fee that FIGI does not — and there is a 500-identifier free threshold worth designing around  
`confidence: medium`

CUSIP Global Services (CGS) assigns both CUSIPs and US ISINs; a US ISIN is derived directly from the CUSIP by prefixing 'US' and appending a check digit. CGS licence fees scale with breadth: an end user touching more than 40,000 securities across four or more business lines in three or more regions could face on the order of $477,750 in fees. Critically, CGS states that no licence fee is required where the number of CGS identifiers accessed and used by the end-user customer is fewer than 500. A class action filed against S&P Global, CGS, the American Bankers Association and FactSet (which took over CGS operation) alleges decades of conspiracy to eliminate competition in CUSIP use and seeks over USD 1 billion; no settlement was found as of this research. By contrast OpenFIGI (Bloomberg's open symbology) is free, unauthenticated at 25 requests/60s (verified today), and returns compositeFIGI and shareClassFIGI which solve the share-class and cross-venue identity problems that tickers cannot.

**Why it matters.** A naive plan stores CUSIP everywhere because that is what filings use, and unknowingly creates a licensing liability that scales with coverage. The correct design is FIGI as the internal primary key, CUSIP/ISIN stored only for the securities the user actually holds or watches — which keeps the count under 500 and inside the no-fee threshold — and ticker treated as a mutable display label, never a key.

- https://www.cusip.com/services/license-fees.html
- https://www.waterstechnology.com/regulation/7936086/class-action-lawsuit-takes-aim-at-cusip-sp-factset-aba
- https://assetidbridge.com/the-hidden-costs-of-cusip-licensing-and-how-to-mitigate-them/
- https://api.openfigi.com/v3/mapping (live test 2026-08-24)

### 15. Survivorship bias is a paid problem: the vendors that solve it are named, cheap, and different from the streaming vendors  
`confidence: high`

Norgate Data (verified pricing pages): US Stocks 6-month subscriptions $148.50 (Silver), $198.00 (Gold), $346.50 (Platinum), $433.13 (Platinum Plus); 12-month $270.00 (Silver), $360.00 (Gold), $630.00 (Platinum), $787.50 (Platinum Plus) — Platinum at $630/12mo is ~$52.50/month. Silver covers currently-listed major exchange equities and indices with 10 years of history; Gold adds extras and fundamentals with 20 years; PLATINUM is the tier that includes DELISTED data, which is what actually removes survivorship bias. Free trials run at Platinum level with 2 years of history, 21 days. Sharadar (via Nasdaq Data Link) SEP covers 21,000+ active AND delisted tickers back to 1998, supplying unadjusted prices, split-adjusted prices, split-and-dividend-adjusted prices, delist reasons and ticker changes; the Core US Equities Bundle spans US Company Fundamentals (1990–), EOD US Stock Prices (1998–), S&P 500 Constituents (1957–), US Insider Holdings (2005–), US Institutional Investors (2013–) and SEC Form 8-K Events (1993–), with separate Professional and Non-Professional licences and professionals required to buy via Nasdaq Data Link. Databento's Corporate Actions ($299/mo) plus Adjustment Factors and Security Master solve the same problem at global scale.

**Why it matters.** None of the cheap streaming vendors give you delisted securities. A terminal for a Buffett-school analyst that cannot show you the chart of a company that went to zero, or that silently omits failures from a screen, is systematically optimistic — the exact bias that ruins judgement. The plan needs a dedicated survivorship-safe history leg at ~$50/month, separate from the real-time leg, and the price-adjustment policy (unadjusted vs split-adjusted vs total-return) must be an explicit, user-visible toggle rather than a hidden default.

- https://norgatedata.com/stockmarketpackages.php
- https://norgatedata.com/prices.php
- https://data.nasdaq.com/databases/SEP
- https://www.quantrocket.com/sharadar/
- https://databento.com/blog/corporate-actions

### 16. Retail/prosumer vendor pricing table, verified from vendor pages on 2026-08-24  
`confidence: high`

TWELVE DATA (twelvedata.com/pricing): Basic free (8 credits/min, 800/day, 3 markets, real-time US equities/ETFs/forex/crypto); Grow $29/mo (55 credits/min, 20+ markets, adds commodities, fundamentals, global EOD); Pro $99/mo (610 credits/min, 500 WS credits, 75 markets, adds EU real-time stocks, delayed AU, fixed income); Ultra $329/mo (2,584 credits/min, 2,500 WS credits, 84 markets). Note: several review sites quote Grow $79 / Pro $229 — the vendor page today says $29 / $99, so treat third-party quotes as stale. TIINGO (tiingo.com/pricing): Starter $0 (500 unique symbols/mo, 50 req/hr, 1,000 req/day, 1 GB/mo); Power $30/mo (109,755 symbols/mo, 10,000 req/hr, 100,000 req/day, 40 GB/mo); both include Tiingo EOD Composite Prices, Tiingo Crypto, IEX feed, Tiingo News with 3-month queryable history; BOTH are 'Internal Use Only — you may not display or share the data with another person or organization'. FMP (site.financialmodelingprep.com/pricing-plans, annual billing): Basic free (250 calls/day, EOD); Starter $22/mo (300 calls/min, 5y history, US); Premium $59/mo (750 calls/min, 30y history, UK+Canada, intraday, technicals); Ultimate $149/mo (3,000 calls/min, global, transcripts, ETF/mutual fund holdings, 13F institutional holdings, 1-minute intraday, bulk). Trailing-30-day bandwidth caps: Free 500MB, Starter 20GB, Premium 50GB, Ultimate 150GB, Enterprise 1TB+. FMP states 'Displaying or redistributing data sourced from FMP requires a specific Data Display and Licensing Agreement with FMP.' EODHD (eodhd.com/pricing): Free $0 (20 calls/day); EOD Historical All-World $19.99/mo ($199/yr); EOD+Intraday All-World Extended $29.99/mo ($299.90/yr); Fundamentals Data Feed $59.99/mo ($599.90/yr); ALL-IN-ONE $99.99/mo ($999.90/yr, includes 15-min delayed live, intraday, real-time WebSocket, news API, options API); paid plans 100,000 calls/day and 1,000 calls/min. IQFEED/DTN (iqhelp.dtn.com/core-service-fees, as of 2025-12-01): Forex-only $50.47/mo, $0 startup; Full IQFeed core service $108.15/mo, $50 startup, exchange fees extra; add-ons RT US Futures & Futures Options $24.87/mo, RT Equity Options $60.90/mo, Level II market depth ~$20–24.15/mo, RT International Exchanges $36.75/mo; exchange fees range from $1.05/mo (delayed NYMEX) to $401.00/mo (Nasdaq Level II professional) and are NON-REFUNDABLE once entitled. ALPACA: Algo Trader Plus $99/mo (full SIP real-time, OPRA options, up to 10,000 requests/min); Basic free (IEX). ALPHA VANTAGE: free 25 requests/day (5/min); Premium $49.99 / $99.99 / $149.99 / $199.99 / $249.99 for 75 / 150 / 300 / 600 / 1,200 requests per minute — $49.99 tier is 15-minute delayed, $99.99 and above include real-time US. MARKETSTACK: free 100 requests/month, EOD, 1 year history; paid from ~$9.99/mo (10,000 requests) to $49.99 (100,000) and $149.99 (500,000). TRADERMADE: FX & Crypto £599/month and CFDs £599/month (REST, live tick, historical, timeseries minute, historical tick, WebSocket, business use); Enterprise custom with white-labelling/redistribution rights, 99.99% SLA, 25+ years history; FIX API from ~GBP 299/month. FINNHUB: free tier 60 API calls/min with WebSocket up to 50 symbols, personal non-commercial only; Premium approximately $11.99–$99.99/mo with institutional data sold as add-ons. BARCHART ONDEMAND: from ~$500/month, usage-based.

**Why it matters.** This is the shopping list with real numbers, and it exposes two structural facts. First, the vendors cluster: $20–30 buys EOD/delayed, ~$100 buys a real-time-ish feed with fundamentals, ~$200 buys genuine real-time, and £599+ buys FX with business-use rights. Second, almost every cheap tier is 'internal use only' or requires a separate display licence — Tiingo and FMP say so explicitly. Since this terminal is internal-use-only by design, those clauses are satisfied; but they also mean none of these vendors can ever be the basis of a shipped product without renegotiation.

- https://twelvedata.com/pricing
- https://www.tiingo.com/pricing
- https://site.financialmodelingprep.com/pricing-plans
- https://eodhd.com/pricing
- https://iqhelp.dtn.com/core-service-fees/
- https://tradermade.com/pricing

### 17. Institutional feeds are two orders of magnitude away and should be explicitly ruled out, with numbers, so the decision never gets relitigated  
`confidence: medium`

Bloomberg Terminal ~$31,980/year per seat (~$2,665/month) in 2026, typically on 2-year contracts with monthly instalments; BLPAPI is bundled with the Terminal, but B-PIPE, SAPI and Data License are separate negotiated enterprise products — reported ranges are B-PIPE roughly $2,000–$3,000/month at the low end and $50,000–$200,000+/year in typical enterprise form, Data License $5,000–$50,000+/year, bespoke enterprise feeds $100,000+/year. LSEG Workspace base platform typically $1,500–$3,000 per user per month, with data entitlements charged separately at $500–$2,000+/user/month and premium content $200–$1,000+/user/month; roughly $22,000/user/year typical, with a stripped-down variant from ~$3,600/user/year; 10–25 user deployments commonly $150,000–$400,000 annual contract value. Xignite (acquired by QUODD, February 2023) does not charge per API call — unlimited usage, priced by asset class, call frequency and region. Exegy's own published analysis puts FPGA feed handlers at ~$100,000 per market (~$2.2M including one-time hardware) and ~$1.8M/year for 18 North American markets. OPRA scale for context: July 2026 projections of 1,564 million messages per 100ms and 311 million per 10ms, ~1.562 Gbps per 100ms; April 2025 peak 1ms bursts exceeded 23.7 million packets/second (~187 million messages/second); 40–100 Gbps networking is standard for raw OPRA, and taking both redundant multicast streams doubles the requirement before retransmission headroom.

**Why it matters.** The user thinks like an institutional analyst and will ask 'why not Bloomberg'. The answer must be numeric and pre-loaded: Bloomberg is ~$2,665/month for a seat you cannot programmatically extend without B-PIPE, versus ~$310–660/month for a stack you own. The OPRA numbers also establish the boundary of the ambition — raw multicast feed handling is a $1.8M/year discipline, and the terminal should consciously buy normalised data rather than pretend to that tier.

- https://costbench.com/software/financial-data-terminals/bloomberg-terminal/
- https://www.vendr.com/marketplace/refinitiv
- https://www.xignite.com/pricing/
- https://www.exegy.com/quantify-the-true-cost-market-data/
- https://cdn.opraplan.com/documents/notices/OPRA_Capacity_Projections_Update_0925.pdf
- https://databento.com/blog/beyond-40-gbps-processing-opra-in-real-time

### 18. Message-rate reality: design for bursts, not averages, and build conflation in from day one  
`confidence: medium`

OPRA's own capacity framework publishes projections in messages per 100 milliseconds and uses a 10-millisecond interval to reflect burst utilisation — an explicit instruction to size for bursts. For equities SIPs, historical peak references include UTP UQDF ~362,000 quotes/second and CQS ~958,000 quotes/second average peaks (Q3 2019), with CTA capacity specifications of 392,000 messages per 100ms on the quote feed and 86,000 on the trade feed; UTP UQDF's 5-second peak rate grew 15x between February 2005 (3,789 msg/s) and February 2013 (57,685 msg/s). marketdatapeaks.net publishes current message, burst, packet and packet-burst rates for US feeds. Practical consequences for a WebSocket-fed desktop app: at the 09:30 open and 15:55–16:00 close, a naive one-render-per-message UI will fall behind and then either lag or drop; the correct pattern is a lock-free ingest thread writing to a last-value cache, with the UI sampling at frame rate (conflation), plus explicit sequence-number tracking and a snapshot+delta reconciliation path so a gap triggers a fresh snapshot rather than a silently wrong book.

**Why it matters.** The commonest failure of a home-built terminal is not that it cannot get data, it is that it degrades invisibly under load — the book drifts, the tape falls behind, and the trader does not know. Conflation, sequence gap detection, snapshot re-request, and a visible feed-health indicator are core features, not polish. Clock discipline matters too: exchange timestamps are nanosecond (Massive's FX quotes carry nanosecond participant_timestamp; Nasdaq halt RSS carries millisecond halt times), so the app must store exchange time and local receipt time separately and never sort by local time.

- https://cdn.opraplan.com/documents/notices/OPRA_Capacity_Projections_Update_0925.pdf
- https://databento.com/microstructure/sip
- https://marketdatapeaks.net/about.html
- https://www.utpplan.com/DOC/UtpBinaryOutputSpec.pdf
- https://massive.com/docs/flat-files/forex/quotes.md

### 19. 'Non-display use' is the sleeping liability for an analysis terminal, because analysis is arguably not display  
`confidence: medium`

Non-display fees are charged separately from, and are vastly larger than, display/device fees. NYSE Integrated non-display is $22,400/month per category (Categories 1, 2 and 3; Category 3 billed per platform, capped at 3 platforms / $67,200) versus $16.00/month for a non-professional display device. NYSE OpenBook non-display $6,000/mo, NYSE BBO non-display $1,500/mo, NYSE Trades non-display $3,000/mo. Nasdaq Depth Non-Display (Direct Access only) is $412 per subscriber for 1–39 subscribers in 2026, with a Non-Display Platform fee of $5,480 per trading platform (max $16,440); Databento documents a $76/subscriber/month Nasdaq Depth Non-Display Usage fee for its delivery and $375/non-display subscriber for RAW delivery. Under the CT Plan the equivalent fees rise: Non-Display (ETS/Own Behalf/For Customer) Tape A $2,000 -> $2,315, Tape B $1,000 -> $1,155, Tape C $3,500 -> $2,025 each for Last Sale and Bid-Ask. Both NYSE and Nasdaq levy a Late Non-Display Declaration fee ($1,000 at NYSE per product; $6,000 for BQT) — meaning you are expected to affirmatively DECLARE your non-display usage.

**Why it matters.** This terminal's whole point is that it computes — screens, scores, ranks, alerts, and feeds an AI knowledge layer. A strict reading is that any real-time datum used to drive logic rather than pixels is non-display use. For a single non-professional using vendor-normalised data the practical exposure is low, but the plan must (a) get this in writing from the chosen vendor, (b) keep AI/derived-analytics pipelines fed from delayed or EOD data where possible, and (c) remember that exchanges expect an affirmative declaration and fine you for filing it late. This is the single most likely source of an unpleasant surprise invoice.

- https://www.nyse.com/publicdocs/nyse/data/NYSE_Market_Data_Pricing.pdf
- https://www.nasdaqtrader.com/content/ProductsServices/PriceList/Nasdaq_US_Equities_Price_List_2025_2026_2027.pdf
- https://www.sec.gov/files/rules/sro/nms/2026/34-105125.pdf
- https://databento.com/blog/understanding-exchange-fees
- https://www.utpplan.com/DOC/NonDisplayDeclaration.pdf

### 20. OANDA v20 gives free streaming FX with an account, but it is a dealer's price, not a market price — and it is not a data licence  
`confidence: medium`

The OANDA v20 REST API has no per-call price, but it cannot be used without an OANDA account; the live environment requires the same KYC, residency checks and (in many regions) minimum deposits as opening a brokerage account (US minimum deposit reported as $0 as of February 2026). Authentication is via a personal access token generated in the account. The API provides REST endpoints for accounts, instruments and candles, plus streaming endpoints for live pricing and transaction confirmation; candle aggregation is server-side. Critically, OANDA does not publish an unlimited historical tick archive via the API — true tick-by-tick history requires capturing the stream yourself. OANDA's Exchange Rates Data API is a separate standalone commercial data product sold apart from fxTrade. Free/cheap historical alternatives: Dukascopy publishes free tick-by-tick bid/ask history (15+ years, 60+ instruments) from its ECN liquidity pool via its Historical Data Export tool, subject to a data usage agreement; HistData.com offers free historical FX in platform-import formats. TraderMade provides tick data since 2016, minute since 1990, at £599/month for business use. LMAX Exchange provides firm limit-order FX data from London, New York, Tokyo and Singapore with monthly market and trade data fees effective 2026-06-01.

**Why it matters.** The right FX design is deliberately plural: OANDA (or LMAX) as the dealable/tradable price the user could actually transact on, an aggregated vendor composite for context, ECB/Frankfurter for the official reference rate, and Dukascopy for free deep tick history to backtest against. Each must be labelled. Also note the trap: a broker-account API is an account entitlement, not a data licence — it carries the same 'own use only' constraint as IBKR, and building history by capturing the stream is the only way to get ticks, which makes a local tick recorder a day-one component rather than a later feature.

- https://developer.oanda.com/rest-live-v20/authentication/
- https://help.oanda.com/us/en/faqs/rest-v20-api-troubleshooting-guide.htm
- https://www.dukascopy.com/swiss/english/marketwatch/historical/
- https://tradermade.com/pricing
- https://www.lmax.com/exchange/market-data-access

### 21. Vendor terms of service on caching, storage and derived works are stricter than the pricing pages imply  
`confidence: high`

Massive (Polygon) Market Data Terms of Service (massive.com/terms/market_data_terms.pdf, last updated 2024-10-09) prohibits redistributing, displaying, disseminating, duplicating, licensing, sublicensing, publishing, broadcasting, transmitting or otherwise transferring Market Data OR ANY DERIVED WORKS to any third party, or using Market Data for business or commercial purposes, absent prior express written consent; the general Massive terms grant only a non-exclusive, non-transferable right to use the Services for the Customer's internal purposes, plus a limited right to use Information in websites or software applications owned or licensed by the Customer. Massive's business-facing terms are now the 'Massive for Businesses Terms of Service' (superseding the prior Commercial Use ToS). Tiingo's plans are marked 'Internal Use Only — you may not display or share the data with another person or organization.' FMP states that displaying or redistributing FMP-sourced data requires a specific Data Display and Licensing Agreement. Intrinio's Individual plan is explicitly 'No redistribution or display', 1 seat, personal use only. IQFeed exchange fees are non-refundable once entitled. Databento's Standard plan does NOT include external distribution rights — those begin at Plus ($1,750/mo).

**Why it matters.** 'Derived works' is the clause that matters most for the AI knowledge layer. If Claude authors a knowledge base that embeds vendor prices, that artefact may itself be a derived work bound by the same no-redistribution terms — meaning the knowledge base cannot be published, shared, or even synced to a third-party service without breaching. The plan should keep vendor-sourced numbers out of any artefact that leaves the machine, and prefer regulatory/free sources (SEC, FINRA, ECB) for anything the AI layer produces as shareable output.

- https://massive.com/terms/market_data_terms.pdf
- https://massive.com/legal/businesses-terms-of-service
- https://www.tiingo.com/pricing
- https://site.financialmodelingprep.com/pricing-plans
- https://intrinio.com/pricing
- https://databento.com/pricing

### 22. Global (non-US) equities are the coverage cliff, and the cheap vendors handle them very differently  
`confidence: medium`

The US-centric vendors degrade sharply outside the US. Twelve Data tiers coverage explicitly by market count: Basic 3 markets, Grow 20+, Pro 75 (adds EU real-time stocks, delayed AU, fixed income), Ultra 84. FMP gates geography by tier: Starter US only, Premium adds UK and Canada, Ultimate adds global coverage plus transcripts, 13F and ETF/mutual-fund holdings. EODHD's proposition is explicitly 'All-World' EOD from $19.99/mo with intraday at $29.99/mo, making it the cheapest broad international EOD source found. Massive's Stocks plans are US-centric, with partner datasets (TMX for Canada, ETF Global) sold at $99/month each. Norgate covers US, Australian and Canadian markets. Databento's corporate actions reach 215 exchanges and 310,000+ securities but its live equity coverage is US venues. For genuinely global real-time across Europe and Asia the realistic answers are IQFeed's RT International Exchanges add-on ($36.75/mo plus per-exchange fees), IBKR's per-exchange non-professional subscriptions, or an enterprise vendor (LSEG, ICE Consolidated Feed, QUODD).

**Why it matters.** A 'global equities' terminal built on a US stack will quietly be a US terminal with delayed foreign EOD. The plan should be explicit about the tiering: US real-time with depth, developed-market EOD plus delayed intraday, and everything else reference-only — and the UI should show coverage class per symbol so the user always knows whether he is looking at a live market or a stale one. Note also that each foreign exchange has its own subscriber agreement and fee schedule; a single vendor subscription does not eliminate per-exchange entitlement paperwork.

- https://twelvedata.com/pricing
- https://site.financialmodelingprep.com/pricing-plans
- https://eodhd.com/pricing
- https://iqhelp.dtn.com/core-service-fees/
- https://www.interactivebrokers.com/en/pricing/market-data-pricing.php
- https://databento.com/blog/corporate-actions

## Recommended decisions

### What is the primary US equities real-time feed?

**Recommendation.** Massive (formerly Polygon.io) Stocks Advanced at $199/month.

**Rationale.** It is the only sub-$250 tier verified today that gives genuine real-time consolidated US equity data with unlimited API calls, WebSocket streaming, tick-level trades and quotes, 20+ years of history, and S3 flat files for cheap bulk backfill — all under one flat fee with no per-exchange entitlement paperwork. For a single-user internal-use terminal the ToS constraints (no redistribution, no derived works to third parties, internal purposes only) are satisfied by construction. The flat-file S3 product is the decisive extra: it makes gap-fill and history loading nearly free in operational terms, which metered vendors do not.

**Rejected.** Databento Standard ($199/mo) rejected as the always-on spine because metered historical bytes plus $299/mo corporate actions plus pass-through exchange fees make the monthly bill unpredictable — it is better used as a research leg. Alpaca Algo Trader Plus ($99/mo, full SIP, 10,000 req/min) is genuinely cheaper and was a close second, but it is a broker data entitlement with the attendant own-use framing and thinner historical depth. Intrinio Individual ($150/mo) rejected because EquitiesEdge is a modelled FMV price, not exchange data. Alpha Vantage rejected on rate limits (1,200 req/min at $249.99 is worse value than unlimited at $199).

**Cost.** $199/month

### What provides depth, microstructure and survivorship-safe history?

**Recommendation.** Databento on the Usage-based (pay-as-you-go) plan for historical, escalating to Standard ($199/mo) only when live depth is genuinely needed; plus Norgate Data Platinum at $630/12 months (~$52.50/month) for delisted-inclusive US history.

**Rationale.** Databento US Equities spans 15 exchanges and 30 ATSs with MBP-10 and MBO schemas and a Security Master carrying FIGI/ISIN/CFI/CIK back to 2005 — nothing at this price point matches it for order-book research. Metering by uncompressed bytes means research bursts are cheap and idle months cost nothing. Norgate Platinum is the specific tier that includes delisted data, which is the only thing that actually removes survivorship bias, at a trivial ~$52/month.

**Rejected.** Sharadar via Nasdaq Data Link is comparable in quality (21,000+ active and delisted tickers to 1998, with delist reasons and ticker changes) and should be revisited if Norgate's coverage proves thin, but its pricing is gated behind login and licence selection, making it harder to commit to at plan time. Building survivorship handling from a streaming vendor's data is not an option — none of them carry dead securities.

**Cost.** ~$50–250/month depending on research intensity; Norgate ~$52.50/month fixed

### What is the independent cross-check / failover leg?

**Recommendation.** Interactive Brokers non-professional market data: US Securities Snapshot and Futures Value Bundle $10.00 + US Equity and Options Add-On Streaming Bundle $4.50 + NASDAQ TotalView-OpenView $16.50 ≈ $31.00/month, consumed via the TWS or Web API strictly for the account holder's own use.

**Rationale.** For $31/month this is genuinely exchange-licensed NBBO plus full Nasdaq depth — cheaper than any pure data vendor because the user is consuming his own entitlements as an account holder, and legally clean for that exact reason. As a second, independently-sourced price leg it catches vendor outages, stale caches and bad ticks that a single-source terminal would display with total confidence.

**Rejected.** IQFeed rejected as the cross-check on cost and rigidity: $108.15/month core plus ~$20–24 Level II plus non-refundable exchange fees, for data the primary vendor already supplies. Free sources rejected outright as a failover — Stooq is now behind a JavaScript proof-of-work wall (verified today) and Yahoo's unofficial endpoints breach its ToS and carry no stability contract. IBKR's constraints must be respected: 3–60 concurrent L2 symbols depending on data allowance, no pro-rating, and an absolute prohibition on redistributing API data to third parties.

**Cost.** ~$31/month (non-professional); ~$260/month if status flips to professional

### How is FX sourced and labelled?

**Recommendation.** A deliberately plural stack: OANDA v20 streaming (free with an account) as the dealable price; Massive Currencies Developer at $79/month as the aggregated composite and historical archive; ECB Data Portal EXR (free, no auth, verified live today) as the official reference rate; Dukascopy free tick export for deep backtest history. Every FX quote in the UI carries source and quote-type labelling. Add a local tick recorder from day one.

**Rationale.** FX is OTC and fragmented — the BIS Triennial put April 2025 turnover at ~$9.5–9.6tn/day with no consolidated tape, and Massive's own FX schema proves the point by carrying a single bid_exchange/ask_exchange contributor ID rather than an NBBO. There is no single true price, so the honest design shows several and makes the spread between them visible. The tick recorder is mandatory because OANDA publishes no unlimited historical tick archive via the API.

**Rejected.** TraderMade rejected at £599/month (~$760) — its business-use rights are worth nothing to an internal-use single-user terminal. LSEG WMR 4pm fix data deferred: it is the institutional benchmark and a Critical Benchmark under UK BMR, but licensing it is an enterprise conversation; show the fix time as a calendar event and the rate only if a licence is later obtained. CLSMarketData (50%+ of global FX volume for 18 CLS-settled currencies) is genuinely differentiated for flow analysis but is an institutional subscription with no published retail pricing.

**Cost.** $79/month (OANDA, ECB and Dukascopy are free)

### What covers global (non-US) equities and fundamentals?

**Recommendation.** EODHD ALL-IN-ONE at $99.99/month ($999.90/year) for All-World EOD, intraday, fundamentals, news and options; plus FMP Ultimate at $149/month (annual billing) for 13F institutional holdings, insider transactions, earnings-call transcripts and ETF/mutual-fund holdings that feed the incentives pillar.

**Rationale.** EODHD is the cheapest verified broad international EOD source ($19.99/month for All-World EOD alone) and its All-In-One bundle collapses several separate subscriptions into one line. FMP Ultimate is the tier where the ownership and insider datasets unlock — precisely the second pillar of this product — at 3,000 calls/minute and 150GB trailing-30-day bandwidth.

**Rejected.** Twelve Data Pro ($99/month, 75 markets including EU real-time) is a reasonable substitute for EODHD and should be reconsidered if real-time European equities matter more than breadth of EOD coverage. Intrinio rejected on the FMV/derived-price issue. Bloomberg and LSEG rejected on cost: ~$2,665/month per Bloomberg seat and $1,500–$3,000/user/month base for LSEG Workspace before data entitlements — roughly 4–10x the entire recommended stack.

**Cost.** $99.99 + $149.00 = ~$249/month (or ~$100/month if FMP is dropped to Premium at $59)

### What is the symbology and identifier strategy?

**Recommendation.** FIGI as the internal primary key via free OpenFIGI v3 (verified working unauthenticated at 25 requests per 60 seconds), with composite and share-class FIGI both stored. Ticker is a mutable display label with change history. CUSIP and ISIN are stored ONLY for securities the user actively holds or watches, deliberately keeping the count under CGS's 500-identifier no-fee threshold.

**Rationale.** FIGI is free, open, and solves share-class and cross-venue identity, which tickers cannot. CUSIP/ISIN carry real licence exposure that scales with breadth — reportedly up to ~$477,750 for broad multi-region use — and CGS is currently the subject of a class action alleging conspiracy to eliminate competition. Staying under 500 identifiers is a designed-in cost control, not an accident.

**Rejected.** Ticker-as-primary-key rejected outright: ticker reuse after delisting silently corrupts history and screens. Buying a CUSIP licence rejected as disproportionate for a single-user tool. RIC rejected as it is LSEG-proprietary and unavailable without a Workspace/Datascope relationship.

**Cost.** $0/month

### How much real-time data should feed automated analytics and the AI knowledge layer?

**Recommendation.** As little as possible. Route the AI knowledge base, scanners, scoring and alerting off delayed or end-of-day data and off free regulatory sources (SEC, FINRA, ECB, OpenFIGI). Reserve real-time data for the display surfaces the user is actually looking at, and obtain written confirmation from Massive that the intended computation is display use.

**Rationale.** Non-display fees are the largest silent liability in this domain: NYSE Integrated non-display is $22,400/month per category against $16.00/month for a non-professional display device, and both NYSE and Nasdaq levy late-declaration penalties ($1,000, and $6,000 for BQT) because they expect an affirmative declaration. A terminal whose defining feature is computation is exactly the profile that attracts the question. Separating the analytics substrate from the display substrate makes the answer defensible and cheap. It also solves the derived-works problem: vendor ToS forbid transferring derived works to third parties, so any AI-authored artefact intended to be shareable must be built from free/regulatory sources only.

**Rejected.** Feeding everything from the real-time stream because it is 'already paid for' rejected — that is the assumption that generates the surprise invoice. Ignoring non-display entirely rejected as an unquantified risk on a multi-year build.

**Cost.** $0 incremental if designed this way; potentially $1,500–$22,400/month per product if not

### What does the whole stack cost, at three tiers?

**Recommendation.** HOBBY ~$29–50/month: Massive Starter $29 (15-min delayed, unlimited calls, 5y history) plus free ECB/Frankfurter FX, free FINRA Reg SHO, free NYSE and Nasdaq halt feeds, free OpenFIGI. Buys a legitimate, legally clean delayed terminal with the full incentives pillar intact. SERIOUS SOLO ~$310/month: Massive Stocks Advanced $199 + Massive Currencies Developer $79 + IBKR non-professional cross-check ~$31, plus all the free sources. Buys real-time US equities with tick-level trades and quotes, a genuine second price leg, and FX with honest labelling. SEMI-PRO ~$660/month: adds EODHD ALL-IN-ONE $99.99 (global EOD, fundamentals, news, options), FMP Ultimate $149 (13F, insiders, transcripts, holdings), Norgate Platinum ~$52.50 (delisted-inclusive history), and a Databento usage-based research allowance ~$50. Buys global coverage, the full ownership/insider dataset, survivorship-safe backtesting and order-book microstructure.

**Rationale.** The tiers are structured so each step buys a distinct capability rather than more of the same: hobby buys legality and the free regulatory pillar; serious solo buys real-time truth and redundancy; semi-pro buys breadth, history integrity and microstructure. Start at serious solo — the $199 real-time step is the one that changes the product's character, and the $31 IBKR cross-check is the cheapest insurance in the entire stack.

**Rejected.** Anything above ~$700/month rejected: the next rung up is institutional (Bloomberg ~$2,665/month per seat, LSEG Workspace $1,500–$3,000/user/month before entitlements, Barchart OnDemand from ~$500/month, Exegy feed handlers ~$100,000 per market) and buys capabilities this product has deliberately scoped out — order execution, multi-user distribution and raw multicast feed handling.

**Cost.** Hobby ~$29–50/mo; Serious solo ~$310/mo; Semi-pro ~$660/mo

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | M | Provenance Chip | Every price, quote and bar on screen carries a compact, hoverable badge stating source venue/vendor, consolidation type (SIP / single-venue / vendor composite / modelled FMV / official reference), latency class (real-time / 15-min delayed / EOD), and exchange timestamp vs local receipt time. Clicking opens the full lineage. | All feeds; metadata layer over Massive, Databento, IBKR, OANDA, ECB |
| P0 | M | Entitlement & Status Console | A first-class settings surface modelling subscriber status (professional vs non-professional, under BOTH the current registration-based test and the CT Plan's incoming use-based test), per-exchange entitlements, display vs non-display declarations, and delayed-data obligations. Drives feature gating and the delay banner automatically. | Nasdaq/NYSE/Cboe fee schedules; CT Plan fee schedule; vendor entitlement APIs |
| P0 | S | Delay Compliance Banner | Non-dismissible, prominently placed 'Prices delayed 15 minutes' indicator bound to entitlement state, with ticker components re-stating the notice at least every 90 seconds as UTP policy requires. Automatically disappears when a real-time entitlement is active. | UTP Data Policies; CTA Delayed Market Data Policy |
| P0 | L | 23/5 Session Engine | A session model that treats a trading day as a named, venue-specific interval rather than a calendar date — supporting the 2026-12-06 UTP 23/5 schedule (Sun 21:00 ET to Fri 20:00 ET with a nightly maintenance hour), 24X's overnight session, pre/post market, and per-exchange holiday calendars. Bars, 'previous close', and session VWAP all resolve through it. | UTP Vendor Alert 2026-24; 24X Exchange calendar; exchange holiday calendars |
| P0 | L | FIGI-Keyed Security Master | Internal identity spine keyed on FIGI (composite and share-class), with ticker as a mutable display label carrying full change history, plus delisting records, and CUSIP/ISIN stored only for actively watched or held names to stay under the CGS 500-identifier no-fee threshold. | OpenFIGI v3 (free, 25 req/60s unauth); Databento Security Master; Sharadar TICKERS/ACTIONS |
| P0 | L | Survivorship-Safe Universe | Every screen, backtest and historical chart runs against a point-in-time universe that includes delisted and dead securities, with delist reason surfaced. A visible 'graveyard' toggle lets the user see what a screen would have excluded. | Norgate Platinum (delisted data); Sharadar SEP/ACTIONS; Databento corporate actions |
| P0 | M | Adjustment Policy Switch | Explicit, per-chart and per-study control over unadjusted vs split-adjusted vs split-and-dividend (total return) prices, with the applied adjustment factor and its source shown, and corporate action markers rendered on the chart axis. | Databento Adjustment Factors ($299/mo tier); Massive splits/dividends endpoints; Sharadar SEP; Norgate |
| P0 | M | Feed Health Monitor | Always-visible panel showing per-feed connection state, sequence-gap count, messages/second versus expected, conflation ratio currently applied, last snapshot reconciliation time, and clock skew between local and exchange time. | WebSocket sequence numbers from Massive/Databento/IBKR; NTP/local clock |
| P0 | L | Conflated Tape & Book Renderer | Lock-free ingest thread writing to a last-value cache, with UI sampling at frame rate; full unconflated tape preserved in the local store while the display conflates. Snapshot+delta reconciliation with automatic re-snapshot on sequence gap. | Databento MBP-10/MBO; Massive WebSocket; IBKR TWS depth |
| P0 | M | FX Quote Triangulation Panel | For any pair, shows side by side: the dealable bid/ask from a broker venue (OANDA/LMAX), a vendor aggregate composite, the ECB daily reference rate at 14:15 CET, and the WMR 4pm London fix where licensed — with the spreads between them made explicit. | OANDA v20 streaming; Massive Currencies; ECB Data Portal EXR (free, verified); LSEG WMR (licensed) |
| P1 | M | Local Tick Recorder | Continuously captures and persists the raw FX and equity streams to a local columnar store, because OANDA and most broker APIs publish no unlimited historical tick archive. Doubles as the gap-fill source and the audit trail. | OANDA v20 stream; Massive WebSocket; Databento live |
| P1 | S | Halt, LULD & SSR Ribbon | Real-time ribbon of trading halts, LULD pauses (including the new overnight indicators G and H arriving 2026-12-06), limit-up/limit-down bands, and short-sale-restriction state, sourced from free official feeds. | NYSE trade-halts CSV (free, verified); Nasdaq Trader halts RSS (free, verified); SIP LULD band messages |
| P1 | S | Short Pressure Tracker | Daily short volume as a share of total volume per symbol, short-exempt volume, trend over time, and cross-reference against Nasdaq Short Interest, with correct handling of fractional volume values. | FINRA Reg SHO daily files (free, verified, fractional volumes); Nasdaq Short Interest |
| P1 | M | Vendor Cross-Check Arbiter | Runs two independent price legs (e.g. Massive as primary, IBKR as secondary) and flags material disagreement in last price, NBBO or volume, showing both values rather than silently picking one. | Massive Stocks Advanced + IBKR non-professional entitlements |
| P1 | M | Cost & Entitlement Ledger | Tracks actual monthly spend per vendor and per exchange entitlement, metered usage against plan caps (Databento GB, FMP trailing-30-day bandwidth, Twelve Data credits/min, EODHD calls/day), and warns before a tier is breached or a non-refundable exchange fee is triggered. | Vendor usage endpoints; IQFeed exchange fee schedule; Databento usage API |
| P1 | M | Backfill & Gap-Fill Orchestrator | Detects holes in the local bar and tick store (overnight downtime, disconnects, sequence gaps), and repairs them from the cheapest adequate source — flat files first (Massive S3 daily aggregates), then metered historical (Databento), never re-pulling data already held. | Massive flat files (S3); Databento historical (metered by uncompressed bytes); EODHD |
| P1 | S | Coverage Class Indicator | Per-symbol badge showing what this terminal can actually offer for that instrument: US real-time with depth / developed-market EOD plus delayed intraday / reference-only — so global coverage limits are visible rather than implied. | Vendor coverage matrices: Twelve Data market counts, FMP geography tiers, EODHD All-World, IQFeed international add-on |
| P2 | S | Reference Rate & Fix Calendar | Surfaces upcoming FX fixing windows (ECB 14:15 CET, WMR 4pm London), month-end and index-rebalance dates, and flags the elevated-volume windows around them. | ECB Data Portal publication schedule; LSEG WMR methodology; exchange rebalance calendars |
| P1 | M | Derived-Works Firewall | Marks vendor-sourced data as licence-encumbered and blocks it from flowing into any artefact that leaves the machine — including the AI knowledge base, exports and shared reports — while allowing free/regulatory sources (SEC, FINRA, ECB, OpenFIGI) through. | Vendor ToS metadata; source-tagging in the data layer |
| P2 | M | Symbology Resolver Bar | One search box accepting ticker, FIGI, ISIN, CUSIP, company name or exchange-local code, resolving across venues and share classes and showing all known identifiers plus historical ticker changes for the matched security. | OpenFIGI v3 (free); Databento Security Master; Sharadar TICKERS |
| P2 | M | Order Imbalance & Auction Monitor | Opening and closing auction imbalance feeds with indicative match price and paired/imbalance size, rendered against the current book. | Massive NYSE Order Imbalances add-on ($49/mo); Nasdaq FilterView/NOIView; IBKR NYSE Arca Order Imbalances ($1.00/mo non-pro); Databento Imbalance schema |
| P1 | M | Time & Sales with Venue Attribution | Tape showing each print's venue, trade condition codes, odd-lot flag, and off-exchange (TRF/dark) attribution, with filters for block prints and condition-excluded trades. | Databento US Equities trades schema; Massive tick-level trades (Advanced tier); IBKR |

## Risks

- STATUS FLIP RISK (highest impact): under the CT Plan's use-based definition, approved July 2026 and launching with the plan in early 2027, 'any use of market data by or on behalf of any entity... limited liability company' is Professional use. If the trader incorporates for tax or liability reasons, his data costs multiply across every vendor simultaneously — Nasdaq TotalView $15 -> $84, IBKR TotalView $16.50 -> $90, IBKR streaming add-on $4.50 -> $125, tape fees ~$2.70 -> ~$73. He must be warned BEFORE he incorporates, not after.
- SESSION MODEL OBSOLESCENCE: the UTP SIP goes 23/5 on 2026-12-06 with new overnight LULD indicators G and H. Any bar store, chart axis or 'previous close' logic that equates trading day with calendar date will be wrong within four months of launch, and retrofitting a session model into a populated time-series store is a migration, not a patch.
- NON-DISPLAY RECLASSIFICATION: this terminal's defining feature is computation. If a vendor or exchange takes the view that scanning, scoring, alerting and AI ingestion of real-time data constitute non-display use, exposure jumps from tens of dollars to $1,500–$22,400/month per product, plus late-declaration penalties of $1,000–$6,000. Get it in writing before building the analytics pipeline on the live stream.
- DERIVED-WORKS CONTAMINATION OF THE AI LAYER: Massive's terms prohibit transferring Market Data 'or any Derived Works' to third parties; Tiingo is internal-use-only; FMP requires a separate Data Display and Licensing Agreement to display or redistribute. A Claude-authored knowledge base embedding vendor prices may itself be an encumbered derived work, meaning it cannot be synced to a cloud service, shared, or published without breach.
- METERED BILLING BLOWOUT: Databento bills historical by uncompressed bytes, FMP enforces trailing-30-day bandwidth caps (150GB on Ultimate), Twelve Data meters credits per minute, EODHD caps calls per day. A backfill loop with a bug can generate a four-figure invoice in hours. Hard byte and call ceilings must be enforced client-side, not trusted to the vendor.
- NON-REFUNDABLE EXCHANGE ENTITLEMENTS: IQFeed states exchange fees are non-refundable once entitled, and IBKR does not pro-rate market data subscriptions — mid-month starts and stops are charged in full. Experimenting with entitlements is more expensive than it looks.
- FREE-SOURCE COLLAPSE: Stooq is now behind a JavaScript proof-of-work wall (verified 2026-08-24) and its legacy CSV quote endpoint 404s. Yahoo's unofficial endpoints still respond but breach Yahoo's ToS, were formally deprecated in 2017, and are changed, rate-limited and blocked without notice. Any architecture that treats these as the resilience layer has none.
- MODELLED PRICES PRESENTED AS REAL: Intrinio's EquitiesEdge and the various 'FMV' products are derived predicted bid/ask/last, not exchange data — which is precisely why they carry no exchange fees. If such a value ever lands in a field the user reads as a quote, the terminal is lying to him at the exact moment accuracy matters most.
- PARTIAL CONSOLIDATION MISREAD AS FULL: Cboe One consolidates only Cboe's four US equities exchanges, and many 'real-time, no exchange fees' vendor tiers serve it (often 15-minute delayed). A Cboe One last can diverge materially from the consolidated last, especially in NYSE-listed large caps.
- FRACTIONAL AND MALFORMED REGULATORY DATA: FINRA Reg SHO daily files now carry fractional volumes (e.g. 509558.830081) reflecting fractional-share trading. Integer parsers will crash or silently truncate. Free regulatory files change format without release notes and have no SLA.
- GLOBAL COVERAGE ILLUSION: the recommended stack is US-real-time, developed-market-EOD. Marketing the product to oneself as a 'global equities terminal' without a per-symbol coverage indicator will lead to acting on a stale Tokyo or Milan close believing it is live.
- BURST-LOAD SILENT DEGRADATION: OPRA's own guidance is to size for 10ms bursts, not averages; equity SIP quote peaks have historically run into the hundreds of thousands of messages per second. A UI that renders per message will fall behind at the open and close and give no indication that it has.
- VENDOR CONSOLIDATION AND REBRAND CHURN: Polygon.io became Massive (2025-10-30), Xignite was absorbed by QUODD (February 2023), CGS operation moved to FactSet, and the CTA/CQ/UTP plans are being replaced by the CT Plan. Any hard-coded vendor name, base URL or plan document reference has a short half-life.
- CUSIP LICENSING CREEP: the CGS no-fee threshold is fewer than 500 identifiers. A feature that bulk-loads CUSIPs — a full security master import, a 13F parser storing every position's CUSIP — silently crosses it and creates a licensing liability that scales with coverage.

## Open questions

- What is the exact approved CT Plan fee schedule as modified by the SEC in the July 2026 order, and the precise implementation date? The March 2026 order (34-105125) gives the proposed tables in full, but the Commission approved 'as modified' — the specific modification and the go-live date were not confirmed from a primary source and must be read from Release 34-105778 / the 2026-07-01 Federal Register order before any pricing is committed to.
- Will Massive (Polygon) confirm in writing that scanning, alerting, scoring and AI ingestion of its real-time feed on the Advanced plan constitute display use rather than non-display use for a single internal user? This single answer moves the risk envelope by four figures per month.
- Does Massive Stocks Advanced deliver full consolidated SIP (CTA + UTP) data, or a proprietary consolidation of direct feeds? The docs index was reachable but the stocks overview page returned only navigation; this determines whether the on-screen 'last' is the official consolidated last.
- What are Massive's exact Currencies/Forex tier prices and entitlements? The pricing page renders asset-class tabs client-side and only the Stocks table was retrievable; the $29/$79/$199 structure for Currencies is inferred from a secondary source and must be confirmed.
- What are Finnhub's exact current plan names and prices? Both finnhub.io/pricing and finnhub.io/pricing-stock-api-market-data returned only a page header; the $11.99–$99.99 range plus institutional add-ons is from secondary sources and is unverified.
- What is Sharadar's actual monthly price for non-professional versus professional licences via Nasdaq Data Link? Both the Nasdaq Data Link product page and QuantRocket's pricing page gate the numbers behind login and licence selection.
- What does IQFeed's Nasdaq Level II exchange fee actually cost a NON-professional? The core service fees page cites $401.00/month for professionals and a $20–24.15 Level II surcharge, but the non-professional exchange fee line was not isolated.
- What are Barchart OnDemand's and QUODD's actual rate cards? Barchart is 'from ~$500/month, usage-based' and QUODD publishes no monthly figure; both require direct sales contact.
- What is LMAX Exchange's market and trade data fee schedule effective 2026-06-01? The page references a pricing PDF whose figures were not retrieved.
- Is CLSMarketData available at any price point below an institutional subscription, and what would FX Volume/FX Flow cost for a single user? This is the most differentiated FX dataset found and its accessibility is unknown.
- Has the CUSIP/CGS antitrust class action against S&P Global, CGS, the ABA and FactSet settled, and would any settlement change the fee schedule or the 500-identifier free threshold?
- What are Twelve Data's current individual prices definitively? The vendor page today shows Grow $29 / Pro $99 / Ultra $329, while a March 2026 vendor update and several review sites cite Grow $79 / Pro $229 — the discrepancy needs resolving before budgeting.
- What are FMP's MONTHLY (non-annual) prices? The pricing page displays only annual-billing figures ($22/$59/$149) with an 'up to 34% discount' badge, so the true month-to-month cost is unconfirmed.
- Does OANDA's v20 data licence permit storing and re-displaying its streaming prices in a third-party desktop application for the account holder's own use, and does the answer differ between the US, UK and EU entities?
- What are Dukascopy's actual data usage agreement terms for redistributing or storing its free tick history, and does building a local research archive from it fall inside them?
- What are the current per-exchange non-professional fees for the major non-US venues the user cares about (LSE, Xetra, Euronext, TSE, HKEX), and which of the recommended vendors can supply them without separate exchange paperwork?
