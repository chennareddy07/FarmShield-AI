# FarmShield AI

Weather-aware crop-risk decision support for paddy and groundnut farmers in Andhra Pradesh (English + Telugu).
Built from `specs/requirements.md`. **Weather is real provider data or an explicit "unavailable" state — nothing is ever simulated.
Risk levels come only from a deterministic, source-referenced rule engine; the AI layer can only explain them.**

## Quick start
```bash
# 1. backend
cd backend
python3 -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env                                    # PowerShell: Copy-Item ..\.env.example .env
# Edit backend/.env to enable optional providers and add their credentials.
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000                 # API docs: http://localhost:8000/api/docs

# 2. frontend (new terminal)
cd frontend
npm install
npm run dev                                                # http://localhost:5173  (proxies /api to :8000)

# 3. single-process production style
cd frontend && npm run build        # backend then serves frontend/dist at http://localhost:8000
```
**First thing to do on a machine with internet:** `cd backend && python scripts/verify_providers.py` — checks Open-Meteo (forecast, geocoding, historical), and any optional provider you configured.

The checked-in root `.env.example` contains placeholders only. Copy it to `backend/.env` as shown above; the backend also reads a root `.env` for local development. Keep real credentials in either untracked file, never put secrets in frontend `VITE_` variables or commit them. If a credential was ever active or committed, revoke and rotate it with its provider—removing it from the current file does not invalidate it.

For mandi market intelligence, set `DATA_GOV_IN_API_KEY` and `AGMARKNET_RESOURCE_ID` in `backend/.env`. The API key is used only by the backend. The app reports missing or unavailable configuration without showing fallback prices. It displays the unit only when the source response supplies it, and reported mandi wholesale prices are not guaranteed farmer selling prices.

### Session ownership and production configuration

The app issues an anonymous, signed browser-session cookie and uses it to scope profiles, assessments, conversations, and notifications. It does **not** create user accounts or authenticate a person's identity; use an identity provider before treating this as account-level access control.

For production, set `SESSION_SECRET` to a stable, random value of at least 32 characters (for example, generate one locally with `python -c "import secrets; print(secrets.token_urlsafe(48))"`). Keep it in the deployment secret manager, use HTTPS, and do not commit it. The backend refuses to start in production without this setting. In development, an in-process random key is used when it is absent, so browser sessions and their access to saved data will not survive a backend restart. Configure a stable key locally if you want development sessions to persist.

Existing database rows created before session ownership was added are left with no owner and are not exposed to newly issued sessions. They require a deliberate, separately verified migration if they must be retained for a specific user; they are not automatically assigned to a browser.

## Tests
```bash
cd backend && pytest -q          # backend unit and integration tests
cd frontend && npm test          # frontend component and workflow tests
cd frontend && npm run build     # production bundle
```

## Using it
Dashboard → search a location (or "Use current location" / pick a district) → choose crop + growth stage → **Analyze**.
You get current weather, 7-day forecast, official-warning status, crop risk per category with the exact rule/threshold/source,
and a timeline. Risk assessment does not call an LLM. To request an AI explanation, choose **Generate AI advisory** after the assessment; the request is made only after that explicit action. Follow-up chat is likewise sent only when you submit a question, and includes the selected location and crop context. Conversation history is scoped to the current browser session and expires after 30 days. Language switch (EN/తెలుగు) re-renders the deterministic result; Telugu agricultural wording still needs domain review.
Navigation badges (`Planned`, `Needs setup`, `Unverified`) come from `/api/meta/modules` and are truthful.

