"""Unit normalisation (L3): Celsius, mm, km/h, %."""
from typing import Optional

WIND_TO_KMH = {"km/h": 1.0, "kmh": 1.0, "m/s": 3.6, "mp/h": 1.609344, "mph": 1.609344, "kn": 1.852}
CARDINALS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def to_celsius(v: Optional[float], unit: str) -> Optional[float]:
    if v is None:
        return None
    u = (unit or "").replace("°", "").strip().upper()
    if u in ("F", "FAHRENHEIT"):
        return round((v - 32) * 5 / 9, 2)
    return v


def to_mm(v: Optional[float], unit: str) -> Optional[float]:
    if v is None:
        return None
    u = (unit or "").strip().lower()
    if u in ("inch", "in"):
        return round(v * 25.4, 3)
    if u == "cm":
        return round(v * 10, 3)
    return v


def to_kmh(v: Optional[float], unit: str) -> Optional[float]:
    if v is None:
        return None
    return round(v * WIND_TO_KMH.get((unit or "km/h").strip().lower(), 1.0), 2)


def cardinal(deg: Optional[float]) -> Optional[str]:
    if deg is None:
        return None
    return CARDINALS[int((deg % 360) / 22.5 + 0.5) % 16]
