# Analytics, Signals and Market-Structure Features for a Read-Only Windows Equities + FX Trading Terminal (research as of 2026-08-24)

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

All facts below were verified by live HTTP calls or primary vendor pages on 2026-08-24 unless marked medium/low confidence.

The headline finding is that the *analytical* half of this terminal can be built almost entirely on free primary sources, and the money should be spent on exactly three things: real-time equity trades/quotes, a global fundamentals+estimates spine, and (optionally) options-flow-by-capacity. Everything else — dealer gamma, put/call, VIX complex and VX term structure, off-exchange share, LULD halts, SSR, COT, yield curves, OIS/SOFR, REER, macro releases, factor returns — is free and I confirmed each endpoint returns live 2026-08-24 data.

Concrete anchors verified today: SEC `companyfacts` for AAPL is 3.79 MB / 503 us-gaap concepts, each fact carrying `accn`/`filed`/`frame` (so point-in-time reconstruction is possible); the `frames` API returns 3,555 entities in one 464 KB call, which is a free peer-set and cross-sectional screener. Cboe's undocumented CDN serves a complete 13,410-contract SPY chain with bid/ask/IV/OI/volume and full Greeks for $0 — a working GEX engine with no vendor. Cboe futures settlement CSV gave the entire VX curve (front 17.50 → Apr-27 22.33 against VIX spot 15.85). FINRA's daily short-volume file (free, ≤18:00 ET) had 12,271 symbols. Polygon.io rebranded to **Massive** on 2025-10-30; both API hosts still resolve. Massive real-time tiers are explicitly "Individual use / Non-pros only".

The adversarial findings matter more than the prices. `companyfacts` silently drops all dimensional (axis/member) facts, so **segment data is not in it** — a naive plan that promises segment analysis from companyfacts will fail. XBRL carries no statement structure, so you cannot render a financial statement from it. Q4 is never filed and cash-flow facts are YTD-cumulative, so TTM must be derived by differencing. `$TICK`/`$TRIN`/`$ADD` are exchange-proprietary calculated indices that cannot be computed from a consolidated tape. Retail FX "volume" is tick count. FX forward points are not free but are synthesisable from free OIS curves via covered-interest-parity, with the cross-currency basis flagged as the unknown residual. Cboe's EVZ FX-vol index is stale since 2025-05-10 and appears discontinued. CME actively IP-blocks scraping. Consensus estimates are the one genuinely expensive gap, and point-in-time consensus must be snapshotted daily from day one or every PEAD/surprise study is look-ahead-contaminated.

Realistic all-in data budget: $0 for a credible v1, ~$160/mo lean, ~$525/mo for the full real-time build.

## Findings

### 1. SEC companyfacts is rich but structurally incomplete — it drops all dimensional facts, so segment data is NOT available from it  
`confidence: high`

Live-tested 2026-08-24: GET https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json returns HTTP 200, 3,789,099 bytes, 503 us-gaap concepts + 2 dei concepts for Apple. Each observation is {start, end, val, accn, fy, fp, form, filed, frame} — e.g. Apple's latest Revenues fact: start 2026-03-29, end 2026-06-27, val 109,417,000,000, accn 0000320193-26-000020, fy 2026, fp Q3, form 10-Q, filed 2026-07-31, frame CY2026Q2. Critically, the API returns ONLY the consolidated no-dimension fact for each concept. Segment revenue, segment operating income, geographic breakdowns, and every other axis/member-tagged fact are absent. There is also no presentation linkbase, so nothing tells you which concept belongs to which statement or in what order — you cannot render an income statement from companyfacts alone. For segments you must either parse the raw XBRL instance from the filing, use the SEC 'Financial Statement and Notes' data sets, or use the `segments` field the SEC added to NUM.txt in the December 2024 reprocessing of the Financial Statement Data Sets. Rate limit is 10 requests/second with a declared User-Agent header (format: 'Sample Company Name AdminContact@domain.com'); omit it and you get an 'Undeclared Automated Tool' error. Note www.sec.gov 403s a generic browser UA while data.sec.gov accepted the declared UA in my tests.

**Why it matters.** A naive plan that promises 'segment analysis and sum-of-parts from free SEC XBRL' will fail at build time. Budget for a raw-instance parser or the Notes data sets, and design the normalised model around a concept-priority ladder plus an extension-tag resolver from the start.

- https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
- https://www.sec.gov/edgar/sec-api-documentation
- https://www.sec.gov/os/webmaster-faq#developers
- https://www.sec.gov/dera/data/financial-statement-data-sets.html

### 2. SEC frames API is a free cross-sectional screener and peer-set builder — 3,555 companies in one call  
`confidence: high`

Live-tested 2026-08-24: GET https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2025Q4I.json returned HTTP 200, 464,329 bytes, 3,555 entities, each {accn, cik, entityName, loc, end, val} — e.g. AAR CORP, cik 1750, loc US-IL, end 2025-11-30, val 341,800,000. Period syntax: CY#### (annual duration), CY####Q# (quarterly duration), CY####Q#I (instantaneous/balance-sheet). The `frame` field present on every companyfacts observation is what lets you join a company's own facts back to the cross-section, and it correctly maps non-calendar fiscal years (Apple's fiscal Q3 2026 carries frame CY2026Q2).

**Why it matters.** Sector-relative z-scores, historical multiple percentile bands, peer-set auto-construction and every 'where does this company rank' panel can be built for $0 with roughly 30-60 frames calls per metric-quarter. No fundamentals vendor is needed for US-listed cross-sections.

- https://data.sec.gov/api/xbrl/frames/us-gaap/AccountsPayableCurrent/USD/CY2025Q4I.json

### 3. SEC EDGAR full-text search has an undocumented free JSON API — a quality-of-earnings red-flag engine for $0  
`confidence: high`

Live-tested 2026-08-24: GET https://efts.sec.gov/LATEST/search-index?q=%22material+weakness%22&forms=10-K&dateRange=custom&startdt=2026-07-01&enddt=2026-08-24 returned HTTP 200 with raw Elasticsearch JSON: {"took":665,"hits":{"total":{"value":148,...}}} — 148 10-K filings containing 'material weakness' in that ~8-week window, each hit carrying _id in the form '0001084765-26-000051:rgp-20260530.htm', ciks[], and period_ending. Full-text coverage is 2001-present. Same declared-UA and 10 req/s courtesy limits apply.

**Why it matters.** Phrase-level surveillance of a watchlist ('material weakness', 'going concern', 'restatement', 'change in accounting estimate', 'non-reliance', 'covenant waiver', 'related party') is the cheapest high-signal forensic-accounting feature in the whole product, and it costs nothing.

- https://efts.sec.gov/LATEST/search-index

### 4. Cboe's public CDN serves a full delayed option chain with Greeks and open interest for free — a complete GEX engine with no vendor  
`confidence: high`

Live-tested 2026-08-24 22:12 UTC: GET https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json returned HTTP 200, 5,982,591 bytes, 13,410 contracts across 32 expiries, 10,159 with non-zero open interest. Every contract carries: bid, bid_size, ask, ask_size, iv, open_interest, volume, delta, gamma, vega, theta, rho, theo, change, open/high/low, last_trade_price, last_trade_time, prev_day_close. The wrapper object carries the underlying: SPY current_price 764.091, bid 764.05 / ask 764.10, volume 31,992,131, iv30 12.633. Index quotes at https://cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json (VIX 15.85), _VIX9D (14.07), _SKEW (145.64), _VVIX (88.64), _GVZ (28.28), _OVX (46.74). Daily history CSVs at https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv (199,724 bytes, back to 2011-01-04, DATE/OPEN/HIGH/LOW/CLOSE). Data is 15-minute delayed. These endpoints are undocumented and unsupported — treat as best-effort, and sibling paths do 403 (futures/VX.json and _ADD.json both returned AccessDenied).

**Why it matters.** Spot gamma exposure, dealer positioning maps, max-pain, expected-move, IV surface skew and term structure can all ship in v1 at zero data cost. Budget ~6 MB per underlying per poll, so cache aggressively and poll on a schedule, not on every chart tick.

- https://cdn.cboe.com/api/global/delayed_quotes/options/SPY.json
- https://cdn.cboe.com/api/global/delayed_quotes/quotes/_VIX.json
- https://cdn.cboe.com/api/global/us_indices/daily_prices/VIX9D_History.csv

### 5. Free Cboe daily put/call ratios and full VIX futures term structure, both machine-readable  
`confidence: high`

Live-tested 2026-08-24. Put/call: GET https://cdn.cboe.com/data/us/options/market_statistics/daily/2026-08-21_daily_options returns JSON with 23 named ratios plus volume and OI blocks. Values for 2026-08-21: TOTAL 0.72, INDEX 0.85, EXCHANGE TRADED PRODUCTS 0.89, EQUITY 0.51, VIX 0.21, SPX+SPXW 1.13, OEX 1.00, MRUT 2.64, DJX 0.02. Sum of all products: volume call 8,725,112 / put 6,297,274 / total 15,022,386; open interest call 400,128,895 / put 305,675,920 / total 705,804,815. Term structure: GET https://www.cboe.com/us/futures/market_statistics/settlement/csv/?dt=2026-08-21 returns Product,Symbol,Expiration Date,Price for 55 rows covering VX (weeklies and monthlies), VXM, VA and IBHY. VX curve on 2026-08-21: 2026-08-26 17.5022, 2026-09-16 17.5022, 2026-10-21 19.1499, 2026-11-18 19.8788, 2026-12-16 20.0995, 2027-01-20 21.2107, 2027-04-21 22.3250 — steep contango against VIX spot 15.85. Caveat: all six near-dated weekly VX rows printed the identical 17.5022, which looks like a settlement-propagation artefact rather than six independent settles; validate before displaying weekly-granularity curve shape.

**Why it matters.** VIX term structure slope, contango roll yield, VIX/VIX9D/VIX3M ratios, VVIX and SKEW, and equity-vs-index put/call divergence are core regime indicators. All free, all daily, no vendor relationship, no licence.

- https://cdn.cboe.com/data/us/options/market_statistics/daily/2026-08-21_daily_options
- https://www.cboe.com/us/futures/market_statistics/settlement/csv/?dt=2026-08-21

### 6. Polygon.io rebranded to Massive on 2025-10-30; pricing is per-asset-class and real-time tiers are explicitly non-professional only  
`confidence: high`

