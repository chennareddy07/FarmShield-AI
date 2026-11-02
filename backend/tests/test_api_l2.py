import asyncio
import io
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Callable

from fastapi.testclient import TestClient
import httpx
import pytest

from app.core import http, i18n, monitoring
from app.core.http import ProviderError
from app.core.logging import redact
from app.core.middleware import BodySizeLimitMiddleware, RateLimitMiddleware
from app.services import history_service as hs, imd_service
from tests.fixtures.open_meteo import make_forecast


# ---------- Health / errors / security (AC1, AC2, E27-E30) ----------
def test_health(client: TestClient):
    r = client.get("/api/health")
    j = r.json()
    assert r.status_code == 200 and j["status"] in ("ok", "degraded") and j["timestamp"] and "database" in j["services"] and "weather_provider" in j["services"]


def test_error_envelope_and_request_id(client: TestClient):
    r = client.get("/api/nope")
    j = r.json()
    assert r.status_code == 404 and {"error_code", "message", "request_id"} <= set(j) and r.headers["x-request-id"] == j["request_id"]
    r = client.get("/api/weather/current?latitude=abc&longitude=1", headers={"X-Request-ID": "abc123"})
    assert r.status_code == 422 and r.json()["request_id"] == "abc123" and r.json()["details"]


def test_no_stack_trace_on_internal_error(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.services import crop_config_service
    monkeypatch.setattr(crop_config_service, "list_crops", lambda *a, **k: 1 / 0)
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(), raise_server_exceptions=False) as c:
        r = c.get("/api/crops")
    assert r.status_code == 500 and "Traceback" not in r.text and "division" not in r.text and r.json()["error_code"] == "internal_error"


def test_body_size_limit(client: TestClient):
    r = client.post("/api/risk/assess", content=b"x", headers={"content-length": str(50 * 1024 * 1024), "content-type": "application/json"})
    assert r.status_code == 413 and r.json()["error_code"] == "payload_too_large"


@pytest.mark.parametrize("headers", [[], [(b"content-length", b"invalid")]])
def test_body_size_limit_counts_stream_without_valid_content_length(headers):
    async def run():
        called = False
        sent = []
        messages = iter([
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": False},
        ])

        async def app(scope, receive, send):
            nonlocal called
            called = True

        async def receive():
            return next(messages)

        async def send(message):
            sent.append(message)

        scope = {"type": "http", "method": "POST", "path": "/api/test", "headers": headers,
                 "state": {"request_id": "test-request"}}
        await BodySizeLimitMiddleware(app, max_bytes=5)(scope, receive, send)
        return called, sent

    called, sent = asyncio.run(run())
    assert not called
    assert sent[0]["status"] == 413
    assert b"test-request" in sent[1]["body"]


def test_provider_http_client_sets_connect_and_read_timeouts():
    async def run():
        async with http.client() as provider_client:
            return provider_client.timeout.connect, provider_client.timeout.read, provider_client.follow_redirects

    connect_timeout, read_timeout, follow_redirects = asyncio.run(run())
    assert 0 < connect_timeout <= read_timeout and not follow_redirects


def test_rate_limit(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "3")
    from app.core.config import get_settings
    get_settings.cache_clear()
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app()) as c:
        codes = [c.get("/api/crops").status_code for _ in range(5)]
    assert codes[:3] == [200] * 3 and 429 in codes


def test_rate_limiter_prunes_expired_buckets_and_caps_memory(monkeypatch: pytest.MonkeyPatch):
    async def run():
        middleware = RateLimitMiddleware(lambda *args: None, per_minute=100, ai_per_minute=100)
        monkeypatch.setattr("app.core.middleware.MAX_RATE_LIMIT_BUCKETS", 3)
        middleware._last_cleanup = 0

        async def call_next(request):
            from starlette.responses import Response
            return Response()

        async def hit(ip):
            from starlette.requests import Request
            scope = {"type": "http", "method": "GET", "path": "/api/crops", "headers": [],
                     "query_string": b"", "client": (ip, 1234), "server": ("test", 80),
                     "scheme": "http", "root_path": ""}
            return await middleware.dispatch(Request(scope), call_next)

        monkeypatch.setattr("app.core.middleware.time.monotonic", lambda: 100)
        middleware.hits[("expired", "std")] = [1]
        for i in range(5):
            await hit(f"192.0.2.{i}")
        return middleware.hits

    buckets = asyncio.run(run())
    assert len(buckets) <= 3 and ("expired", "std") not in buckets


