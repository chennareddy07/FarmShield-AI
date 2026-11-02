import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from ...ai import advisory_generator
from ...core import i18n
from ...core.config import get_settings
from ...core.errors import AppError
from ...schemas.advisory import AdvisoryRequest, ChatRequest
from ...schemas.risk import RiskRequest
from ...services import assistant_tools, assessment_service as asvc, crop_config_service, profile_service, report_service
from ...core.db import session
from ...models.tables import Conversation
from pydantic import BaseModel
from ..deps import current_owner_id

router = APIRouter()
log = logging.getLogger("farmshield.chat")


@router.post("/api/risk/assess")
async def risk_assess(req: RiskRequest, request: Request, owner_id: str = Depends(current_owner_id)):
    a = await asvc.run_assessment(req, request.state.request_id, owner_id)
    return asvc.public_view(a)


@router.get("/api/risk/{assessment_id}")
async def risk_get(assessment_id: str, language: Optional[str] = None, owner_id: str = Depends(current_owner_id)):
    a = asvc.get_assessment(assessment_id, owner_id)
    if language:
        a = asvc.localize(a, language)
    return asvc.public_view(a)


@router.post("/api/advisory/generate")
async def advisory_generate(req: AdvisoryRequest, owner_id: str = Depends(current_owner_id)):
    lang, invalid = i18n.normalize_language(req.language)
    a = asvc.localize(asvc.get_assessment(req.assessment_id, owner_id), lang)
    ctx = profile_service.personalisation_context(req.profile_id, owner_id)
    out = await advisory_generator.generate_advisory(a, lang, req.question, ctx)
    if invalid:
        out["notices"].append(f"Unsupported language code; English is used. Supported: {', '.join(i18n.SUPPORTED_LANGUAGES)}.")
    return out


@router.post("/api/assistant/chat")
async def assistant_chat(req: ChatRequest, owner_id: str = Depends(current_owner_id)):
    lang, _ = i18n.normalize_language(req.language or i18n.detect_language(req.message))
    a = None
    if req.assessment_id:
        a = asvc.localize(asvc.get_assessment(req.assessment_id, owner_id), lang)
    crop = req.crop_id or (a or {}).get("crop_id")
    stage = req.growth_stage_id or (a or {}).get("growth_stage_id")
    if crop:
        crop_config_service.validate_stage(crop_config_service.get_crop(crop), stage)
    location = req.location.model_dump(exclude_none=True) if req.location else (a or {}).get("location")
    snapshot_status = "current"
    assessment_stale = False
    if a:
        try:
            at = datetime.fromisoformat(a["assessment_time"].replace("Z", "+00:00"))
            if at.tzinfo is None:
                at = at.replace(tzinfo=timezone.utc)
            assessment_stale = datetime.now(timezone.utc) - at > timedelta(minutes=get_settings().weather_stale_minutes)
        except (KeyError, TypeError, ValueError):
            assessment_stale = True
        if assessment_stale or a.get("data_quality", {}).get("weather", {}).get("status") in {"stale", "unavailable"}:
            snapshot_status = "historical"
            assessment_stale = True
    user_context = {"location": {key: location[key] for key in ("name", "district") if location and key in location},
                    "crop_id": crop, "growth_stage_id": stage, "language": lang,
                    "assessment_snapshot_status": snapshot_status if a else None}
    cid = req.conversation_id or f"conv-{uuid.uuid4().hex[:12]}"
    history = []
    stale_conversation = False
    try:
        with session() as db:
            conv = db.scalar(select(Conversation).where(
                Conversation.conversation_id == cid, Conversation.owner_id == owner_id))
            if req.conversation_id and conv is None:
                raise AppError(404, "conversation_not_found", "Conversation not found.")
            if conv:
                updated = conv.updated_at
                if updated and updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                stale_conversation = bool(updated and datetime.now(timezone.utc) - updated > timedelta(days=30))
                if stale_conversation:
                    conv.messages = []
                    db.commit()
                else:
                    history = [f"{m['role']}: {m['content'][:350]}" for m in (conv.messages or [])[-6:]
                               if m.get("role") in {"user", "assistant"} and isinstance(m.get("content"), str)]
    except SQLAlchemyError:
        log.exception("chat history lookup failed")
        raise AppError(503, "database_unavailable", "Chat history is temporarily unavailable.")
    if stale_conversation:
        user_context["conversation_history_status"] = "expired"
    calls = assistant_tools.plan_tools(req.message, location=location, crop_id=crop, stage_id=stage,
                                       assessment_id=req.assessment_id, assessment_stale=assessment_stale)
    tool_results = await assistant_tools.execute_tools(calls, owner_id)
    passages = []
    for result in tool_results:
        if result["name"] == "search_agricultural_knowledge" and result["status"] == "available":
            passages.extend(result["data"]["results"])
    res = await advisory_generator.answer_question(req.message, lang, a, passages, history,
                                                   tool_results=tool_results, user_context=user_context)
    try:
        with session() as db:
            conv = db.scalar(select(Conversation).where(
                Conversation.conversation_id == cid, Conversation.owner_id == owner_id))
            if conv is None:
                conv = Conversation(conversation_id=cid, owner_id=owner_id, messages=[])
                db.add(conv)
            stored_evidence = []
            for item in res.get("evidence", [])[:5]:
                if not isinstance(item, dict):
                    continue
                stored_evidence.append({
                    key: value[:500] if isinstance(value, str) else value
                    for key, value in item.items()
                    if key in {"evidence_id", "kind", "title", "publisher", "publication_date", "source_url",
                               "verification_status", "excerpt", "document_id"}
                    and (isinstance(value, str) or value is None)
                })
            assistant_message = {
                "role": "assistant", "content": res["answer"][:1500], "status": res["status"],
                "uncertainties": [item[:450] for item in res.get("uncertainties", [])[:8] if isinstance(item, str)],
                "evidence": stored_evidence,
            }
            conv.messages = ((conv.messages or []) + [{"role": "user", "content": req.message[:800]},
                                                       assistant_message])[-12:]
            db.commit()
    except SQLAlchemyError:
        log.exception("chat history persistence failed")
        raise AppError(503, "database_unavailable", "Chat response could not be saved.")
    return {**res, "conversation_id": cid, "language": lang}


