"""Open-Meteo weather adapter (F2, F3). Normalises to the internal schema; never fabricates data (P1)."""
import logging
import time
import asyncio
import weakref
from collections import OrderedDict
from threading import RLock
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from ..core import monitoring
from ..core.config import get_settings
from ..core.errors import AppError
from ..core.http import ProviderError, request_json
from ..schemas.common import DataQuality
from ..schemas.weather import CurrentWeather, DailyPoint, HourlyPoint, WeatherBundle
from ..utils import units as U
from ..utils.timeutil import iso, localize, minutes_between, parse_iso, utcnow

log = logging.getLogger("farmshield.weather")
PROVIDER = "Open-Meteo"
CURRENT_VARS = ["temperature_2m", "relative_humidity_2m", "apparent_temperature", "precipitation", "rain", "showers",
                "weather_code", "cloud_cover", "wind_speed_10m", "wind_direction_10m"]
HOURLY_VARS = ["temperature_2m", "relative_humidity_2m", "precipitation", "cloud_cover", "wind_speed_10m", "wind_direction_10m", "weather_code"]
DAILY_VARS = ["temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max", "weather_code"]
NORMALISED_UNITS = {"temperature": "°C", "precipitation": "mm", "wind_speed": "km/h", "humidity": "%", "cloud_cover": "%", "wind_direction": "°"}

WMO = {0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast", 45: "Fog", 48: "Depositing rime fog",
       51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle", 56: "Light freezing drizzle", 57: "Dense freezing drizzle",
       61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain", 66: "Light freezing rain", 67: "Heavy freezing rain",
       71: "Slight snow", 73: "Moderate snow", 75: "Heavy snow", 77: "Snow grains", 80: "Slight rain showers",
       81: "Moderate rain showers", 82: "Violent rain showers", 85: "Slight snow showers", 86: "Heavy snow showers",
       95: "Thunderstorm", 96: "Thunderstorm with slight hail", 99: "Thunderstorm with heavy hail"}

CACHE_MAX_ENTRIES = 512
FETCH_LOCK_STRIPES = 64
_cache: "OrderedDict[Tuple[float, float, int], Tuple[WeatherBundle, float]]" = OrderedDict()
_lock_pools: "weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, weakref.ReferenceType[_FetchLockPool]]" = weakref.WeakKeyDictionary()
_cache_lock = RLock()


class _FetchLockPool:
    def __init__(self) -> None:
        self.locks = tuple(asyncio.Lock() for _ in range(FETCH_LOCK_STRIPES))


def _fetch_lock(key: Tuple[float, float, int]):
    loop = asyncio.get_running_loop()
    with _cache_lock:
        pool_ref = _lock_pools.get(loop)
        pool = pool_ref() if pool_ref else None
        if pool is None:
            pool = _FetchLockPool()
            _lock_pools[loop] = weakref.ref(pool)
        return pool.locks[hash(key) % len(pool.locks)], pool


def clear_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _prune_cache(now: float, stale_seconds: float) -> None:
    expired = [key for key, (_, stored_at) in _cache.items() if now - stored_at >= stale_seconds]
    for key in expired:
        _cache.pop(key, None)


def _copy_cached(bundle: WeatherBundle, stored_at: float, now: float, fresh_minutes: int,
                 unavailable_kind: Optional[str] = None) -> WeatherBundle:
    result = bundle.model_copy(deep=True)
    observed = parse_iso(result.current.observed_at) if result.current else None
    age = max(0.0, minutes_between(utcnow(), observed)) if observed else max(0.0, (now - stored_at) / 60)
    result.data_quality.age_minutes = round(age, 1)
    if result.data_quality.status == "stale" or age > fresh_minutes:
        result.data_quality.status = "stale"
    elif result.data_quality.missing_variables:
        result.data_quality.status = "partial"
    else:
        result.data_quality.status = "fresh"
    if unavailable_kind:
        result.data_quality.status = "stale"
        result.data_quality.notes.append(
            f"Provider unavailable ({unavailable_kind}); showing data retrieved {max(0.0, (now - stored_at) / 60):.0f} minutes ago.")
    return result


def wmo_summary(code: Optional[int]) -> Optional[str]:
    return WMO.get(code) if code is not None else None


