from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.db import Base


def _now():
    return datetime.now(timezone.utc)


class Profile(Base):                      # F13 - opt-in only
    __tablename__ = "profiles"
    profile_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    nickname: Mapped[str | None] = mapped_column(String(80), nullable=True)
    preferred_location: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    preferred_crop: Mapped[str | None] = mapped_column(String(40), nullable=True)
    preferred_growth_stage: Mapped[str | None] = mapped_column(String(60), nullable=True)
    farm_area: Mapped[float | None] = mapped_column(Float, nullable=True)
    farm_area_unit: Mapped[str | None] = mapped_column(String(10), nullable=True)
    language: Mapped[str] = mapped_column(String(5), default="en")
    notification_preferences: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class Assessment(Base):                   # L20 audit - non-sensitive; coordinates rounded to 0.1 deg
    __tablename__ = "assessments"
    assessment_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    request_id: Mapped[str] = mapped_column(String(64))
    profile_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    crop_id: Mapped[str] = mapped_column(String(40))
    growth_stage_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    approx_lat: Mapped[float] = mapped_column(Float)
    approx_lon: Mapped[float] = mapped_column(Float)
    overall_risk: Mapped[str] = mapped_column(String(20))
    rule_version: Mapped[str] = mapped_column(String(40))
    providers: Mapped[dict] = mapped_column(JSON)
    knowledge_document_ids: Mapped[list] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="ok")
    payload: Mapped[dict] = mapped_column(JSON)          # full assessment, for advisory/report reuse (no PII)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class KnowledgeDocument(Base):            # F15
    __tablename__ = "knowledge_documents"
    document_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    publisher: Mapped[str] = mapped_column(String(200))
    crop_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    growth_stage_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    region: Mapped[str | None] = mapped_column(String(80), nullable=True)
    topic: Mapped[str] = mapped_column(String(80))
    publication_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    retrieved_at: Mapped[str] = mapped_column(String(40))
    source_url: Mapped[str] = mapped_column(String(600))
    language: Mapped[str] = mapped_column(String(8), default="en")
    verification_status: Mapped[str] = mapped_column(String(20), default="needs_review")
    source_type: Mapped[str] = mapped_column(String(30), default="agricultural_reference")
    content_type: Mapped[str] = mapped_column(String(30), default="educational")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    evidence_status: Mapped[str] = mapped_column(String(32), default="expert_review_required")
    source_access_status: Mapped[str] = mapped_column(String(32), default="not_checked")
    evidence_class: Mapped[str] = mapped_column(String(32), default="source_fact")
    state: Mapped[str | None] = mapped_column(String(40), nullable=True)
    districts: Mapped[list | None] = mapped_column(JSON, nullable=True)
    seasons: Mapped[list | None] = mapped_column(JSON, nullable=True)
    concern: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_section: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_time_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    weather_input_time_window: Mapped[str | None] = mapped_column(Text, nullable=True)
    measurement_window_status: Mapped[str] = mapped_column(String(32), default="not_assessed")
    threshold_details: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(Text, nullable=True)
    limitations: Mapped[str | None] = mapped_column(Text, nullable=True)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    chunk_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    document_id: Mapped[str] = mapped_column(String(80), index=True)
    ordinal: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)


class Subscription(Base):                 # F21 - consent recorded
    __tablename__ = "subscriptions"
    subscription_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    location_id: Mapped[str] = mapped_column(String(80))
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    district: Mapped[str | None] = mapped_column(String(80), nullable=True)
    crop_id: Mapped[str] = mapped_column(String(40))
    growth_stage_id: Mapped[str | None] = mapped_column(String(60), nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    channels: Mapped[list] = mapped_column(JSON, default=list)
    risk_levels: Mapped[list] = mapped_column(JSON, default=list)
    warning_categories: Mapped[list] = mapped_column(JSON, default=list)
    quiet_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    consent_timestamp: Mapped[str | None] = mapped_column(String(40), nullable=True)


class Notification(Base):
    __tablename__ = "notifications"
    notification_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    user_id: Mapped[str] = mapped_column(String(40), index=True)
    category: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(200))
    location_label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")   # active | expired | resolved
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    dedupe_key: Mapped[str] = mapped_column(String(200), index=True)


class Conversation(Base):                 # F14 transient chat memory
    __tablename__ = "conversations"
    conversation_id: Mapped[str] = mapped_column(String(40), primary_key=True)
    owner_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    messages: Mapped[list] = mapped_column(JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)
