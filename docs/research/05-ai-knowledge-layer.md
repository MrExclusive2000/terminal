# The AI Knowledge Layer for a read-only Windows equities/FX trading terminal: Claude-authored knowledge packs, RAG over filings, guardrails, cost and evaluation (research as of 2026-08-24)

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

The AI layer should be a **hybrid**: Claude API (Opus 5 / Sonnet 5 / Haiku 4.5) for everything that requires judgment or citation, a small local ONNX/Foundry-Local model for cheap, high-frequency, privacy-sensitive work (hover-translate, query rewriting, NER, offline degraded mode). Local-only is not viable: a 7–14B model cannot rank materiality in a 10-K redline or red-team a thesis at institutional calibre. Cloud-only is not acceptable either, because the watchlist is the alpha and because the app must still function when the API is down or the monthly spend cap trips.

Verified economics (platform.claude.com, 2026-08-24): Opus 5 $5/$25 per MTok, 1M context, 128K output, cache read $0.50, 1h cache write $10, batch $2.50/$12.50. Sonnet 5 $2/$10 (the scheduled 1 Sep 2026 rise to $3/$15 was cancelled). Haiku 4.5 $1/$5. Web search $10/1,000; web fetch free; code execution free when paired with the current web tools. Cached input tokens do **not** count toward ITPM, so prompt caching raises effective throughput as well as cutting cost. A heavy solo user lands at roughly **$250–450/month** if the knowledge-pack build runs nightly on Batch and interactive Q&A runs on Opus 5 with a cached knowledge prefix — but the Start-tier **$500/month spend cap** will hard-429 with no `retry-after`, so Build tier ($1,000 cap) is the correct starting posture.

The "Claude personally updates the knowledge base" mechanism should be a **Claude Code Routine** (research preview: schedule/API/GitHub triggers, minimum 1-hour cadence, runs on Anthropic cloud infra) operating on a private git repo of **signed, versioned Knowledge Packs**. Critically, Routines require a claude.ai subscription login and cannot be driven by an API key, and Anthropic prohibits third-party products from offering claude.ai login — so this is the *owner's* pipeline publishing to a CDN, not a subsystem shipped inside the binary. The desktop app pulls a signed index, verifies Ed25519 signatures, hot-loads packs, and shows a **claim-level diff** ("what your terminal learned last night, and why") gated by a user approval mode.

Trust is enforced structurally, not by prompting: claims carry sources, confidence and decay; FACT panels render only from deterministic pipelines (XBRL companyfacts, not model prose); INFERENCE panels are visually segregated and every numeric sentence must carry a `citations[]` entry or it is struck. Filings and news are treated as hostile input — Opus 5's `role:"system"` mid-conversation channel is the non-spoofable operator path, the analysis agent has no write tools, and `web_fetch` is domain-restricted and structurally unable to construct URLs.

Two hard API constraints shape the design: **citations and structured outputs are mutually exclusive (400 error)**, and the Opus 4.7+ tokenizer emits ~30% more tokens for the same text, so any cost model built on older counts is wrong by a third.

## Findings

### 1. Claude model pricing and context, verified 2026-08-24  
`confidence: high`

Claude Opus 5 (`claude-opus-5`): $5/MTok input, $25/MTok output, 1M context, 128K max output. 5-min cache write $6.25, 1-hour cache write $10, cache read/refresh $0.50. Batch: $2.50/$12.50. Claude Sonnet 5 (`claude-sonnet-5`): $2/$10, 1M context; the docs explicitly note the launch 'introductory' $2/$10 is now the standard price and the scheduled 1 Sep 2026 increase to $3/$15 will NOT occur. Batch $1/$5, cache read $0.20. Claude Haiku 4.5 (`claude-haiku-4-5`): $1/$5, 200K context, batch $0.50/$2.50, cache read $0.10. Claude Fable 5 (`claude-fable-5`): $10/$50, 1M, batch $5/$25 — and Fable 5 is NOT available under zero data retention. Batch API is a flat 50% off input and output and stacks with prompt caching.

**Why it matters.** Every token-budget decision in the terminal keys off these three price points. The Sonnet 5 price freeze is worth ~33% on the mid-tier tasks (earnings-call tone, comp selection) versus a plan written against the announced increase.

- https://platform.claude.com/docs/en/about-claude/pricing

### 2. Prompt caching is the single biggest cost lever, and it has five silent failure modes  
`confidence: high`

Cache read = 0.1x base input; 5-min write = 1.25x (break-even after 2 requests); 1-hour write = 2x (break-even after 3). Max 4 `cache_control` breakpoints per request. Render order is tools -> system -> messages. Minimum cacheable prefix is NON-MONOTONIC: 512 tokens on Opus 5 / Fable 5, 1024 on Opus 4.8 / Sonnet 5 / Sonnet 4.6, 2048 on Opus 4.7, 4096 on Opus 4.6 / Opus 4.5 / Haiku 4.5. Failure modes: (1) any timestamp/UUID early in the prefix invalidates everything after it; (2) each breakpoint walks back at most 20 content blocks, so an agentic loop that emits >20 tool_use/tool_result blocks in one turn silently misses; (3) N concurrent requests with identical prefixes all pay full write price because an entry is only readable once the first response begins streaming; (4) changing tool definitions or the model invalidates the entire cache; (5) changing `output_config.format` invalidates the prompt cache. Verify with `usage.cache_read_input_tokens`.

**Why it matters.** A terminal that fans out 8 AI panels simultaneously on symbol-open pays 8x the cache write and gets zero reads. The 20-block lookback directly bites the nightly knowledge-pack agent loop. The 4096-token minimum on Haiku 4.5 means a knowledge prefix that caches on Opus silently will not cache on the cheap fallback path.

- https://platform.claude.com/docs/en/about-claude/pricing
- claude-api skill: shared/prompt-caching.md

### 3. Cached input tokens do not count toward rate limits — caching raises throughput, not just cuts cost  
`confidence: high`

For all current models (only retired Haiku 3.5 is excepted), `cache_read_input_tokens` do NOT count toward ITPM. Only `input_tokens` (tokens after the last breakpoint) + `cache_creation_input_tokens` count. Standard limits — Start tier: Opus 5 1,000 RPM / 2M ITPM / 400K OTPM; Build: 5,000 / 5M / 1M; Scale: 10,000 / 10M / 2M. Opus 5 has its own rate-limit bucket separate from the combined Opus 4.x bucket. Batch API has separate limits: Start 200,000 requests in queue, Build 300,000, Scale 500,000; 100,000 requests per batch at every tier.

**Why it matters.** With an 80% cache hit rate a 2M ITPM limit effectively processes 10M input tokens/minute. This makes a large pinned knowledge prefix (30–80K tokens) cheap in both dollars and rate-limit headroom — the opposite of the naive assumption that a big KB in context is expensive per-request.

- https://platform.claude.com/docs/en/api/rate-limits

### 4. Monthly spend caps will hard-fail the terminal with no retry-after  
`confidence: high`

Start tier caps organisation spend at $500/month, Build at $1,000, Scale at $200,000; Custom has none. On hitting the cap the API returns HTTP 429 with `error.type: rate_limit_error` and `error.details.error_code: enforced_spend_limit_reached`, and — unlike a real rate limit — **no `retry-after` header**. SDK automatic retries will fail repeatedly. Access resumes at 00:00 UTC on the 1st of the next month unless you request a higher tier. A user-set spend limit below the tier cap instead returns HTTP 400 `invalid_request_error`.

**Why it matters.** A heavy solo user's realistic bill ($250–450/mo, more if Opus-heavy) sits uncomfortably close to the $500 Start cap. The app must detect `enforced_spend_limit_reached` specifically, stop retrying, degrade to local-model + cached-pack mode, and tell the user why — rather than showing generic 'AI unavailable'.

- https://platform.claude.com/docs/en/api/rate-limits

### 5. Citations: exact mechanics, and the hard incompatibility with structured outputs  
`confidence: high`

Set `citations: {enabled: true}` on each `document` block (all or none). Three document types: plain text (auto-chunked to sentences, citations return `char_location` with 0-indexed exclusive end); PDF (text extracted, sentence-chunked, `page_location` 1-indexed; image citations NOT supported, so scanned PDFs with no extractable text are not citable); custom content (your blocks used as-is with no further chunking, `content_block_location` block indices). The response splits into multiple `text` blocks; cited blocks carry a `citations` array with `cited_text`, `document_index`, `document_title`. Enabling citations adds a small input-token overhead. **Citations cannot be combined with structured outputs**: enabling citations on any `document` or `search_result` block while also sending `output_config.format` returns a 400.

