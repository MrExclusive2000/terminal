# Windows Desktop Tech Stack & Real-Time Charting for a Data-Dense, Read-Only Professional Trading Terminal (research as of 2026-08-24)

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

Recommendation: **.NET 10 LTS (GA 2025-11-11, supported to 2028-11-10) + WPF (`net10.0-windows`) as the shell**, not WinUI 3, not MAUI, not Electron. Rationale is blunt: a terminal lives or dies on *docking with multi-monitor tear-off and layout persistence*, and WPF is the only Microsoft-blessed stack in 2026 with three independent mature docking implementations (Syncfusion DockingManager, DevExpress DockLayoutManager, Dirkster AvalonDock 4.72.x) plus the deepest bench of high-performance financial chart controls (SciChart WPF v9, released 2026-04-23). WinUI 3 still has *no first-party dock manager* (microsoft-ui-xaml issues #668/#4784/#5188 open for years), a smooth-resize defect only targeted for fix in summer 2026, and forces you onto community `WinUI.Dock`. .NET MAUI is disqualified: it pins the WindowsAppSDK version and as of 2026-07-31 is a full major version behind with no supported upgrade path.

Avalonia 12.0 (GA 2026-04-07, MIT, big compositor/dirty-rect wins) is the credible second choice and the only one with a cross-platform escape hatch; its `Dock.Avalonia` 12.1.0 (MIT) is genuinely good, but the financial-charting ecosystem is thinner and you inherit Skia software/GPU quirks under RDP.

Charting: SciChart WPF v9 2D Professional (~$899/dev perpetual, royalty-free; ~$629 no-support variant) is the only .NET control with credible FIFO-streaming-at-scale evidence. Free fallback: ScottPlot 5 (MIT, SkiaSharp) for secondary panels.

Storage: a **three-tier local plan** — SQLite (WAL) for OLTP/app state and the AI vector index via `sqlite-vec`; **DuckDB 1.5.x** (`DuckDB.NET.Data.Full` 1.5.5, with Arrow streaming and allocation-free `AppendRow`) as the analytical engine reading **hive-partitioned Parquet**; raw ticks appended to daily Parquet. Avoid DuckDB VSS for vectors — HNSW persistence is still behind `hnsw_enable_experimental_persistence` with known WAL-recovery data-loss risk.

Ship as a **Velopack** portable/setup with delta updates (not MSIX — its per-user-only model and sideload policy friction buy you nothing here), signed via **Azure Artifact Signing (ex-Trusted Signing) Basic at $9.99/mo**, with an OV+cloud-HSM cert as fallback if the 3-year-entity eligibility rule blocks you.

**Year-1 licence total: ~$1,020** (SciChart $899 + signing $120), assuming Syncfusion Community License eligibility ($0) for docking/grid.

## Findings

### 1. .NET 10 is the correct runtime floor: LTS to Nov 2028, WPF still first-class  
`confidence: high`

.NET 10.0 GA 2025-11-11; LTS with support until 2028-11-10. .NET 11 ships Nov 2026 but is STS (24 months) — skip it. WPF in .NET 10 adds Fluent styles for Label, Hyperlink, GroupBox, GridSplitter, NavigationWindow, plus perf work (managed font-collection loader, cache-operation and array-handling optimisation). WPF in .NET 9 already shipped the Fluent theme with light/dark/System `ThemeMode` and sets the Mica backdrop (DWMSBT_MAINWINDOW via DwmSetWindowAttribute) when Fluent is enabled. Caveat: unlike WinUI, WPF has no Acrylic/Mica *material brushes* — only the window-level backdrop.

**Why it matters.** You get Win11-native dark mode/Mica without a third-party theme pack (no WPF-UI/MahApps dependency), on a runtime with a 3-year support runway that outlives the app's v1→v3 lifecycle.

- https://devblogs.microsoft.com/dotnet/announcing-dotnet-10/
- https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/net100
- https://learn.microsoft.com/en-us/dotnet/desktop/wpf/whats-new/net90
- https://github.com/dotnet/wpf/blob/main/Documentation/docs/using-fluent.md

### 2. WinUI 3 still has no first-party docking manager in 2026 — a hard disqualifier for a terminal shell  
`confidence: high`

microsoft-ui-xaml issues #668 (DockManager/Dockable Windows), #4784 (movable/dockable panels) and #5188 (DockPanel) remain unimplemented. The only options are community `qian-o/WinUI.Dock` (AvalonDock/ImGui-inspired) or paying Telerik for a WinUI DockPanel (which is a layout panel, not a VS-style dock manager). Separately, WinUI 3's smooth-resize defect (black edges / tearing on window resize), first raised in 2021, is only targeted for a fix in summer 2026. Windows App SDK 1.8 shipped Sept 2025 (serviced to March 2026), with SDK 2.0 in preview targeting .NET 10. XAML designer reliability and Hot Reload consistency are still behind WPF.

**Why it matters.** Docking is not a nice-to-have; it is the terminal's core UX. Choosing WinUI 3 means writing or adopting an unproven dock manager AND absorbing shell-level rendering defects on every window resize — the single most visible interaction in a multi-panel app.

- https://github.com/microsoft/microsoft-ui-xaml/issues/668
- https://github.com/microsoft/microsoft-ui-xaml/issues/4784
- https://github.com/microsoft/microsoft-ui-xaml/issues/5188
- https://github.com/qian-o/WinUI.Dock
- https://windowsnews.ai/article/winui-3-resizing-fix-coming-summer-2026-to-stop-black-edges-and-tearing.420604
- https://learn.microsoft.com/en-ca/windows/apps/windows-app-sdk

### 3. .NET MAUI is structurally unfit for this app — it version-pins WindowsAppSDK and inherits every WinUI 3 defect  
`confidence: high`

MAUI's Windows head *is* WinUI 3, so it inherits WinUI's gaps. Worse, MAUI relies on an internally-defined WinUI 3 / Windows App SDK combination; manually upgrading the WindowsAppSDK NuGet reference is unsupported and the build system reverses it. As of 2026-07-31 MAUI was reported a full major version behind WindowsAppSDK with no supported path to close the gap. Community reports through 2026 include mouse-move pegging a CPU core, custom-cursor problems, and nested-ListView-in-DataTemplate binding failures; v10.0.50 shipped another major regression.

**Why it matters.** Rules MAUI out with no further evaluation. Documenting *why* prevents a later 'but it's cross-platform' relitigation.

- https://maboasoft.com/blog/maui-windows-target-migration-scope/
- https://github.com/dotnet/maui/discussions/34171
- https://visualstudiomagazine.com/articles/2026/07/15/net-11-preview-6-roundup-aspnet-core-maui-c-ef-core-and-sdk-updates.aspx

### 4. Avalonia 12.0 (2026-04-07) is the strongest non-Microsoft .NET option; MIT core, real perf work, real accessibility  
`confidence: high`

Avalonia 12.0.0 GA 2026-04-07 (11.3.10 was the last 11.x stable, 2025-12-18). Stated themes: Performance and Stability; vendor claims up to 1,867% FPS improvement on a 350,000-visual-element scene from deferred composition + optimised dirty-rect tracking (vendor benchmark — treat as directional). Core framework is MIT/free. Accessibility on Windows goes through UIA with automatic AutomationPeers on built-in controls; Narrator/NVDA work. Paid tiers (Avalonia Accelerate) as of 2026: Free $0; Plus €299/yr/seat; Pro €899/yr/seat (adds 6 premium controls + '70+ charts and data visualizations'); Enterprise €6,999/yr/seat. Avalonia XPF (run WPF code on macOS/Linux) Business is listed at €29,500 perpetual.

**Why it matters.** If you ever want macOS/Linux, Avalonia is the only .NET path that does not require a rewrite. The Pro tier's bundled charts (€899/yr) is a plausible substitute for SciChart if you commit to Avalonia — but it's rental, not perpetual.

- https://avaloniaui.net/pricing
- https://avaloniaui.net/blog/avalonia-12.0-preview-1/
- https://github.com/AvaloniaUI/Avalonia/releases
- https://docs.avaloniaui.net/docs/app-development/accessibility
- https://avaloniaui.net/xpf/pricing/business

### 5. Docking options and exact costs: Syncfusion Community License is the asymmetric win for a solo trader  
`confidence: high`

Syncfusion Community License is FREE and non-expiring for entities/individuals with <$1M USD annual gross revenue, ≤5 developers, ≤10 total employees, and that have never taken >$3M USD outside capital. It covers the full Essential Studio including WPF DockingManager (dock/float/tabbed-document/auto-hide, `State` property, `PersistState`+AutoSave state persistence, `DeleteDockState`/`ResetState`, float panes to separate monitors) and SfDataGrid. Paid alternatives per developer: Telerik UI for WPF subscription $749/dev/yr (Lite), $849 (Priority), $1,249 (Ultimate) — subscription only, no perpetual listed; Telerik DevCraft Complete from ~$1,273 and DevCraft Ultimate from ~$1,616 (ComponentSource, 2026 Q2); DevExpress Universal from $2,253.99 (ComponentSource, as of 2026-06-18). Free/OSS: Dirkster.AvalonDock 4.72.1 (actively used by Stride; DockingManager with layout serialization) and Xceed.Products.Wpf.Toolkit.AvalonDock 5.2.x. For Avalonia: `Dock.Avalonia` 12.1.0, MIT, floating windows + docking targets + layout persistence in JSON/XML/YAML/Protobuf, ReactiveUI/Prism MVVM integrations, targets net6.0/net8.0/net10.0. Web stacks: Dockview core is MIT (tabs, groups, grids, splitviews, floating groups, maximisable groups, true browser popout windows) with only `dockview-enterprise` proprietary; rc-dock for simpler React cases; Golden Layout is now legacy.

**Why it matters.** A single-trader entity almost certainly qualifies for Syncfusion Community — turning ~$1,300–$2,300/yr of commercial docking+grid into $0. That reallocates the entire component budget to charting. It is also the single biggest cost lever in this whole plan, so eligibility must be confirmed in writing before committing.

- https://www.syncfusion.com/products/communitylicense
- https://help.syncfusion.com/wpf/docking/state-persistence
- https://help.syncfusion.com/wpf/docking/dealing-with-windows
- https://www.telerik.com/purchase/individual/wpf.aspx
- https://www.componentsource.com/product/telerik-devcraft-complete/prices
- https://www.componentsource.com/product/devexpress-universal/prices

### 6. SciChart WPF v9 (2026-04-23) is the defensible charting choice; prices are perpetual and royalty-free  
`confidence: medium`

SciChart WPF SDK v9.0 released 2026-04-23 (NuGet `SciChart` 9.1.0.29201): new chart types, improved MVVM API with axis synchronisation, deferred ZoomExtents, perf work. Pricing (per developer, perpetual, royalty-free redistribution): WPF 2D Professional $899 with 1 year support; Source Code Edition $1,699; a no-support variant of WPF 2D Pro at $629 (3 months of updates, no tech support); some SKUs quoted 'from $1,499'. Rendering: the old `SciChart.Drawing.DirectX` package is REMOVED — the DirectX path is now the built-in VisualXccelerator engine (v6+). Vendor performance claims: 1 billion points at 60 FPS with FIFO scrolling, ~1M new points/sec sustained, up to 25M appends/sec; a competitor comparison shows 10M points at 58.7 FPS vs a rival at 2 FPS for 1M.

**Why it matters.** FIFO/ring-buffer series with cheap appends is exactly the tick-chart primitive you need; almost no free .NET library models it natively. Perpetual + royalty-free means one $899 hit, not a rental that can be repriced against you.

- https://www.scichart.com/scichart-wpf-v9-released/
- https://www.nuget.org/packages/SciChart
- https://www.scichart.com/licensing-scichart-wpf/
- https://www.scichart.com/announcing-new-wpf-ios-android-pricing-option-no-support/
- https://www.scichart.com/example/wpf-chart/wpf-fifo-1-billion-points-performance-demo/
- https://www.scichart.com/scichart-wpf-directx-compatibility/

### 7. Free .NET charting ceiling: ScottPlot 5 handles ~1M–10M points; LiveCharts2 and OxyPlot do not  
`confidence: medium`

ScottPlot 5 (MIT) renders via SkiaSharp (a large step up from ScottPlot 4's System.Drawing.Common). It smoothly renders >1M points in a line plot, and with `Signal`/`SignalConst` data types handles up to ~10M points with careful optimisation (these types exploit evenly-sampled X to skip per-point work). LiveCharts2 (MIT, also SkiaSharp) is optimised for aesthetics/animation and MVVM ergonomics, benchmarking in the OxyPlot tier — below ScottPlot for large static datasets. OxyPlot is effectively legacy for this workload.

**Why it matters.** You do not need a paid licence for every panel. Use ScottPlot 5 for the ~20 secondary panels (breadth gauges, ownership bar charts, insider-flow histograms, correlation heatmaps) and reserve SciChart for the 3–6 primary price/tape charts. That is a real six-figure-of-frames saving with zero extra licence cost.

- https://scottplot.net/faq/version-5.0/
- https://whatmuz.com/how-fast-is-scottplot/
- https://swharden.com/csdv/plotting-free/livecharts/

### 8. TradingView licensing is a trap for a private single-user terminal — Lightweight Charts is not  
`confidence: high`

TradingView **Advanced Charts** (the full Charting Library) free licence requires that TradingView attribution remains visible AND that the implementation environment is PUBLIC — not private use, not behind a paywall. TradingView states explicitly that Advanced Charts and Trading Platform are 'not provided for personal use, hobbies, studies, or testing' and that these licences are only available to companies for use in public web projects/applications. Attribution links must not carry nofollow/ugc/sponsored. Removal of branding requires a negotiated commercial licence. By contrast **Lightweight Charts** is Apache-2.0, unconditionally usable, tiny, canvas-based, engineered for large arrays, with `update()` for incremental repaint (vs `setData()` full replace); v5 is current and the repo now ships an Agent Skill documenting v5 API conventions and foot-guns. Highcharts Stock is ~$833+ per developer (perpetual or annual, ComponentSource June 2026); its free non-commercial grant covers non-profits/personal websites/school projects — a private profit-seeking trading tool is a grey area at best.

**Why it matters.** A private, non-public, single-user desktop terminal fails TradingView's free-licence conditions on its face. Planning around 'we'll just embed TradingView' is a legal landmine. Lightweight Charts (Apache-2.0) inside WebView2 is the clean way to get TradingView *look* without TradingView *terms*.

- https://www.tradingview.com/advanced-charts/
- https://s3.amazonaws.com/tradingview/charting_library_license_agreement.pdf
- https://github.com/tradingview/lightweight-charts
- https://www.tradingview.com/free-charting-libraries/
- https://www.componentsource.com/product/highstock/licensing

### 9. Storage: DuckDB 1.5.x + Parquet is the analytical tier; SQLite WAL is the OLTP tier. Do not pick one.  
`confidence: high`

DuckDB LTS line 1.4.0 ('Andium') added AES-256 encryption, MERGE INTO, Iceberg writes; patches through 1.4.5 (2026-06-17); 1.4 LTS EOL Sept 2026. DuckDB 1.5.0 shipped 2026-03-09. .NET client `DuckDB.NET.Data` / `.Data.Full` 1.5.5 tracks DuckDB v1.5.5 and adds Arrow result streaming (`DuckDBCommand.ExecuteArrowStream`, `ExecuteArrowBatchesAsync`) plus an allocation-free `DuckDBAppender.AppendRow` with reusable rows; `DuckDB.NET.Bindings` 1.5.5 exposes the Arrow C Data Interface (`duckdb_to_arrow_schema`, `duckdb_data_chunk_to_arrow`). Concurrency model: single writer + multiple concurrent readers (MVCC), multi-threaded scans/joins/aggregations — explicitly NOT for many simultaneous writers. SQLite in WAL mode: readers never block writers and vice versa, but the single-writer constraint is unchanged by WAL; measured throughput ~10k–50k write transactions/sec on NVMe (some benchmarks 70k–150k rows/sec for small rows, dropping to ~80k with 1ms of compute per row). Reported DuckDB analytical edge: 50M-row aggregate in <3s directly over CSV vs 45–60s for SQLite; SQLite wins 2x–500x on frequent small writes. .NET columnar tooling: `Apache.Arrow` 23.0.0 (net8.0/netstandard2.0), ParquetSharp (G-Research, uses Arrow C data interface for zero-copy), and Parquet.Net.

**Why it matters.** A naive plan picks 'SQLite for everything' and then discovers that scanning 5 years of minute bars across 3,000 tickers for a screener takes minutes. The opposite naive plan picks 'DuckDB for everything' and discovers a single-writer analytical engine is wrong for 200 UI-driven state writes/sec. The split is the design.

- https://duckdb.org/2026/06/17/announcing-duckdb-145
- https://duckdb.org/2026/03/09/announcing-duckdb-150
- https://www.nuget.org/packages/DuckDB.NET.Data
- https://www.nuget.org/packages/DuckDB.NET.Bindings
- https://posthog.com/blog/duckdb-vs-sqlite
- https://powersync.com/blog/sqlite-optimizations-for-ultra-high-performance

### 10. Do NOT use DuckDB VSS for the AI knowledge base — persistence is still experimental with data-loss risk  
`confidence: high`

DuckDB's HNSW index can only be created in in-memory databases unless `SET hnsw_enable_experimental_persistence = true`. WAL recovery is not properly implemented for custom indexes: a crash or unclean shutdown with uncommitted changes to an HNSW-indexed table can cause data loss or index corruption. Only 32-bit FLOAT vectors are supported; the index is not buffer-managed and must fit entirely in RAM; index memory does NOT count against `memory_limit`, so you can silently OOM. Filtered search is broken (WHERE applied AFTER the index returns candidates, so filtered queries under-return). DELETE only tombstones until manual `PRAGMA hnsw_compact_index`, and serialisation is non-incremental — the whole index is rewritten on checkpoint. Alternative: `sqlite-vec` (pure C, zero deps, runs anywhere SQLite runs, latest ~v0.1.7/0.1.9) with a first-party .NET path via `Microsoft.SemanticKernel.Connectors.SqliteVec` (1.74.0-preview), a `Microsoft.Extensions.VectorData` provider depending on `Microsoft.Data.Sqlite` + `sqlite-vec`. LanceDB is embedded/in-process on the Lance columnar format but has no first-party .NET binding surfaced in current sources; Qdrant is server-oriented.

**Why it matters.** The AI knowledge layer is a differentiating pillar. Silently corrupting its index on a crash — the exact scenario a desktop app faces daily — would be a catastrophic, hard-to-detect failure. `sqlite-vec` co-located in the app's existing SQLite file is boring, durable, and .NET-native.

- https://duckdb.org/docs/current/core_extensions/vss
- https://duckdb.org/2024/05/03/vector-similarity-search-vss
- https://github.com/asg017/sqlite-vec
- https://www.nuget.org/packages/Microsoft.SemanticKernel.Connectors.SqliteVec/
- https://github.com/MicrosoftDocs/semantic-kernel-docs/blob/main/semantic-kernel/concepts/vector-store-connectors/out-of-the-box-connectors/sqlite-connector.md

### 11. Code signing in 2026: Azure Artifact Signing at $9.99/mo is the cheapest legitimate path — but the 3-year rule may exclude a new entity  
`confidence: high`

Azure Trusted Signing was renamed **Azure Artifact Signing**; pricing unchanged: Basic $9.99/month, 5,000 signatures/month, 1 of each certificate-profile type; Premium $99.99/month, 100,000 signatures/month, 10 of each profile type; overage $0.005 per additional signature. Eligibility is the blocker: Public Trust organisation validation requires a verifiable tax history of 3+ years; Microsoft restricted onboarding to organisations with 3+ years of verifiable operating history (initially US/Canada, subsequently extended to verified US/CA/EU/UK businesses and self-employed individuals). Traditional route: since June 2023 the CA/B Forum requires OV code-signing private keys on an HSM or hardware token. SSL.com OV from $129/yr; SSL.com eSigner cloud HSM (FIPS 140-2 Level 3) from ~$180/yr for 240 signatures/yr. Critically: **since March 2024 Microsoft builds SmartScreen reputation identically for OV and EV** — reputation accrues by download volume against the underlying certificate, not by certificate type or signing tool. Always countersign with an RFC-3161 timestamp so signatures survive certificate expiry.

**Why it matters.** For a single-user app you will never build download volume, so SmartScreen will warn on every fresh install regardless of certificate class. Budget for the warning; do not overspend on EV expecting it to disappear. A brand-new LLC formed for this project will likely fail Artifact Signing's 3-year test — plan the OV+eSigner fallback from day one rather than discovering it at release.

- https://azure.microsoft.com/en-us/pricing/details/trusted-signing/
- https://learn.microsoft.com/en-us/azure/trusted-signing/how-to-change-sku
- https://learn.microsoft.com/en-us/answers/questions/5977141/azure-artifact-signing-trusted-signing-is-a-us-llc
- https://www.ssl.com/products/software-integrity/code-signing/ov/
- https://www.ssl.com/products/software-integrity/signing-service/
- https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/code-signing-options

### 12. Packaging: Velopack over Squirrel/MSIX/ClickOnce; MSIX's per-user-only model is a poor fit  
`confidence: high`

Velopack is the maintained successor to Squirrel.Windows and Clowd.Squirrel: Rust-implemented core, one command produces installer + updates + delta packages + self-updating portable package; CLI is near-identical to Clowd.Squirrel so migration is trivial; reported materially faster both at build time and at end-user upgrade time. MSIX by contrast installs strictly per-user with no visibility of other users' installs; sideloading requires policy to allow it and the signing chain to be trusted by the machine (the 'Sideload apps' developer setting historically had to be enabled). Hybrid approaches exist (WiX/FireGiant MSIX extension emits MSIX and MSI from one source; MSI-with-custom-actions can sideload an MSIX) but add moving parts. Visual Studio App Center retired 2025-03-31 except Analytics/Diagnostics, supported to 2026-06-30 (one source says 2027-03-31) — migrate to Azure Monitor; it is not a viable crash pipeline for a new app.

**Why it matters.** MSIX's container isolation also complicates the two features this terminal needs most: an Excel RTD/COM server registration and unrestricted local filesystem access to a multi-GB Parquet lake. Velopack keeps you unpackaged, portable-capable, and delta-updating.

- https://velopack.io/
- https://github.com/velopack/velopack
- https://github.com/clowd/Clowd.Squirrel
- https://learn.microsoft.com/en-us/windows/msix/desktop/desktop-to-uwp-third-party-installer
- https://www.advancedinstaller.com/user-guide/qa-sideload-appx-using-msi.html
- https://learn.microsoft.com/en-us/appcenter/retirement

### 13. GC gotcha that a naive plan will miss: DATAS is ON by default with Server GC from .NET 9 and hurts p99  
`confidence: high`

DATAS (Dynamic Adaptation To Application Sizes) was opt-in in .NET 8 and enabled by DEFAULT in .NET 9 when Server GC is on. Measured regressions vs .NET 8.0.10 in allocation-heavy workloads range from 1.17x (single thread) to 1.69x (multi-threaded); Microsoft's own guidance flags batch/analytics jobs and ultra-low-latency APIs as likely to lose p99. Mitigation: either set `ServerGarbageCollection=false` (workstation concurrent GC is often correct for a single-user desktop) or explicitly disable DATAS (`System.GC.DynamicAdaptationMode=0`) while keeping Server GC, and consider tuning region size.

**Why it matters.** A terminal's felt quality is p99 frame time, not throughput. Shipping with the .NET 9/10 default and then chasing 'random stutters' for weeks is the predictable failure mode. This is a two-line csproj decision that must be made deliberately and measured.

- https://learn.microsoft.com/en-us/dotnet/standard/garbage-collection/datas
- https://github.com/dotnet/runtime/issues/109047
- https://devblogs.microsoft.com/dotnet/preparing-for-dotnet-10-gc/

### 14. Electron/Tauri memory reality at 30+ panels: Electron ~150–250MB per additional window; Tauri ~40–80MB total  
`confidence: medium`

Electron spawns a separate renderer process per BrowserWindow; each additional window adds roughly 150–250MB, and each renderer keeps its own JS heap plus cached decoded media. Known leak patterns with `browserWindow.hide()` leaving dangling references. Tauri v2 (stable since Oct 2024, on the 2.11 line in 2026) uses the OS WebView (WebView2/Chromium on Windows) + Rust core: ~5MB bundles (minimal apps <600KB) vs Electron's ~120–200MB, and ~40–80MB RAM at idle vs Electron's ~150–400MB — roughly 75% less RAM per benchmarks current through August 2026.

**Why it matters.** A 30-panel terminal in Electron with tear-off windows plausibly lands at 3–7GB RSS. Even Tauri, which shares one WebView2 process tree, cannot match a native .NET shell for 30 simultaneously-streaming charts. This is the quantitative argument that kills the web-stack option for the SHELL — while leaving WebView2 as a perfectly good host for one or two web panels.

- https://blog.bloomca.me/2025/07/21/multi-window-in-electron.html
- https://www.electronjs.org/docs/latest/tutorial/process-model
- https://github.com/electron/electron/issues/12027
- https://www.pkgpulse.com/guides/electron-vs-tauri-2026
- https://www.buildmvpfast.com/blog/tauri-v2-vs-electron-desktop-apps-2026

### 15. Qt is the only stack whose licence cost is unquotable — treat that as a red flag, not a TODO  
`confidence: medium`

Qt commercial licences are sold per-developer-per-year, and every device/app developed with Commercial Qt also needs a *Distribution* licence on top of the developer licence. The Qt Company does not publish per-developer USD/EUR figures publicly on qt.io/pricing (the page routes to a quote/calculator); a discounted 'Qt for Small Business' tier exists with revenue-based eligibility, and volume discounting reportedly starts at 5–10 seats. The LGPLv3 route requires dynamic linking and relinking rights, which conflicts with a signed single-file desktop deployment story.

**Why it matters.** A stack you cannot price is a stack you cannot budget. Combined with a C++/QML skillset that has near-zero overlap with the .NET analytics/AI code you will also write, Qt is out.

- https://www.qt.io/pricing
- https://www.qt.io/faq/qt-commercial-licensing
- https://www.qt.io/pricing/qt-for-small-business

### 16. Target-OS baseline shifted: Windows 10 is out of support; Windows 11 is ~70% of Windows desktop  
`confidence: high`

Windows 10 support ended 2025-10-14. Consumer ESU is enrollable until the programme ends 2027-10-12 (security-only, no features, no technical support, requires Win10 22H2). Windows 11 reached 69.9% of worldwide Windows desktop share by June 2026, Windows 10 down to 28.2%; Windows 11 25H2 (late 2025) was the fastest-adopted feature update in the version's history. WPF per-monitor DPI awareness V2 requires Windows 10 1607+/1703+ and an app manifest declaring PerMonitorV2 — the app receives DPI-change notifications and must relayout/redraw itself; Windows does not bitmap-scale.

**Why it matters.** You can set the minimum target to Windows 11 22H2+ x64 with a clear conscience. That unlocks Mica/DWM backdrops, snap layouts, and modern toast APIs without conditional code paths — and it removes the WinUI-3-needs-Win10-1809 style compatibility arguments entirely.

- https://support.microsoft.com/en-us/windows/deployment/updates-lifecycle/windows-10-support-has-ended-on-october-14-2025
- https://learn.microsoft.com/en-us/windows/whats-new/extended-security-updates
- https://www.tweaktown.com/news/110293/windows-11-market-share-sees-dramatic-increase-in-2026/index.html
- https://learn.microsoft.com/en-us/windows/win32/hidpi/high-dpi-desktop-application-development-on-windows
- https://github.com/microsoft/WPF-Samples/blob/main/PerMonitorDPI/readme.md

### 17. Excel round-trip: Excel-DNA gives you a real RTD server in C# with no registration or COM plumbing  
`confidence: high`

RTD (Real-Time Data) is Excel's native push mechanism — a cell formula that continuously updates without user recalc. Excel-DNA is an open-source project that produces native .xll add-ins from C#/VB.NET/F#, requires no installation or registration, and ships a thread-safe `ExcelRtdServer` base class so you implement only the data logic. Commercial precedents exist (Lightstreamer, Solace, Add-in Express) confirming the pattern is standard for market-data-to-Excel bridges.

**Why it matters.** Every institutional trader has an Excel model. `=TERM.PRICE("AAPL")` and `=TERM.INSIDERNET("AAPL",90)` updating live in their own spreadsheet is the single highest-leverage integration feature in this plan, and it costs one .xll project. Note: this is a strong reason to stay unpackaged (non-MSIX) and on .NET/Windows.

- https://excel-dna.net/
- https://putridparrot.com/blog/a-real-time-data-rtd-server-using-excel-dna-in-excel/
- https://lightstreamer.com/blog/real-time-data-made-easy-empowering-excel-with-lightstreamer-and-rtd-integration/
- https://www.add-in-express.com/docs/net-excel-rtd-servers.php

### 18. WebView2 distribution: Evergreen bootstrapper (~2MB) or standalone offline installer; Fixed Version for determinism  
`confidence: high`

Evergreen mode does not package the runtime — it is installed via an online bootstrapper (~2MB, auto-detects architecture, silent install) or the Evergreen Standalone Installer for offline machines, then auto-updates thereafter. Fixed Version packages a specific runtime with the app and never auto-updates. Windows 11 ships WebView2 by default, but you must still handle the missing-runtime case on older/managed machines.

**Why it matters.** The AI knowledge panel, filings/news reader, and any Lightweight Charts surface all live in WebView2. Silent bootstrapper install from the Velopack installer is the correct default; Fixed Version only if you need byte-identical rendering for regression screenshots.

- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution
- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/evergreen-vs-fixed-version

### 19. Toast notifications: use CommunityToolkit.WinUI.Notifications 7.1.2 from WPF — it works unpackaged  
`confidence: high`

`CommunityToolkit.WinUI.Notifications` (latest 7.1.2) is the supported way to send Windows toasts from C# with IntelliSense-driven `ToastContentBuilder`, explicitly supporting WPF, WinForms, UWP and Console **even without MSIX packaging**. In WinUI 3 the modern equivalent is `AppNotificationBuilder` + `AppNotificationManager` from the Windows App SDK, but `ToastContentBuilder` remains valid there too. Microsoft is renaming 'toast notification' to 'app notification' in docs. Neither API is deprecated as of 2026.

**Why it matters.** Alerts (price levels, Form 4 clusters, 13D/G filings, earnings-in-N-minutes) are a core terminal affordance. Confirming the unpackaged path works removes another argument for MSIX.

- https://www.nuget.org/packages/CommunityToolkit.WinUI.Notifications/
- https://learn.microsoft.com/en-us/dotnet/communitytoolkit/archive/windows/notificationsoverview
- https://learn.microsoft.com/en-us/windows/apps/windows-app-sdk/migrate-to-windows-app-sdk/guides/toast-notifications

### 20. kdb+ is now free-ish for commercial use via KDB-X Community Edition — but the caps kill it for a data lake  
`confidence: high`

kdb+ Personal Edition: personal, non-commercial only, up to 2 computers, max 24 cores per computer, 12-month licence period. KDB-X Community Edition (announced Nov 2025) is free for BOTH personal and commercial projects but capped at: 16GB RAM usable by q, 4 secondary threads per q process, 16 connections per q process, and 24 CPU cores across all instances. General commercial availability of KDB-X was planned for early 2026.

**Why it matters.** The 16GB RAM ceiling and the q-language skills tax make kdb+ unjustifiable when DuckDB+Parquet delivers 90% of the analytical capability with a C# API, zero licence, and no core caps. Worth documenting so it is not revisited.

- https://kx.com/kdb-free-personal-edition-license-agreement/
- https://kx.com/news-room/kx-debuts-developer-built-kdb-x-community-edition-transforming-time-series-and-real-time-data-for-the-ai-era/
- https://code.kx.com/q/learn/licensing/

### 21. Crash/telemetry: Sentry Developer tier is free at 5,000 errors/month — sufficient for a single-user terminal  
`confidence: high`

Sentry Developer plan: free, 5,000 errors/month, 10,000 performance units/month, 30-day retention. Team plan $26/mo baseline with 50k errors included; overage from $0.0003625/error (50k–100k) sliding to $0.00015 above 20M. Sentry has a first-party .NET SDK. OpenTelemetry .NET is the vendor-neutral alternative: set Activity status to `Error` and call `RecordException()` to capture full exception detail. App Center is retired and not an option.

**Why it matters.** For one user, 5,000 errors/month is effectively unlimited — telemetry is a $0 line item. But: a read-only terminal handling a trader's positions and watchlists must scrub PII/holdings from breadcrumbs before upload. Default to local-only structured logs (Serilog rolling files) with Sentry as opt-in.

- https://markaicode.com/pricing/sentry-pricing/
- https://last9.io/blog/sentry-pricing/
- https://opentelemetry.io/docs/languages/dotnet/traces/reporting-exceptions/
- https://learn.microsoft.com/en-us/appcenter/retirement

## Recommended decisions

### UI framework for the shell

**Recommendation.** WPF on .NET 10 LTS (`net10.0-windows`, TargetPlatformVersion 10.0.22621.0), x64, Fluent ThemeMode + Mica, PerMonitorV2 manifest. Reassess Avalonia only if cross-platform becomes a real requirement.

**Rationale.** It is the only 2026 stack that simultaneously gives you (a) three mature, independent docking implementations, (b) the deepest financial-charting control market, (c) native per-monitor DPI v2 and Mica/dark mode out of the box in .NET 9/10, (d) the largest .NET desktop hiring pool, and (e) zero framework licence cost. WinUI 3's missing dock manager and unresolved resize rendering defect are disqualifying for a panel-heavy terminal; MAUI is version-pinned a major release behind and inherits WinUI's bugs.

**Rejected.** WinUI 3/WinAppSDK — no first-party DockManager (issues #668/#4784/#5188), smooth-resize fix only targeted for summer 2026, thinner control ecosystem. .NET MAUI — unsupported WindowsAppSDK upgrade path, a full major version behind as of 2026-07-31, documented 2026 regressions. Avalonia 12 — excellent and MIT, but thinner financial charting and no reason to pay the portability tax for a Windows-only brief. Electron — 150–250MB per window makes 30 panels untenable. Tauri v2 — lean, but you inherit WebView2's DOM/canvas ceiling for 30 streaming charts and split your codebase across Rust+TS+.NET. Qt/QML — unquotable per-seat + distribution licensing, wrong skillset. Flutter Desktop / Uno / Win32+ImGui — accessibility, text rendering, and control-ecosystem gaps for a data-dense business app.

**Cost.** $0 (framework and runtime)

### Docking / workspace framework

**Recommendation.** Syncfusion WPF DockingManager under the **Community License ($0)** — confirm eligibility in writing first (<$1M revenue, ≤5 devs, ≤10 employees, never >$3M outside capital). Fallback if ineligible: Dirkster.AvalonDock 4.72.1 (free) rather than paying for DevExpress/Telerik.

**Rationale.** Syncfusion gives dock/float/tabbed-document/auto-hide, cross-monitor float panes, and built-in state persistence (PersistState, AutoSave, DeleteDockState, ResetState) — plus SfDataGrid and 100+ other controls in the same free grant. For an eligible solo entity this converts ~$1,300–$2,300/yr into zero. AvalonDock is the credible free fallback (battle-tested in Stride), and Dock.Avalonia 12.1.0 is the equivalent if you ever move to Avalonia.

**Rejected.** DevExpress Universal from $2,253.99 (2026-06-18) — best-in-class DockLayoutManager but unjustifiable when Community covers it. Telerik UI for WPF $749–$1,249/dev/yr, subscription-only with no perpetual option — recurring cost with no asset accrual. Golden Layout — legacy. Dockview/rc-dock — MIT and excellent, but only relevant if you had chosen a web shell.

**Cost.** $0 under Community License; $1,273–$2,254/yr if ineligible

### Primary charting engine

**Recommendation.** SciChart WPF v9 (NuGet `SciChart` 9.1.0.x), **2D Professional, $899/dev perpetual + royalty-free**, using the VisualXccelerator (DirectX) renderer with FIFO DataSeries for live panes. Pair with ScottPlot 5 (MIT) for all secondary/analytical panels.

**Rationale.** Only .NET control with native FIFO/ring-buffer series semantics and a credible streaming-append story; perpetual + royalty-free means one payment, not an annuity a vendor can reprice. Splitting primary (SciChart) vs secondary (ScottPlot 5, which handles 1M–10M points via Signal types) keeps the licence to a single seat and the bill under $1k.

**Rejected.** LightningChart .NET — GPU-strong but the entry point is ~$2,745/dev perpetual for 2D-only (ComponentSource shows from ~$1,347.50, Mar 2026) with tier-gated features; 3x the cost for no decisive advantage on 2D time series. TradingView Advanced Charts — free licence requires a PUBLIC implementation and explicitly excludes personal use; unusable here. Highcharts Stock (~$833+/dev) — web-only and its non-commercial grant does not cleanly cover a private profit-seeking tool. LiveCharts2/OxyPlot — aesthetics/legacy tier, below ScottPlot for volume. Syncfusion/DevExpress/Telerik charts — fine for dashboards, not for 1M-point streaming panes.

**Cost.** $899 one-time (or $629 no-support); ScottPlot 5 $0

### Web-rendered chart surfaces (if any)

**Recommendation.** TradingView **Lightweight Charts v5** (Apache-2.0) hosted in WebView2 — for the AI-panel inline charts and any shareable/embedded view only. Never TradingView Advanced Charts.

**Rationale.** Apache-2.0 imposes no attribution, no public-deployment condition, no company-only restriction. Canvas-based, engineered for large arrays, with `update()` doing incremental repaint versus `setData()` full replacement — correct for streaming. The repo even ships an Agent Skill documenting v5 conventions, which helps the Claude-authored layer generate correct chart code.

**Rejected.** TradingView Advanced Charts — licence forbids private/personal use and requires a public environment plus permanent unmodified attribution. Highcharts Stock — paid and licence-ambiguous for this use. ECharts/uPlot/D3/KLineCharts — viable OSS but none match Lightweight Charts' financial-chart defaults out of the box.

**Cost.** $0

### Local storage architecture

**Recommendation.** Three tiers. (1) **SQLite in WAL mode** — app/session/workspace/watchlist/alerts/symbol metadata + the `sqlite-vec` embedding index, single file. (2) **Parquet lake, hive-partitioned** — `<root>/bars/interval=1m/symbol=AAPL/year=2026/part-*.parquet`, `<root>/ticks/symbol=AAPL/date=2026-08-24/*.parquet`, `<root>/filings/form=4/cik=.../*.parquet`. (3) **DuckDB 1.5.x** via `DuckDB.NET.Data.Full` 1.5.5 as the stateless query engine over that lake, using `ExecuteArrowStream`/`ExecuteArrowBatchesAsync` for zero-copy reads and the allocation-free `DuckDBAppender.AppendRow` for bulk loads. Hot intraday ticks live in an in-memory ring buffer and are flushed to Parquet on a timer and at shutdown.

**Rationale.** Matches each engine to its actual concurrency model: SQLite is 2x–500x better at frequent small writes (10k–150k tx/sec on NVMe) and is the right OLTP store; DuckDB is a single-writer/multi-reader MVCC analytical engine that scans 50M rows in <3s where SQLite takes 45–60s. Parquet-on-disk keeps history portable, compressible, and directly queryable by external tools without an export step. DuckDB 1.4+ also offers AES-256 database encryption if the user wants the lake at rest encrypted.

**Rejected.** SQLite-only — screener/backtest queries become minutes-long. DuckDB-only — wrong for high-frequency small UI-state writes and risks the single-writer lock becoming a UI stall. kdb+/KDB-X — Community Edition caps at 16GB RAM / 24 cores / 4 secondary threads and costs you the q skillset. ClickHouse/chDB, QuestDB, TimescaleDB — server or embedded-server footprints that add install and process-lifecycle complexity a single-user desktop app should not carry. LiteDB — no analytical story. RocksDB/LMDB — KV, no SQL, wrong abstraction for a screener.

**Cost.** $0 (all OSS: SQLite public domain, DuckDB MIT, Parquet/Arrow Apache-2.0)

### Vector store for the AI knowledge layer

**Recommendation.** **sqlite-vec (0.1.x)** inside the same SQLite file, accessed through `Microsoft.SemanticKernel.Connectors.SqliteVec` (currently 1.74.0-preview, a `Microsoft.Extensions.VectorData` provider). Keep chunk text + metadata in ordinary SQLite tables next to the vectors; keep the embedding model id and dimension in a schema table so re-embeds are detectable.

**Rationale.** One file, one backup, one transaction boundary with the rest of app state. Pure C, no deps, runs everywhere SQLite runs. First-party .NET abstraction means you can swap providers later without rewriting retrieval code.

**Rejected.** DuckDB VSS — HNSW persistence is still behind an experimental flag with unimplemented WAL recovery (documented data-loss/corruption risk on unclean shutdown), index not buffer-managed and excluded from memory_limit, broken post-filter WHERE semantics, non-incremental checkpoint rewrites, FLOAT32 only. LanceDB — genuinely embedded but no first-party .NET binding evident. Qdrant/Chroma — require running a server process. pgvector — requires Postgres, an unacceptable install dependency for a desktop app.

**Cost.** $0

### Installer, update channel and packaging

**Recommendation.** **Velopack** producing a setup EXE + self-updating portable package + delta updates, per-user install to %LocalAppData%, updates hosted on a static HTTPS endpoint (S3/R2/GitHub Releases). Optionally add a WiX v5/v6 MSI later only if a per-machine install is ever required. Do **not** use MSIX. Bundle the WebView2 Evergreen bootstrapper (~2MB) as a silent prerequisite.

**Rationale.** Velopack is the maintained Squirrel successor with a Rust core, one-command output, and true delta packages; the CLI is near-identical to Clowd.Squirrel. Staying unpackaged preserves two things this app needs: COM/RTD registration for the Excel add-in, and unrestricted filesystem access to a multi-GB Parquet lake — both of which MSIX's per-user container model complicates for no benefit, on top of sideload-policy and trusted-chain requirements.

**Rejected.** MSIX — per-user only, sideloading gated by policy and signing-chain trust, container isolation hostile to the Excel bridge and the data lake. ClickOnce — legacy, poor signing/UX story. Squirrel.Windows — unmaintained. Inno Setup — good installer, no update framework. NetSparkle — update-only, no installer/delta pipeline.

**Cost.** $0 (Velopack MIT); hosting ~$1–5/mo for static update feed

### Code signing

**Recommendation.** **Azure Artifact Signing (ex-Trusted Signing) Basic at $9.99/month** ($119.88/yr, 5,000 signatures/mo, 1 of each cert profile type) if the signing entity has 3+ years of verifiable operating history and is US/CA/EU/UK. Otherwise an **OV certificate with cloud HSM** — SSL.com OV from $129/yr plus eSigner from ~$180/yr for 240 signatures. Always RFC-3161 timestamp. Budget for SmartScreen warnings regardless.

**Rationale.** Since March 2024 SmartScreen reputation accrues identically for OV and EV, by download volume against the certificate — so paying an EV premium buys nothing for a low-volume single-user app. Artifact Signing is 10x cheaper than any cert and removes hardware-token handling entirely; the eligibility rule is the only thing that can force the fallback, and it must be tested before release week, not during it.

**Rejected.** EV certificate (~$300–600+/yr with token) — no SmartScreen advantage since March 2024 for this profile. Self-signed / unsigned — Windows will actively block or scare the user on every update. Premium Artifact Signing tier ($99.99/mo, 100k signatures) — 20x more signatures than a solo project will ever produce.

**Cost.** $120/yr (Artifact Signing Basic) or ~$309/yr (SSL.com OV + eSigner)

### Runtime performance configuration for tick throughput

**Recommendation.** Explicitly set `<ServerGarbageCollection>false</ServerGarbageCollection>` + `<ConcurrentGarbageCollection>true</ConcurrentGarbageCollection>` (or keep Server GC with `System.GC.DynamicAdaptationMode=0` to disable DATAS), enable `TieredPGO`. Feed the UI through **bounded** `System.Threading.Channels` with `BoundedChannelFullMode.DropOldest` per-symbol conflation, a single 30–60Hz Dispatcher pump that drains and applies the latest value per subscriber, struct-of-arrays tick storage with `ArrayPool<T>`/`Span<T>`, and ring buffers for chart series. Never marshal per-tick to the UI thread.

**Rationale.** DATAS is on by default with Server GC from .NET 9 and shows 1.17x–1.69x regressions in allocation-heavy workloads, with Microsoft explicitly warning about p99 for latency-sensitive work — this must be a deliberate, measured choice. Bounded+DropOldest is the correct conflation policy for market data specifically because a stale quote has zero value: you want load-shedding, not backpressure, on the render path (backpressure belongs on the *ingest* path where you must not lose a trade print).

**Rejected.** Unbounded channels — unbounded memory growth on a fast feed with a slow UI. Per-tick Dispatcher.Invoke — the classic marshalling storm that pins the UI thread. Rx throttle/sample alone — better than nothing but hides allocation cost and does not give per-symbol last-value semantics. Leaving GC settings at default — the predictable cause of unexplained frame stutter.

**Cost.** $0 (engineering time: ~1–2 weeks to build and benchmark the ingest→conflate→render spine)

### Telemetry and crash reporting

**Recommendation.** Local-first: Serilog rolling files + a built-in log viewer panel and 'export diagnostics bundle' button. Sentry .NET on the **free Developer tier** (5,000 errors/mo, 10k perf units, 30-day retention) as an explicit opt-in, with an aggressive scrubber stripping symbols, watchlists, position sizes and API keys from breadcrumbs and exception data.

**Rationale.** For one user, the free tier is effectively unlimited, so the cost is zero and the value is real stack traces from the field. But the data this app touches — what a trader owns and is watching — is the most sensitive thing they have; default-off with an explicit toggle is the only defensible posture. App Center is retired and not an option.

**Rejected.** Sentry Team ($26/mo) — unnecessary at this volume. App Center — retired 2025-03-31 (Analytics/Diagnostics to 2026-06-30). Full OpenTelemetry pipeline — correct for a fleet, over-engineered for a single desktop user with no backend to correlate against.

**Cost.** $0

### Background work scheduling for the Claude-authored knowledge base

**Recommendation.** In-process scheduler (Coravel or Quartz.NET) hosted in the app, plus an optional headless mode invoked by a Windows Scheduled Task so refreshes can run when the terminal is closed. Do NOT ship a Windows Service.

**Rationale.** A Windows Service requires per-machine install (elevation), complicates signing/updating, and buys nothing for a single-user desktop app that is open most of the trading day. A headless `--refresh` CLI entrypoint on the same binary gives you the same 'runs while I'm away' outcome with one artifact, one signature, one update channel.

**Rejected.** Windows Service — elevation, separate update lifecycle, harder crash diagnostics. Cloud-side scheduler — contradicts the local-first, no-connectivity-dependency design and adds a hosting cost and a data-egress question.

**Cost.** $0

### Total licence budget

**Recommendation.** Year 1: **~$1,020** — SciChart WPF 2D Professional $899 (perpetual) + Azure Artifact Signing $119.88. Year 2+: **~$120/yr** (signing only), rising to ~$1,019 only if you choose to buy a SciChart major-version upgrade. Contingency: +$1,273–$2,254/yr if the Syncfusion Community License proves unavailable.

**Rationale.** Everything structural — runtime, UI framework, docking (via Community), database, vector store, installer, updater, Excel bridge, telemetry — is $0. The only genuinely paid line is the one place where free options measurably fail (1M+ point streaming charts) and the one place where being unsigned is unacceptable.

**Rejected.** A DevExpress Universal + LightningChart + Telerik stack lands around $5,000–6,000 in year 1 with recurring renewals, for capability this brief does not require. Conversely an all-free stack (AvalonDock + ScottPlot 5 only) is viable at $0 but gives up FIFO streaming semantics on the primary chart — the one thing the user will judge the app by in the first ten seconds.

**Cost.** $1,019.88 year 1; $119.88/yr thereafter (worst case ~$3,274 year 1 if Syncfusion Community is unavailable)

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | L | Workspace Manager (named, versioned, hot-swappable layouts) | Persist the full dock tree — panel identity, symbol binding, chart timeframe/indicators, scroll position, column widths, filter state — as a serialized layout keyed by a workspace name. Hotkey cycling (Ctrl+1..9) between 'Open', 'Earnings Day', 'Insider Deep Dive', 'FX Session'. Includes diff/restore and 'reset panel to default'. | Syncfusion DockingManager PersistState/AutoSave + custom per-panel state envelope serialized to SQLite |
| P0 | L | Multi-Monitor Tear-Off with Per-Monitor DPI Correctness | Drag any panel out to a native floating window on another monitor at a different DPI, with correct relayout on DPI-change notifications, monitor-hotplug survival (fallback to primary if a saved monitor is absent), and per-monitor workspace slots. | WPF PerMonitorV2 manifest + DockingManager float windows + saved WorkArea rects validated against current EnumDisplayMonitors |
| P0 | XL | Streaming Price Chart with FIFO Tick Engine | Primary chart hosting candles + tick tape + volume profile, backed by a fixed-capacity ring buffer that discards off-screen history, targeting 60fps with sustained appends. Multi-pane synchronized axes, crosshair sync across all charts bound to the same symbol. | SciChart WPF v9 FIFO DataSeries + VisualXccelerator renderer |
| P0 | L | Incentives Overlay Ribbon on the Price Chart | Render insider buys/sells, 13D/G threshold crossings, 10b5-1 plan adoptions, option grant dates, lockup expiries and buyback authorizations as typed, colored annotation markers on the price axis, with click-through to the source filing in the WebView2 reader. | SciChart AnnotationCollection bound to a filings table in DuckDB; PDF/HTML source rendered in WebView2 |
| P0 | L | Blotter Grid: 5,000-Row Virtualized Screener | UI-virtualized + column-virtualized grid with per-cell flash-on-change (green/red decay), frozen columns, in-place sparklines, multi-column sort, saved column sets, and Excel-compatible copy that preserves numeric precision. | Syncfusion SfDataGrid (Community) bound to an ObservableCollection fed by conflated Channel reads |
| P1 | M | Excel RTD Live-Cell Bridge (.xll) | Ship an Excel-DNA add-in exposing =TERM.PRICE(), =TERM.OWNERSHIP(), =TERM.INSIDERNET(sym,days), =TERM.SHORTINT() as RTD functions that push updates into the user's own models without recalc. | Excel-DNA ExcelRtdServer talking to the running terminal over a named pipe / local gRPC |
| P1 | M | Global Hotkey Command Palette | System-wide hotkey (e.g. Ctrl+Alt+Space) raises the terminal and opens a fuzzy command bar: symbol jump, 'insiders AAPL', 'compare MSFT NVDA 5y', workspace switch, indicator toggle. Also global symbol-follow from clipboard. | RegisterHotKey Win32 interop + in-app command registry |
| P1 | L | Tick Recorder & Session Replay | Record every inbound tick/quote to daily Parquet, then replay any session at 1x/10x/max into the live charting pipeline as if it were real-time, with a scrubber. Used for post-mortem and for reasoning about how a move developed intraday. | Append-only Parquet under ticks/symbol=X/date=YYYY-MM-DD/ replayed via DuckDB Arrow stream |
| P0 | L | Local Screener over the Parquet Lake | SQL-backed screener that runs analytical predicates (5y CAGR, insider net-buy z-score, institutional ownership delta QoQ, days-to-cover) across the full universe locally in seconds, with saved screens and scheduled re-runs. | DuckDB 1.5.x over hive-partitioned Parquet, read via DuckDB.NET ExecuteArrowStream |
| P0 | XL | AI Knowledge Panel with Cited, Local Retrieval | Dockable panel that answers questions over the Claude-authored knowledge base plus the local filings/transcripts corpus, with inline citations that deep-link to the exact source document and paragraph in the reader panel. | sqlite-vec index in the app's SQLite file via Microsoft.Extensions.VectorData; UI in WebView2 or native |
| P1 | M | Scheduled Knowledge-Base Refresh (in-process scheduler) | An in-process scheduled job host (not a Windows Service) that wakes on app start and on cron, pulls new filings/prices, re-embeds changed documents, and writes a dated changelog the user can read: 'what changed in your universe since Friday'. | Coravel/Quartz.NET in-process + Windows Task Scheduler fallback for headless refresh |
| P1 | M | Alert Engine with Native Toasts and Alert History | Rule-based alerts (price level, % move, volume spike, new Form 4 by an officer, 13D filed, short-interest jump) delivered as Windows app notifications with actionable buttons that deep-link into the terminal. Persistent, searchable alert log. | CommunityToolkit.WinUI.Notifications 7.1.2 ToastContentBuilder (works unpackaged) |
| P1 | L | Filings Reader with Diff (WebView2) | Embedded reader for 10-K/10-Q/8-K/DEF 14A/Form 4 with section navigation, a redline diff against the prior period's equivalent section, and one-click 'send to AI panel' for summarization with citation. | WebView2 Evergreen rendering locally cached HTML; diff computed in .NET |
| P2 | L | Ownership & Insider Network Graph | Interactive graph of holders, overlapping board seats, and cross-shareholdings, with node sizing by position value and edge weighting by recent change. Time-scrub to watch the ownership base rotate. | 13F/13D-G data in DuckDB; rendered via SkiaSharp custom control or ScottPlot 5 scatter with custom draw |
| P1 | M | Compare Mode / Relative Performance Workspace | N-symbol overlay normalized to a common base, with pair spread, ratio chart, rolling correlation, and beta-to-index, all sharing a synchronized crosshair and time range across every open chart panel. | SciChart multi-series + shared XAxis range binding |
| P2 | S | FX Session Clock & Liquidity Heat Strip | Always-visible strip showing Tokyo/London/NY session overlaps, scheduled macro releases, and a per-pair typical-spread/liquidity heat band for the current time-of-day. | Static session calendar + historical spread stats aggregated in DuckDB |
| P2 | S | Always-On-Top Mini-Ticker + Tray Mode | Collapse the terminal to a compact borderless always-on-top ticker strip (or system tray) that keeps streaming a watchlist while the user works in Excel or a browser; click to restore the full workspace. | WPF Topmost + WindowChrome; NotifyIcon via H.NotifyIcon |
| P2 | S | Snapshot & Annotate → Clipboard/PNG | One-key capture of any chart or panel (or the whole workspace) with drawn annotations, symbol/timestamp watermark, straight to clipboard for pasting into notes or a message. | RenderTargetBitmap / SciChart ExportToFile + Clipboard interop |
| P1 | M | Data Freshness & Provenance Inspector | Per-panel badge showing source, last-update timestamp, and whether the value is live, delayed, or stale-cached; a global panel listing every feed's health, quota consumption, and last error. | Per-feed metadata table in SQLite + in-memory health registry |
| P1 | S | Local Encrypted Vault for API Keys & Positions | DPAPI/Windows Hello-protected local store for vendor API keys and the user's own position/watchlist data, with an explicit 'never leaves this machine' guarantee surfaced in the UI. | Windows DPAPI ProtectedData + optional DuckDB 1.4+ AES-256 database encryption |
| P3 | S | Portable Mode (USB / no-install) | A self-contained portable build that runs from a folder with all state in a sibling data directory, for locked-down machines where installation is not permitted. | Velopack self-updating portable package |

## Risks

- Syncfusion Community License eligibility is the single largest cost assumption in this plan ($0 vs ~$1,300–$2,300/yr). The criteria (<$1M revenue, ≤5 devs, ≤10 employees, never >$3M outside capital) are checked against the LICENSEE entity — if the terminal is later put inside a fund management company, eligibility can evaporate retroactively for new versions. Get written confirmation before the first line of docking code.
- Azure Artifact Signing's 3-year-operating-history requirement will likely block a newly formed entity. If the plan assumes $9.99/mo signing and the entity is new, release slips while an OV cert + hardware/cloud HSM is procured (multi-day validation). Test eligibility in month 1, not release week.
- SciChart's headline performance numbers (1 billion points at 60fps, 25M appends/sec) are vendor marketing measured on unspecified hardware with FIFO/downsampling active. Real numbers with 6 live panes, annotations, and crosshair sync will be far lower. Build a throwaway spike with the trial licence and 30 simulated feeds before committing the $899 and, more importantly, the architecture.
- WPF renders through DirectX with a software fallback; over RDP, in VMs, on some remote-desktop and GPU-switching (hybrid Intel/NVIDIA) configurations, hardware acceleration silently degrades to software and frame rates collapse. Multi-GPU multi-monitor setups (a common trader configuration) are exactly where this bites. Detect RenderCapability.Tier at startup and degrade panel count / disable animations rather than stuttering.
- DuckDB's single-writer model means a long-running screener query and a tick-flush can contend. If the flush path and the query path share a connection or a database file lock, the UI stalls. Keep DuckDB stateless over Parquet (query-only) and do writes as file-level Parquet appends, not DuckDB table inserts.
- MSIX avoidance and unpackaged deployment mean no Microsoft Store distribution path and no automatic container-based cleanup. Uninstall must explicitly account for a possibly multi-GB Parquet lake — deleting a user's captured tick history on uninstall without asking would be a serious data-loss incident.
- Excel RTD via a .xll requires bitness matching (x64 Excel vs x64 app) and can be silently disabled by Excel's add-in security or by a crash putting the add-in on the disabled list. It also creates a second process boundary that must survive terminal restarts. Budget real time for this; it looks like a weekend project and is not.
- The AI knowledge layer's embedding model choice is a schema commitment: changing embedding models forces a full re-embed of the corpus. Without an explicit model-id + dimension column in the vector schema, mixed-model vectors will silently return garbage neighbours. This is a quiet correctness failure that no test will catch.
- sqlite-vec is at 0.1.x — pre-1.0 by the author's own versioning, with recent releases still fixing 'long-standing bugs' in DELETE and KNN constraint handling. The Semantic Kernel SqliteVec connector is also preview and explicitly warns that breaking changes may still occur. Pin exact versions and own the upgrade.
- Avalonia 12.0 is only ~4 months old (GA 2026-04-07) and its docking library (Dock 12.1.0) required a 200-file migration with acknowledged workarounds for v12 bugs. If Avalonia is chosen as a hedge, do not adopt it in the same quarter as its major-version ecosystem is still settling.
- Windows 11 25H2 and future feature updates periodically change DWM behaviour (Mica, snap layouts, rounded corners) and have historically broken custom WindowChrome implementations. A terminal with a custom title bar for dark-mode consistency is exposed to this on every OS feature update; keep a non-custom-chrome fallback path.
- .NET 11 arrives Nov 2026 as STS. There will be pressure to adopt it for perf wins. Doing so trades a 3-year support runway for 24 months and re-opens the GC/DATAS tuning question. Stay on .NET 10 LTS through at least .NET 12 LTS (Nov 2027).
- Free/OSS chart and docking libraries (ScottPlot, AvalonDock, Dock.Avalonia) are effectively single-maintainer projects. A bus-factor event mid-project is a real risk for a multi-year terminal. Mitigate by keeping chart and dock usage behind a thin internal abstraction so a swap costs weeks, not months.

## Open questions

- Is the licensing entity eligible for the Syncfusion Community License, and will it remain eligible if the terminal is ever used inside a registered fund or advisory business? (Determines a $0 vs ~$1,300–$2,300/yr line item.)
- Does the signing entity have 3+ years of verifiable tax/operating history in the US, Canada, EU or UK? (Determines Azure Artifact Signing $120/yr vs OV+eSigner ~$309/yr and a multi-day validation delay.)
- Exact current SciChart WPF v9 SKU pricing could not be verified on scichart.com directly (the site returned HTTP 403 to automated fetches). Figures of $899 Professional / $1,699 Source / $629 no-support / 'from $1,499' come from search snippets and should be confirmed against a live quote before budgeting. Also unconfirmed: whether v9 is included in a licence purchased today or requires a paid major-version upgrade.
- LightningChart .NET's exact 2026 tier pricing could not be fetched (403). Reported figures span ~$1,347.50 (ComponentSource, Mar 2026) to $2,745 (2D perpetual) — the discrepancy is likely subscription vs perpetual and needs a direct quote if LightningChart is reconsidered.
- Qt's actual per-developer-per-year and per-distribution figures remain unpublished; a quote would be needed to fully close out the Qt option, though the skillset argument already rules it out.
- Exact Syncfusion Essential Studio WPF and DevExpress WPF-only (non-Universal) per-developer prices were not pinned down — only bundle-level figures (DevExpress Universal from $2,253.99, Telerik DevCraft Complete from $1,273.02) — so the 'community license ineligible' contingency figure is approximate.
- How many simultaneously-streaming chart panes must hold 60fps as a hard acceptance criterion — 6, 12, or 30? This single number determines whether ScottPlot 5 alone suffices or SciChart is mandatory, and whether a GPU requirement must be stated in the system requirements.
- What is the actual expected tick rate across the subscribed universe (ticks/sec aggregate, peak vs mean)? Below ~5k msg/sec the entire conflation/ring-buffer architecture is over-engineering; above ~100k msg/sec the Parquet flush cadence and in-memory ring sizing become the dominant design constraints.
- Will the AI knowledge layer's embeddings be generated locally (ONNX/embedded model, no network) or via a hosted embedding API? This determines whether the app must function fully offline, and whether corpus text ever leaves the machine — a material privacy commitment for a tool holding the user's watchlist.
- Is macOS or Linux ever plausible? If the honest answer is 'no', WPF is correct and this is settled. If it is 'maybe in 3 years', the Avalonia 12 option deserves a real spike now, because retrofitting is a rewrite.
- Does the user run multiple GPUs / mixed-DPI / RDP-into-a-workstation? These are the three configurations where WPF's rendering degrades non-obviously, and they are common among traders. Needs to be established before performance targets are set.
- What is the retention policy and disk budget for the local tick lake? At full tick capture for a few hundred symbols this reaches hundreds of GB per year, which changes the Parquet partitioning scheme, the compression codec choice, and whether a rollup/expiry job is a v1 requirement.
