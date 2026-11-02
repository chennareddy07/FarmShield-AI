import asyncio

import httpx
import pytest

from app.core.errors import AppError
from app.services import location_service, weather_service
from app.utils import units
from tests.conftest import mock_transport
from tests.fixtures.open_meteo import AP_RESULT, OTHER_RESULT, make_forecast, make_geocode
from datetime import datetime, timezone


# ---------- Location (F1, AC3, E1-E4) ----------
def test_empty_location_rejected(client):
    r = client.get("/api/locations/search?q=%20%20")
    assert r.status_code == 422 and r.json()["error_code"] == "empty_location"


def test_missing_location_param(client):
    assert client.get("/api/locations/search").status_code == 422


def test_short_query_rejected(client):
    assert client.get("/api/locations/search?q=a").status_code == 422


def test_search_filters_to_andhra_pradesh(client, mock_http):
    mock_http({"geocoding-api": (200, make_geocode([AP_RESULT, OTHER_RESULT]))})
    r = client.get("/api/locations/search?q=Guntur").json()
    assert [x["name"] for x in r["results"]] == ["Guntur"]
    res = r["results"][0]
    assert -90 <= res["latitude"] <= 90 and -180 <= res["longitude"] <= 180 and res["resolution_note"]


def test_unresolved_location_message(client, mock_http):
    mock_http({"geocoding-api": (200, make_geocode([OTHER_RESULT]))})
    r = client.get("/api/locations/search?q=Nowhere").json()
    assert r["results"] == [] and "broader" in r["message"]            # E3


def test_geocoder_outage_is_controlled_error(client, mock_http):
    mock_http({"geocoding-api": (503, {})})
    r = client.get("/api/locations/search?q=Guntur")
    assert r.status_code in (502, 503, 504) and r.json()["error_code"] == "geocoding_unavailable"


@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181), (float("nan"), 0)])
def test_coordinate_validation(lat, lon):
    with pytest.raises(AppError) as e:
        location_service.validate_coordinates(lat, lon)
    assert e.value.status == 422


def test_coordinates_ok_and_pilot_region():
    location_service.validate_coordinates(16.3, 80.4)
    assert location_service.in_pilot_region(16.3, 80.4) and not location_service.in_pilot_region(28.6, 77.2)


def test_district_list_has_no_hardcoded_coordinates(client):
    r = client.get("/api/regions").json()
    assert len(r["districts"]) >= 20 and r["review_status"] == "needs_review"
    import json
    raw = json.load(open(location_service.REGION_FILE))
    assert "latitude" not in json.dumps(raw)


# ---------- Weather normalisation (F2, AC4-AC6, E5-E7) ----------
def _bundle(**kw):
    raw = make_forecast(**kw)
    return weather_service.normalise(raw, datetime.now(timezone.utc), 7, 60)


def test_normalise_basic_fields():
    b = _bundle(rain=[1, 2, 3, 4, 5, 6, 7])
    assert b.current.temperature_c == 31.2 and b.current.wind_direction_cardinal == "SW"
    assert len(b.daily) == 7 and b.daily[0].forecast_for and b.hourly[0].forecast_for.endswith("+05:30")
    assert b.units["wind_speed"] == "km/h" and b.data_quality.status == "fresh" and b.timezone == "Asia/Kolkata"


def test_missing_variable_is_partial_not_zero():
    b = _bundle(drop=("cloud_cover",))
    assert b.current.cloud_cover_pct is None and "cloud_cover" in b.current.missing
    assert b.data_quality.status == "partial" and "cloud_cover" in b.data_quality.missing_variables


def test_missing_rainfall_never_becomes_zero():
    b = _bundle(rain=[None, 0.0, 1, 1, 1, 1, 1])
    assert b.daily[0].precipitation_sum_mm is None and b.daily[1].precipitation_sum_mm == 0.0
    assert "daily.precipitation_sum" in b.data_quality.missing_variables


def test_stale_detection():
    b = _bundle(current_age_min=300)
    assert b.data_quality.status == "stale" and b.data_quality.age_minutes > 60