**Why it matters.** 'Cited JSON' is impossible in one call. Any feature that wants both machine-parseable output AND per-claim citations (screener explanations, red-flag scorecards, pack claim generation) must be two calls, or must emit the structure through a strict tool call and keep citations on the prose blocks. Naive plans assume both.

- https://platform.claude.com/docs/en/build-with-claude/citations
- https://platform.claude.com/docs/en/build-with-claude/structured-outputs

### 6. `search_result` content blocks are the right RAG primitive — first-class citations, no beta header  
`confidence: high`

Schema: `{type: "search_result", source: <required URL or identifier string>, title: <required>, content: [{type:"text", text:"..."}], citations: {enabled: true}}`. Usable two ways: returned from your own custom tool (dynamic RAG) or placed directly as top-level content in a user message (pre-fetched/cached). Supported on all active models except Claude Haiku 3. No beta header — part of the standard Messages API. Claude cites them the same way it cites web search results, carrying your `source` and `title` through to the citation object.

**Why it matters.** This is what makes 'show me the evidence' cheap to build. Set `source` to a deep link the app can resolve — e.g. `sec:0000320193-25-000073#item7-liquidity` — and every citation Claude emits becomes a clickable jump into the filing viewer scrolled to the exact section. No custom citation-parsing needed.

- https://platform.claude.com/docs/en/build-with-claude/search-results

### 7. Structured outputs: current shape, supported JSON Schema subset, and what is rejected  
`confidence: high`

Use `output_config: {format: {type: "json_schema", schema: {...}}}` on `messages.create()`. The old `output_format` parameter and the `structured-outputs-2025-11-13` beta header are deprecated but tolerated; the Python SDK 1.0+ rejects `output_format`. No beta header required. Also available: `strict: true` as a top-level field on a tool definition (requires `additionalProperties: false` + `required`). Supported: object/array/string/integer/number/boolean/null, `enum` (primitives only), `const`, `anyOf`, `allOf`, internal `$ref`/`$defs`, `default`, `required`, `additionalProperties:false`, string formats (date-time, date, email, uri, uuid, ipv4/6), array `minItems` of 0 or 1 only. NOT supported: recursive schemas, complex types in enums, external/http `$ref`, numeric constraints (`minimum`/`maximum`/`multipleOf`), string constraints (`minLength`/`maxLength`), `pattern`, complex anyOf/oneOf combinations. Compiled grammars are cached 24h; first use pays a compilation latency penalty; changing the schema or tool set invalidates that cache.

**Why it matters.** The natural-language screener compiles NL into a deterministic query object — that object's schema cannot use `pattern` or numeric bounds for validation, so range-checking (e.g. short interest 0–100) must happen in your own validator after the model returns. Recursive schemas being unsupported rules out a naive nested boolean-expression AST; use a flat list of predicates plus a separate combinator field.

- https://platform.claude.com/docs/en/build-with-claude/structured-outputs

### 8. Extended thinking on Opus 5: `budget_tokens` is gone, effort is the dial, and disabling thinking is a trap  
`confidence: high`

On Claude Opus 5 use `thinking: {type: "adaptive"}` (thinking is ON by default if the parameter is omitted — a change from Opus 4.8/4.7 where omitting it meant no thinking). `budget_tokens` returns 400 on Opus 5 / Fable 5 / Sonnet 5 / Opus 4.8 / 4.7; so do `temperature`/`top_p`/`top_k`. Depth is controlled by `output_config: {effort: "low"|"medium"|"high"|"xhigh"|"max"}`, default `high`. Thinking `display` defaults to `"omitted"` on Opus 5 (a silent change from 4.6) — set `{type:"adaptive", display:"summarized"}` if you want to stream reasoning to the user. `{type:"disabled"}` is accepted only at effort `high` or below, and has two documented failure modes: the model may write a tool call into visible text instead of emitting a `tool_use` block (silent failure, no error), and may leak `<thinking>` tags. Assistant prefill returns 400 on all 4.6+ models.

**Why it matters.** 'Show me your reasoning' as a UI affordance needs `display: "summarized"` explicitly or the user sees a long pause then an answer. Cost control belongs in `effort` (use `low` for hover-translate subagents, `xhigh` for filing-diff materiality ranking), not in disabling thinking.

- claude-api skill: Thinking & Effort quick reference; shared/model-migration.md

### 9. The Opus 4.7+ tokenizer emits ~30% more tokens for the same text  
`confidence: high`

Anthropic's pricing page states plainly: 'Claude 4.7 and later models and Claude Mythos Preview use a newer tokenizer... This tokenizer produces approximately 30% more tokens for the same text.' Claude Sonnet 4.6 and earlier use the previous tokenizer. Opus 5 shares the 4.7/4.8 tokenizer. Re-baseline with `POST /v1/messages/count_tokens` when moving from Sonnet/Haiku to Opus.

**Why it matters.** A cost model built by counting a 10-K at, say, 90K tokens on the old tokenizer is really ~117K on Opus 5 — a 30% under-estimate across every filing-ingest feature. This also silently changes whether a prompt clears a cache minimum and how many filings fit in the 1M window.

- https://platform.claude.com/docs/en/about-claude/pricing

### 10. Claude Code Routines are the right scheduled-authoring mechanism — but they cannot ship inside the product  
`confidence: high`

Routines (research preview, 2026) are saved Claude Code configs — prompt + repositories + connectors — with schedule, API and GitHub triggers, running on Anthropic cloud infra. Minimum schedule interval is **one hour**; presets are hourly/daily/weekdays/weekly with custom cron via `/schedule update`; runs are staggered by a consistent per-routine offset. API trigger: `POST https://api.anthropic.com/v1/claude_code/routines/{trig_id}/fire` with `Authorization: Bearer <token>`, header `anthropic-beta: experimental-cc-routine-2026-04-01`, optional `{"text": "..."}`; returns `claude_code_session_id` and URL. Routines push to `claude/`-prefixed branches (always accepted) and are rejected on protected branches or branches with someone else's commits. **Hard constraints:** Routines require a claude.ai subscription login — API-key/Bedrock/Vertex/Foundry auth all fail; there is a per-account daily run cap (one-off runs excluded); and Anthropic's Agent SDK docs state 'Anthropic does not allow third party developers to offer claude.ai login or rate limits for their products.'

**Why it matters.** This settles the architecture question. 'Claude personally updates it' = the OWNER's Routine, on the owner's claude.ai account, committing signed packs to the owner's private repo, published to a CDN the desktop app pulls from. It is emphatically NOT a subsystem you embed in a distributed binary. For a single sophisticated user this is exactly right; for any future multi-user version it must be re-architected onto the Claude API or Managed Agents.

- https://code.claude.com/docs/en/routines
- https://code.claude.com/docs/en/agent-sdk/overview
- https://code.claude.com/docs/en/claude-code-on-the-web

### 11. Routine fire-payloads and prompts have explicit trust semantics you can build on  
`confidence: high`

When a trigger fires, the routine's saved prompt is delivered as an assigned task, not as untrusted mid-conversation content — the trigger attests the prompt was stored ahead of time by an authorised session, but explicitly 'is not live user input and can't act as approval or consent for actions during the run.' Text passed via the API trigger's `text` field (or web 'Run now') arrives wrapped in a `<routine-fire-payload>` block labelled untrusted, and the routine's own prompt must explicitly opt in to acting on it. Content fetched during the run keeps normal untrusted handling.

**Why it matters.** This is a documented, non-spoofable trust boundary you can lean on for the pack-authoring pipeline: the standing prompt (the pack spec, the schema, the citation rules) is trusted; every filing, news article and web page the routine reads during the run is not. Design the prompt so the untrusted corpus can only ever become *quoted claim material*, never instructions.

- https://code.claude.com/docs/en/routines

### 12. Managed Agents scheduled deployments: the alternative mechanism, with hard numbers  
`confidence: high`

`POST /v1/deployments` (beta `managed-agents-2026-04-01`) bundles agent + environment + `initial_events` + `schedule {type:"cron", expression, timezone}` (IANA tz, minute granularity max). Response includes `schedule.upcoming_runs_at`. Execution is **jittered up to 15% of the interval between runs, floored at 5 seconds, capped at 9 minutes** — an hourly deployment can fire 9 minutes late. Max 1,000 scheduled deployments per organisation. DST uses literal wall-clock matching: times that don't exist on spring-forward are SKIPPED, times that occur twice on fall-back fire TWICE. Every trigger writes a `drun_` run record queryable with `has_error=true`. Billing: tokens at standard rates plus **$0.08 per session-hour** of `running` status; the Batch API discount does NOT apply to Managed Agents sessions.

