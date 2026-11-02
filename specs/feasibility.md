# Features That Cannot Realistically Be Fully Built Now (task 7)

Nothing is removed from the product architecture; this lists what *cannot be honestly completed* in this session/MVP and why. (Spec §4 policy: "document it as planned rather than presenting it as complete.")

| Feature / part | Blocker | What was done instead | What the user must supply |
|---|---|---|---|
| F4 live IMD warnings | No verified, documented public machine-readable AP warnings endpoint; spec forbids inventing endpoints/scraping around access controls | CAP 1.2 parser behind `IMD_CAP_FEED_URL`; default = explicit *unavailable* state + official links | A confirmed feed URL (or manual bulletin upload) |
| F6 crop-specific numeric rules (most categories) | No verified AP-specific thresholds located; agronomist sign-off required | Engine, schema and rule loader complete; only IMD rainfall rules enabled; paddy/groundnut heat rules shipped as `needs_review` (disabled) | Reviewed thresholds from ANGRAU/ICAR/CRIDA |
| F9 Telugu quality | Agricultural Telugu terminology cannot be verified by me | Full Telugu UI dictionary written; flagged `needs_review` | Native/agri-domain reviewer |
| F16 crop calendar dates | No verified district calendars | Stage list + explicit "calendar unavailable" | Verified calendar data file |
| F19 mandi prices | Requires data.gov.in API key + resource ID; endpoint unverified here | Complete client, normaliser, UI, tests with synthetic fixtures | API key, resource ID |
| F20 image diagnosis | Needs a vision LLM key; any "diagnosis" is inherently preliminary | Upload validation + consent + vision adapter + mandatory limitation labels; no chemical advice | LLM key (vision-capable) |
| F21 email/SMS | Needs mail/SMS vendor, sender verification, legal consent flows | In-app notifications with consent/dedupe/quiet hours | Vendor account |
| F22 satellite | Live MODIS endpoint check passed; cloud/QA handling and NDVI interpretation remain unverified; field-level imagery would need Sentinel Hub/GEE accounts | MODIS NDVI subset client (250 m, 16-day), honest limitations | Product-quality review or Sentinel Hub/GEE credentials |
| F23 server-side Telugu STT | Needs STT vendor | Browser Web Speech API (STT+TTS) with text fallback; optional OpenAI-compatible server STT | STT key |
| F24 additional languages/regions | Need verified translations and per-region thresholds | Registry-driven architecture (add a dictionary + region + rule files) | Reviewed content |
| F25 advanced indicators (SPI, climate maps) | Needs ≥ 30-year baselines, method validation | Simple baseline rainfall deviation with disclosed method and coverage checks | Method sign-off |
| F26 map finer than district | Underlying data (weather grid ≈ 9–25 km; warnings are district-level) can't support finer layers (spec forbids) | District markers only | — |
| F27 PDF with Telugu | Needs font embedding/shaping validation | Downloadable HTML report (browser prints to PDF with system Telugu fonts) | — |
| Account-level access control | No user identity/account system is configured | Signed anonymous session cookie isolates browser-owned profiles, assessments, chat, and notifications; admin route still uses a static bearer token | Identity provider and account/session lifecycle for production user accounts; protect admin token in a secret manager |
| F30 integrations | Each needs its own verified contract | Adapter protocol + quality-check hook only | Per integration |
| Live verification of everything above | Provider availability/configuration varies; some integrations require credentials or domain review | Open-Meteo and MODIS passed the current live check; IMD and Agmarknet were skipped without configuration | Verify remaining providers and review data quality/terms before production |
| 2–3 min demo video, pitch deck, public GitHub repo | Not producible as code here | README demo script | You |
