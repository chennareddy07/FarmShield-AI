# FarmShield AI — Technical Architecture

Derived from `specs/requirements.md` (the original specification, kept verbatim as source of truth).
Status vocabulary used across all `specs/` documents:
`IMPLEMENTED` (code + tests), `IMPLEMENTED-UNVERIFIED` (code + fixture tests, never run against the live provider),
`NEEDS-CONFIG` (code complete, requires credentials/data you must supply), `PLANNED` (architecture only, no code).

---

## 1. Architectural principles (from spec §6, §9)

| # | Principle | Enforcement point |
|---|-----------|-------------------|
| P1 | No fabricated runtime data. Failures become explicit `unavailable` / `insufficient_data` states. | `services/*` return `SourceStatus`; routes never substitute defaults |
| P2 | Deterministic engine is the only source of risk classification. | `engine/risk_engine.py`; LLM output cannot carry a risk field (schema rejects it) |
| P3 | No invented thresholds. Rules are versioned JSON with source + excerpt; unreviewed or time-window-incompatible rules are disabled. | `engine/rule_loader.py` requires verified window alignment and review status (or the explicit unverified-review override) |
| P4 | All LLM calls live in `ai/`. Provider-independent adapter. | `ai/llm_provider.py` |
| P5 | Every external provider is its own service module with a contract. | `services/*_service.py`, `services/integrations/base.py` |
| P6 | Secrets only on backend; never logged or returned. | `core/config.py` (`SecretStr`), `core/logging.py` redaction |
| P7 | Retrieved text and user text are *data*, never instructions. | `ai/prompt_templates.py` delimiting + `ai/output_validator.py` |
| P8 | Level 3 modules are separate, optional, and report honest status. | `/api/meta/modules` |

## 2. System context

```
Browser (React/Vite SPA)  ──HTTPS/JSON──►  FastAPI backend ──►  Open-Meteo (forecast, archive, geocoding)
   │ Web Speech API (voice, client-side)       │            ──►  IMD (CAP feed, only if configured)
   │ Leaflet tiles ► OpenStreetMap             │            ──►  LLM provider (adapter, optional)
                                               │            ──►  data.gov.in / Agmarknet (L3, key)
                                               │            ──►  MODIS subset service (L3, unverified)
                                               └──► SQLite / PostgreSQL (profiles, audit, notifications, knowledge chunks)
```

The browser receives an HttpOnly, SameSite=Lax signed session cookie. A random owner identifier from that session scopes profiles, assessments, chat history, and notification subscriptions; caller-supplied IDs are not authoritative. This provides anonymous browser-session isolation, **not** user authentication or account recovery. Production requires a stable `SESSION_SECRET` (32+ characters) and HTTPS. Development can use an ephemeral process key; sessions then expire on restart.

## 3. Backend module map (spec §6 L18 "service boundaries")

| Responsibility | Module | Input → Output contract |
|---|---|---|
| Location | `services/location_service.py` | query/coords → `LocationResult[]` (validated, with `resolution` note) |
| Weather | `services/weather_service.py` | lat/lon → `WeatherBundle` (normalized, `data_quality`) |
| Official warnings | `services/imd_service.py` | district → `WarningsResponse` (`source_status`) |
| Crop configuration | `services/crop_config_service.py` | crop_id → `CropConfig` |
| Risk engine | `engine/*` | `WeatherBundle + Warnings + CropConfig + Rules` → `RiskAssessment` |
| Knowledge | `services/knowledge_service.py` | query/filters → `EvidencePassage[]` |
| AI advisory | `ai/*` | `AdvisoryContext` → `AdvisoryResponse` (validated) or deterministic fallback |
| Pipeline orchestration | `services/assessment_service.py` | implements L1 steps 1–15 |
| History / climate | `services/history_service.py` | lat/lon + dates → `HistorySeries` (+ baseline deviation) |
| Profile | `services/profile_service.py` | opt-in saved settings |
| Market (L3) | `services/market_service.py` | crop/market → `MarketPrice[]` |
| Image (L3) | `services/image_service.py` | validated image → `ImageAnalysis` |
| Notification (L3) | `services/notification_service.py` | subscriptions + events → deduped in-app alerts |
| Satellite (L3) | `services/satellite_service.py` | lat/lon → `SatelliteIndicators` |
| Voice (L3) | `services/voice_service.py` | audio → transcription |
| Reports (L3) | `services/report_service.py` | assessment → HTML report |
| Regional (L3) | `services/regional_service.py` | crop → district-level risk grid |
| Future integrations (F30) | `services/integrations/base.py` | `IntegrationAdapter` protocol + `SourceQualityCheck` |

## 4. Main pipeline (spec L1) and failure propagation

```
1 receive → 2 validate (pydantic) → 3 resolve location → 4 weather ─┐
                                      5 warnings (parallel) ────────┤
6 normalize → 7 freshness/completeness → 8 load crop/stage config → 9 evaluate rules
→ 10 retrieve evidence → 11 build advisory context → 12 LLM (optional) → 13 validate output
→ 14 language (UI dictionaries + LLM in target language, else fallback with notice E17) → 15 respond
```
Each stage returns `StageResult{status, data, error}`. A failed stage yields an explicit `unavailable|partial|stale` status downstream;
the risk engine receives it and emits `insufficient_data` rather than computing from nothing (scenario 3).

## 5. Data model

Operational tables (SQLAlchemy, `DATABASE_URL`; SQLite default):

