# Security architecture, STRIDE threat model, and legal/regulatory compliance posture for a read-only Windows equities+FX trading terminal with an LLM knowledge layer (research as of 2026-08-24)

> Auto-generated research dossier. Produced by a domain-research agent with live web search on 2026-08-24.
> Confidence labels and sources are the agent's own. Verify anything marked `medium`/`low` before relying on it.

## Executive summary

Three findings dominate. (1) On Windows, secret-at-rest protection is largely theatre against the actual adversary. DPAPI (CryptProtectData) binds a blob to the user, but any process running as that user can call CryptUnprotectData — which is exactly what LummaC2, StealC, Vidar and ACRStealer (the 2026 top families; RedLine declined after Operation Magnus, Oct 2024) do. Google's App-Bound Encryption (Chrome 127, 30 Jul 2024) tried to fix this with an elevation-service identity check and was bypassed within ~45 days (12 Sep 2024), then structurally broken by COM-hijack and "C4 Bomb" padding-oracle attacks. The only Windows primitive that meaningfully raises the bar is CNG with NCRYPT_REQUIRE_VBS_FLAG (VBS/Credential-Guard-class key isolation) or the Microsoft Platform Crypto Provider (TPM 2.0), plus a user-supplied passphrase (Argon2id m=19456,t=2,p=1) so the ciphertext is not silently machine-recoverable. Everything else — SQLCipher, EFS, BitLocker — protects against device theft, not against the infostealer that is the realistic threat. Trading brands are actively impersonated: Bitdefender tracked 75+ malicious "TradingView Premium" Meta ads and 500+ domains from 22 Jul 2025, dropping JSCEAL/WeevilProxy; the user's own download path is an attack surface.

(2) The LLM layer is the app's largest new attack surface. SEC filings, RNS, news, PDFs and RSS are attacker-controlled text (OWASP LLM01, indirect prompt injection). Combined with a WebView2 render surface and markdown image rendering, a poisoned 8-K footnote can exfiltrate the watchlist — alpha-revealing IP — via an image URL. The correct architecture is a hard "AI can read, AI cannot act" boundary, provenance-tagged untrusted content, egress allow-listing, and CSP-locked rendering.

(3) Legally, the binding constraint is not "advice" — it is market data licensing and the single/multi-user cliff. Personal, non-professional, non-redistributive use is broadly available (e.g. Polygon/Massive Individuals ToS, 18 Jul 2025: "personal, non-commercial, and non-business purposes", one App Licence). The moment a second user exists, or the user trades through an entity, the terminal becomes a redistributing vendor facing professional-subscriber fees, vendor agreements and exchange audits. Advice risk is manageable by design (Lowe publisher exclusion; CFTC 4.14(a)(9); FCA generic-advice boundary) provided the AI never personalises to the user's holdings.

## Findings

### 1. DPAPI is not a control against the actual adversary — say so in the architecture doc  
`confidence: high`

CryptProtectData/CryptUnprotectData (DPAPI, user scope) encrypts a blob under a master key derived from the user's credentials. Any code running in that user's context can call CryptUnprotectData and get plaintext — no prompt, no consent. This is the documented mechanism used by StealC (Discord tokens), and by the RedLine/Raccoon/Lumma family for browser credential stores. Machine scope (CRYPTPROTECT_LOCAL_MACHINE) is strictly worse for this app: it makes the blob decryptable by any process on the box. Domain-joined machines have a further hazard: the DC holds a per-domain DPAPI backup RSA key that cannot be rotated with built-in tools; anyone with it can decrypt any domain user's DPAPI data even after a password change. Credential Roaming syncs master keys, certs and private keys between machines, widening blast radius. Setting local-only master key backup on a domain account can permanently brick recovery after an off-box password change.

**Why it matters.** A plan that says 'we store API keys with DPAPI, therefore secure' is wrong on the primary threat (infostealer running as the user). DPAPI buys you: protection against another *user* on the box, and against raw disk/backup theft. Nothing more.

- https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
- https://tierzerosecurity.co.nz/2024/11/26/data-protection-windows-api-revisited.html
- https://hawk-eye.io/2025/08/harvesting-browser-credentials-the-dpapi-exploitation-threat/
- https://learn.microsoft.com/en-us/windows/win32/seccng/cng-dpapi-backup-keys-on-ad-domain-controllers
- https://www.sygnia.co/blog/the-downfall-of-dpapis-top-secret-weapon/

### 2. Chrome's App-Bound Encryption is the cautionary tale for 'app identity' secret binding  
`confidence: high`

Google shipped App-Bound Encryption in Chrome 127 (public rollout 30 Jul 2024): a COM elevation service verifies the caller's app identity before DPAPI-unwrapping the session key. Elastic Security Labs observed working stealer bypasses by 12 Sep 2024 (<45 days). Documented bypass classes: COM hijacking of the elevation service; driving Chrome's own remote-debugging API; in-memory scraping; and CyberArk's 'C4 Bomb' padding-oracle attack against the AppBound key blob that works from a low-privileged context. Kaspersky documented VoidStealer using these in the wild.

**Why it matters.** If Google — with an OS-integrated elevation service — cannot make same-user app-identity binding hold, a solo-built terminal certainly cannot. Design so that compromise of the local machine is assumed to compromise cached secrets, and mitigate by scope-limiting the keys instead (read-only API keys, per-provider, revocable, rate-limited, IP-pinned where the provider supports it).

- https://www.elastic.co/security-labs/katz-and-mouse-game
- https://www.cyberark.com/resources/threat-research-blog/c4-bomb-blowing-up-chromes-appbound-cookie-encryption
- https://www.kaspersky.com/blog/chrome-application-bound-encryption-bypass-voidstealer/55735/
- https://github.com/xaitax/Chrome-App-Bound-Encryption-Decryption/blob/main/docs/RESEARCH.md

### 3. VBS-backed CNG keys and TPM Platform Crypto Provider are the only real Windows uplift  
`confidence: high`

