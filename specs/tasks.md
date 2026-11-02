# Phased Implementation Checklist (task 3)

Final statuses are recorded in the chat summary and in `README.md#status`. `[x]` = done in this repo, `[~]` = partially done / needs your review, `[ ]` = not done.

## Phase 0 — Pre-implementation (spec asked for these first)
- [x] Spec read in full (10 sections, F1–F30, AC1–AC34, E1–E30)
- [x] `specs/architecture.md`
- [x] `specs/traceability-matrix.md`
- [x] `specs/tasks.md` (this file)
- [x] `specs/dependencies.md`
- [x] `specs/external-verification.md`
- [x] `specs/agri-research.md`
- [x] `specs/feasibility.md`

## Phase 1 — Level 1 (mandatory MVP) F1–F10
- [x] Core: config (env), error envelope, request-ID, CORS, rate limit, size limit, log redaction, DB
- [x] F1 location search / geolocation / resolution note  *(live geocoder unverified)*
- [x] F2/F3 Open-Meteo normalisation, freshness, partial detection, stale-cache fallback  *(live API unverified)*
- [~] F4 IMD adapter (CAP parser + honest `not_configured`/`unavailable`)  *(no verified IMD feed exists to connect)*
- [x] F5 crop/stage config + API  *(stage catalogue needs agronomist review)*
- [x] F6 rule loader + deterministic engine + aggregation  *(all five configured rules disabled pending measurement-window compatibility and agricultural review)*
- [x] F7 LLM adapter, prompts, validator, retry, deterministic fallback  *(text endpoint live-tested; intermittent rate limiting; vision unverified)*
- [x] F8 knowledge seed + retrieval + attribution
- [~] F9 EN/TE dictionaries (UI + backend)  *(Telugu needs native/agri review)*
- [x] F10 explainable risk UI
- [x] Frontend shell, nav from module registry, panel states
- [~] Mobile responsiveness  *(Tailwind responsive layout built; never viewed on a device)*
- [x] Automated tests: backend 238 passed, frontend 33 passed; production build passes (large-chunk warning remains)

## Phase 2 — Level 2 F11–F18
- [x] F11 history + coverage + baseline  - [x] F12 timeline  - [x] F13 profile (opt-in, deletable)
- [x] F14 chat (grounded, out-of-scope refusal)  - [x] F15 ingestion script + retrieval UI  - [~] F16 calendar (stages only; dates unavailable)
- [x] F17 district list  - [x] F18 monitoring ledger + status page

## Phase 3 — Level 3 F19–F30 (separate modules, honest status each)
- [~] F19 market (API responds; current scan returned 20 records across 4 states and 14 commodities; no Guntur/groundnut in that response; price units unconfirmed)  - [~] F20 crop health (validation done; analysis needs vision LLM)
- [~] F21 notifications (in-app only; manual "check now", no background scheduler)  - [~] F22 satellite (endpoint live-checked; product QA/interpretation still unverified)
- [~] F23 voice (browser APIs; server STT needs config)  - [ ] F24 multi-region/language (registry-ready, not populated)
- [~] F25 seasonal rainfall deviation only  - [~] F26 district-marker map (unverified live)
- [x] F27 HTML report  - [~] F28 personalisation context only  - [~] F29 aggregated admin dashboard (static token)
- [~] F30 adapter interface only

## Phase 4 — Delivery
- [x] README, `.env.example`, `.gitignore`, `scripts/verify_providers.py`, `scripts/ingest_knowledge.py`
- [x] Packaged as zip
- [x] Live provider verification: Open-Meteo, MODIS, configured LLM text endpoint, and data.gov.in returned usable responses; IMD CAP remains unconfigured
- [ ] Expert review of rules/Telugu and browser/device testing — **yours to do** (see README → Status)

## Batch B — Session ownership and integration reliability
- [x] Replace client-trusted owner IDs with signed anonymous browser-session ownership for profiles, assessments, conversations, and notifications.
- [x] Add an additive migration for owner columns; leave legacy rows unassigned and inaccessible to new sessions.
- [x] Require a stable production `SESSION_SECRET`; document that development's generated key does not survive process restarts.
- [x] Bound weather-cache memory, coalesce same-key requests, isolate returned cached objects, and reuse assessment weather/warning snapshots in the frontend.
- [x] Distinguish invalid, unconfigured, configured-but-untested, operational, and temporarily unavailable LLM states.
- [x] Add regression coverage for ownership, migration, cache limits/concurrency, and frontend provider-call deduplication.
- [~] Anonymous sessions provide browser isolation only; production user identity and account recovery still require an identity provider.
- [x] Verify Open-Meteo forecast/geocoding/history, MODIS, configured LLM text endpoint and data.gov.in live; IMD CAP remains unconfigured.

## Batch E — Agricultural evidence registry and review tooling
- [x] Verify source access and record retrieval/publication details, scope, limitations, and whether a full source document was retained.
- [x] Keep source facts separate from FarmShield interpretation; inaccessible sources remain `source_unverified` and are excluded from assistant grounding.
- [x] Add an additive knowledge-document migration for source status, geographic/season applicability, concerns, and source/input measurement windows.
- [x] Add explicit stage-by-concern `insufficient_evidence` rows and per-rule validation records for all five configured rules.
- [x] Extend knowledge search/list APIs and UI with state, district, season, concern and evidence-status filters; prioritize source status and recency of source verification.
- [x] Add separate paddy and groundnut expert-review records; preserve every unvalidated risk rule as disabled.
- [x] Add backend and frontend regression tests for provenance, filters, coverage gaps, migration, source exclusion and rule-disable invariants.
- [~] Qualified agronomist review, full-text review of the ICAR groundnut study, ANGRAU district/season guidance, current Telugu terminology review, and source reuse/licensing review remain manual.
