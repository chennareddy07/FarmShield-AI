from typing import List, Literal, Optional

from pydantic import BaseModel, Field

Freshness = Literal["fresh", "stale", "unavailable", "partial"]
RiskLevel = Literal["low", "moderate", "high", "critical", "insufficient_data"]
SEVERITY_ORDER = {"low": 0, "moderate": 1, "high": 2, "critical": 3}


class DataQuality(BaseModel):
    status: Freshness
    provider: str
    retrieved_at: Optional[str] = None
    age_minutes: Optional[float] = None
    missing_variables: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)


class ErrorBody(BaseModel):
    error_code: str
    message: str
    request_id: str
    details: Optional[object] = None
