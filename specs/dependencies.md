# Feature Dependency Map (task 4)

`A → B` means A must exist (or be stubbed with an honest "unavailable" state) before B can work.

## Session-scoped ownership

Private browser data depends on Starlette `SessionMiddleware` and its `itsdangerous` signing dependency. Production also requires a stable `SESSION_SECRET`; this design isolates anonymous browser sessions but does not authenticate user accounts.

## Foundational chain (Level 1)

```
F1 location ─┬─► F2 weather ─► F3 dashboard
             │        │
             │        └──────────────┐
F5 crop/stage config ─► F6 risk engine ◄─ F4 warnings (optional input; absence ⇒ category insufficient_data)
                            │
        F8 evidence ◄───────┤  (knowledge store F15-lite seed records)
                            ▼
                    F10 explainable dashboard ─► F7 AI advisory ─► F9 language (UI dictionaries are independent; AI text needs F7)
```

| Feature | Hard dependencies | Soft dependencies / degradation |
|---|---|---|
| F1 | Geocoding provider | Browser geolocation optional; manual search is the fallback (E4) |
| F2 | F1 (lat/lon) | — |
| F3 | F2 | Charts need `hourly[]`/`daily[]` |
| F4 | F1 (district name) | Missing ⇒ `source_status=unavailable`; risk category `severe_weather_warning=insufficient_data` |
| F5 | crop config files | Stage catalogue `needs_review` |
| F6 | F2, F5, rule files | F4 optional. Unverified rules ⇒ disabled |
| F7 | F6, F8 | No LLM ⇒ deterministic fallback; no evidence ⇒ explicit "insufficient evidence" |
| F8 | knowledge store | none ⇒ E13 |
| F9 | translation dictionaries | Falls back to English with notice (E17) |
| F10 | F6, F8, F12 | — |
| F11 | F1, historical provider | E18 on outage |
| F12 | F6 | — |
| F13 | DB | Guest mode always works |
| F14 | F7 context, F8 | No LLM ⇒ retrieval-only answer |
| F15 | DB, ingestion script | F8 depends on it |
| F16 | F5 | **Calendar dates need a verified source** (otherwise stage list only) |
| F17 | F1 | — |
| F18 | F2, F4 | feeds `data_quality` everywhere |
| F19 | F1 (district), API key | independent of L1 |
| F20 | F7's LLM adapter (vision), consent UI | independent of L1 |
| F21 | F13 (identity), F6/F4 (events), F18 | requires consent record |
| F22 | F1, satellite provider | independent |
| F23 | F14 pipeline | browser STT/TTS or server STT |
| F24 | F9, F5, rule files (per-region) | thresholds must be re-verified per region |
| F25 | F11 | needs multi-year baseline coverage |
| F26 | F6, F17 | needs per-district weather batch |
| F27 | F6, F7 (optional), F9 | — |
| F28 | F13, F11, F7 | — |
| F29 | F26, F18 | access control |
| F30 | `integrations/base.py` | — |

## Build order used
1. core (config, errors, logging, DB, i18n) → 2. location/weather/IMD → 3. crop config/rules/engine → 4. knowledge → 5. AI/fallback → 6. pipeline + routes → 7. L2 (history, profile, chat, monitoring) → 8. L3 modules → 9. frontend shell → 10. pages in the order above.