def assess_freshness(observed_at: Optional[str], now: datetime, fresh_minutes: int, missing: List[str]) -> Tuple[str, Optional[float], List[str]]:
    """L4: returns (status, age_minutes, notes). Priority: stale > partial > fresh."""
    notes: List[str] = []
    age = None
    obs = parse_iso(observed_at)
    status = "fresh"
    if obs is not None:
        age = round(minutes_between(now, obs), 1)
        if age > fresh_minutes:
            status = "stale"
            notes.append(f"Latest provider observation/analysis is {age:.0f} minutes old.")
    if missing:
        notes.append("Missing variables: " + ", ".join(sorted(set(missing))))
        if status != "stale":
            status = "partial"
    return status, age, notes


def _col(block: dict, key: str, i: int):
    arr = block.get(key)
    if arr is None or i >= len(arr):
        return None
    return arr[i]


def normalise(raw: dict, retrieved_at: datetime, days: int, fresh_minutes: int, now: Optional[datetime] = None) -> WeatherBundle:
    """Pure function: provider JSON -> WeatherBundle. Unit-tested with synthetic fixtures."""
    now = now or retrieved_at
    off = int(raw.get("utc_offset_seconds") or 0)
    cu, hu, du = raw.get("current_units") or {}, raw.get("hourly_units") or {}, raw.get("daily_units") or {}
    original = {**{f"current.{k}": v for k, v in cu.items()}, **{f"hourly.{k}": v for k, v in hu.items()}, **{f"daily.{k}": v for k, v in du.items()}}
    missing: List[str] = []

    cur_obj = None
    c = raw.get("current")
    if c:
        cur_missing = [v for v in CURRENT_VARS if c.get(v) is None]
        missing += cur_missing
        code = c.get("weather_code")
        wd = c.get("wind_direction_10m")
        cur_obj = CurrentWeather(
            observed_at=localize(c.get("time"), off),
            temperature_c=U.to_celsius(c.get("temperature_2m"), cu.get("temperature_2m", "°C")),
            apparent_temperature_c=U.to_celsius(c.get("apparent_temperature"), cu.get("apparent_temperature", "°C")),
            relative_humidity_pct=c.get("relative_humidity_2m"),
            precipitation_mm=U.to_mm(c.get("precipitation"), cu.get("precipitation", "mm")),
            rain_mm=U.to_mm(c.get("rain"), cu.get("rain", "mm")), showers_mm=U.to_mm(c.get("showers"), cu.get("showers", "mm")),
            weather_code=int(code) if code is not None else None, weather_summary=wmo_summary(int(code)) if code is not None else None,
            cloud_cover_pct=c.get("cloud_cover"), wind_speed_kmh=U.to_kmh(c.get("wind_speed_10m"), cu.get("wind_speed_10m", "km/h")),
            wind_direction_deg=wd, wind_direction_cardinal=U.cardinal(wd), missing=cur_missing)

    hourly: List[HourlyPoint] = []
    h = raw.get("hourly") or {}
    times = h.get("time") or []
    start = 0
    if cur_obj and cur_obj.observed_at:
        cur_hour = (cur_obj.observed_at or "")[:13]
        for i, t in enumerate(times):
            if t[:13] >= cur_hour[:13]:
                start = i
                break
    for i in range(start, min(len(times), start + 48)):
        code = _col(h, "weather_code", i)
        hourly.append(HourlyPoint(
            forecast_for=localize(times[i], off), temperature_c=U.to_celsius(_col(h, "temperature_2m", i), hu.get("temperature_2m", "°C")),
            relative_humidity_pct=_col(h, "relative_humidity_2m", i), precipitation_mm=U.to_mm(_col(h, "precipitation", i), hu.get("precipitation", "mm")),
            cloud_cover_pct=_col(h, "cloud_cover", i), wind_speed_kmh=U.to_kmh(_col(h, "wind_speed_10m", i), hu.get("wind_speed_10m", "km/h")),
            wind_direction_deg=_col(h, "wind_direction_10m", i), weather_code=int(code) if code is not None else None))
    if hourly:
        for var, attr in (("temperature_2m", "temperature_c"), ("precipitation", "precipitation_mm"), ("relative_humidity_2m", "relative_humidity_pct")):
            if any(getattr(p, attr) is None for p in hourly):
                missing.append(f"hourly.{var}")

    daily: List[DailyPoint] = []
    d = raw.get("daily") or {}
    dtimes = d.get("time") or []
    for i, day in enumerate(dtimes[:days]):
        code = _col(d, "weather_code", i)
        daily.append(DailyPoint(
            forecast_for=day, temperature_max_c=U.to_celsius(_col(d, "temperature_2m_max", i), du.get("temperature_2m_max", "°C")),
            temperature_min_c=U.to_celsius(_col(d, "temperature_2m_min", i), du.get("temperature_2m_min", "°C")),
            precipitation_sum_mm=U.to_mm(_col(d, "precipitation_sum", i), du.get("precipitation_sum", "mm")),      # None stays None (never 0)
            wind_speed_max_kmh=U.to_kmh(_col(d, "wind_speed_10m_max", i), du.get("wind_speed_10m_max", "km/h")),
            weather_code=int(code) if code is not None else None, weather_summary=wmo_summary(int(code)) if code is not None else None))
    for var, attr in (("daily.temperature_2m_max", "temperature_max_c"), ("daily.temperature_2m_min", "temperature_min_c"), ("daily.precipitation_sum", "precipitation_sum_mm")):
        if daily and any(getattr(p, attr) is None for p in daily):
            missing.append(var)
    if not daily:
        missing.append("daily")

    status, age, notes = assess_freshness(cur_obj.observed_at if cur_obj else None, now, fresh_minutes, missing)
    notes.append("Current values are model analyses/nowcasts from Open-Meteo, not station observations.")
    return WeatherBundle(
        latitude=raw.get("latitude"), longitude=raw.get("longitude"), elevation_m=raw.get("elevation"), timezone=raw.get("timezone", "UTC"),
        utc_offset_seconds=off, retrieved_at=iso(retrieved_at), units=dict(NORMALISED_UNITS), original_units=original,
        current=cur_obj, hourly=hourly, daily=daily,
        data_quality=DataQuality(status=status, provider=PROVIDER, retrieved_at=iso(retrieved_at), age_minutes=age, missing_variables=sorted(set(missing)), notes=notes))


