from typing import List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatLocation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    name: Optional[str] = Field(default=None, max_length=120)
    district: Optional[str] = Field(default=None, max_length=80)


class AdvisoryRequest(BaseModel):
    assessment_id: str
    language: Optional[str] = None
    question: Optional[str] = Field(default=None, max_length=600)
    profile_id: Optional[str] = None


class AdvisoryResponse(BaseModel):
    advisory_id: str
    summary: str
    risk_explanation: str
    recommended_actions: List[str] = Field(default_factory=list)   # immediate
    preventive_actions: List[str] = Field(default_factory=list)
    when_to_act: str = ""
    uncertainties: List[str] = Field(default_factory=list)
    evidence_ids: List[str] = Field(default_factory=list)
    language: str
    generated_at: str
    model_provider: str
    generation_status: Literal["ai_generated", "fallback_ai_unavailable", "fallback_invalid_output", "fallback_no_provider"]
    notices: List[str] = Field(default_factory=list)
    disclaimer: str = ""
    personalisation_note: Optional[str] = None
    evidence: List[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=800)
    location: Optional[ChatLocation] = None
    crop_id: Optional[str] = Field(default=None, max_length=40)
    growth_stage_id: Optional[str] = Field(default=None, max_length=60)
    language: Optional[str] = None
    conversation_id: Optional[str] = Field(default=None, max_length=40)
    assessment_id: Optional[str] = Field(default=None, max_length=40)


class ChatResponse(BaseModel):
    answer: str
    evidence: List[dict] = Field(default_factory=list)
    uncertainties: List[str] = Field(default_factory=list)
    conversation_id: str
    status: Literal["ai_generated", "retrieval_only", "out_of_scope", "fallback_invalid_output"]
    language: str