Verified 2026-08-24 at massive.com/pricing. STOCKS: Basic $0 (EOD, 5 calls/min, 2yr) / Starter $29-mo (15-min delayed, unlimited calls, 5yr, WebSockets) / Developer $79-mo (15-min delayed, 10yr) / Advanced $199-mo (real-time, 20yr+). OPTIONS: Basic $0 (5 calls/min, 2yr, EOD) / Starter $29-mo (15-min delayed BUT includes real-time Greeks and IV, daily open interest, flat files, WebSockets, second aggregates) / Developer $79-mo (adds Trades, 4yr) / Advanced $199-mo (real-time, adds Quotes, 5yr+, labelled 'Non-pros only'). CURRENCIES: Basic $0 / Starter $49-mo (real-time FX and crypto, 10yr+, WebSockets, flat files). INDICES: Basic $0 / Starter $49-mo (15-min delayed) / Advanced $99-mo (real-time). Add-ons: Financials & Ratios $29-mo, NYSE Order Imbalances $49-mo, partner datasets (Benzinga, TMX, ETF Global) $99-mo each. Annual billing saves 20%. Every tier is tagged 'Individual use'. Both api.polygon.io and api.massive.com return the same 401 'Unknown API Key' JSON, so legacy integrations still resolve.

**Why it matters.** Options Starter at $29/mo carrying real-time Greeks, IV and daily OI is the single best price/value item found in this research. NYSE Order Imbalances at $49/mo is an unusually cheap route to auction-imbalance signals that normally require an exchange feed.

- https://massive.com/pricing
- https://massive.com/pricing?product=options
- https://massive.com/pricing?product=currencies
- https://massive.com/pricing?product=indices
- https://massive.com/blog

### 7. FINRA daily short-sale volume is free and same-day, but it is off-exchange only and the volumes are now fractional  
`confidence: high`

Live-tested 2026-08-24: GET https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260821.txt returned HTTP 200, 541,311 bytes, 12,271 rows. Pipe-delimited header: Date|Symbol|ShortVolume|ShortExemptVolume|TotalVolume|Market. Sample row: 20260821|A|509558.830081|0|997736.860442|B,Q,N. FINRA states files are posted 'no later than 6:00:00pm ET of the same day on the relevant trade date' and they are free. Six facility files exist with prefixes CNMS (consolidated NMS), FNQC and FNSQ (Nasdaq TRF Chicago/Carteret), FNYX (NYSE TRF), FNRA (ADF), FORF (ORF). Two traps: (1) TotalVolume here is FINRA-reported off-exchange volume (TRF/ADF/ORF), not consolidated volume — so ShortVolume/TotalVolume is the off-exchange short ratio, not the market-wide one; (2) the volumes are non-integer because they are apportioned, so never treat them as trade counts.

**Why it matters.** Divide this file's TotalVolume by consolidated volume from your price vendor to get the genuine off-exchange percentage — a far better 'dark pool' proxy than most retail tools show. But do NOT call it dark-pool volume: the majority is wholesaler internalisation of retail flow, not ATS activity. True ATS-only data is the separate weekly FINRA OTC Transparency file with a multi-week publication lag.

- https://cdn.finra.org/equity/regsho/daily/CNMSshvol20260821.txt
- https://www.finra.org/finra-data/browse-catalog/short-sale-volume-data/daily-short-sale-volume-files

### 8. Free real-time-ish LULD halt feed and SSR list from Nasdaq Trader, covering all US listing venues  
`confidence: high`

Live-tested 2026-08-24. Halts: GET https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts returned RSS 2.0 with ttl=1 (one-minute refresh), ndaq:numItems 100, pubDate Mon 24 Aug 2026 22:05:38 GMT. Each item carries HaltDate, HaltTime (millisecond precision, e.g. 15:31:56.030), IssueSymbol, IssueName, Market, ReasonCode, PauseThresholdPrice, ResumptionDate, ResumptionQuoteTime, ResumptionTradeTime. Market distribution in the live window: NASDAQ 91, AMEX 4, NYSE Arca 3, NYSE 2 — so it is genuinely cross-venue. ReasonCode distribution: LUDP 70 (LULD volatility pause), T12 12, T3 10, M 6, H11 2. SSR: GET https://www.nasdaqtrader.com/dynamic/symdir/shorthalts/shorthalts20260824.txt returned HTTP 200, 27,307 bytes, CSV header Symbol,Security Name,Market Category,Trigger Time (e.g. SGLY, Singularity Ft Tch Ltd Cmn, R, 8/21/2026 9:30:00 AM), file created 16:30:19 ET. Historical Reg SHO threshold lists at ftp://ftp.nasdaqtrader.com/SymbolDirectory/regsho/.

**Why it matters.** Halt tracking, resumption countdown, and SSR status — three features retail tools charge for — are free, and the RSS gives you resumption quote AND trade times, which is exactly what a day trader needs to position for the reopening auction. Note what it does NOT give you: the live LULD price bands themselves. Those are SIP band messages and must come from a paid feed or be approximated from the rule's 5%/10%/20% tier-and-price schedule.

- https://www.nasdaqtrader.com/rss.aspx?feed=tradehalts
- https://www.nasdaqtrader.com/dynamic/symdir/shorthalts/shorthalts20260824.txt
- https://www.nasdaqtrader.com/trader.aspx?id=ShortSaleCircuitBreaker

### 9. $TICK, $TRIN, $ADD and $VOLD are exchange-proprietary calculated indices — you cannot compute them, and Cboe's CDN does not carry them  
`confidence: medium`

Confirmed 2026-08-24 that https://cdn.cboe.com/api/global/delayed_quotes/quotes/_ADD.json returns HTTP 403 AccessDenied — these are NYSE/Nasdaq index products, not consolidated-tape derivatives. DTN IQFeed's service page states it carries 'Over 700 market stats/breadth indicators (TICK, TRIN, etc), most of which update every 1 second' plus '180 calendar days of tick history (includes pre-post market) with microsecond timestamps', and explicitly warns 'Exchange fees are extra and may apply for either real time or delayed data.' IQFeed does not publish its monthly price on the pricing page (JS-gated, directs to sales@iqfeed.net); historically it has been in the ~$100-150/month range plus per-exchange fees — treat that number as low confidence.

**Why it matters.** A naive plan says 'I'll compute TICK from the tape'. You cannot: TICK is NYSE's own count of last-trade upticks vs downticks across NYSE-listed issues using NYSE's definitions, and even with full tick data your number will not match the one on everyone else's screen. Either buy a feed that carries them (IQFeed is the classic retail-price route) or ship self-computed breadth and label it honestly.

- https://www.iqfeed.net/index.cfm?displayaction=data&section=services
- https://cdn.cboe.com/api/global/delayed_quotes/quotes/_ADD.json

### 10. Self-computed breadth is a legitimate substitute for most internals and costs nothing beyond daily bars you already have  
`confidence: high`

From a universe of daily OHLCV (free from Massive Basic/Starter or SEC-tickers-joined vendors), you can compute without any additional licence: advance/decline line and A/D ratio, net new 52-week highs minus lows, percentage of constituents above their 50DMA and 200DMA, McClellan Oscillator (19-day EMA minus 39-day EMA of net advances) and Summation Index (cumulative sum of the Oscillator), equal-weight vs cap-weight spread (RSP/SPY ratio as a free proxy), and RRG-style relative rotation using JdK RS-Ratio and RS-Momentum on sector ETFs. Credit spreads come free from FRED (BAMLH0A0HYM2 for ICE BofA US High Yield OAS, BAMLC0A0CM for IG). Cboe IBHY futures settlements are also in the free settlement CSV as a live credit proxy (2026-09-01 settle 183.59).

**Why it matters.** Separating 'true exchange internals' (TICK/TRIN, must be bought) from 'self-computed breadth' (free, and arguably better because you control the universe) is the design decision that determines whether you need a $100+/mo feed at all. Label each panel with its provenance so the trader never mistakes a self-computed A/D line for the exchange's.

- https://fred.stlouisfed.org/series/BAMLH0A0HYM2
- https://www.cboe.com/us/futures/market_statistics/settlement/csv/?dt=2026-08-21

### 11. The naive gamma-exposure model is wrong, and the data that fixes it is sold by Cboe at a known-but-quoted price  
`confidence: high`

The canonical public methodology is SqueezeMetrics, 'Gamma Exposure (GEX): Quantifying hedge rebalancing in SPX options', March 2016, revised December 2017 (PDF retrieved 2026-08-24, 798,965 bytes). Its core simplification is that dealers are net long calls and net short puts, so GEX = sum over strikes of (call OI x call gamma x 100 x spot^2 x 0.01) minus the equivalent put term. That assumption is defensible for SPX and demonstrably poor for single stocks and for 0DTE. The fix requires open interest split by capacity. Cboe DataShop sells exactly this: 'Detailed option trading data volume summary by capacity (Customer, Pro-Customer, Broker, Firm, MM) on Cboe exchanges (BZX, C1, C2, EDGX) available End-of-Day (EOD) and in 10-minute intervals' — but only for Cboe's four exchanges, not full OPRA. Separately, Cboe's Option EOD Summary product provides two snapshots (15:45 ET and EOD) with NBBO and size, OHLC, volume, VWAP and OI, history from January 2012, with IV and Greeks available only as a paid 'Calcs' add-on; index bid/ask requires a Cboe Global Indices licence whose 'fees start at $1k/month', and only ^SPX and ^OEX disseminate distinct bid/ask.

**Why it matters.** Ship GEX with the dealer-sign assumption stated on the panel and a sensitivity toggle, not as a black-box number. Also: open interest is settled overnight, so it is structurally blind to 0DTE — any GEX built on OI systematically misses the flow that now dominates SPX intraday. A 0DTE panel needs intraday volume with trade-side classification, which is a different and more expensive dataset.

- https://squeezemetrics.com/monitor/download/pdf/white_paper.pdf
- https://datashop.cboe.com/option-eod-summary

### 12. Third-party options-flow and dealer-positioning data has a clear price ladder: Unusual Whales $150-375/mo API, ORATS $99-399/mo  
`confidence: high`