NCryptCreatePersistedKey accepts NCRYPT_REQUIRE_VBS_FLAG (fail if VBS unavailable) and NCRYPT_PREFER_VBS_FLAG. VBS-protected keys live in the VTL1 secure kernel: 'keys protected in this way cannot be dumped from process memory or exported in plain text' and are TPM-bound to the device at rest. Requirements: 64-bit, Hyper-V/Windows hypervisor, IOMMU, TPM 2.0 (or vTPM in VMs); Windows 11 / Server 2025 class. Alternative: Microsoft Platform Crypto Provider (MS_PLATFORM_CRYPTO_PROVIDER) generates the key inside TPM 2.0 under the Storage Root Key; private bits never leave the chip. Note .NET has no first-class managed API for the VBS flags (dotnet/runtime issue #102492 is an open API proposal) — expect P/Invoke to ncrypt.dll.

**Why it matters.** This converts 'malware copies your key file' into 'malware must stay resident and ask the TPM/VTL1 to sign/decrypt one item at a time' — detectable, rate-limitable, and non-portable off the box. It is the single highest-leverage security investment in this app.

- https://learn.microsoft.com/en-us/windows/win32/api/ncrypt/nf-ncrypt-ncryptcreatepersistedkey
- https://techcommunity.microsoft.com/blog/windows-itpro-blog/advancing-key-protection-in-windows-using-vbs/4050988
- https://learn.microsoft.com/en-us/windows/win32/seccertenroll/cng-key-storage-providers
- https://github.com/dotnet/runtime/issues/102492

### 4. Windows Credential Manager has a hard 2,560-byte blob limit and weak isolation for full-trust apps  
`confidence: medium`

CredWrite/CredRead: CredentialBlob must be <= CRED_MAX_CREDENTIAL_BLOB_SIZE = 5*512 = 2,560 bytes; oversize writes fail with opaque errors ('The stub received bad data'). Credentials support attributes for up to ~64 KiB of side data. Credential Manager entries are DPAPI-protected under the hood, so the same-user-malware caveat applies. Windows Hello via KeyCredentialManager: Microsoft Q&A guidance indicates the KeyCredential is only cryptographically siloed when the app has package identity AND executes from a true AppContainer process — a full-trust MSIX or plain Win32 app does not get cross-process credential isolation.

**Why it matters.** Two concrete design consequences: (a) don't try to stuff a JSON credential bundle into Credential Manager; store one wrapping key there and keep the bundle in your own encrypted store; (b) 'unlock with Windows Hello' is a UX/consent factor and a phishing-resistance factor, not an isolation boundary, unless you actually ship an AppContainer component.

- https://learn.microsoft.com/en-us/windows/win32/api/wincred/ns-wincred-credentiala
- https://github.com/danieljoos/wincred
- https://learn.microsoft.com/en-us/answers/questions/5912130/what-is-the-security-boundary-of-windows-hello-key
- https://learn.microsoft.com/en-us/windows/msix/msix-container

### 5. Key derivation and DB encryption: exact parameters, and what is theatre  
`confidence: high`

OWASP Password Storage Cheat Sheet (current): Argon2id minimum m=19456 (19 MiB), t=2, p=1; equivalent alternatives m=47104/t=1/p=1, m=12288/t=3/p=1, m=9216/t=4/p=1, m=7168/t=5/p=1. scrypt minimum N=2^17 (128 MiB), r=8, p=1. bcrypt work factor >= 10 (72-byte input cap). PBKDF2 (FIPS path): HMAC-SHA256 600,000 iterations; HMAC-SHA512 220,000; HMAC-SHA1 1,400,000 (legacy). DB-level options: SQLCipher Community Edition is BSD-3-Clause (free, commercial use allowed, attribution required); SQLite Encryption Extension (SEE) is a US$2,000 one-time perpetual source licence, statically linked, no support included. EFS and BitLocker protect only against offline/device-theft and are transparent to a logged-in user's processes — they add nothing against an infostealer.

**Why it matters.** Whole-DB encryption with a key stored next to it (the common pattern) is theatre. Real security = user passphrase -> Argon2id -> unwraps a TPM/VBS-wrapped DEK -> decrypts secrets table only; bulk cached market data can stay in a plain SQLite/DuckDB file for performance because its confidentiality value is low and its licence value is contractual, not secret.

- https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
- https://www.zetetic.net/sqlcipher/license/
- https://sqlite.org/purchase/see

### 6. SecureString is officially discouraged; plan for realistic memory hygiene instead  
`confidence: high`

Microsoft: 'we recommend you don't use the SecureString class for new development on .NET (Core)'. Reasons: no OS secure-string primitive, so data is repeatedly protected/unprotected and exists in cleartext in process memory; the initialisation buffer is cleartext anyway. Practical substitutes: byte[]/Span<byte> with CryptographicOperations.ZeroMemory on dispose, pinned/stack allocation to avoid GC copies, ProtectedMemory (Windows-only), and — better — never materialising the secret at all by keeping the key in CNG/TPM and calling NCryptDecrypt.

**Why it matters.** A plan that promises 'keys held in SecureString' is signalling security it does not have. The honest posture is: minimise plaintext lifetime, zero buffers, and push the actual key material into a hardware/VTL1 boundary so process memory never holds it.

- https://learn.microsoft.com/en-us/dotnet/fundamentals/runtime-libraries/system-security-securestring
- https://learn.microsoft.com/en-us/dotnet/api/system.security.securestring?view=net-10.0

### 7. Trading-brand malvertising is a first-class delivery vector against this exact user  
`confidence: high`

Bitdefender tracked a campaign impersonating 'TradingView Premium' with 75+ malicious Facebook/Meta ads from 22 Jul 2025, tens of thousands of EU impressions, 500+ domains/subdomains, thousands of pages publishing hundreds of ads daily; it expanded to Google Ads and YouTube (a documented in-video YouTube ad on 26 Jul 2026) and to Android (Brokewell) and macOS. Payload JSCEAL/WeevilProxy intercepts network traffic, logs keystrokes, screenshots, steals cookies/passwords/wallets. Brands impersonated include Binance, Bitget, MetaTrader, OKX. Separately, 2026's most active commodity stealers are LummaC2, ACRStealer, StealC and Vidar; RedLine declined after Operation Magnus (Oct 2024) but its logs still circulate.

**Why it matters.** The threat model must include 'user installs a trojanised copy of *your* app, or a trojanised competitor, from a paid ad'. Mitigations: publish only from one signed channel, sign every binary and the update manifest, publish SHA-256 hashes, make the in-app updater the only supported path, and consider a first-run 'verify your installer' check.

- https://www.bitdefender.com/en-us/blog/labs/the-scam-that-wont-quit-malicious-tradingview-premium-ads-jump-from-meta-to-google-and-youtube
- https://safedep.io/youtube-ad-fake-tradingview-macos-stealer/
- https://whiteintel.io/blog/infostealer-monitoring

### 8. Supply chain: the npm blast radius argument is now quantitative  
`confidence: high`

Shai-Hulud (from 16 Sep 2025) was a self-propagating npm worm that harvested CI/CD and cloud-metadata secrets and republished itself into ~40 packages including CrowdStrike-published ones, chained from the 27 Aug 2025 Nx compromise. Shai-Hulud 2.0 (reported early Nov 2025, ongoing into 2026 per Unit 42 and CSA Singapore advisory AD-2026-009 covering Keyv and the AntV ecosystem) affected tens of thousands of GitHub repositories — roughly 25,000 malicious repos across ~350 users; 2,200+ repos created with exfiltrated tokens. On the .NET side, the concrete controls are: NuGet Package Source Mapping (packageSourceMapping in nuget.config) to defeat dependency confusion, RestorePackagesWithLockFile + packages.lock.json with --locked-mode restores, NuGet Audit / `dotnet list package --vulnerable --include-transitive`, and OSV/GitHub Advisory scanning.

**Why it matters.** This is the strongest available argument for a lean .NET/WinUI/WPF tree over an Electron/npm tree for a security-sensitive financial app: the .NET dependency graph is an order of magnitude smaller and its registry has not suffered a self-propagating worm at this scale. If Electron/React is chosen for the UI, it must be a build-time-only dependency with a vendored, lockfile-pinned, hash-verified tree, never a runtime npm install.

- https://unit42.paloaltonetworks.com/npm-supply-chain-attack/
- https://www.csa.gov.sg/alerts-and-advisories/advisories/ad-2026-009/
- https://www.stepsecurity.io/blog/shai-hulud-here-we-go-again-mass-npm-supply-chain-attack-hits-the-antv-ecosystem
- https://learn.microsoft.com/en-us/nuget/concepts/auditing-packages
- https://www.mykolaaleksandrov.dev/posts/2025/11/package-source-mapping/

### 9. Code signing and SBOM: cheap, and now table stakes  
`confidence: high`

Azure Trusted Signing (rebranded Azure Artifact Signing) is open to individual developers: Basic US$9.99/month up to 5,000 signatures, Premium US$99.99/month up to 100,000, overage US$0.005/signature. It replaces long-lived EV certs + hardware tokens with identity validation once and short-lived certs (~72h validity, renewed daily) from a Microsoft CA that Windows already trusts. SBOM baseline: CISA and international partners published the 2026 Minimum Elements for an SBOM on 29 Jul 2026 (first full update to the 2021 NTIA baseline); the Aug 2025 draft added Component Hash, License, Tool Name and Generation Context to the original seven fields. Current formats: CycloneDX 1.7 (Oct 2025; ECMA-424 2nd Edition, Dec 2025), SPDX 3.0.1 (3.0 line from Apr 2024).

**Why it matters.** $120/year removes SmartScreen friction, gives update-integrity provenance, and is a prerequisite for any future distribution. Emitting a CycloneDX 1.7 SBOM per release costs one CI step and is what turns 'was I affected by CVE-X / by Shai-Hulud 3.0' from a week into a grep.

- https://azure.microsoft.com/en-us/pricing/details/trusted-signing/
- https://techcommunity.microsoft.com/blog/microsoft-security-blog/trusted-signing-is-now-open-for-individual-developers-to-sign-up-in-public-previ/4273554
- https://media.defense.gov/2026/Jul/29/2003971159/-1/-1/1/CSI_2026_cisa_sbom_minimum_elements_508c.PDF
- https://runsafesecurity.com/blog/sbom-minimum-elements-cyclonedx-spdx/

### 10. Certificate pinning: do not pin leaf certs in this app; pin selectively or not at all  
`confidence: high`

Industry consensus has moved against pinning for general client apps: it is fragile on rotation, causes outages, is trivially bypassed by an attacker with local code execution (the exact adversary here), and breaks corporate MITM proxies. OWASP's pinning cheat sheet is explicitly scoped to mobile. Recommended alternatives: default OS trust store, Certificate Transparency monitoring, HSTS, strong TLS 1.3 config, DNS CAA. Note the specific conflict for this app: a bank/hedge-fund user behind a corporate TLS-inspection proxy will have a locally-installed root CA; a pinned client fails closed and looks broken.

**Why it matters.** Naive plans reflexively add pinning and then ship an app that dies when a provider rotates CAs. The defensible middle: pin to CA/SPKI set for your *own* update/knowledge-base endpoint only (you control both ends), never for third-party market-data vendors; and expose an explicit 'trust system proxy' toggle with a visible warning banner.

- https://cheatsheetseries.owasp.org/cheatsheets/Pinning_Cheat_Sheet.html
- https://owasp.org/www-community/controls/Certificate_and_Public_Key_Pinning
- https://www.lrqa.com/en/cyber-labs/tls-certificate-pinning-101/

### 11. Prompt injection is the #1 LLM risk and this app's content sources are all attacker-influenced  
`confidence: high`

OWASP Top 10 for LLM Applications 2025: LLM01 Prompt Injection (top spot for the second consecutive edition), LLM02 Sensitive Information Disclosure, LLM05 Improper Output Handling, LLM06 Excessive Agency, LLM09 Misinformation. Indirect injection = instructions embedded in documents the model later processes. In this product the ingest set is: SEC/EDGAR filings (issuer-authored free text, including exhibit and footnote fields), RNS/regulatory news, press releases, transcripts, PDFs, RSS, social. All are attacker-controllable by the issuer, by a promoter, or by anyone who can get text into a feed. Exfiltration channel: model emits a markdown/HTML image whose URL encodes the stolen context; the renderer fetches it. Documented in the wild against multiple production LLM products (Google AI Studio, ChatGPT, EchoLeak).

**Why it matters.** An issuer under short attack has a direct financial incentive to plant text in a filing that manipulates a widely-used AI terminal's summary. This is not hypothetical adversarial theatre — it is a rational market-manipulation vector. Treat every ingested document as hostile, tag provenance, and never let ingested text reach the system-prompt or tool-selection layer.

- https://owasp.org/www-project-top-10-for-large-language-model-applications/assets/PDF/OWASP-Top-10-for-LLMs-v2025.pdf
- https://embracethered.com/blog/posts/2024/google-ai-studio-data-exfiltration-now-fixed/
- https://www.microsoft.com/en-us/msrc/blog/2025/07/how-microsoft-defends-against-indirect-prompt-injection-attacks
- https://arxiv.org/pdf/2509.10540

### 12. WebView2 rendering of AI output is the injection-to-RCE bridge if done carelessly  
`confidence: high`

Microsoft's WebView2 security guidance: treat all third-party content as untrusted; check document origin before ExecuteScript/PostWebMessageAsJson/PostWebMessageAsString; validate all web messages and host-object parameters; call RemoveHostObjectFromScript on the ContentLoading event when navigating; restrict navigation via NavigationStarting; do not run the WebView2-hosting component elevated — isolate any privileged work in a separate de-elevated-host design.

**Why it matters.** If AI output is rendered as HTML in a WebView2 that has AddHostObjectToScript bindings, a prompt injection becomes arbitrary host-object invocation. Concrete rule: render AI output as sanitised, allow-listed markdown -> HTML with a restrictive CSP (default-src 'none'; img-src 'self' data:; script-src 'none'), no remote image loading, no iframes, no host objects on any surface that displays model or feed content.

- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/security
- https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/developer-guide

### 13. MCP / plugin extensibility is a documented, CVE-bearing attack surface  
`confidence: high`

OWASP's MCP Top 10 codifies tool poisoning as MCP03:2025, alongside rug pulls and tool shadowing. Rug pull: a server behaves during review, is approved, then changes server-side — CVE-2025-54136 (CVSS 8.8, disclosed Jul 2025) confirmed tool-definition approval does not survive server-side changes. Microsoft's 'state of MCP security in 2026' and Practical DevSecOps report 40+ CVEs against MCP implementations between Jan and Apr 2026. Named classes: tool poisoning, rug pull, tool shadowing, cross-server attacks, confused-deputy/OAuth weaknesses, line jumping, and the 'lethal trifecta' (private data + untrusted content + external communication).

**Why it matters.** If this terminal ever accepts third-party MCP servers or plugins, it inherits all of that. Recommended controls if extensibility ships: allow-list servers, pin tool-definition hashes and re-prompt on change, run every plugin out-of-process with no filesystem/network capability by default, and never expose the secret vault or the watchlist to a plugin.

- https://labs.cloudsecurityalliance.org/research/csa-research-note-mcp-tool-poisoning-ai-agent-exfiltration-2/
- https://techcommunity.microsoft.com/blog/microsoft-security-blog/the-state-of-mcp-security-in-2026/4531327
- https://www.practical-devsecops.com/mcp-security-statistics-2026-report/
- https://arxiv.org/pdf/2509.06572

### 14. Hosted-LLM privacy: Anthropic commercial API defaults are good but not zero  
`confidence: medium`

Anthropic's commercial privacy documentation states that for the Anthropic API, inputs and outputs are automatically deleted from the backend within 30 days of receipt/generation, with exceptions: customer-controlled services (e.g. Files API), negotiated Zero Data Retention agreements, up to 2 years retention for Usage Policy violations, legal-compliance retention, and limited retention for Covered Models safety work. Feedback submissions (thumbs up/down, bug reports) are retained 5 years. Anthropic does not train on commercial API/Claude for Work/Enterprise customer content by default. Note a conflicting secondary claim that API log retention dropped to 7 days on 2025-09-14 — treat the official 30-day figure as authoritative and the 7-day claim as unverified.

**Why it matters.** Anything sent to the model is, by default, on a third party's infrastructure for up to 30 days. For this app the sensitive payload is the *watchlist and the user's notes* — which reveal the trading thesis. Design: strip identifiers, batch and generalise queries, keep positions/notes out of prompts unless explicitly opted in per-query, and offer a local-model mode for the position-aware features.

- https://privacy.claude.com/en/articles/7996866-how-long-do-you-store-personal-data
- https://privacy.claude.com/en/articles/10023548-how-long-do-you-store-my-data

### 15. Market data licensing is the biggest legal risk, and the cliff is the second user  
`confidence: high`

Retail-tier vendor terms are explicit. Polygon.io 'for Individuals' ToS (Last Updated 18 Jul 2025; the domain now redirects to massive.com, indicating a rebrand/acquisition) grants a 'non-exclusive, non-transferable, non-assignable, worldwide, limited right to access and use the Services... solely for your own personal, non-commercial, and non-business purposes', prohibits sale/transfer of access, prohibits derivative works, and its Market Data ToS (Last Updated 9 Oct 2024) prohibits redistributing, displaying, disseminating, duplicating, licensing, sublicensing, publishing, broadcasting or transmitting Market Data to any third party, and prohibits building an application 'intended for use by end users other than you', with one (1) App Licence per subscription. Exchange 'Nonprofessional Subscriber' status requires a natural person receiving data solely for personal, non-business use who is NOT: registered/qualified with the SEC, CFTC, a state securities agency, any exchange/association or contract market; engaged as an investment adviser under s.202(a)(11) of the Advisers Act (registered or not); or employed by an exempt bank/organisation performing certain functions. Vendors must actively verify subscriber status. Exchange licensing separately splits Display Use (per-user Professional/Non-Professional/Enterprise/Digital Media fees) from Non-Display Use in three categories (own behalf / on behalf of clients / internal matching).

**Why it matters.** Three concrete traps: (a) trading through a personal company or LLC, or being an unregistered 'investment adviser' by activity, can flip the user to Professional and multiply fees; (b) shipping the app to one friend converts personal use into redistribution and requires vendor/exchange agreements plus reporting; (c) using cached quotes to drive alerts, scanners, backtests or AI-generated numbers may be characterised as Non-Display Use, which is licensed and priced separately from Display Use even for one person.

- https://massive.com/legal/individuals-terms-of-service
- https://polygon.io/legal/market-data-terms-of-service
- https://www.nyse.com/publicdocs/nyse/data/Policy-Non-ProfessionalSubscribers_PDP.pdf
- https://www.ctaplan.com/publicdocs/ctaplan/Policy_Non-Professional_Subscribers_CTA.pdf
- https://www.cmegroup.com/market-data/distributor/files/cme-group-data-licensing-policy-guidelines-and-non-display-licensing-faq.pdf
- https://databento.com/blog/subscriber-status

### 16. US advice perimeter: the publisher exclusion is available but conditional on impersonality  
`confidence: high`

Lowe v. SEC, 472 U.S. 181 (1985) construed the Advisers Act exclusion for 'publishers of any bona fide newspaper, news magazine or business or financial publication of general and regular circulation' to cover impersonal investment advice offered to the general public on a regular basis. The three-part test: (1) general and impersonal — not attuned to any specific portfolio or client's particular needs; (2) bona fide/genuine; (3) of general and regular circulation. Communications must remain entirely impersonal and must not develop into fiduciary, person-to-person relationships. On the futures/FX side, CFTC Rule 17 CFR 4.14(a)(9) (adopted Mar 2000) exempts CTAs whose advice is standardised and delivered via newsletters, prerecorded newslines, websites and non-customized computer software, provided the advice is not tailored to a subscriber's particular circumstances and the CTA does not direct client accounts.

**Why it matters.** This is the safe-harbour the product should be architected into, and it has a sharp edge: a terminal that knows the user's holdings, cash and risk tolerance and produces 'you should trim your NVDA' is neither impersonal nor non-customized. If the app is single-user and never distributed, neither regime bites at all; the design constraint only becomes live if a second user or a subscription ever exists.

- https://supreme.justia.com/cases/federal/us/472/181/
- https://caselaw.findlaw.com/court/us-supreme-court/472/181.html
- https://www.ecfr.gov/current/title-17/chapter-I/part-4/subpart-A/section-4.14
- https://www.federalregister.gov/documents/2000/03/10/00-5823/exemption-from-registration-as-a-commodity-trading-advisor

### 17. UK perimeter: Article 53 advising, plus the s.21 promotion regime that catches unauthorised communicators  
`confidence: high`

Article 53(1) RAO covers advising on investments. Post-FAMR, for an FCA-authorised firm the activity is only triggered by a personal recommendation; PERG 8.30B explains personal recommendation, and PERG 8.24 confirms generic/general advice (e.g. merits of investment trusts vs unit trusts, or Japanese vs European equities) is NOT the regulated activity. Separately s.21 FSMA prohibits an unauthorised person, in the course of business, communicating an invitation or inducement to engage in investment activity unless approved by an authorised person or exempt; since 7 Feb 2024 approvers need a specific FCA 'approver permission'. PERG 8.5: 'in the course of business' requires a commercial interest — genuinely personal communications between friends, family, or on a personal internet forum, fall outside; the Treasury has never defined it, so the ordinary meaning governs. High-risk investment promotion rules from PS22/10 took effect 1 Dec 2022 / 1 Feb 2023. New regime: FCA PS25/22 targeted support — Advice Guidance Boundary Review (Targeted Support) Instrument 2026 (FCA 2026/5) in force 6 Apr 2026, applications open from 2 Mar 2026, covering pensions and investments; the FCA says it intends to consult further on perimeter guidance.

**Why it matters.** For a single-user private tool there is no 'course of business' communication and no s.21 exposure. The risk appears the instant output is shared publicly — screenshots on X, a newsletter, a Discord. The FCA is enforcing hard here: 2025 and 2026 international 'weeks of action' (9 then 17 regulators), 120 account takedown requests, 1,267 illegal ads reaching 2,338,372 UK accounts, criminal charges against finfluencers under s.21, and the FCA is seeking to raise the maximum sentence from 2 to 5 years.

- https://handbook.fca.org.uk/handbook/PERG/8/24.html
- https://handbook.fca.org.uk/handbook/perg8/perg8s41
- https://handbook.fca.org.uk/handbook/perg8/perg8s5
- https://handbook.fca.org.uk/handbook/perg8/perg8s9
- https://www.fca.org.uk/publications/policy-statements/ps22-10-strengthening-our-financial-promotion-rules-high-risk-investments-firms-approving-financial-promotions
- https://www.fca.org.uk/publications/policy-statements/ps25-22-consumer-pensions-investment-decisions-rules-targeted-support

### 18. EU: MAR Article 20 catches 'experts' who publish recommendations, and it is a formatting/disclosure regime  
`confidence: high`

MAR Art.20 plus Commission Delegated Regulation (EU) 2016/958 (RTS on objective presentation of investment recommendations and disclosure of interests/conflicts) require the producer to identify themselves, distinguish fact from opinion/estimate, cite sources, state valuation methodology and the meaning of any recommendation ('buy/hold/sell', target price, time horizon), disclose the date/time of production and dissemination, disclose all relationships and holdings that could impair objectivity, and maintain a record. Per ESMA, the regime applies to independent analysts, investment firms and credit institutions, to persons 'whose main business is to produce investment recommendations', and also to third parties who disseminate such material. Separately, MiFID II Delegated Reg (EU) 2017/565 Arts 36-37 distinguish 'investment research' (recommends or suggests an investment strategy and provides a substantiated opinion on present/future value) from 'marketing communication', which must carry prominent wording identifying it as such and stating it was not prepared under research-independence rules. Art. 9 / ESMA supervisory briefing ESMA35-43-3861 govern the definition of advice.

**Why it matters.** An AI panel that outputs a target price, a 'buy' label, or a substantiated opinion on future value is, functionally, an investment recommendation. Kept private it is nothing. Published to any audience in the EU/UK it triggers Art.20 disclosure obligations regardless of whether the author is authorised. Safe design: the AI produces evidence and framed questions, not ratings or price targets — and any rating-like output carries a machine-generated Art.20-style disclosure block if export is ever enabled.

- https://eur-lex.europa.eu/eli/reg_del/2016/958/oj/eng
- https://www.esma.europa.eu/sites/default/files/2023-07/ESMA35-43-3861_Supervisory_briefing_on_understanding_the_definition_of_advice_under_MiFID_II.pdf
- https://www.fi.se/en/markets/investors/investment-recommendations/
- https://www.lw.com/admin/Upload/Documents/Quick-Start-Guide-MiFID-II-research_4.pdf

### 19. EU AI Act Article 50 transparency obligations are live NOW (2 Aug 2026)  
`confidence: high`

Article 50 of Regulation (EU) 2024/1689 became enforceable on 2 August 2026 — three weeks before today's date. It applies regardless of whether the system is Annex III high-risk. Providers of AI systems that interact directly with natural persons (chatbots, assistants) must ensure the person is informed they are dealing with an AI system unless obvious from context. Providers/deployers of systems generating synthetic audio, image, video or text must mark outputs in a machine-readable, detectable format; deployers must disclose deepfakes. Under the AI Act 'Digital Omnibus', providers of generative systems already on the market before 2 Aug 2026 have until 2 Dec 2026 for the marking obligation, but the chatbot-disclosure, deepfake-labelling and emotion-recognition obligations had NO grace period. Annex III high-risk compliance was separately deferred to 2 Dec 2027.

**Why it matters.** If the terminal is ever made available in the EU (even free, even to one EU user), the AI panel needs an explicit 'this is AI-generated' affordance and machine-readable marking of AI-generated text. This is cheap to build now and expensive to retrofit. Note also: AI systems used to evaluate creditworthiness are Annex III high-risk — an AI feature that scores counterparty/issuer credit for third parties could stray toward that classification (low confidence, fact-specific).

- https://artificialintelligenceact.eu/article/50/
- https://www.goodwinlaw.com/en/insights/publications/2026/08/alerts-technology-dpc-eu-ai-act-transparency-obligations-now-in-force
- https://artificialintelligenceact.eu/transparency-rules-article-50/
- https://www.stibbe.com/publications-and-insights/the-ai-acts-transparency-obligations-rules-scope-and-timeline

### 20. Scraping: 'not a federal crime' is not 'lawful' — contract and tort are the live theories  
`confidence: high`

hiQ v. LinkedIn ended in Nov 2022 with the district court finding hiQ breached LinkedIn's user agreement's anti-scraping and fake-profile terms, and in Dec 2022 with a stipulated consent judgment: US$500,000 against hiQ, admitted liability under California trespass to chattels and misappropriation, and a permanent injunction effectively barring future scraping. Van Buren v. United States (2021) narrowed CFAA 'exceeds authorized access' to a gates-up-or-down test, and the Ninth Circuit's earlier hiQ ruling held scraping public data does not violate CFAA — but breach of contract, trespass to chattels, misappropriation, copyright and DMCA §1201 all survive. EDGAR is a specific, documented case: SEC fair access states a current max request rate of 10 requests/second, requires a declarative User-Agent header of the form 'Sample Company Name AdminContact@<domain>.com', states 'The SEC does not allow botnets or automated tools to crawl the site', and asks users to 'Download only what you need'; violations produce 403/429 and roughly a 10-minute IP block. Yahoo's ToS prohibit automated access without written permission and restrict copying/republishing; yfinance is explicitly not affiliated with or vetted by Yahoo.

**Why it matters.** For a data-heavy terminal the correct rule is: paid API or public-domain bulk file, never a scraper against a site with anti-scraping terms. EDGAR is fine and should be used properly (declared UA, <=10 rps, prefer daily-index and bulk submissions files over crawling). Yahoo/Google Finance are technically possible and contractually indefensible — and they are also the exact dependency that breaks silently and poisons the AI's numbers.

- https://www.sec.gov/search-filings/edgar-search-assistance/accessing-edgar-data
- https://www.privacyworld.blog/2022/12/linkedins-data-scraping-battle-with-hiq-labs-ends-with-proposed-judgment/
- https://www.morganlewis.com/blogs/sourcingatmorganlewis/2022/12/linkedin-v-hiq-landmark-data-scraping-suit-provides-guidance-to-data-scrapers-and-web-operators
- https://www.zwillgen.com/alternative-data/hiq-v-linkedin-wrapped-up-web-scraping-lessons-learned/

### 21. Insider/incentives pillar: aggregating public disclosures is safe; the alt-data adjacency is where it breaks  
`confidence: high`

Aggregating Form 4s, Schedules 13D/13G, 13Fs, DEF 14A compensation tables, UK PDMR/MAR Art.19 managers'-transactions RNS and short-interest data is aggregation of already-public information and does not create MNPI. The failure mode is adjacency to non-public sourcing. SEC v. App Annie Inc. and Bertrand Schmitt (14 Sep 2021) was the SEC's first enforcement action against an alternative data provider: charges under Exchange Act s.10(b)/Rule 10b-5 for misrepresenting how the data was derived and for inadequate MNPI controls; App Annie paid a US$10m penalty, Schmitt US$300,000 plus a three-year officer-and-director bar. Timing facts that matter for the feature set: Schedule 13D initial filings are due within 5 business days (amendments 2 business days); Schedule 13G for QIIs/exempt investors 45 days after quarter end, passive investors 5 business days, with the >10% triggers at 5 business days (QII, month end) and 2 business days (passive); compliance with revised 13G deadlines began 30 Sep 2024 and structured-data (XML) requirements 18 Dec 2024. Section 16 Form 4 is due within 2 business days of the transaction (not re-verified in this research pass — medium confidence).

**Why it matters.** The 'who is buying, who is dumping, who is paid to make the number' pillar is legally clean as long as every datum traces to a public filing with a filing timestamp. It stops being clean the moment the roadmap adds expert-network transcripts, employee-sourced channel checks, credit-card panels, geolocation, or app-telemetry panels — categories that carry both MNPI and privacy exposure and that App Annie made an enforcement priority.

- https://www.sec.gov/newsroom/press-releases/2021-176
- https://www.gibsondunn.com/sec-announces-first-enforcement-action-against-alternative-data-provider-for-securities-fraud-highlighting-regulatory-risks-in-growing-industry/
- https://www.sec.gov/newsroom/press-releases/2023-219
- https://www.velaw.com/insights/shorter-schedule-13d-and-schedule-13g-filing-deadlines-and-new-guidance-sec-adopts-final-rules-amending-beneficial-ownership-reporting/

### 22. UK/EU privacy posture for a genuinely single-user app is near-trivial — until telemetry appears  
`confidence: medium`

UK GDPR does not apply to processing by an individual purely for personal or household purposes. If the app is used solely by its author on their own machine with no telemetry and no cloud account, there is no controller/processor relationship to register. ICO data protection fee tiers for 2026 (unchanged from prior year): Tier 1 £52 (micro: turnover <= £632,000 or <= 10 staff), Tier 2 £78 (turnover <= £36m or <= 250 staff), Tier 3 £3,763. There is no blanket sole-trader exemption — liability follows what you do with personal data. The moment the product ships to another person and collects crash reports, usage analytics, or an account email, the builder becomes a controller, needs a lawful basis, a privacy notice, and (absent an exempt-purposes-only profile) the fee.

**Why it matters.** Local-first with telemetry OFF by default is not just good practice here — it is the difference between zero regulatory surface and a full controller obligation set. Any telemetry must be opt-in, per-category, inspectable in-app, and must never include symbols, watchlists, notes or query text.

- https://ico.org.uk/for-organisations/data-protection-fee/data-protection-fee/
- https://ico.org.uk/for-organisations/data-protection-fee/data-protection-fee/data-protection-fee-faqs/

### 23. Non-obvious asset: the watchlist IS the alpha, and current designs leak it everywhere  
`confidence: medium`

Assets ranked by real value to an adversary, not by conventional sensitivity: (1) watchlist + screener criteria + alert thresholds + notes = the trading thesis, worth more than any API key; (2) API keys (replaceable, revocable, low individual value); (3) cached licensed market data (contractual liability, not confidentiality); (4) the AI knowledge base (integrity asset — poisoning it changes decisions silently); (5) positions/P&L if ever entered; (6) telemetry. The leak paths are mundane: watchlist symbols embedded in LLM prompts to a hosted model; symbols in DNS queries and TLS SNI to per-symbol vendor endpoints (visible to a network observer even under TLS 1.3 without ECH); symbols in crash dumps and log files; symbols in the window title and in Recent Files; symbols in an unencrypted SQLite cache readable by any process; symbols in autocomplete telemetry.

**Why it matters.** A naive plan protects the API key and broadcasts the alpha. Concrete mitigations: batch/obfuscate per-symbol requests, prefer bulk snapshot endpoints over per-symbol polling, keep the watchlist table in the encrypted store, scrub logs and crash dumps of symbol identifiers, never put symbols in the window title, and gate hosted-LLM prompts through a redaction/consent step.


### 24. Practical hardening details that a naive Windows plan omits  
`confidence: medium`

Concrete items: (a) require no administrator rights at any point — installation per-user under %LOCALAPPDATA%, no service, no driver; (b) build native components with /DYNAMICBASE (ASLR) + /HIGHENTROPYVA + /GS + /guard:cf (Control Flow Guard) + /CETCOMPAT (shadow stacks) and /guard:ehcont; (c) restrict the data directory ACL to the user SID only, explicitly removing inherited Users/Authenticated Users ACEs (default %LOCALAPPDATA% inheritance is usually fine but installers frequently break it); (d) MSIX packaging gives package identity, filesystem/registry virtualization and clean uninstall, but the default MSIX Packaging Tool output is a *full trust* package — AppContainer isolation must be opted into and breaks most Win32 desktop behaviour; (e) update integrity: sign the installer and the update manifest, verify signature+SHA-256 before applying, use a monotonic version counter to prevent rollback attacks, and consider TUF-style role separation if the knowledge base updates independently of the binary; (f) never log API keys, bearer tokens, full quote payloads or prompt contents — structured logging with an explicit allow-list of loggable fields, not a deny-list; (g) crash reporting must be opt-in and must strip the heap.

**Why it matters.** These are the items that separate a professional-feeling product from a hobby build, and several (no-admin, CET, per-user install) are also what makes the app installable inside a corporate estate without a security exception.

- https://learn.microsoft.com/en-us/windows/msix/msix-containerization-overview
- https://learn.microsoft.com/en-us/windows/msix/msix-container
- https://learn.microsoft.com/en-us/windows/win32/secauthz/appcontainer-isolation

## Recommended decisions

### What actually protects API keys on Windows?

**Recommendation.** Layered: user passphrase -> Argon2id (m=19456, t=2, p=1) derives a KEK; the DEK is additionally wrapped by a CNG persisted key created with NCRYPT_REQUIRE_VBS_FLAG, falling back to Microsoft Platform Crypto Provider (TPM 2.0), falling back to DPAPI user-scope with a visible 'reduced protection' badge. Never machine scope. Never a key file next to the database.

**Rationale.** DPAPI alone is defeated by any process running as the user, which is precisely the infostealer threat model (LummaC2/StealC/Vidar/ACRStealer). VBS/TPM turns an exportable secret into a non-exportable handle, forcing the attacker to stay resident and use it in place — which is detectable and rate-limitable. The passphrase ensures the ciphertext is not silently machine-recoverable.

**Rejected.** DPAPI-only (defeated by same-user malware). Windows Credential Manager as primary store (same DPAPI weakness plus a 2,560-byte blob cap). Chrome-style app-identity binding (broken within 45 days by COM hijacking and the C4 Bomb padding oracle). Azure Key Vault as primary (adds a cloud dependency, an auth secret that itself needs local storage, and network availability as a hard requirement for a desktop terminal).

**Cost.** Engineering only. TPM 2.0 + VBS require Windows 11-class hardware; a documented graceful downgrade path is mandatory.

### Encrypt the whole database or only the secrets?

**Recommendation.** Encrypt only the secrets, watchlists, alert rules and user notes. Leave bulk cached time-series in a plain high-performance store. Use SQLCipher Community Edition (BSD-3-Clause, free for commercial use, attribution required) or app-layer AES-256-GCM for the sensitive store.

**Rationale.** Bulk market data's exposure is contractual (redistribution/retention terms), not confidential — encrypting it costs real query latency and buys nothing against the same-user adversary. The watchlist and notes are the genuine crown jewels and are small enough to encrypt with no measurable cost.

**Rejected.** SQLite SEE (US$2,000 perpetual, statically linked, no support — no advantage over SQLCipher for this use). Whole-DB encryption with a machine-recoverable key (theatre: the key sits next to the ciphertext). Relying on BitLocker/EFS (transparent to the logged-in user's processes; protects only device theft).

**Cost.** $0 licence (SQLCipher Community) vs $2,000 one-off (SEE).

### Certificate pinning?

**Recommendation.** Pin only your own update and knowledge-base endpoints (SPKI pin set with at least one backup pin and a documented rotation runbook). Do not pin third-party market-data vendors. Ship an explicit, warned 'trust system TLS proxy' toggle for corporate-MITM environments, defaulting to the OS trust store with TLS 1.3.

**Rationale.** Pinning provides negligible defence against a local attacker who can patch the pin, while guaranteeing outages on vendor CA rotation and hard-failing behind corporate inspection proxies used by exactly this app's likely user. Pinning your own endpoint is defensible because you control both ends.

**Rejected.** Pin everything (fragile, outage-prone, bypassable). Pin nothing including your own updater (loses the one place pinning genuinely helps: update integrity).

**Cost.** Low engineering; ongoing rotation discipline.

### Where is the boundary between AI and action?

**Recommendation.** Absolute: AI can read, AI cannot act. The model process gets no credentials, no filesystem write, no network egress, and a fixed hashed set of read-only tools. No AI output ever triggers an irreversible or outbound operation — no email, no webhook, no file write, no purchase, no ordering (which is out of scope anyway), and no automatic knowledge-base mutation without a signed bundle.

**Rationale.** Every ingested document is attacker-influenceable (OWASP LLM01 is #1 for the second consecutive edition). If the model cannot act, a successful injection produces at worst wrong prose that the citation-enforcement layer exposes. This is the only defence that does not depend on detecting injection.

**Rejected.** Prompt-level guardrails alone (bypassed routinely; OWASP itself recommends defence-in-depth with privilege restriction). Human-in-the-loop confirmation for AI actions (confirmation fatigue; still gives the model an action surface).

**Cost.** Architectural; costs some agentic convenience.

### How is AI output rendered?

**Recommendation.** Sanitised allow-listed markdown -> HTML in a WebView2 with CSP default-src 'none'; img-src 'self' data:; script-src 'none'; style-src 'self' 'unsafe-inline'. No remote image loading anywhere in the app. No host objects bound on any WebView that displays model or feed content. NavigationStarting blocks all navigation; RemoveHostObjectFromScript on ContentLoading.

**Rationale.** Markdown image rendering is the proven exfiltration channel (documented against Google AI Studio, ChatGPT, EchoLeak). Blocking remote img-src closes it. Removing host-object bindings closes the injection-to-host-code path that Microsoft's own WebView2 guidance warns about.

**Rejected.** Rendering full HTML from the model (unbounded). Proxying remote images through your own server (adds infrastructure and still leaks the fetch pattern; unnecessary for a desktop app where remote images add nothing).

**Cost.** Low; mainly discipline plus a markdown sanitiser.

### UI/runtime stack from a supply-chain risk perspective

**Recommendation.** A lean .NET (WPF/WinUI 3) tree with NuGet Package Source Mapping, packages.lock.json + --locked-mode restores, NuGet Audit and `dotnet list package --vulnerable --include-transitive` in CI. If any web UI is needed, WebView2 rendering locally-vendored, hash-pinned assets — never a runtime npm dependency graph.

**Rationale.** Shai-Hulud (Sep 2025) and Shai-Hulud 2.0 (Nov 2025 onward, ~25,000 malicious repos across ~350 users) demonstrated self-propagating worm behaviour in npm that has no .NET analogue at that scale. A 200-package Electron tree is 200 maintainer accounts that can each be phished into your trader's machine.

**Rejected.** Electron/React as the primary shell (large transitive attack surface, larger memory footprint, worse latency for a charting app). Tauri (smaller than Electron but still an npm frontend tree).

**Cost.** Engineering-only; some UI velocity cost vs React.

### Build signing and release integrity

**Recommendation.** Azure Artifact Signing (formerly Trusted Signing) Basic at US$9.99/month (5,000 signatures; Premium US$99.99/month for 100,000; overage US$0.005/signature). Sign the installer, all binaries, the update manifest and the knowledge-base bundle. Publish SHA-256 hashes and a CycloneDX 1.7 SBOM per release. Verify signature + hash + monotonic version before applying any update.

**Rationale.** ~US$120/year removes SmartScreen friction, gives short-lived (~72h) Microsoft-CA-issued certs with no hardware token to guard, and is the only defence a user has against the documented trading-brand malvertising campaigns that distribute trojanised 'TradingView'-class installers.

**Rejected.** Traditional EV code-signing certificate with a hardware token (higher cost, key custody burden). Unsigned distribution (SmartScreen friction plus zero tamper evidence — indefensible for a financial app).

**Cost.** US$119.88/year plus CI integration.

### Which market-data licence tier to build against?

**Recommendation.** Design explicitly for a single natural person, non-professional, non-redistributing, display-use licence. Build the Licence Ledger from day one so the multi-user cliff is a configuration change plus a commercial negotiation, not a rewrite. Verify with each vendor in writing whether alerting, scanning, backtesting and AI-derived numbers count as Non-Display Use under their agreement.

**Rationale.** Retail terms are explicit and narrow: Polygon/Massive Individuals ToS (18 Jul 2025) grants use 'solely for your own personal, non-commercial, and non-business purposes'; the Market Data ToS (9 Oct 2024) forbids redistribution to any third party and building an app for end users other than you, with one App Licence. Exchange Non-Display Use is licensed and priced separately from Display Use, and a scanner/alert engine is the classic grey area.

**Rejected.** Assuming personal use covers alerting/backtesting (Non-Display categories exist precisely for this). Building for eventual multi-user distribution without exchange vendor agreements (would require professional-subscriber reporting, audits and materially higher fees).

**Cost.** Retail feed subscriptions plus exchange non-professional fees; a professional reclassification is typically an order-of-magnitude increase (exact 2026 per-exchange figures not verified in this pass).

### Scraping policy

**Recommendation.** Hard rule: paid API, official bulk file, or nothing. EDGAR is permitted and must be used correctly — declared User-Agent of the form 'Name AdminContact@domain', <=10 requests/second, prefer daily-index and bulk submission files over crawling, model the ~10-minute block on 403/429. No Yahoo Finance, no Google Finance, no yfinance, no headless-browser scraping of any site whose terms prohibit automated access.

**Rationale.** Post-hiQ, CFAA is not the risk — breach of contract, trespass to chattels and misappropriation are, and hiQ's consent judgment (Dec 2022: US$500,000, admitted trespass/misappropriation liability, permanent injunction) shows what that looks like. Scraped sources also break silently and poison AI-derived numbers.

**Rejected.** 'It's public data so it's fine' (Van Buren narrowed CFAA only; contract and tort survive). Scraping with rotating proxies (converts a contract issue into evidence of intentional circumvention).

**Cost.** Higher data spend; materially lower legal and data-quality risk.

### Does the AI ever give an opinion?

**Recommendation.** No ratings, no price targets, no position sizing, no 'buy/sell/hold', and no personalisation to holdings. The AI produces evidence, incentive maps, disclosure timelines, base rates, contradictions between filings, and sharp questions. Ship the MAR Art.20 disclosure wrapper built but disabled, and enable it only if a share/export/publish path is ever added.

**Rationale.** This keeps the product inside three safe harbours simultaneously: the Lowe publisher exclusion (impersonal, bona fide, general circulation), CFTC 4.14(a)(9) (standardised, non-customized, no account direction), and the FCA generic-advice boundary (PERG 8.24; not a personal recommendation under PERG 8.30B). It also keeps output outside 'investment research' under MiFID II Delegated Reg 2017/565 Arts 36-37, which turns on providing a substantiated opinion on present or future value.

**Rejected.** Ratings plus a disclaimer (disclaimers do not change the legal characterisation of the activity; the FCA is prosecuting s.21 cases and MAR Art.20 applies to the substance of the communication, not its labelling). Personalised AI that reads the user's positions (destroys the impersonality condition in all three safe harbours simultaneously).

### Privacy and telemetry default

**Recommendation.** Local-first, telemetry off by default, opt-in per category, no account required, no cloud sync of watchlists. Hosted-LLM calls gated by a redaction preview on first use per feature. Offer a fully local-model mode for position-aware analysis.

**Rationale.** UK GDPR does not reach purely personal/household processing, so a single-user, no-telemetry build has effectively zero controller obligations. Adding telemetry converts the builder into a controller with a lawful-basis, notice and (usually) ICO fee obligation — Tier 1 is £52, Tier 2 £78, Tier 3 £3,763 for 2026. Separately, the Anthropic commercial API deletes inputs/outputs within 30 days by default (with named exceptions up to 2 years for policy violations and 5 years for feedback), so hosted calls are never zero-exposure.

**Rejected.** Anonymous usage analytics on by default (small product benefit, disproportionate legal and thesis-leakage cost). Mandatory cloud account (creates a controller relationship and a credential to steal).

**Cost.** £0 while single-user; £52/year ICO Tier 1 if it ever ships with telemetry to others.

### Ship an extension/MCP surface?

**Recommendation.** Not in v1. If demanded later: out-of-process, capability-zero by default, server allow-list, tool-definition hash pinning with re-consent on change, all tool output through the Untrusted Content Firewall, and never any vault or watchlist access.

**Rationale.** 40+ CVEs against MCP implementations were disclosed between Jan and Apr 2026, and CVE-2025-54136 (CVSS 8.8) established that approval of a tool definition does not survive server-side changes (rug pull). Adding this surface to a terminal holding market-data credentials and a trading thesis is a poor trade in v1.

**Rejected.** Open plugin marketplace (imports the entire third-party trust problem). In-process plugins (no containment boundary at all).

**Cost.** Deferred engineering; some ecosystem opportunity cost.

## Candidate features

| Pri | Eff | Feature | Description | Source |
|---|---|---|---|---|
| P0 | L | Hardware Vault | Secret store where each provider API key is sealed by a DEK that is itself wrapped by a CNG persisted key created with NCRYPT_REQUIRE_VBS_FLAG (fallback: Microsoft Platform Crypto Provider / TPM 2.0, fallback: DPAPI user scope with an explicit in-app 'reduced protection' badge). Passphrase -> Argon2id (m=19456, t=2, p=1) -> unwrap. Capability tiers shown honestly in a Security page. | Windows CNG (ncrypt.dll) via P/Invoke; TPM 2.0 |
| P1 | M | Vault Unlock with Windows Hello | Windows Hello (KeyCredentialManager) as the day-to-day unlock factor with the passphrase as recovery. Idle re-lock timer, lock on workstation lock / sleep / RDP disconnect. | Windows Hello / KeyCredentialManager |
| P0 | M | Split Store: encrypted secrets, plain cache | Two physical stores: an encrypted store (SQLCipher or app-layer AES-GCM) for keys, watchlists, notes and alert rules; a plain columnar/SQLite store for bulk time-series, sized for speed. Explicit rationale surfaced in docs. | SQLCipher Community (BSD-3) or app-layer AEAD |
| P0 | M | Egress Console + Allow-list | Live panel showing every outbound host, byte counts, request rates and per-provider quota burn; a hard allow-list of permitted hostnames enforced in the HTTP stack; any attempt to reach a non-listed host is blocked and surfaced as an alert. | App HTTP layer / HttpClientHandler |
| P0 | L | Untrusted Content Firewall | Every ingested document (filing, RNS, PDF, RSS item, transcript) is parsed, stripped of hidden/zero-width/bidi characters and invisible-Unicode tag blocks (ASCII smuggling), wrapped in a provenance envelope, and passed to the model only as delimited data — never concatenated into the system prompt. Injection-pattern detector flags documents containing imperative meta-instructions and quarantines them with a visible banner. | EDGAR, RNS, news APIs, PDF text layer |
| P0 | L | AI Read-Only Boundary (capability manifest) | Architectural enforcement, not a prompt: the model process holds no credentials, no filesystem write, no network egress, and can call only a fixed, versioned set of read tools. All tool schemas hashed and pinned; any change requires an explicit user re-approval. No tool that mutates state, sends anything, or spends money. | Internal architecture |
| P0 | M | Sanitised Render Surface | AI and feed output rendered as allow-listed markdown -> HTML inside a WebView2 with CSP default-src 'none'; img-src 'self' data:; script-src 'none'; no remote images, no iframes, no host objects bound on any content-bearing WebView; NavigationStarting blocks all navigation; RemoveHostObjectFromScript on ContentLoading. | WebView2 |
| P0 | M | Prompt Redaction Gate | Pre-flight pass over every hosted-LLM prompt: strips API keys, tokens, file paths, email, machine name; optionally pseudonymises tickers; shows a diff-style 'this is what will leave your machine' preview on first use per feature and a persistent byte counter thereafter. | Internal; Anthropic API |
| P0 | M | Provenance Badges and Citation Enforcement | Every AI-stated fact carries a click-through to the exact source document, filing accession number, page and timestamp. Uncited assertions are rendered in a visually degraded 'unsourced' style. A 'show me the filing' action opens the primary document. | EDGAR accession numbers, RNS IDs, vendor record IDs |
| P1 | M | Signed Knowledge Base with Rollback Protection | The Claude-authored knowledge base ships as a signed, versioned bundle with a monotonic counter; the app verifies signature and refuses downgrades. Diff view of what changed since last update; a 'freeze KB' switch for a research session. | Internal build pipeline / Azure Artifact Signing |
| P0 | M | Licence & Entitlement Ledger | Per-source record of the licence under which each datum was obtained (vendor, tier, personal/non-professional, permitted uses, retention limit, redistribution prohibited y/n). Every chart, export and AI answer inherits and displays the most restrictive licence of its inputs. | Vendor ToS, exchange policies |
| P1 | S | Export & Screenshot Guard | Exports and copy-to-clipboard of licensed data are gated by the Licence Ledger; blocked exports explain which term forbids it. Optional watermarking of exported images with 'personal use — not for redistribution' and a timestamp. | Licence Ledger |
| P1 | S | Non-Professional Status Assistant | A guided self-assessment implementing the exchange Nonprofessional Subscriber tests (SEC/CFTC/state/exchange registration; investment adviser under s.202(a)(11) registered or not; employment by an exempt bank/organisation; use for a business or on behalf of an entity), with a dated attestation record and a re-prompt when the user's circumstances change. | NYSE/CTA/UTP nonprofessional policies |
| P0 | M | Not-Advice Framing Engine | The AI layer is constrained by output schema, not by disclaimer: it may produce evidence, base rates, disclosure timelines, incentive maps and framed questions; it may not produce a rating, a target price, a position size, or a substantiated opinion on future value. A single global 'personalisation off' guarantee keeps output impersonal. | Internal |
| P2 | M | MAR Article 20 Disclosure Wrapper (dormant, ships disabled) | If a recommendation-shaped output or an export/share feature is ever enabled, the output is automatically wrapped with the Delegated Reg (EU) 2016/958 elements: producer identity, date/time of production and dissemination, sources, methodology, meaning of the recommendation, time horizon, and disclosure of holdings/interests in the instrument. | Delegated Reg (EU) 2016/958; user position data |
| P1 | S | AI Transparency Marking (EU AI Act Art. 50) | Persistent 'AI-generated' affordance on every model-produced surface plus machine-readable marking (metadata/provenance tag) on AI-generated text exports, satisfying the Art.50 obligations that became enforceable 2 Aug 2026. | Regulation (EU) 2024/1689 |
| P0 | S | Rate-Limit & ToS Governor | Per-source politeness engine: EDGAR capped at <=10 req/s with the required 'Name AdminContact@domain' User-Agent, exponential backoff on 403/429 with the ~10-minute EDGAR block modelled explicitly; per-vendor quotas from the Licence Ledger; a hard refusal to add any source whose ToS prohibits automated access. | SEC EDGAR fair access policy; vendor ToS |
| P0 | M | Public-Filing-Only Provenance Lock for the Insiders pillar | Hard architectural rule enforced at the source-registration layer: every incentives/insiders datum must carry a public filing identifier and a filing timestamp (Form 4, 13D/13G, 13F, DEF 14A, PDMR/MAR Art.19 RNS, FINRA short interest). Sources without one cannot be registered. Any alt-data source proposal is routed to a blocked list with the App Annie rationale shown. | EDGAR, RNS, FINRA |
| P1 | S | Filing Clock | Surfaces the statutory disclosure lag on every insider datapoint: 13D 5 business days (amendments 2), 13G 45 days after quarter end for QIIs/exempt or 5 business days for passive, 13F 45 days after quarter end, Form 4 2 business days. Shows 'as reported' vs 'as of' and the maximum staleness of any position shown. | SEC rules; EDGAR filing timestamps |
| P1 | L | Local-First Mode / Air-Gapped Research | A switch that disables all hosted-model calls and all telemetry, running the AI layer against a local model over the cached corpus only. Clearly indicated in the chrome. Telemetry ships off by default and is opt-in per category. | Local model runtime |
| P1 | M | Panic Lock & Selective Purge | One-key vault lock; scheduled retention purge driven by the Licence Ledger's per-source retention limits; 'forget this symbol' that removes it from cache, logs, recent items and prompt history; cryptographic erase by destroying the CNG-held wrapping key. | Internal |
| P1 | M | Supply Chain Attestation Panel | In-app 'About > Integrity' page showing the release's Authenticode signature status, SHA-256, the CycloneDX 1.7 SBOM, the pinned NuGet lockfile hash, and the date of the last vulnerability scan; a one-click verify of the running binaries against the signed manifest. | Build pipeline; Azure Artifact Signing; CycloneDX |
| P2 | L | Plugin/MCP Confinement (only if extensibility ships) | Third-party MCP servers and plugins run out-of-process with no vault access, no filesystem, no network by default; server allow-list; tool-definition hash pinning with re-consent on change (rug-pull defence); all tool-returned content treated as untrusted and routed through the Untrusted Content Firewall. | MCP ecosystem |
| P0 | S | Secure Logging & Crash Policy | Structured logging with an explicit allow-list of loggable fields; keys, tokens, prompt text, quote payloads and symbols never logged; crash dumps opt-in and heap-stripped; log files inside the ACL-restricted data directory with automatic rotation and age-based deletion. | Internal |

## Risks

- The dominant realistic compromise is a commodity infostealer running as the user (LummaC2/StealC/Vidar/ACRStealer class), not a targeted attack. Any control that does not survive same-user code execution — DPAPI, Credential Manager, SecureString, whole-DB encryption with a local key, BitLocker, EFS — is documentation, not defence.
- Trojanised installer via malvertising: Bitdefender documented 75+ malicious 'TradingView Premium' Meta ads from 22 Jul 2025 across 500+ domains, expanding to Google Ads/YouTube and to macOS/Android, delivering JSCEAL/WeevilProxy. A user who searches for this terminal by name could install someone else's build.
- Indirect prompt injection from an issuer's own filing. A company under short attack has a rational incentive to plant instructions in an 8-K/RNS free-text field that manipulate widely-used AI terminals. This is an economically motivated attack, not a lab curiosity.
- Watchlist exfiltration via mundane channels: prompts to a hosted model, TLS SNI and DNS on per-symbol vendor endpoints, window titles, crash dumps, log files, unencrypted cache. The alpha leaks before the API key does.
- Market data licensing is the single largest legal exposure. Adding a second user, trading through a personal company, or being treated as an 'investment adviser' by activity can flip the subscriber to Professional retroactively. Exchanges and vendors audit, and retail vendor terms (e.g. Polygon/Massive: 'personal, non-commercial, and non-business purposes', one App Licence) are unambiguous.
- Non-Display Use ambiguity: alerting engines, screeners, backtests and AI-derived numbers computed from licensed feeds may be characterised as Non-Display Use, which exchanges license and price separately even for a single user. Unresolved and vendor-specific.
- EU AI Act Article 50 became enforceable on 2 Aug 2026 — three weeks before today. Any EU availability without AI-interaction disclosure and machine-readable marking of AI-generated text is already non-compliant (marking has a grace period to 2 Dec 2026 only for systems already on the market before 2 Aug 2026).
- Publishing anything — screenshots on X, a Substack, a Discord — moves the output from private tool to communication. In the UK that engages s.21 FSMA if made in the course of business (PERG 8.5: requires a commercial interest); the FCA is actively prosecuting finfluencers under s.21 and seeking to raise the maximum sentence from 2 to 5 years.
- An AI panel that emits a rating or a target price is functionally an investment recommendation under MAR Art.20 / Delegated Reg (EU) 2016/958, with mandatory objective-presentation and conflicts-disclosure obligations — obligations that attach to unauthorised producers too, if the recommendation is disseminated.
- Feature drift into alt data (expert networks, credit-card panels, geolocation, app-telemetry panels) carries both MNPI and privacy exposure. SEC v. App Annie (14 Sep 2021, >US$10m total, first alt-data enforcement) shows the SEC will charge the data provider directly under 10(b)/10b-5 for how the data was derived and controlled.
- Supply chain: npm self-propagating worms (Shai-Hulud, Sep 2025; 2.0 from Nov 2025 with ~25,000 malicious repos across ~350 users) and NuGet dependency confusion. Without Package Source Mapping, lockfiles and audit gates, a build-time compromise reaches the trader's machine with your signature on it.
- Certificate pinning done naively causes outages on vendor CA rotation and hard-fails behind the corporate TLS-inspection proxies common in this user's environment — an availability risk masquerading as a security control.
- Anthropic's default commercial API retention is 30 days with named exceptions (up to 2 years for Usage Policy violations, 5 years for feedback submissions). Not zero. Any prompt carrying the thesis is a third-party-held asset for that window unless a ZDR agreement is in place.
- VBS/TPM key protection requires Windows 11-class hardware (64-bit, hypervisor, IOMMU, TPM 2.0/vTPM). A silent downgrade to DPAPI on unsupported machines would give false assurance; the capability tier must be visible.
- Corporate/domain-joined deployment adds DPAPI domain-backup-key exposure (the per-domain RSA backup key cannot be rotated with built-in tools and decrypts any domain user's DPAPI data), plus Credential Roaming widening blast radius across machines.
- Regulatory posture drift over time: the FCA has signalled further consultation on perimeter guidance after PS25/22 (targeted support, in force 6 Apr 2026), and CISA's SBOM minimum elements were updated 29 Jul 2026. Compliance assumptions need a scheduled re-review, not a one-off assessment.

## Open questions

- Exact 2026 per-exchange non-professional display fees for the target venues (NYSE/CTA Tape A-B, Nasdaq/UTP Tape C, LSE, Xetra, TSE) were not verified in this pass — the web search budget was exhausted before the fee schedules could be read. These are published in the NYSE Proprietary Market Data Pricing Guide (14 May 2026 edition) and the CTA/UTP Schedule of Market Data Charges and must be confirmed before any cost model.
- Whether each chosen vendor treats an in-app alert engine, screener, backtest, or AI-computed derived value as Display Use or Non-Display Use. This is contract-specific, materially affects cost, and should be resolved in writing with each vendor before build.
- FX specifically: there is no consolidated tape and no exchange licensing analogue for spot FX, so the licence terms come entirely from the vendor (LSEG/Refinitiv, EBS, OANDA, Polygon/Massive, Databento). The exact redistribution and caching terms of the chosen FX source were not examined here.
- Whether the user trades personally or through a company/LLC/partnership. This single fact determines non-professional vs professional subscriber status across every US exchange and is the largest single cost variable in the whole project.
- The conflicting Anthropic API retention figure: official documentation says inputs/outputs deleted within 30 days; a secondary source claims log retention dropped to 7 days on 2025-09-14. Needs confirmation directly with Anthropic, along with whether a Zero Data Retention agreement is available at this account's scale.
- Whether .NET will expose managed APIs for NCRYPT_REQUIRE_VBS_FLAG / NCRYPT_PREFER_VBS_FLAG, or whether P/Invoke to ncrypt.dll remains the only path (dotnet/runtime issue #102492 is an open proposal, status not confirmed as of this research).
- Precise minimum Windows build and hardware matrix for VBS key protection availability, and what proportion of plausible target machines will fall back to TPM-only or DPAPI-only.
- Whether an AppContainer-hosted helper process for Windows Hello KeyCredential operations is practical alongside a full-trust WPF/WinUI host, or whether the cryptographic siloing benefit is unobtainable without a full MSIX AppContainer app.
- Whether the app will ever be published to the Microsoft Store or shared with a second person. Every material legal conclusion in this research flips at that boundary — market data redistribution, s.21 FSMA, MAR Art.20, EU AI Act Art.50, UK GDPR controller status.
- Form 4 filing deadline (Section 16(a): two business days after the transaction) was not independently re-verified in this pass and should be confirmed against 17 CFR 240.16a-3 before it is displayed as an authoritative timeline in the Filing Clock feature.
- Whether any planned data source's terms prohibit the specific act of feeding its content to a third-party LLM. Several news and filings vendors have added AI/model-training and machine-processing restrictions since 2024; each ToS needs an explicit check for an AI clause.
- Whether the EULA should be a bespoke instrument or an adapted standard form, and which jurisdiction/governing law to specify. Limitation-of-liability drafting for a financial information tool sold to consumers is jurisdiction-sensitive (UK CRA 2015 fairness rules constrain what can be excluded) and warrants actual legal review rather than a template.
- Whether any planned data provider uses OAuth or device-code flows rather than static API keys, which would change the vault design (refresh-token custody, revocation semantics) — not enumerated in this pass.
