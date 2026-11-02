# Feature Traceability Matrix (F1–F30)

Paths are relative to `frontend/src/` (FE) and `backend/app/` (BE); tests are in `backend/tests/` (BT) or `frontend/src/__tests__/` (FT).
"Acceptance" refers to AC/Scenario IDs in spec §10 and edge-case IDs (E#) in spec §8.

> **Implementation note — actual file names (supersede planned names in the tables below).**
> | Planned | Actual |
> |---|---|
> | `context/SelectionContext.jsx`, `ProfileContext.jsx`, `LanguageContext.jsx` | single `context/AppContext.jsx` |
> | `components/RuleDetail.jsx`, `TriggerTimeline.jsx` | exported from `components/RiskPanel.jsx` |
> | `components/DataQuality.jsx` | `QualityRow` in `components/SourcesPanel.jsx` |
> | `components/LanguageSwitch.jsx` | language `<select>` in `layouts/AppLayout.jsx` |
> | `charts/HistoryCharts.jsx` | charts inline in `pages/HistoryPage.jsx` |
> | `engine/explainability.py` timeline | same file; `core/modules.py` is the module registry |
> | BT `test_location.py`, `test_weather.py` | `tests/test_weather_location.py` |
> | BT `test_crop_config.py`, `test_risk_engine.py`, `test_rules_loader.py` | `tests/test_engine.py` |
> | BT `test_knowledge.py`, `test_advisory.py`, `test_assistant.py` | `tests/test_knowledge_ai.py` |
> | BT `test_api.py`, `test_i18n.py`, `test_history.py`, `test_profile.py`, `test_imd.py`, `test_monitoring.py`, `test_report.py`, `test_integrations.py` | `tests/test_api_l2.py` |
> | BT `test_image/notifications/market/satellite/voice/regional.py` | `tests/test_level3.py` |
> | FT `selection.test.js`, `translations.test.js` | `src/__tests__/components.test.jsx`, `translations.test.js` |
> `scripts/verify_providers.py` and `scripts/ingest_knowledge.py` live in `backend/scripts/`.

## Level 1 — Core MVP

| ID | Feature | Frontend | Backend service | API | Data source | Tests | Acceptance |
|---|---|---|---|---|---|---|---|
| F1 | Location selection & geolocation | `components/SelectionPanel.jsx`, `hooks/useGeolocation.js`, `context/SelectionContext.jsx` | `services/location_service.py` | `GET /api/locations/search` | Open-Meteo Geocoding API (filtered to India/Andhra Pradesh) + `data/regions/andhra_pradesh.json` (district names only, no coordinates) | BT `test_location.py` (validation, AP filter, unresolved→E3), FT `selection.test.js` | AC3, E1–E4 |
| F2 | Live weather intelligence | `components/WeatherOverview.jsx`, `components/DataQuality.jsx` | `services/weather_service.py` (+ `utils/units.py`) | `GET /api/weather/current` | Open-Meteo Forecast API | BT `test_weather.py` (normalization, missing≠0, partial) | AC4, AC6, E5–E7 |
| F3 | Forecast dashboard | `components/ForecastCharts.jsx` (Recharts), `pages/DashboardPage.jsx`, `pages/WeatherPage.jsx` | `services/weather_service.py` | `GET /api/weather/forecast?days=7` | Open-Meteo Forecast API | BT `test_weather.py` (hourly/daily shape, timestamps) | AC5 |
| F4 | Official warnings (IMD) | `components/WarningsPanel.jsx` | `services/imd_service.py` (CAP 1.2 parser; feed URL configurable) | `GET /api/warnings` | IMD — **access not verified** (see `external-verification.md`); renders `unavailable` + official links when not configured | BT `test_imd.py` (CAP fixture parse, unavailable path, no fabrication) | AC16, AC17, E12 |
| F5 | Crop & growth-stage selection | `components/SelectionPanel.jsx` | `services/crop_config_service.py`, `data/crop_configs/*.json` | `GET /api/crops` | Crop config JSON (stage catalogue `needs_review`) | BT `test_crop_config.py` | AC7, E8, E9 |
| F6 | Deterministic risk engine | `components/RiskPanel.jsx`, `pages/CropRiskPage.jsx` | `engine/risk_engine.py`, `engine/rule_loader.py`, `data/risk_rules/*.json` | `POST /api/risk/assess` | Five configured rules; **zero enabled** pending source/input window alignment and agronomic review; no validated crop-stage rules | BT `test_engine.py` (disabled rules, coverage, stale/partial data) | AC8–AC10, E10, E11, Scenario 2 |
| F7 | AI advisory assistant | `components/AdvisoryPanel.jsx`, `pages/AdvisorPage.jsx` | `ai/advisory_generator.py`, `ai/llm_provider.py`, `ai/prompt_templates.py`, `ai/fallback.py` | `POST /api/advisory/generate` | LLM provider (adapter) + verified, matching agricultural evidence; no crop actions when absent | BT `test_knowledge_ai.py` (fallback, retry, no risk override/actions without evidence) | AC11, AC12, E14, E15, Scenario 5 |
| F8 | Evidence & attribution | `components/EvidenceList.jsx`, `components/SourcesPanel.jsx` | `services/knowledge_service.py`, `ai/output_validator.py`, additive knowledge metadata migration | evidence in `risk/assess` + `advisory/generate` | `knowledge/metadata/seed_documents.json` and `evidence_registry.json`; source access, expert review, geography, season, source/input windows and limitations are distinct | BT `test_knowledge_ai.py`, `test_evidence_registry.py`, `test_advisory.py::evidence_ids` | AC13, E13, E16, Scenario 4 |
| F9 | English + Telugu | `translations/en.js`, `translations/te.js`, `context/LanguageContext.jsx`, `components/LanguageSwitch.jsx` | `core/i18n.py` (backend message dictionaries) | `language` param on risk/advisory/chat | Translation dictionaries (Telugu **needs native/agri review**) | BT `test_i18n.py` (key parity, number/URL preservation, E29), FT `translations.test.js` (key parity) | AC14, E17, E29, Scenario 6 |
| F10 | Explainable risk dashboard | `components/RiskPanel.jsx`, `components/RuleDetail.jsx`, `pages/DashboardPage.jsx` | `engine/explainability.py` | `POST /api/risk/assess` | engine output | BT `test_risk_engine.py::explainability` | AC15, AC18 |

## Level 2 — Important extensions

| ID | Feature | Frontend | Backend service | API | Data source | Tests | Acceptance |
|---|---|---|---|---|---|---|---|
| F11 | Historical weather analysis | `pages/HistoryPage.jsx`, `charts/HistoryCharts.jsx` | `services/history_service.py` | `GET /api/history` | Open-Meteo Historical (ERA5 reanalysis) API — labelled *reanalysis*, not observation | BT `test_history.py` (coverage, baseline rules, E18) | AC19, AC20 |
| F12 | Risk-trigger timeline | `components/TriggerTimeline.jsx` | `engine/explainability.py` (timeline builder) | `risk/assess` → `timeline[]` | engine output | BT `test_risk_engine.py::timeline` | AC15 |
| F13 | Farmer profile (opt-in) | `pages/SettingsPage.jsx`, `context/ProfileContext.jsx` | `services/profile_service.py`, `models/tables.py` | `POST/GET/DELETE /api/profile` | SQLite/Postgres | BT `test_profile.py` (opt-in, delete, no PII required) | AC22 |
| F14 | Conversational Q&A | `components/ChatBox.jsx`, `pages/AdvisorPage.jsx` | `ai/advisory_generator.py::answer_question`, `services/knowledge_service.py` | `POST /api/assistant/chat` | LLM + knowledge base; out-of-knowledge refusal | BT `test_assistant.py` (grounding, out-of-scope, no LLM) | AC23 |
| F15 | Knowledge retrieval | `pages/KnowledgePage.jsx` | `services/knowledge_service.py`, `scripts/ingest_knowledge.py` | `GET /api/knowledge/search`, `GET /api/knowledge/documents`, `GET /api/knowledge/evidence-registry` | Source-applicability filters; explicit `insufficient_evidence` rows; per-rule records in `knowledge/metadata/rule_validation_records.json`; all unvalidated rules disabled | BT `test_knowledge.py`, `test_evidence_registry.py` (provenance, state/district/season/concern filters, coverage gaps, disabled-rule parity) | AC21 |
| F16 | Regional crop calendar | `pages/CalendarPage.jsx` | `services/crop_config_service.py` | `GET /api/crops/{id}/calendar` | Stage catalogue only; **calendar dates unavailable until a verified AP calendar is supplied** | BT `test_crop_config.py::calendar_unavailable` | — |
| F17 | District coverage | `components/SelectionPanel.jsx` (district picker) | `services/location_service.py`, `data/regions/*.json` | `GET /api/regions` | district name list (geocoded live) | BT `test_location.py::districts` | — |
| F18 | Monitoring & reliability | `pages/DataStatusPage.jsx`, `components/DataQuality.jsx` | `core/monitoring.py` (provider health ledger), `services/weather_service.py`, `services/imd_service.py` | `GET /api/health`, `GET /api/monitoring/status` | internal ledger | BT `test_monitoring.py` | AC1, AC2, E30 |

## Level 3 — Advanced (kept in architecture; each is a separate module)

| ID | Feature | Frontend | Backend service | API | Data source | Tests | Acceptance | Build status |
|---|---|---|---|---|---|---|---|---|
| F19 | Mandi prices | `pages/MarketPage.jsx` | `services/market_service.py` | `GET /api/market/prices` | data.gov.in Agmarknet resource (API key + resource ID required) | BT `test_market.py` (normalisation, unit check, no-key→unavailable) | AC24, AC25, E19 | NEEDS-CONFIG, IMPLEMENTED-UNVERIFIED |
| F20 | Crop-image analysis | `pages/CropHealthPage.jsx` | `services/image_service.py` (validation) + `ai/llm_provider.py` vision | `POST /api/crop-health/analyze` | Vision-capable LLM (key required) | BT `test_image.py` (magic bytes, 413, 415, uncertain label) | AC26–AC28, E20–E22 | Validation IMPLEMENTED; analysis NEEDS-CONFIG |
| F21 | Notifications | `pages/NotificationsPage.jsx`, header bell | `services/notification_service.py` | `GET /api/notifications`, `POST /api/notifications/preferences` | subscriptions + risk/warning events | BT `test_notifications.py` (consent, dedupe, quiet hours) | AC29, AC30, E23, E24 | In-app IMPLEMENTED; email/SMS PLANNED |
| F22 | Satellite NDVI | `pages/SatellitePage.jsx` | `services/satellite_service.py` | `GET /api/satellite/indicators` | NASA MODIS subset via ORNL DAAC (**unverified**) | BT `test_satellite.py` | AC31, E25 | IMPLEMENTED-UNVERIFIED |
| F23 | Voice assistant | `pages/VoicePage.jsx`, `hooks/useSpeech.js` (Web Speech API STT/TTS) | `services/voice_service.py` | `POST /api/voice/transcribe` | Browser speech APIs; server STT only if configured | BT `test_voice.py` | AC32, E26 | Browser path IMPLEMENTED; server STT NEEDS-CONFIG |
| F24 | Multi-language/region | `translations/` registry | `core/i18n.py`, `data/regions/`, `data/crop_configs/` | `GET /api/meta/languages` | config registries | BT `test_i18n.py::registry` | — | Architecture IMPLEMENTED; Hindi/Tamil/etc. PLANNED |
| F25 | Advanced climate | `pages/HistoryPage.jsx` (seasonal tab) | `services/history_service.py` (baseline deviation) | `GET /api/history/seasonal` | Open-Meteo Historical | BT `test_history.py::baseline` | — | PARTIAL (rainfall deviation only; no SPI/maps) |
| F26 | Regional risk map | `pages/RegionalPage.jsx` (react-leaflet markers) | `services/regional_service.py` | `GET /api/regional/risk` | Open-Meteo multi-location + engine | BT `test_regional.py` | AC34 | IMPLEMENTED-UNVERIFIED (district markers only) |
| F27 | Report generation | `pages/ReportsPage.jsx` | `services/report_service.py` | `POST /api/reports/generate` | stored assessment | BT `test_report.py` | AC33 | IMPLEMENTED (HTML; print-to-PDF) |
| F28 | Personalised recs | `components/AdvisoryPanel.jsx` (context note) | `ai/advisory_generator.py` (profile + history context) | `advisory/generate` (`profile_id`) | profile + audit history | BT `test_advisory.py::personalised` | — | PARTIAL |
| F29 | Regional dashboard | `pages/AdminPage.jsx` | `services/regional_service.py` | `GET /api/admin/regional-summary` (token) | aggregated engine output | BT `test_regional.py::admin_auth` | 401/403 | PARTIAL |
| F30 | Future integrations | — | `services/integrations/base.py` | — | — | BT `test_integrations.py` (contract + quality check) | — | Interface IMPLEMENTED; no adapters |

## Cross-cutting

| Concern | Where | Tests |
|---|---|---|
| Error envelope / HTTP codes | `core/errors.py` | `test_api.py` |
| Rate limiting / size limit | `core/middleware.py` | `test_api.py` |
| Log redaction | `core/logging.py` | `test_api.py::redaction` |
| Prompt-injection defence | `ai/prompt_templates.py`, `ai/output_validator.py` | `test_advisory.py::injection` |
| Test-data policy (synthetic ≠ live) | fixtures only under `backend/tests/fixtures/` | static check in `test_api.py::no_fixture_import_in_app` |