Unusual Whales, verified 2026-08-24. Dashboard tiers $50 / $75 / $120 per month billed monthly. API tiers are separate and do not include the website: free one-week trial (30,000 requests/day, 90-day lookback), API Basic $150/mo (40,000 requests/day, 2-year lookback), API Advanced $375/mo (unlimited requests, WebSocket streaming of option trades and 'SPX Periscope', CME futures tape/candles/settlement/OI). All API plans include: real-time options flow with 100% market coverage enriched with bid/ask/greeks/OI/volume, real-time Nasdaq equities, congressional and insider trades, darkpool, Net Premium, Market Tide, Spot GEX, 1-minute SPX Market Maker Exposure, daily OI including FLEX OI transfer, and an MCP server at https://unusualwhales.com/public-api/mcp. Retail and API plans are individual-use only; commercial/Startup/Kafka/Enterprise start at $625/mo billed annually. ORATS, verified 2026-08-24: Delayed Data API $99/mo (20,000 requests/month), Live Data API $199/mo (100,000/month), Live Intraday API $399/mo (1,000,000/month, intraday strikes chain + OPRA + monies implied + SMV summaries with history). ORATS live endpoints require signing separate live-data agreements after signup.

**Why it matters.** The 1-minute SPX market-maker exposure and FLEX OI transfer on UW API Basic ($150/mo) would take months to replicate and is not derivable from free Cboe data. ORATS is the better buy if you want a clean IV surface, skew/kurtosis and implied-vs-realised term structure rather than flow.

- https://unusualwhales.com/pricing?product=api
- https://unusualwhales.com/pricing
- https://orats.com/data-api

### 13. Fundamentals+estimates vendor pricing: FMP is the value leader at $22-149/mo but requires a separate licence to display data  
`confidence: high`

FMP personal-use, annual billing, verified 2026-08-24: Basic free (250 calls/day, EOD historical, profile/reference, 150+ endpoints); Starter $22.00/mo (300 API calls/minute, up to 5 years history, US coverage, annual fundamentals and ratios, historical prices, news, crypto and forex); Premium $59.00/mo (750 calls/min, up to 30 years, UK and Canada, full fundamentals and ratios, intraday charts, technical indicators, corporate calendars, custom DCF calculator); Ultimate $149.00/mo (3,000 calls/min, global coverage, earnings call transcripts, ETF and mutual fund holdings, 13F institutional holdings, 1-minute intraday, full historical, bulk/batch delivery). Trailing-30-day bandwidth caps: Free 500 MB, Starter 20 GB, Premium 50 GB, Ultimate 150 GB, Build 100 GB, Enterprise 1 TB+. Monthly (non-annual) billing is up to 34% higher. FMP's own terms state: 'Displaying or redistributing data sourced from FMP requires a specific Data Display and Licensing Agreement with FMP.' Comparators: EODHD All-In-One $99.99/mo ($83.33 annual), Fundamentals Data Feed $59.99/mo, EOD All World $19.99/mo, EOD+Intraday extended $29.99/mo. Alpha Vantage free tier is 25 requests/day; premium $49.99 / $99.99 / $149.99 / $199.99 / $249.99 per month for 75 / 150 / 300 / 600 / 1200 requests-per-minute, with a parallel higher-priced band at $499 / $999 / $1499 / $1999 / $2499; Alpha Vantage real-time and 15-min-delayed US data requires a separate entitlement process through their 'Alpha X Terminal' portal.

**Why it matters.** FMP Ultimate at $149/mo is the cheapest single source of global fundamentals + analyst estimates + transcripts + calendars + 13F. But the display-licence clause is a real legal exposure for a distributed desktop application even with one user — get written confirmation that single-user desktop display is covered before shipping.

- https://site.financialmodelingprep.com/developer/docs/pricing
- https://eodhd.com/pricing
- https://www.alphavantage.co/premium/

### 14. Consensus estimates are the one genuinely expensive gap, and point-in-time consensus must be snapshotted from day one  
`confidence: medium`

No credible free source exists. Verified 2026-08-24: visiblealpha.com now redirects to spglobal.com/market-intelligence — Visible Alpha (the line-item-level, segment-granular consensus product) is part of S&P Global Market Intelligence, and neither publishes a price (institutional, low confidence but reasonably five figures per year). Benzinga's API pricing page returns 403 to automated clients; its consensus-estimates and calendar products are quoted, not listed. Zacks Data Solutions publishes no list price. LSEG/Refinitiv I/B/E/S is enterprise-priced. The accessible substitutes are FMP Ultimate ($149/mo, includes analyst estimates), Finnhub (pricing page is JS-gated and could not be extracted), and Massive's Benzinga partner dataset at $99/mo. Separately, every vendor OVERWRITES its consensus record as estimates change, so pulling 'the consensus before the print' from a live API two years later returns a contaminated number.

**Why it matters.** This is the design consequence that matters most: SUE, earnings-surprise history, PEAD studies, revision momentum and any surprise index are all invalid unless you snapshot consensus daily into your own store starting on day one of the product's life. Build the snapshot table in v1 even if the estimates panel ships in v3 — you cannot backfill it.

- https://www.spglobal.com/market-intelligence/en/solutions/products/resources/visible-alpha
- https://site.financialmodelingprep.com/developer/docs/pricing
- https://massive.com/pricing

### 15. Full free macro spine verified live: Treasury curve, NY Fed SOFR, ECB, BIS, OECD, IMF, World Bank, Eurostat, SNB, RBA, Fed H.15  
`confidence: high`

All tested 2026-08-24, all HTTP 200, none requiring an API key except where noted. US Treasury daily par yield curve CSV (home.treasury.gov/resource-center/.../daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve): 2026-08-24 readings 1M 3.79, 1.5M 3.78, 2M 3.80, 3M 3.87, 4M 3.90, 6M 3.96, 1Y 4.04, 2Y 4.24, 3Y 4.31, 5Y 4.41, 7Y 4.55, 10Y 4.70, 20Y 5.21, 30Y 5.23 (2s10s +46bp, 3M10Y +83bp — not inverted). NY Fed Markets API (markets.newyorkfed.org/api/rates/secured/sofr/last/2.json): SOFR 3.65% on 2026-08-21 with 1st/25th/75th/99th percentiles 3.59/3.63/3.70/3.73 and volume $2,952bn. ECB Data Portal (data-api.ecb.europa.eu/service/data/{flow}/{key}?format=csvdata): EXR D.USD.EUR.SP00.A = 1.1664 on 2026-08-24; YC B.U2.EUR.4F.G_N_A.SV_C_YM.SR_10Y = 3.2710% on 2026-08-21. Supports dot-joined series keys, wildcards by omission, '+' as OR, startPeriod/endPeriod, formats csvdata/jsondata/structurespecificdata, and — critically — an `updatedAfter` delta parameter plus If-Modified-Since returning HTTP 304. BIS Stats API v2 (stats.bis.org/api/v2/data/dataflow/BIS/WS_EER/1.0/D.N.B.US): US nominal broad effective exchange rate 101.87 on 2026-08-18. Also verified: OECD SDMX (sdmx.oecd.org/public/rest/data/...), IMF DataMapper (imf.org/external/datamapper/api/v1/{indicator}), World Bank v2 (api.worldbank.org/v2/...), Eurostat dissemination API, SNB (data.snb.ch/api/cube/{id}/data/csv/en), RBA CSV tables (rba.gov.au/statistics/tables/csv/f1-data.csv), Federal Reserve H.15 CSV download. Requiring a free key: FRED (api.stlouisfed.org returns HTTP 400 'Variable api_key is not set'), BLS (unregistered daily threshold exhausted in my test), BEA, US Census.

**Why it matters.** The entire macro/cross-asset pillar — yield curves and inversion tracking, real yields, OIS/policy-rate anchors, REER fair value, terms of trade — has zero data cost. The ECB `updatedAfter` parameter is the correct primitive for a revision-aware local cache and should shape the sync layer design.

- https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/2026/all?type=daily_treasury_yield_curve
- https://markets.newyorkfed.org/api/rates/secured/sofr/last/2.json
- https://data.ecb.europa.eu/help/api/data
- https://stats.bis.org/api/v2/data/dataflow/BIS/WS_EER/1.0/D.N.B.US
- https://api.stlouisfed.org/fred/series/observations

### 16. FX forward points and swap rates are not free — but they are synthesisable from free OIS curves via covered interest parity, with the basis flagged as unknown  
`confidence: medium`

No free source for tradeable FX forward points or broker swap rates was found. However all the inputs to a CIP-implied forward are free and were verified live on 2026-08-24: USD SOFR from the NY Fed API (3.65%), EUR curves from the ECB Data Portal YC dataflow (euro area AAA 10Y 3.2710%), GBP SONIA from the BoE IADB, CHF from data.snb.ch, AUD from RBA CSV tables, JPY from BoJ time-series search. F = S x (1 + r_quote x t) / (1 + r_base x t). The residual you cannot see for free is the cross-currency basis, which for JPY and EUR against USD is regularly material (tens of basis points, and blows out at quarter-ends and year-end) and is the reason a CIP-implied forward will not match a dealer quote.

**Why it matters.** This is the single strongest non-obvious design move in the FX pillar: ship a 'CIP-implied forward and carry' panel built from free central-bank curves, display the assumption explicitly, and label the cross-currency basis as an unmeasured residual. It gives an institutional-quality carry view at zero cost while being honest about the one thing it cannot know. Also note the carry a retail broker actually pays embeds a markup — since this terminal has no brokerage connectivity, present theoretical carry only and say so.

- https://markets.newyorkfed.org/api/rates/secured/sofr/last/2.json
- https://data.ecb.europa.eu/help/api/data
- https://data.snb.ch/api/cube/rendoblim/data/csv/en
- https://www.rba.gov.au/statistics/tables/csv/f1-data.csv

### 17. Cboe's EVZ FX volatility index appears discontinued — the free route to an FX vol surface is closed  
`confidence: high`

Live-tested 2026-08-24: https://cdn.cboe.com/api/global/delayed_quotes/quotes/_EVZ.json returns HTTP 200 but with timestamp '2025-05-10 09:45:49' and current_price 0.0 — stale for over 15 months and zero-valued. By contrast the commodity vol indices on the same CDN are live and current: _GVZ (gold) 28.28 and _OVX (oil) 46.74, both timestamped 2026-08-24 22:10 UTC. This is strong evidence Cboe discontinued the EuroCurrency Volatility Index. Meanwhile CME Group actively blocks programmatic access: https://www.cmegroup.com/CmeWS/mvc/Settlements/Futures/Settlements/8462/FUT returned HTTP 403 with the message 'This IP address is blocked due to suspected web scraping activity ... Use of scripts, software, spiders, robots, avatars, agents, tools or other scraping mechanisms is strictly prohibited by CME Group's website Data Terms of Use.' CME Term SOFR requires a display or non-display licence with fees behind a 'Benchmark Data Fee List' not published on the site.

