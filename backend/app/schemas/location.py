from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class Coordinates(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class LocationResult(BaseModel):
    location_id: str
    name: str
    district: Optional[str] = None
    mandal: Optional[str] = None
    state: Optional[str] = None
    latitude: float
    longitude: float
    source: Literal["search", "geolocation", "saved_profile"] = "search"
    resolution_note: str = ("Weather is modelled on a grid (roughly 1-25 km depending on the provider model). "
                            "A district or town centre does not represent every village in the district.")

    @field_validator("latitude")
    @classmethod
    def _lat(cls, v):
        if not -90 <= v <= 90:
            raise ValueError("latitude out of range")
        return v