@router.get("/api/assistant/conversations/{conversation_id}")
async def assistant_conversation_history(conversation_id: str, owner_id: str = Depends(current_owner_id)):
    try:
        with session() as db:
            conv = db.scalar(select(Conversation).where(
                Conversation.conversation_id == conversation_id, Conversation.owner_id == owner_id))
            if conv is None:
                raise AppError(404, "conversation_not_found", "Conversation not found.")
            updated = conv.updated_at
            if updated and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)
            if updated and datetime.now(timezone.utc) - updated > timedelta(days=30):
                conv.messages = []
                db.commit()
            messages = []
            for item in (conv.messages or [])[-12:]:
                if item.get("role") not in {"user", "assistant"} or not isinstance(item.get("content"), str):
                    continue
                message = {"role": item["role"], "content": item["content"][:1500]}
                if item["role"] == "assistant":
                    if item.get("status") in {"ai_generated", "retrieval_only", "out_of_scope", "fallback_invalid_output"}:
                        message["status"] = item["status"]
                    message["uncertainties"] = [value[:450] for value in item.get("uncertainties", [])[:8]
                                                if isinstance(value, str)]
                    message["evidence"] = [evidence for evidence in item.get("evidence", [])[:5]
                                           if isinstance(evidence, dict) and isinstance(evidence.get("evidence_id"), str)]
                messages.append(message)
            return {"conversation_id": conversation_id, "messages": messages}
    except SQLAlchemyError:
        log.exception("chat history retrieval failed")
        raise AppError(503, "database_unavailable", "Chat history is temporarily unavailable.")


class ReportRequest(BaseModel):
    assessment_id: str
    language: str = "en"
    include_advisory: bool = False


@router.post("/api/reports/generate")
async def reports_generate(req: ReportRequest, owner_id: str = Depends(current_owner_id)):
    lang, _ = i18n.normalize_language(req.language)
    a = asvc.localize(asvc.get_assessment(req.assessment_id, owner_id), lang)
    adv = await advisory_generator.generate_advisory(a, lang) if req.include_advisory else None
    html = report_service.build_report(a, lang, adv)
    return HTMLResponse(html, headers={"Content-Disposition": f'attachment; filename="farmshield-report-{a["assessment_id"]}-{lang}.html"'})