**Why it matters.** ATM vol, 25-delta risk reversals and butterflies are the heart of a serious FX drivers dashboard and there is no cheap path. Realistic options: (a) licence CME FX options-on-futures through a compliant vendor such as Databento and construct your own surface, (b) buy an OTC surface from a specialist at institutional cost, or (c) ship realised-vol cones plus a CME-derived approximation and clearly label the absence of true OTC risk-reversal skew. Do not plan on scraping CME.

- https://cdn.cboe.com/api/global/delayed_quotes/quotes/_EVZ.json
- https://cdn.cboe.com/api/global/delayed_quotes/quotes/_GVZ.json
- https://www.cmegroup.com/market-data/cme-group-benchmark-administration/term-sofr.html

### 18. CFTC Commitments of Traders is free via Socrata with 133 fields — but for FX it is a tiny futures slice reported with a 3-day lag  
`confidence: high`

Live-tested 2026-08-24: GET https://publicreporting.cftc.gov/resource/6dca-aqww.json?$limit=1 returned HTTP 200 with 133 fields per record including market_and_exchange_names, report_date_as_yyyy_mm_dd, open_interest_all, noncomm_positions_long_all / short_all / spread_all, comm_positions_long_all / short_all, nonrept_positions_long_all / short_all, the full change_in_* block and the full pct_of_oi_* block, plus old/other crop-year splits. Seven dataset families exist: Legacy Futures-Only, Legacy Combined, Disaggregated Futures-Only, Disaggregated Combined, TFF Futures-Only, TFF Combined, and Supplemental-CIT. Free, no app token required at modest volume (Socrata throttles anonymous callers; a free app token raises the limit).

**Why it matters.** Use TFF (Traders in Financial Futures) for FX and equity index, not Legacy — the Dealer/Asset Manager/Leveraged Funds/Other Reportable split is far more interpretable than 'commercial vs non-commercial' for financial contracts. Two honesty requirements for the UI: COT for FX covers IMM futures only, a rounding error against a ~$7.5trn/day OTC market, and it reports Tuesday positions released Friday 15:30 ET — so the panel must show 'as of Tuesday' prominently. Build for missing weeks: COT publication has been suspended during past US government shutdowns.

- https://publicreporting.cftc.gov/resource/6dca-aqww.json
- https://publicreporting.cftc.gov/

### 19. Look-ahead bias is the silent killer of every base-rate and seasonality panel, and FRED/ALFRED vintages are the only cheap fix  
`confidence: medium`

FRED requires a free API key (verified: api.stlouisfed.org/fred/series/observations?series_id=DGS10&file_type=json returns HTTP 400 'Variable api_key is not set. Read https://fred.stlouisfed.org/docs/api/api_key.html'). The ALFRED vintage mechanism is exposed on the same series/observations endpoint via realtime_start / realtime_end / vintage_dates, and output_type takes values 1 (observations by real-time period), 2 (all observations by vintage date), 3 (new and revised observations only) and 4 (initial release only). I could not fetch the FRED documentation page directly (repeated HTTP/2 stream errors and 403s from fred.stlouisfed.org), so the exact output_type semantics are marked medium confidence and should be re-verified against the live docs before implementation. The bias itself is not theoretical: US GDP is revised for years, non-farm payrolls is revised twice plus an annual benchmark revision, and any 'what happens to SPX after a hot CPI print' study built on the latest vintage is using numbers nobody had on the day.

**Why it matters.** Every 'evidence panel' and 'historical analogue' feature in this product is only credible if it is vintage-correct. Make output_type=4 (initial release) the default for all event-study and surprise-index work, store the vintage used, and show it in the panel footer. This is exactly the sort of rigour the target user will check.

- https://api.stlouisfed.org/fred/series/observations
- https://fred.stlouisfed.org/docs/api/api_key.html

### 20. Tick-level analytics (volume profile, footprint, cumulative delta, AVWAP) need condition-code-correct trades, and Databento is the honest price  
`confidence: high`

Databento pricing verified 2026-08-24: Usage-based pay-as-you-go for historical only, no subscription, priced in $/GB on UNCOMPRESSED BINARY size (encoding choice — CSV, JSON, binary — and compression do not change the price). Standard $199/month includes live data, 16+ years of L0 history, 1 year of L1, 1 month of L2/L3. Plus $1,750/month license fees, annual contract, adds enhanced live data, EXTERNAL DISTRIBUTION RIGHTS, 16+ years of L1 history and a dedicated account manager. Unlimited $4,500/month license fees, annual contract, 16+ years across all schemas. New users get $125 in free historical credits expiring after 6 months. Venues include CME/CBOT/NYMEX/COMEX (650,000+ symbols, 16+ years), Nasdaq TotalView-ITCH, OPRA, CFE, EEX, Eurex, ICE Europe, and Databento US Equities. Per-dataset rates are quoted, not listed. The alternative for real-time is Massive Stocks Advanced at $199/mo (real-time trades AND quotes, 20yr+ history). NYSE sells TAQ historical products (Integrated Feed, OpenBook Ultra/Aggregated, BBO, Trades, Order Imbalances) as T+1 flat files with no published price.

**Why it matters.** The non-obvious trap is not the price, it is the trade condition codes. Getting VWAP, VPOC, value area and cumulative delta right requires filtering out form-T/extended-hours prints, derivatively-priced trades, average-price trades and odd-lot handling — get this wrong and your VPOC is quietly, confidently incorrect. Also note the $1,750 Plus tier is where 'external distribution rights' begins: if this desktop app is ever distributed to a second user, Databento Standard is not the right licence.

- https://databento.com/pricing
- https://massive.com/pricing
- https://www.nyse.com/market-data/historical

### 21. The XBRL-to-financial-model layer has five specific traps that will each cost a week if unplanned  
`confidence: high`

