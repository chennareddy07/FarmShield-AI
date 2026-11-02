from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

from .common import DataQuality, RiskLevel


class RiskRequest(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    crop_id: str
    growth_stage_id: Optional[str] = None
    language: str = "en"
    district: Optional[str] = None
    location_name: Optional[str] = None
    profile_id: Optional[str] = None
    forecast_days: int = Field(default=7, ge=1, le=16)

    @field_validator("crop_id")
    @classmethod
    def _crop(cls, v):
        return v.strip().lower()


class EvidenceItem(BaseModel):
    evidence_id: str
    kind: Literal["risk_rule", "agricultural_reference", "meteorological_reference", "official_warning", "forecast"]
    title: str
    publisher: Optional[str] = None
    publication_date: Optional[str] = None
    excerpt: Optional[str] = None
    source_url: Optional[str] = None
    verification_status: Optional[str] = None
    evidence_status: Optional[str] = None
    source_access_status: Optional[str] = None
    evidence_class: Optional[str] = None
    document_id: Optional[str] = None
    crop_id: Optional[str] = None
    growth_stage_id: Optional[str] = None
    state: Optional[str] = None
    districts: List[str] = Field(default_factory=list)
    seasons: List[str] = Field(default_factory=list)
    concern: Optional[str] = None
    source_section: Optional[str] = None
    limitations: Optional[str] = None


class RuleEvaluation(BaseModel):
    rule_id: str
    risk_category: str
    state: Literal["triggered", "not_triggered", "not_evaluable", "disabled_unverified", "not_applicable"]
    severity: Optional[str] = None
    weather_variable: Optional[str] = None
    operator: Optional[str] = None
    threshold: Optional[float] = None
    threshold_unit: Optional[str] = None
    source_time_window: Optional[str] = None
    weather_input_time_window: Optional[str] = None
    actual_value: Optional[float] = None
    period: Optional[str] = None                 # human readable time period examined
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    reason: str
    source_reference: Optional[Dict[str, Any]] = None
    evidence_id: Optional[str] = None
    review_status: Optional[str] = None
    rule_version: Optional[str] = None


class RiskCategoryResult(BaseModel):
    category: str
    label: str
    risk: RiskLevel
    risk_label: str
    reason: str
    rule_ids: List[str] = Field(default_factory=list)


class RecommendedAction(BaseModel):
    kind: Literal["immediate", "preventive", "general"]
    text: str
    evidence_ids: List[str] = Field(default_factory=list)
    verified: bool = False


class TimelineEvent(BaseModel):
    rule_id: str
    category: str
    start: str
    end: str
    severity: str
    actual_value: Optional[float] = None
    unit: Optional[str] = None
    label: str


class RiskAssessment(BaseModel):
    assessment_id: str
    request_id: str
    location: Dict[str, Any]
    crop_id: str
    crop_name: str
    growth_stage_id: Optional[str] = None
    growth_stage_name: Optional[str] = None
    assessment_time: str
    forecast_window: Dict[str, Optional[str]]
    overall_risk: RiskLevel
    overall_risk_label: str
    risk_categories: List[RiskCategoryResult]
    triggered_rules: List[RuleEvaluation]
    all_evaluations: List[RuleEvaluation] = Field(default_factory=list)
    explanations: List[str]
    recommended_actions: List[RecommendedAction]
    evidence: List[EvidenceItem]
    timeline: List[TimelineEvent] = Field(default_factory=list)
    coverage: Dict[str, Any]
    data_quality: Dict[str, DataQuality]
    warnings_status: str = "unavailable"
    confidence_label: str
    stage_specific: bool
    rule_version: str
    language: str
    notices: List[str] = Field(default_factory=list)
    disclaimer: str
    method_note: str = "Rule-based classification from documented rules. Not a machine-learning prediction."
