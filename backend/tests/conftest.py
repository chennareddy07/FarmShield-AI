import json
import os
import tempfile

import httpx
import pytest

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["LLM_PROVIDER"] = "disabled"
os.environ["APP_ENV"] = "test"
os.environ["PROVIDER_MAX_RETRIES"] = "0"

from app.core import db, http, monitoring  # noqa: E402
from app.core.config import Settings, get_settings  # noqa: E402


@pytest.fixture(autouse=True)
def _isolate(monkeypatch):
    monkeypatch.setattr(Settings, "model_config", {**Settings.model_config, "env_file": None})
    get_settings.cache_clear()
    db.reset_engine()
    from app.models import tables  # noqa
    db.Base.metadata.drop_all(db.get_engine()) if False else None
    db.init_db()
    from sqlalchemy import text
    with db.get_engine().begin() as c:
        for t in ("assessments", "profiles", "subscriptions", "notifications", "conversations", "knowledge_chunks", "knowledge_documents"):
            c.execute(text(f"DELETE FROM {t}"))
    from app.services import knowledge_service, weather_service, location_service, regional_service, assessment_service, crop_config_service, market_service
    from app.engine import rule_loader
    weather_service.clear_cache(); location_service.clear_cache(); regional_service.clear_cache(); rule_loader.clear_cache()
    assessment_service._memory.clear()
    market_service.clear_cache()
    knowledge_service.seed_from_metadata_dir()
    monitoring.reset()
    http.set_transport(None)
    from app.ai import llm_provider
    llm_provider.set_provider_override(None)
    yield
    http.set_transport(None)
    llm_provider.set_provider_override(None)
    get_settings.cache_clear()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app()) as c:
        yield c


def mock_transport(routes: dict):
    """routes: substring-of-url -> (status, json|str) or callable(request)->httpx.Response"""
    def handler(request: httpx.Request) -> httpx.Response:
        for key, val in routes.items():
            if key in str(request.url):
                if callable(val):
                    return val(request)
                status, body = val
                return httpx.Response(status, json=body) if not isinstance(body, str) else httpx.Response(status, text=body)
        return httpx.Response(404, json={"error": "no mock"})
    return httpx.MockTransport(handler)


@pytest.fixture
def mock_http():
    def _set(routes):
        http.set_transport(mock_transport(routes))
    return _set