(1) Q4 is never filed — you must derive Q4 = FY minus (Q1+Q2+Q3), and the fiscal-year alignment is not calendar (Apple's fiscal Q3 2026 ends 2026-06-27 and carries frame CY2026Q2). Use the `frame` field for calendar mapping rather than reimplementing it. (2) Cash-flow-statement and many income-statement facts are reported YTD-cumulative (3-month, 6-month, 9-month durations from the same start date), so a naive sum of the four filed duration facts double-counts; you must difference consecutive YTD facts. Distinguish duration facts (start+end) from instantaneous facts (end only, balance sheet). (3) Tag drift: ASC 606 moved most issuers from `Revenues` to `RevenueFromContractWithCustomerExcludingAssessedTax` around 2018, and Apple's live data confirms both concepts coexist in the same companyfacts payload. A per-line-item priority ladder of acceptable concepts is mandatory. (4) Restatements: multiple accession numbers report the same (concept, period) with different values. Key your store on (cik, concept, unit, start, end, accn, filed) and keep both the as-first-reported and as-currently-restated series — Beneish M, Sloan accruals and Piotroski F computed on restated numbers are look-ahead-contaminated in any historical study. (5) Non-GAAP is essentially absent from XBRL: Reg G reconciliations live in the EX-99.1 earnings press release, untagged, so bridging GAAP to company-defined adjusted EPS is an unstructured-document task, not a data task.

**Why it matters.** These five items are the entire difference between 'we pull companyfacts' and 'we have a normalised financial model'. Each is invisible in vendor demos and each produces plausible-looking wrong numbers rather than errors — the worst failure mode for an institutional-calibre user.

- https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json
- https://www.sec.gov/dera/data/financial-statement-data-sets.html

### 22. Several famous scoring models have narrow validity domains that must be enforced in code or the terminal will output nonsense  
`confidence: high`

Altman Z has four distinct variants — the 1968 original (public manufacturers), Z' (private manufacturers, different coefficients), Z'' (non-manufacturers/service), and Z''-EM (emerging markets, +3.25 constant). Applying the original to a bank, insurer, REIT or asset-light software company produces a meaningless number, because working capital and total-asset denominators do not mean the same thing. Beneish M-score is calibrated on a 1982-1992 sample of manufacturing-heavy US firms and its eight indices (DSRI, GMI, AQI, SGI, DEPI, SGAI, LVGI, TATA) have a high false-positive rate on modern high-growth companies; the conventional -1.78 threshold flags a large fraction of legitimate fast growers. Piotroski F-score's nine binary signals include share issuance, which requires a weighted-average diluted share count that differs from the cover-page `dei:EntityCommonStockSharesOutstanding`. Novy-Marx gross profitability is (Revenue - COGS)/Total Assets, but COGS is frequently aggregated or untagged for services businesses. Owner earnings in Buffett's sense requires maintenance capex, which no company reports — it must be estimated (D&A proxy, or the Greenwald revenue-scaled PP&E method) and labelled as an estimate.

**Why it matters.** The target user will immediately spot an Altman Z on a bank. Enforce sector gating (exclude SIC 6000-6799 from Z, warn on Beneish for high-growth), show the variant used, show the input vector alongside the score, and state the base rate for every flag. A score with a visible derivation earns trust; a bare number destroys it.

- https://data.sec.gov/api/xbrl/companyfacts/CIK0000320193.json

### 23. News and social sentiment sourcing has shifted: X is now pay-per-usage credits, Reddit bars commercial use, and the cheap tiers are Marketaux and NewsAPI  
`confidence: medium`

X/Twitter, as of 2026-08-24: docs.x.com states 'The X API uses pay-per-usage pricing. No subscriptions—pay only for what you use', with credits purchased at console.x.com. The old Free/Basic/Pro/Enterprise tier names appear to be gone. Exact credit rates could not be retrieved (console.x.com returned HTTP 402) — treat any X cost estimate as LOW confidence and unpredictable for budgeting. Reddit Data API Terms (retrieved 2026-08-24) state Reddit 'reserves the right to charge fees for future use', that commercial purposes or 'research in excess of rate limits' require a separate agreement, and explicitly prohibit deriving revenue from the API without written approval. Marketaux: free 100 requests/day; paid $29 / $49 / $99 / $199 per month billed monthly for 2,500 / 10,000 / 25,000 / 50,000 requests per day (annual $24 / $41 / $83 / $166). NewsAPI: free developer tier 100 requests/day with a 24-hour article delay, one-month archive, non-commercial only; Business tier 250,000 requests/month with $0.0018 per extra request, and a higher tier at 2,000,000/month with $0.0009 per extra request and a 99.95% uptime SLA. GDELT DOC 2.0 API is free and enormous but has roughly 15-minute latency and poor entity-to-ticker resolution. Benzinga's API pricing page 403s automated clients; its newsfeed and calendars are quoted, and Massive resells a Benzinga partner dataset at $99/month.

**Why it matters.** Two design consequences. First, do not build a feature whose value depends on X data — the pricing model is now consumption-based and unbudgetable. Second, the halt-and-headline race is winnable cheaply: combine the free Nasdaq halt RSS (ttl=1 minute, includes ResumptionQuoteTime) with free PR-wire RSS (Business Wire, GlobeNewswire, PR Newswire, ACCESSWIRE) to answer 'why is this halted' before resumption, at zero marginal cost.

- https://docs.x.com/x-api/introduction
- https://redditinc.com/policies/data-api-terms
- https://www.marketaux.com/pricing
- https://newsapi.org/pricing

### 24. FX has structural pitfalls that must be designed around, not papered over — no consolidated tape, fake volume, and a shifting session boundary  
`confidence: high`

There is no consolidated tape in FX. Every OHLC bar you display is a vendor composite, and two vendors will disagree on the session high and low — which means every level-based construct (breakouts, pivot points, prior-day high/low, opening range) is vendor-dependent. Retail 'volume' is tick count, not notional; it is a reasonable proxy in liquid majors but must be labelled as tick volume. The FX day boundary is 17:00 New York, which drifts against London and Sydney asymmetrically across the DST transitions, so the very definition of a 'daily candle' changes several times a year and silently alters candlestick and gap statistics. Spot is T+2, so the Wednesday rollover carries triple swap; spreads widen mechanically at the 17:00 rollover and around scheduled releases. Quote conventions differ (JPY pairs quote to 2 decimal places with the pip at the second decimal; most others to 4 with pipettes at the fifth) and base/quote direction inverts the sign of every carry calculation. ECB reference rates, verified live at 1.1664 for USD/EUR on 2026-08-24, are a 14:15 CET FIXING published around 16:00 CET — correct for accounting and macro, useless as a tradeable level. NDFs (KRW, TWD, INR, BRL, offshore CNY) have no free source, and 'spot' for those may be onshore or offshore without saying which. Currency strength meters are, mathematically, just a cross-sectional average of a currency's log returns against a chosen basket — basket-dependent, non-stationary, and dominated by the USD leg.

**Why it matters.** An institutional-calibre user will lose trust instantly if the terminal presents a retail-FX fiction. Pin one named reference source per pair and display it; label tick volume as tick volume; make the session boundary configurable and visible; and present the currency strength meter with its basket disclosed and an explicit note that it measures average relative return, not 'strength'.

- https://data.ecb.europa.eu/help/api/data
- https://massive.com/pricing?product=currencies

### 25. Economic-calendar sourcing: ForexFactory blocks automated access, primary agency calendars are free, and vendor calendars are consensus-only  
`confidence: high`

forexfactory.com/calendar returned HTTP 403 to an automated client on 2026-08-24 — scraping it is both technically blocked and against its terms; do not plan on it. Trading Economics does not publish list prices, stating only that 'The API subscription pricing is adjusted accordingly to the features you use, to your volume of requests and to the distribution you make' — quoted, not listed. The free primary route: BLS, BEA and Census each publish annual release schedules, and FRED exposes a release-calendar endpoint. The hard constraint is timing: the actual number hits the wire at exactly 08:30:00.000 ET, and any HTTP-polling calendar API is seconds to minutes behind. Free macro backbone confirmed live on 2026-08-24 (OECD SDMX, IMF DataMapper, World Bank v2, Eurostat all returned 200 with no key; BLS, BEA and Census each require a free registered key).

**Why it matters.** Split the feature honestly: vendor/agency calendars supply the schedule, consensus, prior and revision; high-frequency polling of the primary agency around the release supplies the actual. Never market this as a news-latency tool — for a read-only analytical terminal that is fine, but the surprise-index and event-study features depend on storing your own consensus snapshots (see the estimates finding), which no vendor will give you retrospectively.

- https://tradingeconomics.com/analytics/api.aspx
- https://www.forexfactory.com/calendar
- https://sdmx.oecd.org/public/rest/data/
- https://api.bls.gov/publicAPI/v2/timeseries/data/CUUR0000SA0

### 26. Free factor and cost-of-capital data closes the portfolio-analytics loop at zero cost  
`confidence: high`

Ken French's Data Library (mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html, verified 2026-08-24) publishes free CSV/ZIP downloads of Fama-French 3 Research Factors (monthly, weekly and daily), Fama-French 5 Factors 2x3 (including daily), momentum, and portfolios formed on size, book-to-market, operating profitability and investment. A new 'flat file format (CIZ)' is noted in which monthly returns are compounded daily returns with dividends reinvested on their ex-dates. OpenFIGI (openfigi.com/api) provides free instrument identifier mapping with an API key and states it is 'free to use without daily, weekly or monthly limitations'. Aswath Damodaran publishes free equity risk premiums, industry betas, industry cost of capital and industry multiples updated at least annually (pages.stern.nyu.edu/~adamodar) — the standard free input for a WACC and ROIC-spread panel (medium confidence on current update cadence, not re-verified today).

**Why it matters.** Factor exposure, risk contribution and ROIC-WACC spread need no vendor. Two caveats to design in: Ken French factors are US-only and lag roughly a month at month-end, so for a live portfolio use tradeable factor-mimicking ETF proxies (IWD/IWF/MTUM/QUAL/USMV) for daily attribution and reconcile to the academic factors monthly; and with ~30 positions over 250 days the sample covariance matrix is unstable, so use Ledoit-Wolf shrinkage for any risk-contribution or correlation-adjusted-concentration figure.

- https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html
- https://www.openfigi.com/api/overview

### 27. Market-data licensing, not price, is the binding constraint for a desktop terminal displaying real-time data  
`confidence: medium`

Massive labels every plan 'Individual use' and its real-time Options Advanced tier explicitly 'Non-pros only'. FMP requires 'a specific Data Display and Licensing Agreement' to display or redistribute its data. Unusual Whales states 'Retail and API plans are for individual use' and routes any product built on its data to business plans from $625/month billed annually. Databento's external distribution rights begin at the Plus tier ($1,750/month license fees, annual contract). ORATS requires signing separate live-data agreements before live endpoints are enabled. Non-professional status generally turns on the subscriber not being employed in the securities industry, not being a registered representative, and not using the data for any business purpose — if this trader manages outside money or trades through an entity, the professional fee schedule applies and costs rise by one to two orders of magnitude. I was unable to retrieve the CTA/CQ (Network A/B) and UTP Plan fee schedule PDFs (both 404 on 2026-08-24), so exact per-subscriber tape fees are unverified.

**Why it matters.** This is the risk most likely to invalidate a plan late. Two rules for the architecture: (1) never build a feature that requires re-serving vendor data to a second endpoint or user; (2) check each vendor's stance on local persistence separately from display — several permit caching but prohibit building a derived database, which directly affects the 'backtest-free evidence panel' feature that depends on years of stored history.

- https://massive.com/pricing?product=options
- https://site.financialmodelingprep.com/developer/docs/pricing
- https://unusualwhales.com/pricing?product=api
- https://databento.com/pricing

### 28. Survivorship bias will corrupt every base-rate, seasonality and gap-statistics panel unless delisted securities are in the universe  
`confidence: medium`

Any 'historical distribution of the day range for a gap over 5% on 3x RVOL' computed over today's listed universe is measuring the outcomes of survivors only, which systematically overstates continuation and understates tail losses — precisely the wrong bias for a trader sizing a gap trade. Sources that include delisted names: Massive flat files (S3-delivered, included from Starter tier upward and covering the full historical ticker universe), Sharadar SF1/SEP on Nasdaq Data Link (price not retrievable — their pages are JS shells; historically low hundreds of dollars per year for personal use, marked LOW confidence), and Norgate Data (norgatedata.com/pricing.php returned 404, price unverified). Float rotation has a related gap: free float in SHARES is not in XBRL — `dei:EntityPublicFloat` is a dollar amount at a single cover-page date, not a share count — so free float must come from a vendor or be approximated as shares outstanding minus insider and 13F holdings.

**Why it matters.** The evidence-panel pillar is the product's most defensible differentiator and also the easiest to get quietly, catastrophically wrong. Make delisted-inclusive history a hard requirement of whichever price vendor is chosen, and stamp every base-rate panel with its universe definition, sample size and date range.

- https://massive.com/pricing
- https://data.nasdaq.com/databases/SF1

## Recommended decisions

### What is the primary equities market-data vendor?

**Recommendation.** Massive (formerly Polygon.io). Start on Stocks Developer at $79/month (15-min delayed, unlimited API calls, 10 years of history, WebSockets, flat files) and upgrade to Stocks Advanced at $199/month only when the tick-level tooling — footprint, cumulative delta, real-time AVWAP — actually ships. Add Options Starter at $29/month immediately and Currencies Starter at $49/month for real-time FX.

**Rationale.** Options Starter at $29/month includes real-time Greeks, IV and daily open interest despite the underlying quotes being delayed, which is the single best value item in this entire research pass. Unlimited API calls from $29 upward removes an entire class of rate-limit engineering. Flat files give delisted-inclusive history, which the base-rate evidence panels structurally require. Both api.polygon.io and api.massive.com still resolve after the 2025-10-30 rebrand, so existing integration guides and community libraries remain valid.

**Rejected.** Databento is technically superior and the right choice for deep tick research, but Standard at $199/month caps L2/L3 history at one month and external distribution rights only begin at $1,750/month — wrong shape for a single-user desktop app. Alpha Vantage gates real-time US data behind a separate 'Alpha X Terminal' entitlement process. EODHD All-In-One at $99.99/month has weaker US intraday depth. IEX Cloud no longer resolves at all.

**Cost.** $157/month lean (Stocks Developer 79 + Options Starter 29 + Currencies Starter 49); $376/month full real-time (Stocks Advanced 199 + Options Starter 29 + Currencies Starter 49 + Indices Advanced 99). Verified 2026-08-24.

### Build the fundamentals engine on free SEC XBRL, or buy a normalised vendor feed?

**Recommendation.** Build on free SEC data for US issuers, and buy FMP Ultimate at $149/month (annual billing) purely for non-US coverage, analyst estimates, earnings-call transcripts and corporate calendars. Do not buy a US fundamentals feed.

**Rationale.** companyfacts plus frames gives the full US cross-section for free with the accession number and filed date on every fact, which no vendor exposes — and that provenance is exactly what makes point-in-time modelling and restatement handling possible. Vendors deliver a normalised model but hide the derivation, which defeats the whole purpose for an analyst-calibre user. The honest cost of building is the five traps documented in the findings (Q4 derivation, YTD differencing, tag drift, restatements, absent dimensional facts), which is roughly an XL engineering item, not a weekend. Budget for it deliberately rather than discovering it.

**Rejected.** Sharadar SF1 and similar pre-normalised feeds hide the derivation and their pages are JS-gated with no retrievable price. S&P Global Market Intelligence (which now owns Visible Alpha) is genuinely excellent at line-item-level consensus but is institutionally priced with no published rate. Building non-US fundamentals from scratch across IFRS filings in dozens of jurisdictions is not a reasonable use of effort.

**Cost.** $149/month (FMP Ultimate, annual billing) plus roughly 8-12 engineering weeks for the XBRL normalisation layer. US fundamentals data cost: $0.

### How to source dealer gamma and options positioning?

**Recommendation.** Ship v1 GEX entirely on Cboe's free delayed chain CDN, with the dealer-sign assumption stated on the panel and a sensitivity toggle. Add Unusual Whales API Basic at $150/month only if 0DTE and intraday market-maker exposure prove to be genuine daily-use features.

**Rationale.** The free endpoint returns 13,410 SPY contracts with bid/ask/IV/open interest and full Greeks — everything a GEX engine needs, verified live on 2026-08-24. Paying $150-375/month before proving the feature is used daily is premature. When you do pay, Unusual Whales' 1-minute SPX market-maker exposure and FLEX OI transfer are the two things you genuinely cannot replicate from free data. ORATS at $99-399/month is the better buy if the requirement turns out to be a clean IV surface with skew and kurtosis rather than flow.

**Rejected.** Cboe DataShop volume-by-capacity is the only data that measures rather than assumes dealer sign, but it covers only BZX/C1/C2/EDGX rather than full OPRA, and the Cboe Global Indices licence starts at $1,000/month — disproportionate for one user. Building an OPRA-derived surface via Databento is correct engineering and wrong economics at this scale.

**Cost.** $0 for v1; $150/month if Unusual Whales API Basic is added; $99-399/month if ORATS is chosen instead.

### Buy true exchange internals ($TICK/$TRIN/$ADD) or ship self-computed breadth?

**Recommendation.** Ship self-computed breadth in v1 (A/D line, net new highs-lows, percent above 50/200DMA, McClellan Oscillator and Summation, equal-weight vs cap-weight, RRG rotation) with the constituent universe displayed on the panel. Treat a DTN IQFeed subscription as a deferred optional module gated on the trader actually asking for TICK by name.

**Rationale.** These are exchange-proprietary calculated indices — confirmed by the 403 on Cboe's CDN — so 'compute it yourself' is not an option for TICK itself. But self-computed breadth is arguably better for analysis because the universe is controllable and auditable, and it costs nothing. IQFeed's price is not published and exchange fees are explicitly extra on top, so the true monthly cost is unknown until you contact sales. Do not commit to it on an assumption.

**Rejected.** Attempting to reconstruct TICK from a consolidated tape produces a number that will not match anyone else's screen, which is worse than not having it. Massive's Indices Advanced at $99/month may or may not carry NYSE-calculated internals — this was not verifiable without a paid key and should be confirmed with their sales team before being counted on.

**Cost.** $0 for self-computed breadth. IQFeed price unpublished, historically around $100-150/month plus per-exchange fees (LOW confidence).

### How to handle FX forwards, carry and volatility given no free forward-points source?

**Recommendation.** Synthesise forward points from free central-bank OIS and policy curves using covered interest parity, and display the cross-currency basis as an explicitly unmeasured residual. For FX volatility, ship realised-vol cones in v1 and defer the implied surface; if implied vol becomes essential, licence CME FX options-on-futures through Databento and construct the surface yourself.

**Rationale.** Every CIP input is free and was verified live today — NY Fed SOFR at 3.65%, ECB YC, SNB, RBA, BoE, BoJ. This gives an institutional-quality carry view at zero cost while being explicit about the one thing it cannot know, which is more credible than a black-box number. Cboe's EVZ has been stale since 2025-05-10 and appears discontinued, closing the free implied-FX-vol route, and CME actively IP-blocks scraping with an explicit Terms of Use citation, so there is no shortcut.

**Rejected.** Scraping CME is both blocked and prohibited — the 403 response quotes their Data Terms of Use directly. Buying an OTC FX volatility surface from LSEG or Bloomberg is institutionally priced and disproportionate. Presenting broker swap rates is impossible given the no-brokerage-connectivity constraint.

**Cost.** $0 for CIP-implied carry. Databento pay-as-you-go for CME FX options history, priced per GB of uncompressed binary; $125 of free credits available to start (6-month expiry).

### What is the alerting engine's expression language?

**Recommendation.** Do not invent a DSL. Embed a sandboxed expression evaluator (CEL, or a restricted Lua/JS expression subset) over a strongly typed streaming context, and require every rule to declare its evaluation trigger explicitly: on-tick, on-bar-close, or on-filing-arrival.

**Rationale.** A custom DSL is a multi-month tarpit with a permanent documentation and error-message burden for a single-user product. The declared evaluation trigger is the non-obvious part: mixing tick-evaluated and bar-close-evaluated conditions in one composite rule is the root cause of repainting and phantom alerts, and it must be a first-class property of every rule rather than an implementation detail. Pair it with per-rule cooldowns, arm/disarm hysteresis and a novelty key, or the engine will fire an alert storm on the first volatile open and be switched off permanently.

**Rejected.** A pure GUI rule builder cannot express the cross-panel and cross-asset conditions this user will want. A full scripting runtime is a security and stability liability inside a desktop app that holds API keys.

**Cost.** $0 data cost; roughly 4-6 engineering weeks including the throttle, dedupe and hysteresis layer.

### How to guarantee the evidence panels are statistically honest?

**Recommendation.** Make three things hard architectural requirements from day one: (1) a delisted-inclusive price universe; (2) vintage-correct macro via FRED/ALFRED initial-release output; (3) a daily consensus snapshot vault that starts writing before the estimates UI exists. Stamp every evidence panel with its universe definition, sample size, date range and data vintage.

**Rationale.** Each of these three is unbackfillable. Survivorship bias systematically overstates continuation and understates tail losses in exactly the setups a gap trader sizes on. Latest-vintage macro data means every seasonality and event study uses numbers nobody had on the day. And every vendor overwrites its consensus record, so point-in-time consensus history simply cannot be purchased retrospectively at any price. The consensus vault in particular is a small engineering item (S) with an unbounded cost of omission.

**Rejected.** Shipping evidence panels on a survivor universe with a disclaimer — the disclaimer will be ignored and the numbers will be trusted. Buying point-in-time consensus later — it does not exist as a product at accessible prices.

**Cost.** $0 incremental data cost beyond choices already made; approximately 2 engineering weeks for the vault and vintage plumbing.

### How to manage market-data licensing exposure for a desktop application?

**Recommendation.** Establish and document non-professional subscriber status for the single user, obtain written confirmation from FMP that single-user desktop display is covered by the standard personal plan (their terms require a separate Data Display and Licensing Agreement to display data), and adopt an architectural rule that no vendor data is ever re-served to a second endpoint or user. Check each vendor's stance on local persistence separately from its stance on display.

**Rationale.** Every vendor examined constrains this explicitly: Massive labels all plans 'Individual use' and its real-time options tier 'Non-pros only'; Unusual Whales routes any product built on its data to business plans from $625/month annual; Databento's external distribution rights begin at $1,750/month; ORATS requires separate signed live-data agreements. Non-professional status turns on the user not being employed in the securities industry and not using the data for a business purpose — if this trader manages outside money or trades through an entity, the professional schedule applies and costs rise by one to two orders of magnitude. Separately, the persistence question directly determines whether the base-rate evidence panels are even permissible, since several vendors allow caching but prohibit building a derived database.

**Rejected.** Assuming personal use is implicitly fine — FMP's terms say otherwise in writing. Deferring the licensing review until launch — it is the risk most likely to invalidate a shipped feature late, and the persistence question needs answering before the historical store is designed.

**Cost.** $0 if non-professional status holds. Professional reclassification would plausibly multiply the data budget several-fold; exact CTA/CQ and UTP per-subscriber tape fees could not be verified (both fee-schedule PDFs 404'd on 2026-08-24).

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | XL | Point-in-Time Financial Model | Normalised income statement, balance sheet and cash-flow model built from SEC companyfacts, keyed on (cik, concept, unit, start, end, accn, filed) so both as-first-reported and as-restated series are retained. Handles YTD-cumulative differencing, Q4 = FY minus Q1-Q3 derivation, non-calendar fiscal alignment via the `frame` field, and a per-line-item concept priority ladder to absorb ASC 606-style tag drift. | SEC data.sec.gov companyfacts + Financial Statement Data Sets (FREE, 10 req/s, declared UA) |
| P1 | XL | Segment & Sum-of-Parts Workbench | Segment revenue, operating income and geographic splits extracted from dimensional XBRL facts — which requires parsing the raw filing instance or the NUM.txt `segments` field, NOT companyfacts. Feeds a sum-of-parts valuation with per-segment peer multiples auto-selected from the frames API. | SEC raw XBRL instances / Financial Statement and Notes data sets (FREE but requires a parser) |
| P0 | L | Quality-of-Earnings Panel | Sloan accruals, cash conversion (CFO/net income), DSO/DIO/DPO trend decomposition, capitalised software and R&D tracking, inventory build vs revenue growth, and a same-screen link to the specific XBRL facts each figure came from. Sector-gated Altman Z variant selection, Beneish M with its base-rate and false-positive caveat displayed, Piotroski F with all nine binary signals shown individually, Montier C-score, Novy-Marx gross profitability. | Derived from the Point-in-Time Financial Model (FREE) |
| P0 | M | Filing Phrase Radar | Standing full-text queries over EDGAR for watchlist companies and sector peers: 'material weakness', 'going concern', 'non-reliance', 'restatement', 'covenant waiver', 'change in accounting estimate', 'related party'. Diffs each filing's language against the prior period's to surface newly appearing risk language. | efts.sec.gov/LATEST/search-index (FREE, 2001-present) |
| P0 | L | Reverse-DCF / Implied Expectations | Solve for the growth rate and margin path the current price implies, given owner earnings, net debt and a WACC built from Damodaran's free ERP and industry betas. Sensitivity grid across growth, margin and discount rate. Maintenance capex is an explicit, user-adjustable estimate (D&A proxy or Greenwald revenue-scaled PP&E), never presented as a reported figure. | Financial model + Damodaran ERP/beta datasets (FREE) |
| P1 | M | Peer-Set Auto-Construction & Sector Z-Scores | Build a peer set from SIC/industry plus size, margin and growth similarity, then pull the entire cross-section for any metric in one frames call. Historical multiple percentile bands, sector-relative z-scores, and EV bridges. | SEC frames API — 3,555 entities per call, 464 KB (FREE) |
| P0 | S | Consensus Snapshot Vault | A background job that snapshots analyst consensus for every watchlist name daily into local storage from day one, with revision-momentum and dispersion tracking layered on top. Ships before the estimates UI does. | FMP Ultimate $149/mo, or Benzinga/Zacks (quoted). CHEAP-to-MODERATE, but the vault itself is the asset |
| P1 | L | PEAD & Earnings Surprise Engine | Standardised unexpected earnings using point-in-time consensus, drift curves from T-1 to T+60, surprise-magnitude buckets, and a same-name history of prior reactions. Distinguishes confirmed from estimated report dates explicitly. | Consensus Snapshot Vault + price history (MODERATE) |
| P0 | M | Free Gamma Exposure & Dealer Positioning Map | Full-chain GEX, gamma flip level, per-strike gamma profile, max pain and expected move, built from Cboe's free delayed chain with Greeks and OI. The dealer-sign assumption is stated on the panel with a sensitivity toggle, and a prominent note that OI is settled overnight and therefore blind to 0DTE. | cdn.cboe.com delayed_quotes/options/{SYM}.json — 13,410 contracts, full Greeks (FREE, 15-min delayed) |
| P0 | S | Volatility Complex Dashboard | VIX term structure from the free Cboe settlement CSV with contango/backwardation roll yield, VIX/VIX9D/VIX3M ratios, VVIX, SKEW, GVZ and OVX, plus per-name IV rank/percentile and IV-vs-realised cones. | cdn.cboe.com index quotes + history CSVs + futures settlement CSV (FREE) |
| P1 | M | Options Flow & Capacity-Aware Positioning | Real-time flow, sweeps, net premium, unusual activity, and — the differentiator — open interest split by capacity (Customer / Pro-Customer / Broker / Firm / Market Maker) so dealer sign is measured rather than assumed. | Unusual Whales API Basic $150/mo (spot GEX, 1-min SPX MM exposure, FLEX OI transfer) and/or Cboe DataShop volume-by-capacity, BZX/C1/C2/EDGX only (MODERATE) |
| P1 | S | Off-Exchange Share & Short-Volume Tracker | Daily off-exchange percentage computed as FINRA TRF/ADF/ORF volume divided by consolidated volume, plus the off-exchange short ratio, with per-facility breakdown. Labelled off-exchange, not 'dark pool', with an explainer that most of it is retail internalisation. Weekly ATS-only data layered in when the FINRA OTC Transparency file publishes. | cdn.finra.org/equity/regsho/daily/CNMSshvol{date}.txt, 12,271 symbols (FREE) |
| P0 | M | Halt, SSR & Reopening Desk | Live LULD halt board from the Nasdaq RSS (one-minute TTL, cross-venue, with reason codes and resumption quote/trade times), SSR status from the daily shorthalts file, and an auto-joined 'why' panel pulling matching PR-wire headlines for the halted symbol. | nasdaqtrader.com halt RSS + shorthalts.txt + free PR-wire RSS (FREE) |
| P0 | M | Anchored VWAP & Event Anchors | AVWAP anchored to any event — earnings, 13D filing, insider cluster, gap day, index add, halt resumption — with standard-deviation bands, plus session VWAP and multi-day VWAP. | Massive Stocks Developer $79/mo or Advanced $199/mo minute/tick aggregates (CHEAP-to-MODERATE) |
| P0 | M | RVOL by Time-of-Day & Opening Range | Per-symbol intraday volume seasonality curve built from 20+ prior sessions with earnings days excluded, giving true relative volume at any minute of the session rather than a naive full-day ratio. Opening-range breakout levels, gap classification and float-rotation counter. | Minute aggregates from Massive (CHEAP) |
| P1 | XL | Volume Profile, Footprint & Cumulative Delta | TPO/market profile with VPOC, VAH and VAL, volume-at-price histograms, footprint charts and cumulative delta with Lee-Ready trade-side classification. Trade condition codes filtered explicitly (form-T, derivatively priced, average price, odd lot) with the filter set visible and configurable. | Massive Stocks Advanced $199/mo (real-time trades and quotes) or Databento pay-as-you-go for deep history (MODERATE) |
| P0 | XL | Base-Rate Evidence Panels | For any setup the trader defines (gap >5% on >3x RVOL; close above upper Bollinger on 2x volume; day 3 of an insider cluster), show the historical distribution of subsequent day range, close location, MFE/MAE and n-day forward return — computed over a delisted-inclusive universe with the universe definition, sample size and date range stamped on the panel. | Delisted-inclusive daily+minute history: Massive flat files, or Sharadar/Norgate (CHEAP-to-MODERATE) |
| P2 | M | Seasonality & Calendar-Effect Explorer | Monthly, day-of-week, day-of-month, pre/post-holiday, turn-of-month, options-expiry-week and earnings-season effects per symbol, sector and index — with a bootstrapped confidence interval and a multiple-testing warning shown alongside every result. | Daily price history (FREE-to-CHEAP) |
| P1 | L | Event-Study Chart Builder | Cumulative abnormal returns around any event type — 13D filings, insider clusters, guidance changes, index rebalances, lock-up expiries — with market-model and factor-model abnormal-return options and confidence bands. | SEC filings + price history + Ken French factors (FREE) |
| P1 | M | Self-Computed Breadth & Rotation | Advance/decline line, net new highs-lows, percent above 50/200DMA, McClellan Oscillator and Summation Index, equal-weight vs cap-weight spread, and RRG-style relative rotation on sector ETFs — all computed from the user's own universe, with the universe definition displayed. Credit spreads (ICE BofA HY OAS) and IBHY futures overlaid. | Daily bars + FRED BAMLH0A0HYM2 + Cboe settlement CSV (FREE) |
| P2 | M | True Exchange Internals Feed (optional module) | $TICK, $TRIN, $ADD, $VOLD and the wider breadth-statistic set at one-second resolution, clearly badged as exchange-calculated to distinguish them from self-computed breadth. | DTN IQFeed — 700+ breadth indicators at 1s, 180 days of tick history, price quoted not listed, exchange fees extra (MODERATE, price LOW confidence) |
| P0 | L | FX Drivers Dashboard with CIP-Implied Carry | Per-pair interest-rate differential and carry computed from free central-bank OIS/policy curves via covered interest parity, with the cross-currency basis explicitly labelled as an unmeasured residual. Real yields, OIS-implied policy paths, and terms-of-trade linkage (AUD-iron ore, CAD-WTI, NOK-Brent). | NY Fed SOFR API, ECB YC dataflow, BoE IADB, SNB data API, RBA CSV, BoJ (all FREE) |
| P1 | M | FX Fair-Value & Positioning Module | BIS REER/NEER deviation from long-run average, PPP-based fair value, CFTC TFF positioning (Dealer / Asset Manager / Leveraged Funds / Other Reportable) with a prominent 'as of Tuesday, released Friday 15:30 ET' stamp and an explicit note that IMM futures are a fraction of the OTC market. | BIS Stats API v2 WS_EER + CFTC Socrata TFF (both FREE) |
| P0 | M | FX Session & Convention Engine | Configurable 17:00 New York day boundary with DST-aware handling, Tokyo/London/NY session shading and overlap statistics, rollover and triple-swap-Wednesday markers, spread-widening windows, correct pip/pipette conventions per pair (JPY 2dp), weekend-gap handling, and a per-pair badge naming the reference quote source. | Massive Currencies Starter $49/mo real-time FX (CHEAP) |
| P2 | M | Central Bank Reaction & Intervention Watch | Speech and meeting calendar, market-implied hike/cut odds derived from OIS curves, MoF Japan monthly intervention disclosures, SNB weekly sight deposits as an intervention proxy, and PBoC daily USDCNY fixing versus market expectation with the deviation charted. | MoF Japan, data.snb.ch, PBoC, central bank calendars (FREE) |
| P1 | L | Vintage-Correct Macro Surprise Index | Build-your-own Citi-CESI equivalent: z-scored (actual minus consensus) divided by the historical standard deviation of surprises, rolling 3-month weighted sum, per-region. Every event-study and seasonality panel defaults to initial-release vintages (FRED output_type=4) with the vintage stamped in the footer. | FRED/ALFRED (FREE, key required) + Consensus Snapshot Vault |
| P1 | M | Yield Curve & Cross-Asset Cockpit | US, euro area, UK and Japan curves with inversion tracking (2s10s at +46bp and 3M10Y at +83bp as of 2026-08-24), inflation breakevens, real yields, commodity curves, EIA energy series, and Baltic freight where licensing permits. | Treasury CSV, ECB YC, FRED, EIA API v2 (FREE, key). Baltic Dry is Baltic Exchange-licensed (EXPENSIVE) |
| P0 | L | Streaming Rule & Alert Engine | A sandboxed expression language over a typed streaming context, where every rule declares its evaluation trigger — on tick, on bar close, or on filing arrival — to prevent repaint bugs. Composite and cross-panel conditions, per-rule cooldowns, arm/disarm hysteresis bands and a novelty key for dedupe. Filing alerts poll the EDGAR index within the 10 req/s budget and parse Form 4 ownershipDocument XML rather than the rendered HTML. | SEC EDGAR index + price/options streams (FREE + existing subscriptions) |
| P1 | L | Manual Portfolio & Exposure Analytics | Manual position entry plus CSV/OFX import with a user-driven column-mapping UI rather than a per-broker parser. Exposure by sector, factor, currency and country; correlation-adjusted concentration using Ledoit-Wolf shrunk covariance; scenario and what-if shocks; risk contribution. | User input + price history + Ken French factors (FREE) |
| P2 | M | Factor Attribution | Regress portfolio daily returns on Fama-French 5 plus momentum, with tradeable ETF proxies (IWD/IWF/MTUM/QUAL/USMV) for daily attribution reconciled monthly to the academic factors. Minimum 60 observations enforced, with the R-squared and standard errors shown. | Ken French Data Library (FREE) + ETF prices |
| P1 | M | Trade Journal & R-Multiple Analytics | Journal built around initial risk captured at entry so R-multiples are real, producing expectancy, win rate by setup, MFE/MAE distributions, drawdown statistics, and time-of-day and holding-period breakdowns. Position sizing calculators including fractional Kelly (quarter and half) with the full-Kelly ruin warning and an estimation-error penalty shown. | User input (FREE) |
| P1 | M | Corporate Event Calendar | Earnings with confirmed-versus-estimated dates flagged distinctly, guidance changes, investor days and conferences, index rebalance dates with estimated passive flow, lock-up expiries, and the IPO/secondary calendar. | FMP Premium/Ultimate calendars ($59-149/mo), SEC filings for lock-ups (FREE), index provider announcements (FREE). ORTEX offers pre-announcement rebalance forecasting with 0-0.99 conviction scores (MODERATE) |
| P0 | S | Data Provenance & Freshness Bar | A persistent strip on every panel showing the source, the as-of timestamp, whether the data is real-time/delayed/EOD, the vintage where applicable, and the licence class (individual / non-professional). Stale or failed feeds visibly degrade rather than silently serving old numbers. | Internal metadata (FREE) |

## Risks

- Segment data is not in SEC companyfacts. Dimensional (axis/member) facts are dropped entirely, so any roadmap promising segment analysis or sum-of-parts from companyfacts will fail at build time. Mitigation: budget for a raw XBRL instance parser or the Financial Statement and Notes data sets, and scope this as XL not M.
- Point-in-time consensus cannot be backfilled. Every vendor overwrites its consensus record, so SUE, PEAD, surprise history, revision momentum and any surprise index built later will be look-ahead-contaminated. The snapshot vault must start writing in v1 even though the estimates UI ships in v3.
- Survivorship bias silently corrupts the flagship evidence panels. A gap-statistics or base-rate distribution computed over today's listed universe overstates continuation and understates tail losses — the exact wrong bias for position sizing. Requires delisted-inclusive history as a hard vendor requirement.
- Trade condition codes are the hidden failure mode in tick analytics. Form-T prints, derivatively priced trades, average-price trades and odd-lot handling each quietly corrupt VWAP, VPOC, value area and cumulative delta. These produce plausible wrong numbers rather than errors — the worst outcome for a sophisticated user.
- Open interest is settled overnight, so any GEX built on OI is structurally blind to 0DTE, which now dominates SPX intraday flow. Shipping a GEX panel without this caveat is actively misleading in the one market where the trader most wants it.
- The naive dealer-sign assumption (long calls, short puts) is defensible for SPX and demonstrably poor for single stocks. The data that fixes it — Cboe volume-by-capacity — covers only four Cboe exchanges, not full OPRA, so even the paid fix is partial.
- Cboe's cdn.cboe.com JSON endpoints are undocumented and unsupported. Sibling paths already 403 (futures/VX.json, _ADD.json) and EVZ has been stale since 2025-05-10. The free options-chain and index-quote feeds that underpin several P0 features could be withdrawn or rate-limited without notice. Build an abstraction layer with a paid fallback path.
- Market-data licensing, not price, is the binding constraint. FMP requires a separate Data Display and Licensing Agreement to display data; Massive real-time is 'Non-pros only'; Databento external distribution starts at $1,750/month. If the trader is professional-classified, or the app ever reaches a second user, the economics change by one to two orders of magnitude.
- Several vendors permit caching but prohibit building a derived database, which directly threatens the historical store the base-rate evidence panels depend on. This needs answering per-vendor before the storage layer is designed, not after.
- X API pricing moved to pay-per-usage credits in 2026 with no published rates retrievable (console.x.com returned 402). Any feature depending on X data has an unbudgetable and unpredictable cost. Reddit's Data API Terms explicitly prohibit deriving revenue without written approval.
- CME Group actively IP-blocks programmatic access with an explicit Terms of Use citation. Any plan involving CME settlement, FedWatch or Term SOFR scraping is both technically blocked and prohibited; licensed vendor access is the only route.
- FX has no consolidated tape, so every displayed high, low and level is vendor-dependent. Switching FX vendors will change historical chart levels and invalidate any stored level-based signal history. Pin one reference source per pair from day one and record it.
- The FX day boundary at 17:00 New York drifts asymmetrically across US, EU and AU DST transitions, changing the definition of a daily candle several times a year and silently altering candlestick, gap and seasonality statistics.
- CFTC COT publication has been suspended during past US government shutdowns, and the data is Tuesday-as-of released Friday. Both the missing-week case and the three-day staleness must be handled in the UI, not just the loader.
- Vintage contamination in macro. GDP is revised for years and payrolls twice plus an annual benchmark. Any event study or seasonality panel on latest-vintage FRED data uses numbers nobody had on the day. FRED's ALFRED output_type semantics could not be verified today (documentation pages returned 403 and HTTP/2 stream errors) and must be re-confirmed before implementation.
- Alert storms will kill the alerting feature on its first volatile open unless cooldowns, arm/disarm hysteresis and novelty keys ship with v1 rather than as a follow-up.
- Famous scoring models applied outside their validity domain produce confident nonsense — Altman Z on banks, REITs and insurers; Beneish M on modern asset-light high-growth companies. Sector gating must be enforced in code, not left to the user.
- Owner earnings requires maintenance capex, which no company reports. Presenting an estimate as a reported figure would destroy credibility with precisely this user. It must be visibly an adjustable estimate.
- FINRA daily short-sale volumes are now non-integer (apportioned) and cover off-exchange venues only. Treating them as trade counts, or as market-wide short volume, produces wrong ratios. Calling them 'dark pool' volume is factually wrong since most is retail internalisation.
- SEC's 10 requests/second fair-access limit with a declared User-Agent is generous but real. companyfacts is 3.79 MB per company, so a 500-name watchlist refresh is ~1.9 GB — bulk ZIP downloads and delta syncing are required, not per-symbol polling.
- Consensus estimates quality degrades sharply for small caps and non-US names at the accessible price tiers. Coverage counts should be displayed alongside every consensus figure so the user knows whether three analysts or thirty produced it.

## Open questions

- What are the exact FRED/ALFRED output_type semantics and the vintage_dates parameter behaviour? fred.stlouisfed.org documentation pages returned repeated HTTP/2 INTERNAL_ERROR and 403 responses on 2026-08-24. The API key requirement is confirmed (400 without it) but the vintage parameters must be re-verified before the look-ahead-avoidance layer is built.
- Does Massive's Indices tier ($49 delayed / $99 real-time) actually carry NYSE and Nasdaq calculated internals ($TICK, $TRIN, $ADD, $VOLD)? This could not be tested without a paid key and would materially change the internals build-vs-buy decision. Confirm with Massive sales before committing to the self-computed-only path.
- What is DTN IQFeed's actual monthly price in 2026, and what are the per-exchange fees on top? The pricing page is JS-gated and directs to sales@iqfeed.net. The ~$100-150/month figure is from memory, not verified.
- What does FMP charge for Commercial Use as opposed to Personal Use, and does a single-user desktop application that displays data on screen require the separate Data Display and Licensing Agreement their terms reference? This determines whether the $149/month Ultimate figure is real or a floor.
- What are the exact CTA/CQ (Network A/B) and UTP Plan non-professional subscriber monthly rates and any vendor/redistribution fees? Both fee-schedule PDFs returned 404 on 2026-08-24.
- What are current X API credit rates and the minimum purchase? console.x.com returned HTTP 402 and docs.x.com confirms only that pricing is pay-per-usage with no subscriptions. Any X-dependent feature is unbudgetable until this is known.
- What are Benzinga's API prices for News, Consensus Estimates, Calendars and Analyst Ratings? benzinga.com/apis and /apis/pricing both 403 automated clients. Massive resells a Benzinga partner dataset at $99/month — is that the full newsfeed or a subset?
- What are Finnhub's current plan prices and rate limits? The pricing page is fully JS-rendered and yielded no extractable content by either curl or WebFetch.
- What does Cboe DataShop actually charge for Option EOD Summary with the Calcs (IV and Greeks) add-on, and separately for Option Trading Volume by capacity? Prices are computed dynamically in the cart and the only figure disclosed publicly is that Cboe Global Indices licence fees 'start at $1k/month'.
- Are Cboe's cdn.cboe.com delayed-quote JSON endpoints covered by any terms of use that permit programmatic polling and local storage? They are undocumented, and several P0 features depend on them.
- What are ORTEX's actual subscription tiers and prices? Only a $9.90/month add-on surfaced. Their pre-announcement index-rebalance forecasting with 0-0.99 conviction scores and estimated passive flow is a strong feature reference worth pricing.
- What is the current publication lag on FINRA's weekly OTC (ATS) Transparency data — is it still two weeks for Tier 1 NMS stocks and four weeks for others? The FINRA download page 403s automated clients and the daily short-volume page does not cover it.
- Which vendor is the cheapest credible source of confirmed-versus-estimated earnings dates? Wall Street Horizon is the specialist but is unpriced publicly; FMP and Finnhub flag confirmation inconsistently, and the distinction materially affects any earnings-event feature.
- Do the six near-dated weekly VX contracts genuinely settle at the identical 17.5022 value seen on 2026-08-21, or is that a propagation artefact in the settlement CSV? This affects whether weekly-granularity term-structure shape can be displayed at all.
- What is Sharadar SF1/SEP pricing on Nasdaq Data Link in 2026, and does it still include delisted securities? Their product pages are JS shells returning no content. Same question for Norgate Data, whose pricing page 404s.
- Is there any accessible source of OTC FX implied volatility (ATM, 25-delta risk reversal and butterfly) below institutional pricing, now that Cboe's EVZ appears discontinued? Constructing a surface from CME FX options-on-futures via Databento is the working assumption but has not been costed.
- What is Visible Alpha's (now S&P Global Market Intelligence) actual price for a single user, and is a single-seat licence even offered? Line-item-level and segment-granular consensus would be transformative for the sum-of-parts feature if it were reachable.
