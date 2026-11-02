"""SYNTHETIC TEST FIXTURES - never imported by application code (checked in test_api.py). Not real weather."""
from datetime import datetime, timedelta, timezone

IST = 19800


def make_forecast(rain=None, tmax=None, tmin=None, days=7, current_age_min=5, drop=(), units=None, lat=16.3, lon=80.4):
    now = datetime.now(timezone(timedelta(seconds=IST))).replace(microsecond=0, second=0)
    cur_time = (now - timedelta(minutes=current_age_min)).strftime("%Y-%m-%dT%H:%M")
    start = now.date()
    dates = [(start + timedelta(days=i)).isoformat() for i in range(days)]
    rain = rain if rain is not None else [0.0] * days
    tmax = tmax if tmax is not None else [32.0] * days
    tmin = tmin if tmin is not None else [24.0] * days
    hours = [(datetime.combine(start, datetime.min.time()) + timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M") for h in range(24 * min(days, 3))]
    cur = {"time": cur_time, "interval": 900, "temperature_2m": 31.2, "relative_humidity_2m": 62, "apparent_temperature": 35.0, "precipitation": 0.0, "rain": 0.0,
           "showers": 0.0, "weather_code": 2, "cloud_cover": 40, "wind_speed_10m": 11.5, "wind_direction_10m": 225}
    for k in drop:
        cur.pop(k, None)
    raw = {"latitude": lat, "longitude": lon, "elevation": 20.0, "timezone": "Asia/Kolkata", "utc_offset_seconds": IST,
           "current_units": units or {"temperature_2m": "°C", "wind_speed_10m": "km/h", "precipitation": "mm"},
           "hourly_units": {"temperature_2m": "°C", "precipitation": "mm", "wind_speed_10m": "km/h"},
           "daily_units": {"temperature_2m_max": "°C", "precipitation_sum": "mm", "wind_speed_10m_max": "km/h"},
           "current": cur,
           "hourly": {"time": hours, "temperature_2m": [30.0] * len(hours), "relative_humidity_2m": [60] * len(hours), "precipitation": [0.0] * len(hours),
                      "cloud_cover": [30] * len(hours), "wind_speed_10m": [10.0] * len(hours), "wind_direction_10m": [200] * len(hours), "weather_code": [1] * len(hours)},
           "daily": {"time": dates, "temperature_2m_max": tmax, "temperature_2m_min": tmin, "precipitation_sum": rain, "wind_speed_10m_max": [20.0] * days, "weather_code": [3] * days}}
    return raw


def make_geocode(results):
    return {"results": results}


AP_RESULT = {"id": 1, "name": "Guntur", "latitude": 16.3, "longitude": 80.45, "admin1": "Andhra Pradesh", "admin2": "Guntur", "country_code": "IN"}
OTHER_RESULT = {"id": 2, "name": "Guntur Colony", "latitude": 17.4, "longitude": 78.5, "admin1": "Telangana", "admin2": "Hyderabad", "country_code": "IN"}
