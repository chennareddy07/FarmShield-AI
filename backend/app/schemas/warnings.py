from typing import List, Literal, Optional

from pydantic import BaseModel, Field

OFFICIAL_LINKS = [
    {"label": "IMD - India Meteorological Department", "url": "https://mausam.imd.gov.in/"},
    {"label": "IMD Amaravati (Andhra Pradesh)", "url": "https://mausam.imd.gov.in/amaravati/"},
    {"label": "IMD district-wise warnings", "url": "https://mausam.imd.gov.in/responsive/districtWiseWarning.php"},
]


class Warning(BaseModel):
    warning_id: str
    source: str
    title: str
    description: Optional[str] = None
    warning_type: Optional[str] = None
    severity: Optional[str] = None               # exactly as supplied by the source
    severity_color: Optional[str] = None
    affected_area: Optional[str] = None
    issued_at: Optional[str] = None
    valid_from: Optional[str] = None
    valid_until: Optional[str] = None
    source_url: Optional[str] = None
    retrieved_at: str


class WarningsResponse(BaseModel):
    warnings: List[Warning] = Field(default_factory=list)
    source_status: Literal["available", "unavailable", "not_configured", "partial", "stale"]
    source_status_message: Optional[str] = None
    retrieved_at: str
    district: Optional[str] = None
    official_links: List[dict] = Field(default_factory=lambda: list(OFFICIAL_LINKS))