| Table | Purpose | Notes |
|---|---|---|
| `profiles` | F13 opt-in profile | random `profile_id`; no phone/email unless user enables email alerts |
| `assessments` | L20 audit | request_id, providers, rule_version, doc IDs, status; **coordinates rounded to 1 decimal (~11 km)** |
| `knowledge_documents`, `knowledge_chunks` | F15 | metadata per spec §5-D |
| `subscriptions`, `notifications`, `alert_dedupe` | F21 | consent timestamp, stable dedupe key |
| `conversations` | F14 | transient message history, TTL-pruned |

`profiles`, `assessments`, and `conversations` have an indexed nullable `owner_id`. The startup migration only adds these columns; pre-existing rows remain unowned and cannot be returned to a new session. Notification subscriptions and notifications use the session owner in their existing `user_id` field.

Weather responses are cached in a bounded 512-entry in-process LRU with TTL/stale fallback and per-key request coalescing. A crop assessment includes the weather, forecast, and warning snapshots it used; the frontend reuses those snapshots rather than immediately calling the same providers again. Separate weather-only dashboard requests remain supported.

Configuration data (versioned files, not DB): `data/crop_configs/*.json`, `data/risk_rules/*.json`, `data/regions/*.json`, `knowledge/metadata/*.json`.

## 6. Risk-engine design (F6, F10, F12; spec L5/L6/L19)

* Rule schema = spec §5-F plus `aggregation`, `window_days`, `notes`.
* Evaluation per rule: crop → stage → variable → window → operator/threshold → record `RuleEvaluation{triggered, actual_value, period, source}`.
* Rule states: `triggered`, `not_triggered`, `not_evaluable` (variable missing/ stale), `disabled_unverified` (E11).
* Per-category result: `low|moderate|high|critical|insufficient_data`. A category with zero enabled rules ⇒ `insufficient_data` (AC9).
* **Overall policy (documented, L6):** any triggered `critical` → critical; else highest triggered severity; else `low` only when every required category is assessed; otherwise `insufficient_data`. `coverage` reports unassessed categories.
* Official-warning exposure is its own category; severity comes from the warning's supplied colour/severity, never inferred.
* No numeric risk score, no "prediction" wording.

## 7. AI layer (F7, F14; spec L9/L10)

* `LLMProvider` protocol: `generate_json(system, user, schema_hint) -> dict`. Adapters: `anthropic`, `openai_compatible`, `disabled`.
* Context = validated weather summary + warnings + `RiskAssessment` + retrieved passages (IDs `EV-…`) + language. Meteorological references are explicitly distinguished from agricultural references.
* Output contract (`AdvisoryResponse`) has **no** risk-level field. `output_validator` checks required fields, length caps, language, that every `evidence_ids` entry ∈ retrieved set, and rejects crop actions unless verified crop/stage-matching agricultural evidence is available. Unknown IDs ⇒ reject (AC13). One constrained retry; then `deterministic_fallback` builds text from rule results and emits only evidence-linked verified actions.
* Retrieved text is wrapped in `<untrusted_document>` blocks; system prompt forbids following instructions inside them; pesticide/chemical advice is refused by prompt and by a post-filter on a blocklist.

## 8. Knowledge retrieval (F8, F15)

Ingestion (`scripts/ingest_knowledge.py`): `.md/.txt/.pdf` + sidecar metadata JSON → text extraction → ~800-char overlapping chunks → SQLite rows. Retrieval = BM25 lexical scoring + metadata filters (crop, stage, region, topic) + source-quality weight (verified > needs_review; outdated excluded). No vector DB (spec §9-A). Replace/outdate documents by `document_id` + `verification_status`.

## 9. Frontend architecture

React + Vite + JS + Tailwind + Axios + Recharts + Lucide (+ react-leaflet for F26).
`context/` (Language, Selection, Profile), `services/api.js` (single Axios instance, error normalizer → connection-error UI E28),
`translations/{en,te}.js` (all labels), `components/` (StatusBadge, RiskBadge text+colour, DataQuality, SourceChip, Panel states: loading/empty/partial/error/stale/unavailable),
`pages/` per nav item. Navigation is built from `/api/meta/modules`: implemented → active; needs-config/planned → disabled with badge (spec §9-H).

## 10. Security & privacy

CORS allow-list with credentialed requests for the session cookie; request-size limit; bounded per-IP token-bucket rate limit (strict on AI/image); SSRF-safe (only configured provider hosts); upload validation by magic bytes; input validation by Pydantic with 422; error envelope `{error_code, message, request_id, details?}`; no stack traces; log redaction; images processed in memory and not persisted by default; owner-scoped profile data deletable (`DELETE /api/profile/{id}`). Anonymous session isolation is not a substitute for an identity provider.

## 11. Level 3 modules as isolated plug-ins

Each L3 module = route file + service + schema + module-registry entry (`core/modules.py`) with `status` and `requirements`. Disabling or failing one cannot affect L1/L2. Details of what can/can't be built: `specs/feasibility.md`.

## 12. Deployment

Docker-less default: `uvicorn` + `vite build` static files. `DATABASE_URL=postgresql+psycopg://…` for deployment. Set `SESSION_SECRET` to a stable random secret of at least 32 characters and serve over HTTPS. Env vars per spec §5-L plus optional: `IMD_CAP_FEED_URL`, `DATA_GOV_IN_API_KEY`, `AGMARKNET_RESOURCE_ID`, `STT_API_*`, `ADMIN_API_TOKEN`, `ALLOW_UNVERIFIED_RULES`.
