"""Historical analysis (F11) and seasonal rainfall deviation (F25, partial). Open-Meteo Historical = ERA5 REANALYSIS, not station observations."""
import logging
from collections import defaultdict
from datetime import date, timedelta
from typing import Dict, List, Optional

from ..core import monitoring
from ..core.config import get_settings
from ..core.errors import AppError
from ..core.http import ProviderError, request_json
from ..utils.timeutil import iso, utcnow

log = logging.getLogger("farmshield.history")
PROVIDER = "Open-Meteo Historical (ERA5 reanalysis)"
MAX_RANGE_DAYS = 3700
DAILY = "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"
LIMITATIONS = ["Reanalysis data (ERA5) is a modelled reconstruction on a coarse grid, not a station observation.",
               "Recent days (about the last 5) may be unavailable.",
               "A difference between periods is not, by itself, a scientifically established climate trend."]


def parse_dates(start: str, end: str) -> tuple:
    try:
        s, e = date.fromisoformat(start), date.fromisoformat(end)
    except (ValueError, TypeError):
        raise AppError(422, "invalid_date", "Dates must be in YYYY-MM-DD format.")
    if s > e:
        raise AppError(422, "invalid_date_range", "start_date must not be after end_date.")
    if (e - s).days > MAX_RANGE_DAYS:
        raise AppError(422, "date_range_too_long", f"Maximum range is {MAX_RANGE_DAYS} days.")
    if e > date.today():
        raise AppError(422, "future_date", "Historical analysis cannot include future dates.")
    return s, e


def build_series(raw: dict) -> List[dict]:
    d = raw.get("daily") or {}
    times = d.get("time") or []
    g = lambda k, i: (d.get(k) or [None] * len(times))[i] if i < len(d.get(k) or []) else None
    return [{"date": t, "temperature_max_c": g("temperature_2m_max", i), "temperature_min_c": g("temperature_2m_min", i),
             "temperature_mean_c": g("temperature_2m_mean", i), "precipitation_sum_mm": g("precipitation_sum", i)} for i, t in enumerate(times)]


def coverage(series: List[dict], start: date, end: date) -> dict:
    expected = (end - start).days + 1
    have = [s for s in series if s["precipitation_sum_mm"] is not None]
    have_t = [s for s in series if s["temperature_mean_c"] is not None]
    return {"expected_days": expected, "days_with_rainfall": len(have), "days_with_temperature": len(have_t),
            "rainfall_coverage_pct": round(100 * len(have) / expected, 1) if expected else 0,
            "temperature_coverage_pct": round(100 * len(have_t) / expected, 1) if expected else 0}


def monthly_summary(series: List[dict]) -> List[dict]:
    by: Dict[str, List[dict]] = defaultdict(list)
    for s in series:
        by[s["date"][:7]].append(s)
    out = []
    for m, rows in sorted(by.items()):
        rain = [r["precipitation_sum_mm"] for r in rows if r["precipitation_sum_mm"] is not None]
        tmax = [r["temperature_max_c"] for r in rows if r["temperature_max_c"] is not None]
        tmin = [r["temperature_min_c"] for r in rows if r["temperature_min_c"] is not None]
        out.append({"month": m, "rainfall_total_mm": round(sum(rain), 1) if rain else None, "days_with_rainfall_data": len(rain), "days_in_range": len(rows),
                    "temperature_max_mean_c": round(sum(tmax) / len(tmax), 1) if tmax else None, "temperature_min_mean_c": round(sum(tmin) / len(tmin), 1) if tmin else None,
                    "rain_days_ge_2.5mm": sum(1 for r in rain if r >= 2.5)})
    return out