**Why it matters.** If the pack pipeline ever needs to be API-key-driven (multi-user, or CI without a claude.ai login), this is the path — at the cost of losing the 50% batch discount. The DST double-fire is a real corruption risk for a versioned pack repo: schedule builds outside 01:00–03:00 local or use UTC, and make pack writes idempotent on `content_version`.

- claude-api skill: shared/managed-agents-scheduled-deployments.md
- https://platform.claude.com/docs/en/about-claude/pricing

### 13. Agent SDK / headless Claude Code: the practical harness for the pack builder  
`confidence: high`

Claude Agent SDK is Python and TypeScript only; other languages drive it by running the CLI as a subprocess. Key headless flags: `claude -p "<prompt>"`, `--output-format json|stream-json|text`, `--json-schema '<JSON Schema>'` (structured result lands in `structured_output`), `--allowedTools "Read,Edit,Bash(git diff *)"` using permission-rule prefix syntax (the space before `*` matters), `--permission-mode auto|dontAsk|acceptEdits`, `--append-system-prompt`, `--continue`/`--resume <session_id>`, and `--bare` (skips auto-discovery of hooks, skills, MCP servers, plugins, CLAUDE.md — recommended for CI, and will become the `-p` default). `--output-format json` returns `total_cost_usd` plus a per-model breakdown (client-side estimates). Piped stdin is capped at 10MB. Exit code 0 on success, 143 on SIGTERM.

**Why it matters.** `--bare` + `--json-schema` + `--allowedTools` is exactly the shape of a deterministic, auditable, reproducible pack-build step, and `total_cost_usd` per invocation gives you a per-pack cost meter without touching the usage dashboard. Note `--bare` does not read OAuth credentials — set `ANTHROPIC_API_KEY` — which is the API-key path if you move off Routines.

- https://code.claude.com/docs/en/headless
- https://code.claude.com/docs/en/agent-sdk/overview

### 14. Windows local-AI landscape 2026: Phi Silica is being deleted in November 2026  
`confidence: high`

Microsoft Foundry on Windows = three layers: Windows AI APIs (ready-made, mostly Copilot+ PC), Foundry Local (ready-made LLM/STT, Win 10+), Windows ML (ONNX Runtime, bring your own model, Win 10+). **Phi Silica is a trap**: it is a Limited Access Feature requiring an unlock token, is not available in China, and Microsoft's own docs state it 'is being replaced by Aion Instruct' — standalone sideloadable package early Oct 2026, Windows Insider rollout Oct 2026, **retail rollout and Phi Silica REMOVAL in November 2026**. Aion Instruct needs no LAF token. Phi Silica GPU support (NVIDIA RTX 30-series+ with 6+GB VRAM, AMD RX 9060+ with 6+GB) requires Developer Mode enabled, Insider Experimental build 26300.8553+, Windows App SDK 2.2.2-experimental9+, and manufacturer-direct drivers (NVIDIA 615.21 beta, AMD Adrenalin 26.10.2). Prompt compression and speculative decoding are NPU-only, absent on GPU. The GPU model is not pre-installed — it is a multi-GB on-demand Windows Update download via `EnsureReadyAsync`, and the user can delete it at Settings > System > AI Components.

**Why it matters.** Any local-AI plan built on Phi Silica will break within three months of ship. This is the single highest-value adversarial finding in the local-model domain. Also: 'local model' does not mean 'always available' — GetReadyState can return NotReady or NotSupportedOnCurrentSystem at any time, so the local path needs the same graceful-degradation treatment as the cloud path.

- https://learn.microsoft.com/en-us/windows/ai/apis/phi-silica
- https://learn.microsoft.com/en-us/windows/ai/overview

### 15. Foundry Local is the durable local-inference option on Windows  
`confidence: high`

Install: `winget install Microsoft.FoundryLocal`. No unlock tokens, no Copilot+ requirement. Prerequisites: Windows 11 version 24H2 (build 26100) or later, .NET 9.0 SDK+, and a DirectX 12-capable GPU (integrated or discrete) — VMs without GPU passthrough return successful responses with EMPTY content. .NET: `Microsoft.AI.Foundry.Local.WinML` 1.0.0 (auto-selects Qualcomm NPU / NVIDIA GPU / CPU via ONNX Runtime); cross-platform variant is `Microsoft.AI.Foundry.Local`. Python: `foundry-local-sdk-winml` (Windows, accelerated) or `foundry-local-sdk` — never both, they pin conflicting `onnxruntime-core`. Also JS/Node and Rust. Pass a model ALIAS (not full ID) so the right hardware variant is chosen: `phi-3.5-mini` (2.53 GB), `phi-4`, `qwen2.5-0.5b`, `qwen2.5-7b`, `deepseek-r1-7b`; 20+ models, catalog at foundrylocal.ai/models. Models are hosted by Microsoft, acquired at runtime, and shared across apps.

**Why it matters.** This gives you a zero-marginal-cost, zero-data-egress tier for hover-translate, query rewriting, entity extraction over news, PII/position-size scrubbing before any cloud call, and an offline degraded mode. The 24H2 floor and the DX12/VM caveat are deployment gates the installer must check.

- https://learn.microsoft.com/en-us/windows/ai/foundry-local/get-started
- https://learn.microsoft.com/en-us/windows/ai/overview

### 16. Embedding and reranking costs are negligible — Voyage pricing as of 2026-08-24  
`confidence: high`

Embeddings per million tokens: voyage-4-large $0.12 (200M free tokens), voyage-4 $0.06 (200M free), voyage-4-lite $0.02 (200M free), voyage-context-4 $0.12 (200M free), voyage-code-4 $0.12 (200M free), voyage-finance-2 $0.12 (50M free), voyage-code-3 $0.12 (50M free). Older: voyage-3.5 $0.06 (no free tier), voyage-3-large $0.18 (no free tier). Rerankers: rerank-2.5 $0.05/MTok (200M free), rerank-2.5-lite $0.02/MTok (200M free). The pricing page does not publish context length or dimension per model.

**Why it matters.** Embedding 500 companies x 3 filings x ~110K tokens = ~165M tokens, which fits inside voyage-4's 200M free allowance — i.e. the initial corpus build is effectively free, and ongoing re-embedding of ~200 filings/month costs about $1.20. Reranking 60 queries/day over 50 candidates is under $2/month. Retrieval quality is therefore a design choice, not a budget choice: use hybrid + rerank always.

- https://docs.voyageai.com/docs/pricing

### 17. Use XBRL structured facts instead of parsing prose — and know EDGAR's hard limits  
`confidence: high`

