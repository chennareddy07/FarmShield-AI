from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from .common import DataQuality


class CurrentWeather(BaseModel):
    observed_at: Optional[str] = None            # model analysis time reported by provider (not a station reading)
    kind: str = "model_analysis"
    temperature_c: Optional[float] = None
    apparent_temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    rain_mm: Optional[float] = None
    showers_mm: Optional[float] = None
    weather_code: Optional[int] = None
    weather_summary: Optional[str] = None
    cloud_cover_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    wind_direction_cardinal: Optional[str] = None
    missing: List[str] = Field(default_factory=list)


class HourlyPoint(BaseModel):
    forecast_for: str
    temperature_c: Optional[float] = None
    relative_humidity_pct: Optional[float] = None
    precipitation_mm: Optional[float] = None
    cloud_cover_pct: Optional[float] = None
    wind_speed_kmh: Optional[float] = None
    wind_direction_deg: Optional[float] = None
    weather_code: Optional[int] = None


class DailyPoint(BaseModel):
    forecast_for: str                            # local date YYYY-MM-DD
    temperature_max_c: Optional[float] = None
    temperature_min_c: Optional[float] = None
    precipitation_sum_mm: Optional[float] = None  # Open-Meteo local-calendar-day total; not an IMD 24-hour observation
    wind_speed_max_kmh: Optional[float] = None
    weather_code: Optional[int] = None
    weather_summary: Optional[str] = None


class WeatherBundle(BaseModel):
    provider: str = "Open-Meteo"
    attribution: str = "Weather data by Open-Meteo.com (CC BY 4.0)"
    latitude: float
    longitude: float
    elevation_m: Optional[float] = None
    timezone: str
    utc_offset_seconds: int = 0
    retrieved_at: str
    units: Dict[str, str]
    original_units: Dict[str, str] = Field(default_factory=dict)
    spatial_note: str = "Gridded model data for the point nearest the requested coordinates; not a farm-level measurement."
    current: Optional[CurrentWeather] = None
    hourly: List[HourlyPoint] = Field(default_factory=list)
    daily: List[DailyPoint] = Field(default_factory=list)
    data_quality: DataQuality