def test_unit_conversions():
    assert units.to_kmh(10, "m/s") == 36.0 and units.to_kmh(10, "mp/h") == 16.09
    assert units.to_celsius(212, "°F") == 100.0 and units.to_mm(1, "inch") == 25.4
    assert units.cardinal(0) == "N" and units.cardinal(None) is None


def test_non_metric_provider_units_are_converted():
    raw = make_forecast(units={"temperature_2m": "°F", "wind_speed_10m": "mp/h", "precipitation": "inch"})
    raw["current"]["temperature_2m"] = 86.0
    b = weather_service.normalise(raw, datetime.now(timezone.utc), 7, 60)
    assert b.current.temperature_c == 30.0 and b.current.wind_speed_kmh == round(11.5 * 1.609344, 2)
    assert b.original_units["current.temperature_2m"] == "°F"


def test_weather_endpoints_success(client, mock_http):
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    cur = client.get("/api/weather/current?latitude=16.3&longitude=80.4").json()
    assert cur["provider"] == "Open-Meteo" and cur["observed_at"] and cur["retrieved_at"] and cur["units"] and cur["data_quality"]["status"] == "fresh"
    fc = client.get("/api/weather/forecast?latitude=16.3&longitude=80.4&days=7").json()
    assert len(fc["daily"]) == 7 and len(fc["hourly"]) > 0 and "Open-Meteo" in fc["attribution"]


def test_weather_provider_down_returns_unavailable_not_fake(client, mock_http):
    mock_http({"api.open-meteo.com": (500, {})})
    r = client.get("/api/weather/current?latitude=16.3&longitude=80.4")
    assert r.status_code in (502, 503, 504) and r.json()["error_code"] == "weather_unavailable"
    assert "current" not in r.json()                                    # AC6


def test_weather_malformed_response_is_error(client, mock_http):
    mock_http({"api.open-meteo.com": (200, {"unexpected": True})})
    assert client.get("/api/weather/current?latitude=16.3&longitude=80.4").status_code in (502, 503)


def test_stale_cache_served_and_marked_when_provider_fails(client, mock_http, monkeypatch):
    mock_http({"api.open-meteo.com": (200, make_forecast())})
    assert client.get("/api/weather/current?latitude=16.3&longitude=80.4").status_code == 200
    from app.core.config import get_settings
    monkeypatch.setenv("WEATHER_CACHE_SECONDS", "0")
    get_settings.cache_clear()
    mock_http({"api.open-meteo.com": (500, {})})
    r = client.get("/api/weather/current?latitude=16.3&longitude=80.4").json()
    assert r["data_quality"]["status"] == "stale" and any("unavailable" in n for n in r["data_quality"]["notes"])    # E7


def test_weather_cache_coalesces_concurrent_requests_and_returns_isolated_copies():
    from app.core import http

    calls = 0

    def handler(_request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=make_forecast())

    http.set_transport(httpx.MockTransport(handler))

    async def fetch_pair():
        _, pool = weather_service._fetch_lock((16.3, 80.4, 7))
        pair = await asyncio.gather(
            weather_service.fetch_weather(16.3, 80.4),
            weather_service.fetch_weather(16.3, 80.4),
        )
        assert len(pool.locks) == weather_service.FETCH_LOCK_STRIPES
        return pair

    first, second = asyncio.run(fetch_pair())
    assert calls == 1
    first.current.temperature_c = -999
    cached = asyncio.run(weather_service.fetch_weather(16.3, 80.4))
    assert cached.current.temperature_c != -999


def test_weather_cache_has_a_fixed_size(monkeypatch):
    from app.core import http

    monkeypatch.setattr(weather_service, "CACHE_MAX_ENTRIES", 2)
    http.set_transport(mock_transport({"api.open-meteo.com": (200, make_forecast())}))

    async def fetch_locations():
        for offset in range(3):
            await weather_service.fetch_weather(16.3 + offset, 80.4)

    asyncio.run(fetch_locations())
    assert len(weather_service._cache) == 2


def test_forecast_days_validation(client):
    assert client.get("/api/weather/forecast?latitude=16&longitude=80&days=99").status_code == 422