## Architecture & documents (`specs/`)
`architecture.md` · `traceability-matrix.md` (F1–F30 → components/services/APIs/data/tests) · `tasks.md` (phased checklist) · `dependencies.md` ·
`external-verification.md` (APIs to verify) · `agri-research.md` (thresholds found / still missing) · `feasibility.md` (what can't be done yet) · `requirements.md` (original spec). Agricultural evidence provenance and stage-coverage gaps are in `knowledge/metadata/evidence_registry.json`; each risk rule has a validation record in `knowledge/metadata/rule_validation_records.json`. Paddy and groundnut expert review is pending in `knowledge/reviews/`.

## Data sources
Open-Meteo (forecast, ERA5 historical, geocoding — free tier is **non-commercial**, attribution shown) · IMD (only via a CAP feed you configure) ·
data.gov.in/Agmarknet (key) · NASA MODIS via ORNL DAAC (live endpoint check passed; product-quality interpretation remains unverified) · LLM of your choice (key). Knowledge base: 6 short source paraphrases with provenance, access/review status, applicability, measurement-window limits, and citations; no full source documents are vendored.

## Status
See the chat summary delivered with this build and `specs/tasks.md`. Key facts:
* **Enabled risk rules:** none. The three IMD rainfall classes are meteorological source facts, not crop-impact thresholds, and their 24-hour observation window does not align with Open-Meteo's local-calendar-day totals. Paddy/groundnut heat rules also remain disabled pending agronomic review and compatible exposure windows.
  Categories without an assessed, verified rule report **Insufficient data** (`specs/agri-research.md`). `ALLOW_UNVERIFIED_RULES=true` cannot override unverified time-window alignment.
* **Evidence review:** source access and agronomic approval are separate. One source was verified as a meteorological fact, three accessible agricultural sources require expert review, and two bibliographic leads remain source-unverified. The registry records 107 uncovered crop-stage-concern combinations as `insufficient_evidence`; no risk threshold or crop recommendation was approved.
* **Source handling:** JIRCAS and IMD PDFs were retrieved temporarily for verification, then deleted; the AP IMD bulletin is dated and not seeded as reusable evidence. The inaccessible Springer and ICRISAT sources are not used for assistant grounding.
* **IMD warnings:** shown as "not connected" until you supply a verified CAP feed (`IMD_CAP_FEED_URL`).
* **Telugu** text needs review by a native/agricultural-domain speaker.
* **Live provider check:** Open-Meteo forecast, geocoding, and historical endpoints passed; MODIS returned observations. The configured LLM text endpoint succeeded for paddy advisories in English and Telugu, a groundnut advisory in English, and a cited assistant response; intermittent rate limiting was observed. data.gov.in returned 20 market records spanning 4 states and 14 commodities in the checked response; Guntur and groundnut were absent, and price units were unconfirmed. IMD CAP remains unconfigured.
* **Live workflow check:** Guntur geocoding → Open-Meteo → paddy/flowering and groundnut/pegging assessments → retrieval-only chat passed with the LLM disabled. Both assessments correctly reported `insufficient_data` under the current conservative risk configuration. Chat fallback now includes available agricultural source excerpts and citations when LLM output is unavailable or rejected. Browser speech and visual/mobile rendering remain unverified.

## Troubleshooting
* *"Live weather information is currently unavailable"* → no internet / Open-Meteo down; run `verify_providers.py`; the app shows last good data marked **Stale** for up to 6 h.
* *Location search finds nothing* → try the district name; geocoder coverage of villages is sparse.
* *CORS error in browser* → add your frontend origin to `CORS_ORIGINS`.
* *AI advisory is unavailable* → configure `LLM_PROVIDER`, `LLM_API_KEY`, `LLM_MODEL` (and `LLM_BASE_URL` for `openai_compatible`), then explicitly choose **Generate AI advisory**. Assessment and chat-without-LLM continue to show only available deterministic or provider-sourced information.
* *Saved profile or assessment is not found after restarting development backend* → set a persistent `SESSION_SECRET` locally; the development-only random key changes when the process restarts.
* *Map tiles blank* → needs internet access to OpenStreetMap tiles.

## Demo script (2–3 min)
1. Dashboard in English → Guntur → Paddy / Flowering → Analyze; point out provider, timestamps, data-quality chips.
2. Open "Why this result" on a triggered rule (threshold, actual value, period, source link) — or show the "Insufficient data" categories and explain why.
3. Switch to తెలుగు; show the same assessment re-rendered. 4. Ask a follow-up question; ask an out-of-scope one to show refusal.
5. Data Status page (provider health, module honesty). 6. Download a report.

## Limitations
Decision support only — not an official warning, not agronomic prescription, not a yield predictor. Weather is gridded model data (not farm-level).
Rate limiter, provider ledger and assessment cache are in-process (use shared stores for multi-worker deployments).