data.sec.gov endpoints, JSON, no API key, no CORS: `https://data.sec.gov/submissions/CIK##########.json` (10-digit zero-padded CIK; at least one year or 1,000 most recent filings, with references to older files); `https://data.sec.gov/api/xbrl/companyconcept/CIK##########/us-gaap/{Concept}.json` (all disclosures of one concept, fact arrays per unit of measure); `https://data.sec.gov/api/xbrl/companyfacts/CIK##########.json` (every concept in one call); `https://data.sec.gov/api/xbrl/frames/us-gaap/{Concept}/USD/CY2019Q1I.json` (cross-sectional peer pull; CY####, CY####Q#, CY####Q#I). Submissions update within ~1 second; XBRL within ~1 minute; bulk ZIPs republished nightly around 03:00 ET. **Maximum access rate is 10 requests per second**, monitored. A declared `User-Agent` is required, format `Company Name AdminContact@domain.com`, plus `Accept-Encoding: gzip, deflate`. Full-text search is `efts.sec.gov` (Elasticsearch-shaped: 100 hits per page out of the total, with aggregations by entity, SIC, state and form type).

**Why it matters.** Every tagged number in the terminal should render from companyfacts, never from an LLM restating prose — that eliminates a whole class of hallucination by construction and makes the FACT/INFERENCE split enforceable rather than aspirational. The 10 req/s ceiling and the real-contact User-Agent are operational: getting IP-blocked kills the entire insiders/filings pillar. Backfill from the nightly bulk ZIPs, use the APIs only for deltas.

- https://www.sec.gov/search-filings/edgar-application-programming-interfaces
- https://www.sec.gov/os/webmaster-faq
- https://efts.sec.gov/LATEST/search-index

### 18. The code-execution sandbox has NO internet — which shapes how quant tools are built  
`confidence: high`

`code_execution_20260521` / `_20260120` runs Python and bash in a sandboxed container with **no internet access**; Claude cannot install packages at runtime, only the pre-installed library set is available (numpy/pandas ecosystem plus pyarrow, openpyxl, xlsxwriter, pillow, python-pptx, python-docx, pypdf, pdfplumber, pypdfium2, reportlab and similar). Containers expire 30 days after creation, are checkpointed after ~5 minutes of inactivity, and are restored by passing the `container.id` back in the top-level `container` parameter. With `_20260120`+ and programmatic tool calling, Python interpreter state persists across requests that reuse the container; each Python cell has a 90-second wall-clock limit (returns non-zero `return_code` with a `detection_timeout` message). Each `bash_code_execution` call gets a fresh `$OUTPUT_DIR`; only top-level files there are returned as `file_id`s. Billing: free when the request also includes `web_search_20260209`/`web_fetch_20260209` or later; otherwise 1,550 free container-hours per organisation per month, then $0.05 per hour per container, minimum 5 minutes per execution, and billed even if the tool is not called when files are pre-loaded.

**Why it matters.** A 'let Claude compute the Beneish M-score / Altman Z / Piotroski F' feature must be fed the XBRL facts as tool input — the sandbox cannot fetch them. That is actually the desirable design: the numbers arrive from a deterministic source, Claude only does the arithmetic and the interpretation, and the arithmetic is auditable because you get the code back.

- https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool
- https://platform.claude.com/docs/en/about-claude/pricing

### 19. Web fetch cannot construct URLs — a deliberate exfiltration control with a design consequence  
`confidence: high`

Latest version `web_fetch_20260318` (adds `response_inclusion`); `web_fetch_20260309` added `use_cache`; `web_fetch_20260209` added dynamic filtering (Claude writes code to filter fetched content before it enters context, running on the auto-provisioned code-execution tool). Parameters: `max_uses`, `allowed_domains` XOR `blocked_domains`, `citations:{enabled}` (OFF by default, unlike web search), `max_content_tokens`. Anthropic's explicit warning: 'Enabling the web fetch tool in environments where Claude processes untrusted input alongside sensitive data poses data exfiltration risks.' Mitigation baked in: **Claude cannot dynamically construct URLs — it can only fetch URLs already present in the conversation** (user messages, client tool results, prior search/fetch results); otherwise `url_not_in_prior_context`. URLs cap at 250 chars. No JavaScript rendering. Errors return HTTP 200 with an error object, not an exception. Web fetch costs nothing beyond tokens; web search is $10 per 1,000 searches. Rough token sizes: 10 kB page ~2,500 tokens, 100 kB page ~25,000, 500 kB PDF ~125,000.

**Why it matters.** This is the strongest available structural defence against prompt-injection-driven exfiltration of the watchlist: a malicious 8-K cannot make Claude beacon to `evil.com/?tickers=...` because it cannot mint that URL. Combine with `allowed_domains` pinned to sec.gov, the exchanges, and a vetted news list. The design consequence: 'go find the latest 8-K' needs web_search first, or the app supplies candidate URLs.

- https://platform.claude.com/docs/en/agents-and-tools/tool-use/web-fetch-tool
- https://platform.claude.com/docs/en/about-claude/pricing

### 20. Opus 5 supports a mid-conversation `role: "system"` message — the non-spoofable operator channel  
`confidence: high`

On Claude Opus 5, Opus 4.8, Fable 5 and Mythos 5 (NOT Sonnet 5), append `{"role": "system", "content": "..."}` to the `messages` array instead of editing top-level `system`. No beta header. Constraints: must follow a `user` message (or an assistant message ending in server-tool use), must be either the last entry or followed by an assistant turn, cannot be `messages[0]`, text-only. Unsupported models return 400 `role 'system' is not supported on this model`. Anthropic's own guidance: this is 'the prompt-injection-safe replacement for embedding operator instructions as text inside a user turn (the `<\system-reminder>` pattern)' — both cache identically, but `role:"system"` cannot be forged by anything that writes to user-visible input, whereas text inside user/tool content can.

**Why it matters.** Filings and news are attacker-controlled text that will sit in the same context as your instructions. Every mid-conversation rule change — 'the user just switched to FX mode', 'refuse advice', 'the current pack version is X' — belongs in this channel, and it costs nothing in cache invalidation. This is the single most important prompt-injection defence available and it is model-gated, which is another reason the main analysis loop should be Opus 5, not Sonnet 5.

- claude-api skill: shared/prompt-caching.md § Mid-conversation system messages
- claude-api skill: Mid-Conversation System Messages quick reference

### 21. The memory tool is client-side and is the wrong tool for the knowledge base — but the right one for the decision journal  
`confidence: high`

`{"type": "memory_20250818", "name": "memory"}`, no beta header, all Claude 4+ models. Commands: `view` (with optional `view_range`), `create`, `str_replace`, `insert`, `delete`, `rename`, all rooted at a `/memories` prefix your handler maps to real storage. The API auto-injects a system instruction telling Claude to view the memory directory before doing anything and to assume interruption. Anthropic ships `BetaLocalFilesystemMemoryTool` (Python, TypeScript), `BetaAbstractMemoryTool` (Python, C#), `betaMemoryTool` (TS), `BetaMemoryToolHandler` (Java). Explicit security warning: a path like `/memories/../../secrets.env` reaches outside — validate every path, resolve to canonical form, reject `../`, `..\`, and URL-encoded `%2e%2e%2f`. Pairs with context editing (`clear_tool_uses_20250919`, `clear_thinking_20251015`) and server-side compaction (beta `compact-2026-01-12`, default trigger ~150K tokens).

**Why it matters.** Knowledge Packs are curated, signed, versioned artefacts — the memory tool's freeform mutation model is wrong for them. But the decision journal that 'argues back' is exactly a memory-tool use case: it accretes across sessions, must survive context resets, and is genuinely per-user. Keep them separate: packs are read-only inputs; memory is the user's own record.

- https://platform.claude.com/docs/en/agents-and-tools/tool-use/memory-tool

### 22. Realistic monthly AI bill for a heavy solo trader: ~$250–450, with a clear path to $150  
`confidence: medium`

Modelled on verified 2026-08-24 rates. (a) Nightly knowledge-pack maintenance, one Opus 5 agent batch: ~100K uncached input ($0.50) + ~300K cache reads ($0.15) + ~60K output ($1.50) + ~20 web searches ($0.20) = ~$2.35/night = ~$70/mo; on the Batch API the token half of that drops ~50% to ~$38/mo. (b) Morning 'what changed and why' brief, 1/day, ~150K mostly-cached input + 8K output = ~$0.32/day = ~$10/mo. (c) Hover plain-English translate, 100/day on Haiku 4.5 at 3K in / 300 out = ~$0.45/day = ~$14/mo. (d) 10-K vs prior 10-K redline: ~240K input + 20K output on Opus 5 = ~$1.70 per filing; 30 filings/mo = $51, or ~$25 on Batch overnight. (e) Interactive Q&A / thesis stress-test, 40/day on Opus 5 with a cached 40K knowledge prefix and 3K output = ~$0.10 each = ~$125/mo. (f) Embeddings + reranking: under $5/mo after the free allowances. Total ≈ $275–450/mo Opus-heavy; ≈ $150–200/mo if (b)(c)(d) move to Sonnet 5/Haiku 4.5 and everything overnight goes on Batch.

**Why it matters.** This is affordable for the stated user, but it exceeds the Start-tier $500/month cap under any burst (a heavy earnings week doubles (d) and (e)). Budget for Build tier. The dominant line item is interactive Q&A, and its cost is dominated by OUTPUT tokens at $25/MTok — so terseness instructions and `effort` tuning are worth more than any input-side optimisation.

- https://platform.claude.com/docs/en/about-claude/pricing
- https://platform.claude.com/docs/en/api/rate-limits

### 23. RAGAS gives you the evaluation vocabulary, but not the metrics that matter most here  
`confidence: high`

RAGAS ships: Faithfulness, Response Relevancy, Context Precision, Context Recall, Context Entities Recall, Noise Sensitivity, multimodal variants; plus Nvidia metrics (Answer Accuracy, Context Relevance, Response Groundedness), agent metrics (Topic Adherence, Tool Call Accuracy/F1, Agent Goal Accuracy), NL-comparison metrics (Factual Correctness, Semantic Similarity, BLEU/ROUGE/CHRF, String Presence, Exact Match), SQL metrics, and general-purpose Aspect Critic / Rubrics scoring. Most are LLM-judged (one or more LLM calls each).

**Why it matters.** Faithfulness and Context Recall are necessary but not sufficient for a trading terminal. The metric that actually matters is **numeric exactness against XBRL ground truth** — did the model say $94.9bn when companyfacts says $94.9bn — plus **citation span validity** (does the cited text actually contain the number) and **refusal rate on an unanswerable set**. Those you build yourself; RAGAS covers the retrieval-quality half.

- https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/

### 24. Model deprecation is the under-appreciated risk to a Claude-authored knowledge base  
`confidence: medium`

Anthropic maintains a model-deprecation page; Opus 4.1, Opus 4, Sonnet 4 and Haiku 3.5 are already retired on the first-party API (surviving only on Bedrock/Google Cloud). Prompt caches are model-scoped, so a model switch invalidates the entire cache. The 4.7+ tokenizer change means token counts shift ~30% on migration. Thinking configuration (`budget_tokens` -> `effort`), prefill support, and `role:"system"` availability all differ across model generations.

**Why it matters.** A Knowledge Pack is not model-neutral: its prose density, its claim granularity, and the golden-set answers it was validated against were all produced under one model's behaviour. Pin the authoring model ID and effort level in every pack manifest, keep the golden set as a regression suite, and re-run it on every model migration before promoting packs. Naive plans version the content and forget to version the author.

- https://platform.claude.com/docs/en/about-claude/model-deprecations
- https://platform.claude.com/docs/en/about-claude/pricing

### 25. Zero Data Retention is available but has feature and product carve-outs  
`confidence: medium`

Citations, search results, the memory tool, code execution and web fetch are all documented as ZDR-eligible (each links to the API-and-data-retention page for specifics), with the exception that Covered Models are excluded. Claude Fable 5 explicitly requires 30-day data retention and is NOT available under ZDR — requests from an org whose retention configuration doesn't meet the requirement return 400. Separately, organisations with Zero Data Retention enabled **cannot use `/web-setup` or other cloud session features**, which includes Claude Code on the web and therefore Routines.

**Why it matters.** Direct conflict: the privacy posture the user wants (ZDR, because the watchlist is the alpha) is mutually exclusive with the scheduled-authoring mechanism that is most convenient (Routines). Resolution: run the pack pipeline on a SEPARATE, non-ZDR account/org that never sees the watchlist — it only researches public companies and public macro — while the terminal's interactive path runs against a ZDR org. This separation is a feature, not a workaround: the pack builder should never know what the user holds.

- https://platform.claude.com/docs/en/build-with-claude/citations
- https://code.claude.com/docs/en/claude-code-on-the-web
- claude-api skill: Claude Fable 5 section

### 26. Managed Agents web tools ignore environment network policy — a containment gotcha  
`confidence: high`

On Claude Managed Agents, `web_search` and `web_fetch` run on Anthropic's servers in both cloud and self-hosted environments, so the environment's `networking` setting does not restrict them, and Console org-level web settings apply to the Messages API only. Restriction must be done per-tool via `allowed_domains` XOR `blocked_domains` on the toolset `configs` entry: 1–64 plain hostnames per list (subdomains covered); IPs, bare TLDs, single-label and localhost-style names are rejected on both tools; a path suffix is allowed only on `web_search`.

**Why it matters.** If you move the pack pipeline to Managed Agents and assume 'no network egress' contains the agent, you are wrong — the web tools bypass it. The domain allowlist is the actual control, and it must be set on the tool, not the environment.

- claude-api skill: shared/managed-agents-tools.md; Common Pitfalls

## Recommended decisions

### Hosted Claude API vs local model vs hybrid

**Recommendation.** Hybrid, with a hard split by task class. Claude Opus 5 for judgment (filing diff materiality, thesis red-team, morning brief, pack authoring). Claude Sonnet 5 for volume analysis (earnings-call tone, comp rationale, news triage). Claude Haiku 4.5 for cheap classification and the assistant. Foundry Local (qwen2.5-7b class) for hover-translate, query rewriting, NER over news, PII/position scrubbing, and offline degraded mode. Never route a numeric claim through a local model.

**Rationale.** The quality ceiling of a 7–14B local model is nowhere near what materiality ranking on a 10-K redline requires, and the failure mode (a plausible-sounding wrong number) is exactly the one this product cannot tolerate. Conversely, at 100+ hover-translates/day the cloud round-trip is both a latency and a privacy tax for zero quality benefit. The split is by task class, not by 'try local first'.

**Rejected.** Local-only: fails on quality and on the FX/macro reasoning that has no structured ground truth. Cloud-only: fails on offline, on the $500 spend-cap 429, and on the privacy of high-frequency interactions that reveal what the user is staring at.

**Cost.** ~$275–450/mo cloud at heavy use; local tier is $0 marginal after a ~2.5–5 GB model download

### Which local runtime on Windows

**Recommendation.** Foundry Local (`winget install Microsoft.FoundryLocal`, `Microsoft.AI.Foundry.Local.WinML` 1.0.0) as primary, with a bundled ONNX Runtime GenAI fallback for machines below Windows 11 24H2. Explicitly DO NOT build on Phi Silica.

**Rationale.** Microsoft's own docs state Phi Silica is being replaced by Aion Instruct with retail rollout and Phi Silica REMOVAL in November 2026 — three months from today. Phi Silica also requires a Limited Access Feature unlock token, is unavailable in China, and its GPU path needs Insider Experimental builds, Developer Mode and manufacturer-direct drivers. Foundry Local needs none of that, uses model aliases to auto-select NPU/GPU/CPU variants, and works on any Win 11 24H2 machine with a DX12 GPU.

**Rejected.** Phi Silica (being deleted, LAF-gated). Ollama (fine, but ships a second model store and service the user must manage; Foundry Local's models are Microsoft-hosted and shared across apps). Raw llama.cpp (more control, but you own quantisation, hardware detection and updates).

**Cost.** $0 licence; 2.5–5 GB disk per model; installer must gate on Win 11 build 26100+ and a real (non-VM) DX12 GPU

### How Claude authors and publishes the knowledge base

**Recommendation.** A Claude Code Routine on the OWNER's claude.ai account, scheduled daily, working in a private GitHub repo of Markdown+JSON packs; a GitHub Action validates schema, runs the golden-set regression, signs with Ed25519, and publishes a signed index + pack tarballs to a CDN. The desktop app is a pure consumer: pull, verify, stage, atomic-swap, hot-load.

**Rationale.** Routines give exactly the requested semantics ('Claude personally updates it') with a git-native audit trail, PR-shaped review, and free rollback. Anthropic's own trust model helps: the routine's stored prompt is treated as an assigned task while everything fetched during the run stays untrusted. The repo/CDN split keeps signing keys out of the agent's reach — the agent commits, the CI signs.

**Rejected.** Managed Agents scheduled deployments: viable and API-key-driven, but loses the 50% Batch discount, adds $0.08/session-hour, and has cron jitter up to 9 minutes. Doing it inside the desktop app: impossible — Routines need a claude.ai login and Anthropic forbids third-party products offering claude.ai login. A plain GitHub Action calling the Messages API: works, but you rebuild the agent harness by hand.

**Cost.** Draws down the owner's Claude Max subscription (~$100–200/mo) rather than API spend; CDN and repo effectively free at this size

### Reconciling Zero Data Retention with the Routine-based pipeline

**Recommendation.** Two separate Anthropic identities. Identity A (ZDR-enabled org, API key) serves the terminal's interactive path and never leaves the user's control. Identity B (non-ZDR, claude.ai subscription) runs the pack Routine, researches only public companies and public macro, and never sees the watchlist, positions or P&L.

**Rationale.** ZDR orgs cannot use Claude Code on the web, and therefore cannot use Routines. Rather than fight that, exploit it: the pack builder has no business knowing what the user holds. The separation is a genuine security property, not a compromise.

**Rejected.** Single non-ZDR account for everything (leaks the watchlist through interactive queries). Abandoning ZDR (unnecessary — the interactive path can have it). Abandoning Routines for a hand-rolled cron (loses the harness and the audit trail).

**Cost.** No incremental cost; one extra account to administer

### Knowledge Pack schema and versioning

**Recommendation.** Dual versioning: `schema_version` as semver (the app declares a supported range, e.g. `>=2.0.0 <3.0.0`) and `content_version` as CalVer + build (`2026.08.24-1`). The atomic unit is the CLAIM, not the document: every claim carries `{id, text, type: fact|interpretation|rule_of_thumb|historical_analogue, confidence, as_of, decay, sources:[{url,title,retrieved_at,quote,locator}], contradicts:[], review_status}`. The manifest pins the authoring model ID, effort level, routine ID and run ID. Hard size budget: 8–40 KB body per pack, 128 KB cap.

**Rationale.** Stable claim IDs are what make the diff view, rollback, per-claim provenance, decay-driven refresh scheduling and the 'no citation, no claim' rule all mechanically possible. Splitting schema (compatibility) from content (freshness) means a pack refresh never risks breaking the app, and the app can refuse a pack whose schema it does not understand rather than half-rendering it. Pinning the authoring model is what protects you at the next model migration.

**Rejected.** Free-form Markdown packs (no diffable unit, no per-claim provenance, no rollback granularity). A single semver for everything (conflates 'the app can read this' with 'this is fresh'). A database instead of files (loses git as the audit and review substrate).

**Cost.** Design effort only; ~800 packs at ~25 KB average = ~20 MB, ~5 MB compressed

### Retrieval architecture over filings and news

**Recommendation.** Structure-aware chunking by 10-K Item, then heading path, then 600–900 token windows with ~15% overlap, carrying `{item_id, heading_path, accession, filed_date, form}` as metadata. Hybrid retrieval: SQLite FTS5/Tantivy BM25 + dense embeddings via voyage-4 (or voyage-finance-2 for filing text), fused with reciprocal rank fusion (k=60), then rerank-2.5 over the top 50 down to the top 8. Freshness multiplier `exp(-age_days/half_life)` with half-life 90d for news, 400d for filings, none for primers. Return results as `search_result` blocks with `source` set to a resolvable deep link.

**Rationale.** Item-aware chunking is what makes citations useful ('Item 7 > Liquidity and Capital Resources' beats 'page 47'). Hybrid beats either alone on financial text because exact tag/number matching is a BM25 strength and paraphrase is a dense strength. Reranking is essentially free (rerank-2.5 at $0.05/MTok with 200M free tokens) and is the highest-leverage single quality improvement. `search_result` blocks give first-class citations with zero custom parsing.

**Rejected.** Dense-only (misses exact us-gaap tags and specific numbers). Naive fixed-size chunking (destroys the Item structure that makes citations navigable). Local BGE/E5 embeddings (defensible for privacy, but filings are public — spend the privacy budget where it matters, and voyage-4's first 200M tokens are free anyway).

### Numbers: XBRL facts vs LLM extraction

**Recommendation.** Absolute rule — any concept that is XBRL-tagged renders from `data.sec.gov/api/xbrl/companyfacts` and is NEVER restated by a model. The LLM may annotate, contextualise, and compute derived ratios in the code-execution sandbox from facts passed in as tool input, but the primitive number always comes from the tagged source, displayed with its us-gaap tag, unit, period, form and accession number.

**Rationale.** This eliminates an entire hallucination class by construction and is what makes the FACT/INFERENCE split enforceable rather than a UI convention. companyfacts updates within ~1 minute of filing, needs no API key, and covers every tagged concept in one call. Cross-sectional peer pulls come free from the frames API.

**Rejected.** LLM extraction from filing prose as the primary path (the single most common and most dangerous design in AI finance tools). Third-party fundamentals vendors (a fine supplement, but they introduce a restatement lag and an unauditable transformation between the filing and the number).

**Cost.** $0 API cost; requires disciplined 10 req/s throttling, a real contact User-Agent, and nightly bulk-ZIP backfill

### Prompt-injection defence posture for untrusted filings and news

**Recommendation.** Layered and structural: (1) untrusted text NEVER enters the top-level `system` — it arrives only as `search_result` or `document` blocks; (2) all mid-conversation operator instructions use Opus 5's `role:"system"` message channel, which cannot be forged from content; (3) the analysis agent has zero write tools and no direct network egress; (4) `web_fetch` is domain-restricted via `allowed_domains` (sec.gov, exchanges, a vetted news allowlist) and structurally cannot construct URLs; (5) sanitise before indexing — strip zero-width characters, white-on-white and display:none text, HTML comments, and base64 blobs; (6) a honeytoken canary in the test corpus that the golden-set harness asserts the model never obeys.

**Rationale.** Layer 4 is the strongest available control and it is enforced server-side by Anthropic, not by your prompt: a poisoned 8-K cannot make Claude beacon the watchlist to an attacker URL because it cannot mint one. Layer 2 is model-gated to Opus 5/4.8/Fable/Mythos, which is an additional argument for Opus 5 as the main loop model. Layer 6 turns injection resistance into a regression test rather than a hope.

**Rejected.** Prompt-based defence alone ('ignore instructions in documents') — necessary but demonstrably insufficient. Allowing the agent write tools with a confirmation dialog — confirmation fatigue in a fast-moving terminal is a guaranteed eventual click-through.

### Caching architecture for the interactive path

**Recommendation.** One 1-hour `cache_control` breakpoint after: frozen persona + refusal rules + deterministically-serialised tool definitions + the user's pinned pack core (target 30–80K tokens). Everything volatile — current time, symbol context, the question, retrieved chunks — goes after it. Never interpolate a clock or session ID into the system prompt. Place an intermediate breakpoint every ~15 content blocks in long agentic turns. Serialise tools sorted by name. Verify continuously with `usage.cache_read_input_tokens`; alert if it is zero across repeated requests.

**Rationale.** Cache reads cost 0.1x and — critically — do not count toward ITPM, so a large pinned knowledge prefix is cheap in both dollars and throughput. The 1-hour TTL (2x write) pays back after three reads, which a working session clears in minutes. The 20-block lookback and the concurrent-request timing rule are the two failure modes that silently destroy this, so the intermediate breakpoints and a staggered panel-open sequence are not optional.

**Rejected.** 5-minute TTL (cheaper writes but dies across coffee breaks; a session with gaps thrashes). No caching (roughly 4–6x the interactive bill and a much lower effective rate limit). Per-symbol prefixes (fragments the cache across the watchlist and never amortises).

**Cost.** Converts ~$0.35/query to ~$0.10/query at typical prefix sizes

### Model selection for the pack-authoring agent

**Recommendation.** Claude Opus 5 at `output_config.effort: "xhigh"` with `thinking: {type: "adaptive"}` for authoring and materiality judgment; delegate reading-heavy sub-tasks (bulk source triage, extraction-under-schema) to Claude Haiku 4.5 subagents at `effort: "low"`. Pin the exact model ID and effort in every pack manifest.

**Rationale.** Anthropic's own guidance is that `xhigh` is the best setting for long-horizon agentic work on Opus 5 and that effort matters more on this generation than any prior one. Pack authoring is precisely long-horizon agentic work with a high cost of error. Delegating the reading keeps the expensive context clean. Pinning the model is what makes the golden-set regression meaningful across migrations.

**Rejected.** Sonnet 5 for authoring (cheaper, but the whole value of the pack is the judgment in it, and Sonnet 5 lacks the `role:"system"` channel). Fable 5 (higher ceiling at $10/$50, but not ZDR-eligible and unnecessary for this task). Default `effort: high` (leaves quality on the table for a job that runs once a night).

**Cost.** ~$2.35/night at standard rates, ~$1.30/night on the Batch API

### Where the evaluation gate sits

**Recommendation.** In CI, between the agent's commit and the signing step. A pack build that fails the golden set — numeric exactness against XBRL, citation-span validity, refusal rate on the unanswerable set, or the injection canary — cannot be signed and therefore cannot reach the desktop app. Every model migration re-runs the full suite before any pack is re-promoted.

**Rationale.** Signing is the only chokepoint that the app trusts, so it is the only place a quality gate is unbypassable. Putting evaluation after publication means bad knowledge reaches the user and is remediated by rollback — acceptable for a bug, unacceptable for the thing shaping their analytical priors.

**Rejected.** Post-publication monitoring only (too late). Human review of every pack (does not scale past ~50 packs and defeats the point). Model-as-judge alone without XBRL ground truth (measures fluency, not correctness).

**Cost.** ~$3–8 per full golden-set run on Sonnet 5 as judge, plus deterministic checks at $0

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | L | Nightly Knowledge Pack Build ("Claude's night shift") | A Claude Code Routine on the owner's account, scheduled daily at ~03:30 local (outside the 01:00–03:00 DST hazard window), that reads a pack manifest of due-for-refresh packs, researches with web_search + web_fetch + EDGAR, rewrites claims with sources, bumps content_version, signs, and opens a commit on a `claude/kb-YYYY-MM-DD` branch. A GitHub Action verifies schema, runs the golden-set regression, signs with Ed25519 and publishes to CDN. | Claude Code Routines (schedule trigger, min 1h cadence) + web_search/web_fetch + data.sec.gov + private git repo + CDN |
| P0 | M | Knowledge Pack Changelog & Claim-Level Diff | A dedicated 'What your terminal learned' panel. Because every claim has a stable ID, the diff is claim-level, not text-level: Added / Removed / Rewritten (old -> new side by side) / Confidence changed / Sources changed / Expired. Ranked by materiality: claims touching a watchlist entity first, then packs opened in the last 30 days, then the rest. Each entry shows the source that caused the change and a one-line 'why'. | Pack manifests, claim IDs, git history of the pack repo |
| P0 | M | Pack Approval Gate & Rollback | Three modes per pack class: Auto (goes live, changelog badge), Review (staged; the terminal keeps running the last-approved version until the user accepts the diff), Locked (offline / manual import only). Default: Review for any pack whose diff touches a watchlist entity, Auto otherwise. Retain the last 3 generations on disk; one-click rollback with a reason field that feeds back into the next build prompt. | Local pack store (%LOCALAPPDATA%), signed index.json |
| P0 | M | Signed Pack Distribution & Hot-Load | App polls a small signed `index.json` (ETag/If-None-Match), downloads only changed packs, verifies an Ed25519 detached signature over an RFC 8785 canonical serialisation of the manifest (which itself contains a SHA-256 digest per file), stages to `kb/staging`, atomically swaps to `kb/active`, hot-reloads without restart. Public key pinned in the binary plus a rotation key. | CDN (R2/CloudFront) + Ed25519 |
| P1 | M | Offline Genesis Bundle | Ship a complete pack set at install: ~800 packs, 8–40 KB body each (hard cap 128 KB), ~60–150 MB uncompressed, ~15–25 MB zstd. The terminal is fully useful with zero network and zero API key — packs, glossary, checklists and playbooks all work; only live data and generative features degrade. | Installer payload |
| P0 | M | Evidence-Locked Answer Panel ("no citation, no claim") | Every AI answer renders as a stream of text blocks; blocks carrying a `citations[]` entry get an inline superscript that opens the exact cited span in the filing/news viewer. A post-processor scans for sentences containing a number, date, percentage or proper noun with no citation and either strikes them or marks them 'unsourced — do not rely'. Hard rule enforced in code, not prompt. | Messages API citations (char_location / page_location / content_block_location) + search_result blocks |
| P0 | M | FACT vs INFERENCE Surface Split | Two visually distinct chrome systems. FACT panels render only from deterministic pipelines (XBRL companyfacts, exchange data, Form 4 filings) — no model in the path. INFERENCE panels carry a persistent badge with model ID, effort level, pack versions consulted and generation timestamp. They are never interleaved in the same grid, and a FACT panel can never be populated by an LLM restating a number. | data.sec.gov companyfacts (facts) vs Claude API (inference) |
| P0 | L | Filing Diff & Materiality Redline | 10-K vs prior 10-K (and 10-Q vs 10-Q, proxy vs proxy) structure-aware diff by Item, with each change scored for materiality: new risk factor > removed risk factor > changed accounting policy > changed segment definition > boilerplate. Language-change detection on hedging words ('substantially all' -> 'a majority of'). Runs overnight on the Batch API at 50% off. | EDGAR filing HTML/iXBRL + Claude Opus 5 (Batch API) |
| P0 | M | Morning Brief: "What changed overnight and why" | One Opus 5 call at a user-set time, with a cached knowledge prefix (persona + tool defs + pinned packs, 1h TTL) and a volatile tail (overnight moves, filings hit, news, calendar). Output is a ranked list of 5–12 items, each with a claim, an evidence link, a 'so what for your book' line, and an explicit 'nothing happened here' section for watchlist names that did NOT move. | Pack store + market data + EDGAR deltas + Claude Opus 5 |
| P0 | L | Natural-Language Screener -> Deterministic Query Compiler | NL in ('small caps where insiders bought over $1m in the last 30 days and short interest over 15%'), a validated query object out via strict tool use with `additionalProperties:false`. The compiled query is SHOWN to the user in structured form before it runs, is editable, and is saveable as a named screen. The model never touches the result set — it only writes the query. Note the schema cannot use `pattern` or numeric bounds, so range validation happens in your own validator. | Claude structured outputs / strict tool use + local screener engine over EDGAR + market data |
| P0 | M | Thesis Stress-Test / Red-Team-My-Idea | User writes a thesis; Claude produces (1) the strongest steel-manned bear case with citations, (2) the three facts that would most cheaply falsify the thesis, (3) the historical analogue where this exact reasoning failed, drawn from the analogue library pack, (4) an explicit 'what the consensus already knows' section. Never a verdict, never a recommendation. | Company dossier packs + historical analogue pack + RAG over filings + Claude Opus 5 at effort xhigh |
| P1 | M | Accounting Red-Flag Scorecard (deterministic maths, AI annotation) | Beneish M-score, Altman Z, Piotroski F, Sloan accruals, Montier C-score computed in the code-execution sandbox from XBRL facts supplied as tool input (the sandbox has no internet, so it must be fed). Every input line item shows its us-gaap tag and filing provenance. Claude writes only the interpretation layer: which component is driving the score, and whether the drivers are benign for this business model. | data.sec.gov companyfacts + code_execution_20260521 + Claude |
| P1 | M | Earnings-Call Tone & Tell Analysis | Transcript ingested as custom-content citation documents (one block per speaker turn, so citations resolve to a specific speaker at a specific moment). Analysis of: question dodging (which analyst question got answered least), hedging-word delta vs prior calls, prepared-remarks vs Q&A language divergence, first-mention-of and last-mention-of tracking for key metrics. Runs on Sonnet 5. | Transcript source + Claude Sonnet 5 with custom-content citations |
| P1 | XL | Entity & Relationship Graph (who sits on whose board, who owns whom) | Built from DEF 14A proxies, Form 3/4/5, 13D/G and 13F. Claude's role is extraction-under-schema from proxy prose (strict tool use), not inference. Rendered as an interactive graph with each edge carrying the filing that established it and an as-of date. Query it in natural language ('who else is on the comp committee of a company my CEO chairs'). | EDGAR DEF 14A, Forms 3/4/5, SC 13D/G, 13F + Claude structured extraction |
| P1 | S | Plain-English Hover Translate | Hover any metric, filing phrase, or panel and get a one-sentence plain-English translation plus 'why it matters for THIS company'. Runs on the local model (Foundry Local, qwen2.5-7b or similar) for latency and zero cost, falling back to Haiku 4.5 when the local model is unavailable or the term is unknown. Answers come from the glossary pack where one exists — the model only phrases, it does not invent. | Glossary pack + Foundry Local / Haiku 4.5 |
| P1 | M | Pre-Trade Checklist Agent | Before the user acts on an idea (the terminal executes nothing, so this is a discipline tool), Claude walks a checklist derived from the relevant packs: what is the variant perception, who is on the other side and why, what does the incentive structure predict, what does the last analogue say, what is the falsifier, is there an event in the next 10 days that makes this a coin flip. It refuses to give a verdict and says so explicitly. | Packs + decision journal + event calendar |
| P1 | M | Decision Journal That Argues Back | User logs a thesis and the reasoning. Claude records it via the memory tool (`memory_20250818`, client-side handler with strict path validation) and, at set intervals or when a falsifier trips, returns with 'you said X would happen because Y; Y did not happen; here is what actually drove the move.' Tracks the user's own base rates by thesis type. | Memory tool with local encrypted store + market data |
| P2 | M | Comparable-Company Auto-Selection | Proposes a comp set with a written rationale per name and an explicit 'rejected comps and why' list. Uses the XBRL frames API for cross-sectional metric pulls rather than the model guessing peers, then Claude argues the business-model similarity case (revenue model, unit economics, capital intensity, customer concentration) drawn from the dossier packs. | data.sec.gov frames API + SIC/GICS + company dossier packs + Claude |
| P0 | M | FX Pair Dossier Panel | Per-pair pack rendered as a live panel: primary drivers with current weightings, rolling correlations to rates/commodities/equities, session-by-session behaviour (Tokyo/London/NY), typical daily range vs current realised, central bank reaction function with the last N decisions and the language that preceded each turn, and the event calendar with historical average impact. | FX pair dossier packs + central bank statements + market data |
| P1 | M | Event Playbooks (CPI / NFP / FOMC / earnings / OPEC) | Pack-driven pre-event panel: what the market is priced for, what the historical distribution of surprises looks like, which assets moved most per unit of surprise historically, the last 8 instances with outcome and reaction, and the specific lines in the release to read first and in what order. | Event playbook packs + historical release data |
| P1 | M | Filing-Reading Guide Overlay | When a filing opens, an overlay ranks what to read and in what order for THIS company type (a bank's 10-K reads nothing like a SaaS company's), with jump links to each Item and a per-section 'what changed vs last year' badge. Derived from the filing-reading-guide pack plus the diff engine. | Filing-reading guide packs + Item-level structural parse + diff engine |
| P2 | S | In-App Assistant Over the Terminal's Own Docs | The terminal's own feature documentation ships as a pack, so the assistant can answer 'how do I build a screen for X' and 'what does this column mean' from the same evidence-cited machinery as everything else. Runs on Haiku 4.5 with a cached prefix. | Terminal documentation pack + Haiku 4.5 |
| P0 | M | Insider-Signal Interpretation Guide | Not raw Form 4 data (that is the market-data domain) but the interpretive layer: 10b5-1 plan vs discretionary, the tell of a plan adopted 30 days before a buy, cluster buys vs a single director, buying into strength vs weakness, and the specific base rates for each pattern. Rendered next to every insider transaction. | Insider-signal interpretation pack + Form 4 feed |
| P0 | L | Golden-Set Regression Harness (ships as a first-class internal tool) | 200+ question set with typed ground truth: 60 numeric lookups verified against XBRL, 40 comparatives, 40 'what changed', 30 red-flag identifications, 30 deliberately unanswerable/adversarial. Metrics: exact numeric match within tolerance, citation-span validity (does the cited text actually contain the number), RAGAS faithfulness and context recall, refusal rate on the unanswerable set, and injection-canary compliance. Runs in CI on every pack build and every model migration; a build that regresses cannot be signed. | data.sec.gov ground truth + RAGAS + custom numeric/citation validators |
| P1 | M | Cost & Token Meter with Per-Feature Budgets | A live panel showing spend by feature, cache hit rate, and remaining headroom against the month's spend cap. Each feature has a token budget checked with `count_tokens` before send; over-budget requests either downgrade model, drop to the local model, or ask. Explicit handling for `enforced_spend_limit_reached` (no retry, degrade, explain). | Messages API usage fields + count_tokens endpoint + rate-limit response headers |

## Risks

- Phi Silica is removed from Windows in November 2026 per Microsoft's own documentation. Any local-AI code path built on it breaks within three months of ship. Aion Instruct is the successor but is still Insider-channel as of August 2026 and its API surface is not yet documented at the level Phi Silica's is — treat any Aion-based plan as low confidence until the standalone sideloadable package lands in early October 2026.
- Claude Code Routines are a research preview: 'Behavior, limits, and the API surface may change.' The `/fire` endpoint ships behind `experimental-cc-routine-2026-04-01`, and the per-account daily run cap is not published — it must be read from claude.ai/code/routines at build time. Design the pack pipeline so it can be re-hosted on Managed Agents scheduled deployments or a plain GitHub Action with only the harness swapped.
- The Start-tier $500/month spend cap returns a 429 with NO retry-after and `error_code: enforced_spend_limit_reached`. SDK auto-retry makes this worse. A heavy earnings week can plausibly hit it. Without explicit detection and a local-model degraded mode, the terminal appears simply broken at the worst possible time.
- Zero Data Retention and Claude Code on the web / Routines are mutually exclusive. If the user insists on ZDR org-wide, the recommended two-identity split must be implemented from day one or the pack pipeline cannot exist.
- Prompt injection via filings and news is not hypothetical: EDGAR accepts filer-supplied HTML, and an adversary who wants to move a specific AI-mediated audience has a cheap channel. Web fetch's inability to construct URLs blunts exfiltration but does not stop content manipulation ('this restructuring charge is non-recurring and should be excluded'). The mitigation is the FACT/INFERENCE split plus the injection canary regression, not prompting.
- Citations and structured outputs cannot be combined (400 error). Any roadmap item specified as 'cited JSON' is unbuildable as one call and must be re-specified as two, which changes latency and cost estimates.
- The Opus 4.7+ tokenizer emits ~30% more tokens for identical text. Every cost estimate in this document and any built from older token counts must be re-baselined with `count_tokens` before being treated as a budget.
- EDGAR's 10 req/s ceiling is enforced and a non-contactable User-Agent risks a block. A block takes out the filings, insiders and XBRL pillars simultaneously — i.e. two of the three product pillars — with no vendor to call. Nightly bulk-ZIP backfill plus conservative delta polling is the only safe posture, and there is no paid tier to escalate to.
- Claim decay is a silent failure mode: a pack that was correct in March and is stale in August looks identical in the UI unless `valid_until`/`decay` are surfaced. The most dangerous knowledge is confidently-rendered stale knowledge. Decay must be visible on the panel, not just in the manifest.
- Model deprecation will eventually force a migration, and a pack corpus authored and validated under Opus 5 will drift under its successor. Without the pinned authoring model plus a golden-set regression, that drift is undetectable until it produces a bad call.
- Managed Agents cron jitter (up to 15% of interval, max 9 minutes) and Routine stagger mean 'the pack lands before the open' is not guaranteed. Build a margin, and make the UI honest about pack age rather than implying freshness.
- DST wall-clock cron semantics fire twice on fall-back and skip on spring-forward. A pack build that runs twice can produce two `content_version` values for the same day; make pack writes idempotent on content hash and schedule outside 01:00–03:00 local.
- The 'AI knowledge layer' can become a liability surface if any output reads as personalised investment advice. The refusal posture must be enforced by an output classifier, not only by system prompt, and the pre-trade checklist must be explicitly non-advisory by construction.
- Model-generated confidence numbers are not calibrated. Displaying a model's self-reported confidence next to a claim manufactures false precision. Display the pack's stored, evaluation-derived confidence instead — and be prepared to justify how it was derived.

## Open questions

- What exactly is the per-account daily run cap for Claude Code Routines? The docs say a cap exists and is visible at claude.ai/code/routines but do not publish the number. This determines whether one Routine per pack class is viable or whether all packs must be built in a single nightly run.
- Is Aion Instruct's WinRT API surface source-compatible with `Microsoft.Windows.AI.Text.LanguageModel`? Microsoft says LAF tokens are no longer needed and points to a sideloadable package in early October 2026, but does not state whether existing Phi Silica call sites compile unchanged. This decides whether any Windows AI APIs work is wasted.
- What are voyage-4 / voyage-finance-2 context lengths and embedding dimensions? The pricing page does not publish them, and both matter for chunk sizing and index storage. Needs a fetch of the model-reference page before finalising the chunking strategy.
- Does Claude Opus 5 support `role: "system"` mid-conversation messages on every platform the app might use, or Claude API only? The skill notes Sonnet 5 is unsupported and that sources conflict; platform availability for Opus 5 specifically should be confirmed against `shared/platform-availability.md` before the injection-defence design depends on it.
- What is the actual latency of Opus 5 at `effort: xhigh` on a 200K-token filing-diff prompt? This determines whether the redline is genuinely an overnight Batch job or can be offered interactively. Needs measurement, not documentation.
- Are transcripts of earnings calls licensable at a solo-user price point, and under what redistribution terms? The tone-analysis feature is high value but the input is not free like EDGAR. This is the one AI feature whose data dependency is commercially uncertain.
- What is the real-world numeric accuracy of Claude on XBRL-grounded questions when the answer requires combining facts across two filings (e.g. a three-year CAGR)? The 'render from XBRL, never restate' rule handles single facts; derived multi-fact figures are the residual hallucination surface and need measurement on the golden set.
- Does the Claude Code Routine environment's Trusted network allowlist include sec.gov and data.sec.gov by default? The docs describe a default allowlist of package registries, cloud APIs and dev domains — if sec.gov is not on it, the environment needs Custom network access configured, which is easy but must be known before the first build.
- How large can the pinned knowledge prefix get before the marginal quality gain goes negative? At 1M context there is no hard ceiling, but attention dilution is real. This wants an ablation on the golden set at 20K / 50K / 100K / 200K prefix sizes.
- What is the right cadence per pack class? Company dossiers presumably follow the filing calendar, FX pair dossiers weekly, macro regime playbooks on central bank meetings, event playbooks before each event. The 1-hour Routine minimum is not binding, but the decay/valid_until values need to be set from actual observed staleness rather than guessed.