async def fetch_history(lat: float, lon: float, start: str, end: str) -> dict:
    s_, e_ = parse_dates(start, end)
    st = get_settings()
    try:
        raw = await request_json(PROVIDER, "GET", f"{st.open_meteo_archive_url.rstrip('/')}/v1/archive",
                                 params={"latitude": lat, "longitude": lon, "start_date": s_.isoformat(), "end_date": e_.isoformat(), "daily": DAILY,
                                         "timezone": "auto", "temperature_unit": "celsius", "precipitation_unit": "mm"})
        monitoring.record_success("history")
    except ProviderError as e:
        monitoring.record_failure("history", e.kind)
        raise AppError(e.http_status, "history_unavailable", "Historical data is currently unavailable.", {"provider": PROVIDER, "kind": e.kind})   # E18
    series = build_series(raw)
    cov = coverage(series, s_, e_)
    notes = []
    if cov["rainfall_coverage_pct"] < 90:
        notes.append("Rainfall coverage is below 90% of the requested range; totals and comparisons may be misleading.")     # AC20
    return {"series": series, "monthly": monthly_summary(series), "units": {"temperature": "°C", "precipitation": "mm"}, "provider": PROVIDER,
            "data_type": "reanalysis", "coverage": cov, "notes": notes, "limitations": LIMITATIONS, "retrieved_at": iso(utcnow()),
            "attribution": "Weather data by Open-Meteo.com (CC BY 4.0)", "latitude": raw.get("latitude"), "longitude": raw.get("longitude")}


def seasonal_deviation(series: List[dict], year: int, start_md: tuple, end_md: tuple, baseline_years: List[int], cutoff: Optional[date] = None) -> dict:
    """Pure function. Period-matched comparison of rainfall in (start_md..end_md) between `year` and the mean of baseline years.
    Returns status 'unavailable' unless baseline coverage is adequate (>=5 years and >=90% of days)."""
    by_year: Dict[int, List[dict]] = defaultdict(list)
    for s in series:
        by_year[int(s["date"][:4])].append(s)

    def window(y: int):
        a = date(y, *start_md)
        b = date(y, *end_md)
        if cutoff and y == year and cutoff < b:
            b = cutoff
        return a, b

    def total(y: int):
        a, b = window(y)
        rows = [r for r in by_year.get(y, []) if a <= date.fromisoformat(r["date"]) <= b]
        n = (b - a).days + 1
        vals = [r["precipitation_sum_mm"] for r in rows if r["precipitation_sum_mm"] is not None]
        return (sum(vals), len(vals) / n if n > 0 else 0, n)

    cur_total, cur_cov, n_days = total(year)
    base = [(y,) + total(y) for y in baseline_years]
    good = [b for b in base if b[2] >= 0.9]
    method = (f"Compared total rainfall for {date(2000, *start_md):%d %b} to {date(2000, *end_md):%d %b} (period-matched to the same calendar days) in {year} "
              f"against the arithmetic mean of {len(good)} baseline years. This is a simple difference, not a climate-trend or drought-probability estimate.")
    if len(good) < 5 or cur_cov < 0.9:
        return {"status": "unavailable", "reason": "Insufficient data coverage for a valid comparison (need at least 5 baseline years and at least 90% daily coverage).",
                "baseline_years_used": [b[0] for b in good], "current_coverage_pct": round(cur_cov * 100, 1), "method": method}
    mean = sum(b[1] for b in good) / len(good)
    dev = cur_total - mean
    return {"status": "available", "year": year, "observed_total_mm": round(cur_total, 1), "baseline_mean_mm": round(mean, 1), "deviation_mm": round(dev, 1),
            "deviation_pct": round(100 * dev / mean, 1) if mean > 0 else None, "baseline_years_used": [b[0] for b in good],
            "baseline_totals_mm": {str(b[0]): round(b[1], 1) for b in good}, "days_in_window": n_days, "method": method, "limitations": LIMITATIONS}


async def fetch_seasonal(lat: float, lon: float, start_month: int, end_month: int, baseline_years: int = 10) -> dict:
    if not (1 <= start_month <= 12 and 1 <= end_month <= 12) or start_month > end_month:
        raise AppError(422, "invalid_season", "Months must be 1-12 with start_month <= end_month (seasons crossing the new year are not supported yet).")
    if not 5 <= baseline_years <= 30:
        raise AppError(422, "invalid_baseline", "baseline_years must be between 5 and 30.")
    today = date.today()
    year = today.year
    first = date(year - baseline_years, 1, 1)
    data = await fetch_history(lat, lon, first.isoformat(), (today - timedelta(days=1)).isoformat())
    last_day = (date(year, end_month, 28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    cutoff = min(today - timedelta(days=6), last_day)         # reanalysis lag
    res = seasonal_deviation(data["series"], year, (start_month, 1), (end_month, last_day.day), list(range(year - baseline_years, year)), cutoff)
    return {"comparison": res, "provider": PROVIDER, "data_type": "reanalysis", "retrieved_at": data["retrieved_at"], "coverage": data["coverage"]}