def test_cors_only_known_origin(client: TestClient):
    ok = client.options("/api/crops", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    bad = client.options("/api/crops", headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173" and "access-control-allow-origin" not in bad.headers


def test_log_redaction():
    assert "sk-abcdefghijk123" not in redact("key sk-abcdefghijk123 used")
    assert "gsk_sensitivevalue123" not in redact("provider error gsk_sensitivevalue123")
    assert "SECRET99" not in redact("api_key=SECRET99xyz")


def test_secrets_not_exposed(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LLM_API_KEY", "sk-supersecretvalue123")
    from app.core.config import get_settings
    get_settings.cache_clear()
    for p in ("/api/health", "/api/meta/modules", "/api/monitoring/status"):
        assert "supersecret" not in client.get(p).text


def test_llm_status_requires_complete_provider_configuration(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-provider-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.delenv("LLM_BASE_URL", raising=False)
    get_settings.cache_clear()
    assert client.get("/api/health").json()["services"]["llm"] == "not_configured"
    advisor = next(module for module in client.get("/api/meta/modules").json()["modules"] if module["id"] == "advisor")
    assert advisor["status"] == "implemented_ai_not_configured"

    monkeypatch.setenv("LLM_BASE_URL", "https://provider.example/v1")
    get_settings.cache_clear()
    assert client.get("/api/health").json()["services"]["llm"] == "configured_not_tested"
    from app.core import monitoring
    monitoring.record_success("llm")
    assert client.get("/api/health").json()["services"]["llm"] == "operational"
    monitoring.record_failure("llm", "timeout")
    assert client.get("/api/health").json()["services"]["llm"] == "temporarily_unavailable"


@pytest.mark.parametrize("base_url", ["http://provider.example/v1", "https://user:pass@provider.example/v1", "not-a-url"])
def test_llm_status_rejects_invalid_provider_configuration(client: TestClient, monkeypatch: pytest.MonkeyPatch, base_url):
    from app.core.config import get_settings
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    monkeypatch.setenv("LLM_API_KEY", "test-provider-key")
    monkeypatch.setenv("LLM_MODEL", "test-model")
    monkeypatch.setenv("LLM_BASE_URL", base_url)
    get_settings.cache_clear()
    assert client.get("/api/health").json()["services"]["llm"] == "invalid_configuration"
    advisor = next(module for module in client.get("/api/meta/modules").json()["modules"] if module["id"] == "advisor")
    assert advisor["status"] == "needs_config"


def test_session_bootstrap_uses_http_only_cookie(client: TestClient):
    response = client.get("/api/session")
    assert response.status_code == 200 and response.json()["mode"] == "anonymous"
    assert "farmshield_session=" in response.headers["set-cookie"]
    assert "httponly" in response.headers["set-cookie"].lower()
    assert "samesite=lax" in response.headers["set-cookie"].lower()
    assert "owner_id" not in response.text


def test_assessment_returns_provider_snapshots_from_single_weather_fetch(client: TestClient, mock_http):
    requests = []

    def forecast(request):
        requests.append(request)
        return httpx.Response(200, json=make_forecast())

    mock_http({"api.open-meteo.com": forecast})
    response = client.post("/api/risk/assess", json={
        "latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering",
    })
    result = response.json()
    assert response.status_code == 200 and len(requests) == 1
    assert result["weather_snapshot"]["current"]["provider"] == "Open-Meteo"
    assert result["weather_snapshot"]["forecast"]["daily"]
    assert result["warnings_snapshot"]["source_status"] == "not_configured"


def test_production_requires_configured_session_secret(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    from app.main import create_app
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("SESSION_SECRET", raising=False)
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="SESSION_SECRET"):
        create_app()
    get_settings.cache_clear()


def test_production_rejects_short_session_secret(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    from app.main import create_app
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "too-short")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError, match="at least 32 characters"):
        create_app()
    get_settings.cache_clear()


def test_production_session_cookie_requires_https(monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    from app.main import create_app
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_SECRET", "a" * 48)
    get_settings.cache_clear()
    with TestClient(create_app(), base_url="https://testserver") as production_client:
        cookie = production_client.get("/api/session").headers["set-cookie"].lower()
        assert "secure" in cookie and "httponly" in cookie and "samesite=lax" in cookie
    get_settings.cache_clear()


def test_llm_status_rejects_placeholder_api_key(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.core.config import get_settings
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("LLM_API_KEY", "your-api-key")
    monkeypatch.setenv("LLM_MODEL", "claude-test")
    get_settings.cache_clear()
    assert client.get("/api/health").json()["services"]["llm"] == "invalid_configuration"


def test_profile_assessment_and_chat_are_scoped_to_session(client: TestClient, mock_http):
    from app.core.config import get_settings
    from app.main import create_app
    get_settings.cache_clear()
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    profile = client.post("/api/profile", json={"nickname": "private"}).json()
    assessment = client.post("/api/risk/assess", json={
        "latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering",
        "profile_id": profile["profile_id"]}).json()
    conversation = client.post("/api/assistant/chat", json={"message": "rice heat flowering", "crop_id": "paddy"}).json()
    history = client.get(f"/api/assistant/conversations/{conversation['conversation_id']}")
    assert history.status_code == 200 and [message["role"] for message in history.json()["messages"]] == ["user", "assistant"]
    from app.services import assessment_service
    assessment_service._memory.clear()
    with TestClient(create_app()) as another_session:
        assert another_session.get(f"/api/profile/{profile['profile_id']}").status_code == 404
        assert another_session.put(f"/api/profile/{profile['profile_id']}", json={"nickname": "changed"}).status_code == 404
        assert another_session.delete(f"/api/profile/{profile['profile_id']}").status_code == 404
        assert another_session.get(f"/api/risk/{assessment['assessment_id']}").status_code == 404
        assert another_session.post("/api/advisory/generate", json={"assessment_id": assessment["assessment_id"]}).status_code == 404
        assert another_session.post("/api/assistant/chat", json={
            "message": "more", "conversation_id": conversation["conversation_id"]}).status_code == 404
        assert another_session.get(f"/api/assistant/conversations/{conversation['conversation_id']}").status_code == 404
    assert client.get(f"/api/profile/{profile['profile_id']}").json()["nickname"] == "private"
    assert client.get(f"/api/risk/{assessment['assessment_id']}").status_code == 200


def test_legacy_database_owner_migration_is_additive():
    from sqlalchemy import create_engine, inspect, text
    from app.core.db import upgrade_owner_columns
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        for table, primary_key in (("profiles", "profile_id"), ("assessments", "assessment_id"),
                                   ("conversations", "conversation_id")):
            connection.execute(text(f"CREATE TABLE {table} ({primary_key} VARCHAR(40) PRIMARY KEY)"))
            connection.execute(text(f"INSERT INTO {table} ({primary_key}) VALUES ('legacy-row')"))
    upgrade_owner_columns(engine)
    for table in ("profiles", "assessments", "conversations"):
        columns = {column["name"] for column in inspect(engine).get_columns(table)}
        assert "owner_id" in columns
        with engine.connect() as connection:
            assert connection.execute(text(f"SELECT owner_id FROM {table}")).scalar() is None
    engine.dispose()


def test_checked_in_environment_example_uses_empty_optional_secrets():
    example = (Path(__file__).resolve().parents[2] / ".env.example").read_text(encoding="utf-8")
    assert "LLM_PROVIDER=disabled" in example
    assert re.search(r"^LLM_API_KEY\s*=\s*$", example, re.MULTILINE)
    for name in ("DATA_GOV_IN_API_KEY", "STT_API_KEY", "ADMIN_API_TOKEN", "IMD_CAP_FEED_URL"):
        assert re.search(rf"^{name}\s*=\s*$", example, re.MULTILINE)


def test_database_outage_is_controlled(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    from app.services import assessment_service
    assessment_service._memory.clear()
    monkeypatch.setattr("app.services.assessment_service.session", lambda: (_ for _ in ()).throw(RuntimeError("secret-db-host")))
    r = client.get("/api/risk/as-zzz")
    assert r.status_code == 503 and "secret-db-host" not in r.text                       # E27


def test_app_code_never_imports_test_fixtures():
    root = Path(__file__).resolve().parent.parent / "app"

    for f in root.rglob("*.py"):
        source = f.read_text(encoding="utf-8")

        assert (
            "tests.fixtures" not in source
            and "fixtures.open_meteo" not in source
        ), f

def test_backend_dictionary_parity():
    assert set(i18n.MESSAGES["en"]) == set(i18n.MESSAGES["te"]) and set(i18n.REASONS["en"]) == set(i18n.REASONS["te"])
    assert set(i18n.CATEGORY_LABELS["en"]) == set(i18n.CATEGORY_LABELS["te"]) and set(i18n.RISK_LABELS["en"]) == set(i18n.RISK_LABELS["te"])
    assert i18n.normalize_language("xx") == ("en", True) and i18n.normalize_language(None) == ("en", False) and i18n.normalize_language("te") == ("te", False)
    for key, text in i18n.MESSAGES["en"].items():       # placeholders must match between languages
        assert sorted(re.findall(r"\{(\w+)\}", text)) == sorted(re.findall(r"\{(\w+)\}", i18n.MESSAGES["te"][key])), key


# ---------- End-to-end scenarios 1 & 3 ----------
def test_scenario1_full_journey(client: TestClient, mock_http: Callable[..., None]):
    mock_http({"api.open-meteo.com": (200, make_forecast(rain=[0, 70, 0, 0, 0, 0, 0]))})
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering", "language": "en", "location_name": "Guntur"}).json()
    assert a["overall_risk"] == "insufficient_data" and not a["triggered_rules"] and a["data_quality"]["weather"]["status"] == "fresh"
    assert a["warnings_status"] == "not_configured" and a["data_quality"]["warnings"]["status"] == "unavailable"
    assert a["evidence"] and any(item["document_id"] == "KB-ICAR-KHARIF-2025-PADDY-ZONAL" for item in a["evidence"])
    assert a["overall_risk"] == "insufficient_data" and a["rule_version"] and "_inputs" not in a
    assert client.get(f"/api/risk/{a['assessment_id']}").json()["assessment_id"] == a["assessment_id"]


def test_scenario3_weather_outage_no_fabricated_assessment(client: TestClient, mock_http: Callable[..., None]):
    mock_http({"api.open-meteo.com": (500, {})})
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering"}).json()
    assert a["overall_risk"] == "insufficient_data" and a["data_quality"]["weather"]["status"] == "unavailable" and not a["triggered_rules"]


def test_scenario4_no_evidence_message(client: TestClient, mock_http: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    from app.services import knowledge_service as ks
    for d in ks.list_documents():
        ks.mark_outdated(d["document_id"])
    mock_http({"api.open-meteo.com": (200, make_forecast(rain=[0, 130, 0, 0, 0, 0, 0]))})
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering"}).json()
    assert a["overall_risk"] == "insufficient_data" and not a["triggered_rules"]
    adv = client.post("/api/advisory/generate", json={"assessment_id": a["assessment_id"]}).json()
    assert any("could not find enough verified" in u for u in adv["uncertainties"])
    assert not adv["recommended_actions"] and not adv["preventive_actions"]


def test_outside_pilot_notice(client: TestClient, mock_http: Callable[..., None]):
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    a = client.post("/api/risk/assess", json={"latitude": 28.6, "longitude": 77.2, "crop_id": "paddy"}).json()
    assert any("outside" in n for n in a["notices"]) and a["stage_specific"] is False


def test_audit_record_has_rounded_coordinates_no_pii(client: TestClient, mock_http: Callable[..., None]):
    from app.core.db import session
    from app.models.tables import Assessment
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    client.post("/api/risk/assess", json={"latitude": 16.34567, "longitude": 80.41234, "crop_id": "paddy", "location_name": "My farm", "profile_id": None})
    with session() as db:
        row = db.query(Assessment).one()
    assert (row.approx_lat, row.approx_lon) == (16.3, 80.4) and row.rule_version


def test_report_generation(client: TestClient, mock_http: Callable[..., None]):                                              # AC33
    mock_http({"api.open-meteo.com": (200, make_forecast(rain=[0, 130, 0, 0, 0, 0, 0]))})
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering", "location_name": "<b>Guntur</b>"}).json()
    r = client.post("/api/reports/generate", json={"assessment_id": a["assessment_id"], "language": "en", "include_advisory": True})
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    assert a["assessment_id"] in r.text and "Report created" in r.text and "<b>Guntur</b>" not in r.text   # escaped
    assert "rsmcnewdelhi.imd.gov.in" not in r.text
    te = client.post("/api/reports/generate", json={"assessment_id": a["assessment_id"], "language": "te"})
    assert 'lang="te"' in te.text and "ధృవీకరించ" in te.text


# ---------- Profile (F13, AC22) ----------
def test_profile_lifecycle_and_guest_mode(client: TestClient):
    assert client.get("/api/crops").status_code == 200                                   # guest works without profile
    p = client.post("/api/profile", json={"nickname": "Plot A", "preferred_crop": "groundnut", "preferred_growth_stage": "pegging", "language": "te", "farm_area": 2.5, "farm_area_unit": "acre",
                                          "preferred_location": {"name": "Guntur", "latitude": 16.3, "longitude": 80.4}}).json()
    assert p["profile_id"].startswith("fp-") and client.get(f"/api/profile/{p['profile_id']}").json()["language"] == "te"
    u = client.put(f"/api/profile/{p['profile_id']}", json={"preferred_crop": "paddy", "preferred_growth_stage": "flowering"}).json()
    assert u["preferred_crop"] == "paddy" and u["farm_area"] == 2.5
    assert client.delete(f"/api/profile/{p['profile_id']}").json()["deleted"] and client.get(f"/api/profile/{p['profile_id']}").status_code == 404


@pytest.mark.parametrize("body", [{"preferred_crop": "wheat"}, {"preferred_crop": "paddy", "preferred_growth_stage": "pegging"}, {"language": "zz"}, {"farm_area": -1},
                                  {"farm_area": 1, "farm_area_unit": "bigha"}, {"preferred_location": {"latitude": 200, "longitude": 0}}])
def test_profile_validation(client: TestClient, body: dict[str, str] | dict[str, int] | dict[str, int | str] | dict[str, dict[str, int]]):
    assert client.post("/api/profile", json=body).status_code == 422


def test_personalisation_context_is_passed_as_context_only(client: TestClient, mock_http: Callable[..., None]):            # F28
    mock_http({"api.open-meteo.com": (200, make_forecast(rain=[0, 130, 0, 0, 0, 0, 0]))})
    p = client.post("/api/profile", json={"farm_area": 3, "farm_area_unit": "acre"}).json()
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "growth_stage_id": "flowering", "profile_id": p["profile_id"]}).json()
    adv = client.post("/api/advisory/generate", json={"assessment_id": a["assessment_id"], "profile_id": p["profile_id"]}).json()
    assert "3.0 acre" in adv["personalisation_note"] and "Assessments in the last 30 days: 1" in adv["personalisation_note"]


# ---------- IMD (F4, AC16, AC17, E12) ----------
CAP = """<?xml version="1.0"?><alert xmlns="urn:oasis:names:tc:emergency:cap:1.2"><identifier>IMD-1</identifier><sender>imd@gov.in</sender><senderName>IMD Amaravati</senderName><sent>2026-11-01T08:00:00+05:30</sent>
<info><event>Heavy Rain</event><severity>Severe</severity><headline>Heavy rainfall warning</headline><description>Heavy rain likely.</description><effective>2026-11-02T00:00:00+05:30</effective><expires>2026-11-04T00:00:00+05:30</expires>
<web>https://mausam.imd.gov.in/x</web><parameter><valueName>color</valueName><value>Orange</value></parameter><area><areaDesc>Guntur, Krishna</areaDesc></area></info></alert>"""


@pytest.mark.parametrize("url", [
    "http://feed.example/cap.xml",
    "file:///etc/passwd",
    "https://localhost/cap.xml",
    "https://127.0.0.1/cap.xml",
    "https://10.0.0.1/cap.xml",
    "https://169.254.1.1/cap.xml",
    "https://[::1]/cap.xml",
    "https://feed.example.evil/cap.xml",
])
def test_cap_url_rejects_untrusted_or_non_public_urls(url):
    origin = ("feed.example", 443)
    with pytest.raises(ProviderError):
        imd_service.validate_cap_url(url, origin)


def test_cap_url_allows_configured_https_origin():
    assert imd_service.validate_cap_url("https://FEED.example/cap.xml") == ("feed.example", 443)
    assert imd_service.validate_cap_url("https://feed.example/alerts.cap", ("feed.example", 443)) == ("feed.example", 443)


def test_parse_cap_populates_only_supplied_fields():
    w = imd_service.parse_cap(CAP, "2026-11-01T00:00:00Z")[0]
    assert (w.source, w.severity, w.severity_color, w.affected_area, w.valid_until, w.source_url) == ("IMD Amaravati", "Severe", "Orange", "Guntur, Krishna", "2026-11-04T00:00:00+05:30", "https://mausam.imd.gov.in/x")
    assert w.issued_at and w.valid_from and w.warning_type == "Heavy Rain"


def test_warnings_not_configured_has_official_links_no_fabrication(client: TestClient):
    r = client.get("/api/warnings?district=Guntur").json()
    assert r["source_status"] == "not_configured" and r["warnings"] == [] and any("imd.gov.in" in l["url"] for l in r["official_links"])


def test_warnings_from_feed_and_district_filter(client: TestClient, mock_http: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/cap.xml")
    from app.core.config import get_settings
    get_settings.cache_clear()
    mock_http({"feed.example": (200, CAP)})
    ok = client.get("/api/warnings?district=Guntur").json()
    assert ok["source_status"] == "available" and len(ok["warnings"]) == 1
    none = client.get("/api/warnings?district=Kurnool").json()
    assert none["source_status"] == "available" and none["warnings"] == [] and "no warning" in none["source_status_message"]


def test_warning_feed_follows_only_same_configured_https_host(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/index.xml")
    from app.core.config import get_settings
    from app.core import http
    get_settings.cache_clear()
    rss = '<feed><link href="https://feed.example/alerts.cap"/></feed>'
    requests = []

    def handler(request):
        requests.append(request.url)
        return httpx.Response(200, text=rss if request.url.path == "/index.xml" else CAP)

    http.set_transport(httpx.MockTransport(handler))
    result = client.get("/api/warnings?district=Guntur").json()
    assert result["source_status"] == "available" and len(result["warnings"]) == 1
    assert [request.path for request in requests] == ["/index.xml", "/alerts.cap"]


def test_warning_feed_rejects_hostile_link_before_request(client: TestClient, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/index.xml")
    from app.core.config import get_settings
    from app.core import http
    get_settings.cache_clear()
    rss = '<feed><link href="http://127.0.0.1/private.cap"/></feed>'
    requests = []

    def handler(request):
        requests.append(request.url)
        return httpx.Response(200, text=rss)

    http.set_transport(httpx.MockTransport(handler))
    result = client.get("/api/warnings?district=Guntur").json()
    assert result["source_status"] == "unavailable" and result["warnings"] == []
    assert [request.host for request in requests] == ["feed.example"]


def test_warning_feed_rejects_redirect(client: TestClient, mock_http: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/cap.xml")
    from app.core.config import get_settings
    get_settings.cache_clear()
    mock_http({"feed.example": (302, "")})
    result = client.get("/api/warnings?district=Guntur").json()
    assert result["source_status"] == "unavailable" and result["warnings"] == []


def test_warnings_source_failure_is_unavailable(client: TestClient, mock_http: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/cap.xml")
    from app.core.config import get_settings
    get_settings.cache_clear()
    mock_http({"feed.example": (500, "")})
    r = client.get("/api/warnings?district=Guntur").json()
    assert r["source_status"] == "unavailable" and r["warnings"] == []
    mock_http({"feed.example": (200, "<not xml")})
    assert client.get("/api/warnings?district=Guntur").json()["source_status"] == "unavailable"


def test_warning_drives_risk_assessment(client: TestClient, mock_http: Callable[..., None], monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("IMD_CAP_FEED_URL", "https://feed.example/cap.xml")
    from app.core.config import get_settings
    get_settings.cache_clear()
    cap = CAP.replace("2026-11-04T00:00:00+05:30", (date.today() + timedelta(days=3)).isoformat() + "T00:00:00+05:30")
    mock_http({"feed.example": (200, cap), "api.open-meteo.com": (200, make_forecast())})
    a = client.post("/api/risk/assess", json={"latitude": 16.3, "longitude": 80.4, "crop_id": "paddy", "district": "Guntur"}).json()
    cats = {c["category"]: c["risk"] for c in a["risk_categories"]}
    assert cats["severe_weather_warning"] == "high" and a["overall_risk"] == "high" and any(e["kind"] == "official_warning" for e in a["evidence"])


# ---------- History (F11, F25, AC19, AC20, E18) ----------
def archive(days=10, rain=2.0, drop_every=0):
    start = date.today() - timedelta(days=days + 6)
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    return {"latitude": 16.3, "longitude": 80.4, "daily": {"time": dates, "temperature_2m_max": [33.0] * days, "temperature_2m_min": [24.0] * days, "temperature_2m_mean": [28.0] * days,
                                                              "precipitation_sum": [None if drop_every and i % drop_every == 0 else rain for i in range(days)]}}, start, dates


def test_history_endpoint_with_coverage(client: TestClient, mock_http: Callable[..., None]):
    raw, start, dates = archive()
    mock_http({"archive-api": (200, raw)})
    r = client.get(f"/api/history?latitude=16.3&longitude=80.4&start_date={dates[0]}&end_date={dates[-1]}").json()
    assert r["data_type"] == "reanalysis" and r["coverage"]["rainfall_coverage_pct"] == 100 and r["limitations"] and r["units"]["precipitation"] == "mm" and r["monthly"]


def test_history_incomplete_coverage_flagged(client: TestClient, mock_http: Callable[..., None]):
    raw, start, dates = archive(drop_every=2)
    mock_http({"archive-api": (200, raw)})
    r = client.get(f"/api/history?latitude=16.3&longitude=80.4&start_date={dates[0]}&end_date={dates[-1]}").json()
    assert r["coverage"]["rainfall_coverage_pct"] < 90 and any("below 90%" in n for n in r["notes"])


def test_history_unavailable_and_validation(client: TestClient, mock_http: Callable[..., None]):
    mock_http({"archive-api": (500, {})})
    assert client.get("/api/history?latitude=16&longitude=80&start_date=2025-01-01&end_date=2025-01-05").json()["error_code"] == "history_unavailable"
    for q in ("start_date=2025-02-01&end_date=2025-01-01", "start_date=bad&end_date=2025-01-01", f"start_date=2025-01-01&end_date={date.today() + timedelta(days=5)}", "start_date=1990-01-01&end_date=2025-01-01"):
        assert client.get(f"/api/history?latitude=16&longitude=80&{q}").status_code == 422


def synthetic_years(first, last, per_day=5.0, current_factor=1.0):
    series = []
    d = date(first, 1, 1)
    while d <= date(last, 12, 31):
        series.append({"date": d.isoformat(), "precipitation_sum_mm": per_day * (current_factor if d.year == last else 1.0)})
        d += timedelta(days=1)
    return series


def test_seasonal_deviation_valid():
    s = synthetic_years(2015, 2025, 5.0, 1.5)
    r = hs.seasonal_deviation(s, 2025, (6, 1), (9, 30), list(range(2015, 2025)))
    assert r["status"] == "available" and r["deviation_pct"] == 50.0 and len(r["baseline_years_used"]) == 10 and "not a climate-trend" in r["method"]


def test_seasonal_deviation_refuses_thin_baseline():
    s = [x for x in synthetic_years(2015, 2025) if x["date"][:4] in ("2023", "2024", "2025")]
    assert hs.seasonal_deviation(s, 2025, (6, 1), (9, 30), [2023, 2024])["status"] == "unavailable"
    s2 = synthetic_years(2015, 2025)
    for x in s2[:: 2]:
        x["precipitation_sum_mm"] = None
    assert hs.seasonal_deviation(s2, 2025, (6, 1), (9, 30), list(range(2015, 2025)))["status"] == "unavailable"


def test_seasonal_endpoint_param_validation(client: TestClient):
    assert client.get("/api/history/seasonal?latitude=16&longitude=80&start_month=9&end_month=6").status_code == 422
    assert client.get("/api/history/seasonal?latitude=16&longitude=80&baseline_years=2").status_code == 422


# ---------- Monitoring (F18) ----------
def test_monitoring_ledger_records_failures_and_success(client: TestClient, mock_http: Callable[..., None]):
    mock_http({"api.open-meteo.com": (500, {})})
    client.get("/api/weather/current?latitude=16.3&longitude=80.4")
    assert monitoring.snapshot()["weather"]["failures"] == 1 and monitoring.status_for("weather") == "unavailable"
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    from app.services import weather_service
    weather_service.clear_cache()
    client.get("/api/weather/current?latitude=16.3&longitude=80.4")
    s = client.get("/api/monitoring/status").json()
    assert s["providers"]["weather"]["last_success"] and client.get("/api/health").json()["services"]["weather_provider"] == "available"


def test_bounded_retry_on_rate_limit(client: TestClient, monkeypatch: pytest.MonkeyPatch, mock_http: Callable[..., None]):                  # E30
    monkeypatch.setenv("PROVIDER_MAX_RETRIES", "2")
    from app.core.config import get_settings
    get_settings.cache_clear()
    calls = {"n": 0}
    import httpx
    def h(req):
        calls["n"] += 1
        return httpx.Response(429, json={}) if calls["n"] < 3 else httpx.Response(200, json=make_forecast())
    mock_http({"api.open-meteo.com": h})
    assert client.get("/api/weather/current?latitude=16.3&longitude=80.4").status_code == 200 and calls["n"] == 3
    calls["n"] = 0
    def always(req):
        calls["n"] += 1
        return httpx.Response(429, json={})
    from app.services import weather_service
    weather_service.clear_cache()
    mock_http({"api.open-meteo.com": always})
    r = client.get("/api/weather/current?latitude=17&longitude=81")
    assert r.status_code in (502, 503, 504) and calls["n"] == 3


def test_integration_contract():
    from app.services.integrations import base
    c = base.DataContract("soil", "1", {"ph": "float", "district": "str"}, "monthly", "CC0")
    assert base.check_required_fields([{"ph": 6.5, "district": "x"}], c).passed
    assert not base.check_required_fields([{"ph": 6.5}], c).passed and not base.check_required_fields([], c).passed
    with pytest.raises(ValueError):
        base.register("bad", object())