async def fetch_weather(latitude: float, longitude: float, days: int = 7, use_cache: bool = True) -> WeatherBundle:
    s = get_settings()
    key = (round(latitude, 2), round(longitude, 2), days)
    now_m = time.monotonic()
    with _cache_lock:
        _prune_cache(now_m, s.weather_stale_minutes * 60)
        cached = _cache.get(key)
        if cached:
            _cache.move_to_end(key)
            if use_cache and now_m - cached[1] < s.weather_cache_seconds:
                return _copy_cached(cached[0], cached[1], now_m, s.weather_fresh_minutes)

    lock, _lock_pool = _fetch_lock(key)
    async with lock:
        now_m = time.monotonic()
        with _cache_lock:
            _prune_cache(now_m, s.weather_stale_minutes * 60)
            cached = _cache.get(key)
            if cached:
                _cache.move_to_end(key)
                if use_cache and now_m - cached[1] < s.weather_cache_seconds:
                    return _copy_cached(cached[0], cached[1], now_m, s.weather_fresh_minutes)
        params = {"latitude": latitude, "longitude": longitude, "current": ",".join(CURRENT_VARS), "hourly": ",".join(HOURLY_VARS),
                  "daily": ",".join(DAILY_VARS), "forecast_days": days, "timezone": "auto", "wind_speed_unit": "kmh",
                  "temperature_unit": "celsius", "precipitation_unit": "mm"}
        try:
            raw = await request_json(PROVIDER, "GET", f"{s.open_meteo_base_url.rstrip('/')}/v1/forecast", params=params)
            if not isinstance(raw, dict) or ("current" not in raw and "daily" not in raw and "hourly" not in raw):
                raise ProviderError(PROVIDER, "bad_response", "Unexpected provider response shape.")
            bundle = normalise(raw, utcnow(), days, s.weather_fresh_minutes)
            monitoring.record_success("weather")
            stored_at = time.monotonic()
            with _cache_lock:
                _cache[key] = (bundle, stored_at)
                _cache.move_to_end(key)
                _prune_cache(stored_at, s.weather_stale_minutes * 60)
                while len(_cache) > CACHE_MAX_ENTRIES:
                    _cache.popitem(last=False)
            return bundle.model_copy(deep=True)
        except ProviderError as e:
            monitoring.record_failure("weather", e.kind)
            if cached and now_m - cached[1] < s.weather_stale_minutes * 60:
                return _copy_cached(cached[0], cached[1], now_m, s.weather_fresh_minutes, e.kind)
            raise AppError(e.http_status, "weather_unavailable", "Live weather information is currently unavailable. Please try again later.",
                           {"provider": PROVIDER, "kind": e.kind})
