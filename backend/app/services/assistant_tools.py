"""Allowlisted, bounded assistant tools backed by existing FarmShield services."""
import asyncio
import logging
import re
from datetime import date, timedelta
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from ..core.errors import AppError
from . import assessment_service, crop_config_service, history_service, imd_service, knowledge_service, weather_service

log = logging.getLogger("farmshield.assistant_tools")
MAX_TOOL_CALLS = 3
TOOL_TIMEOUT_SECONDS = 15
TOOL_NAMES = {
    "get_current_weather",
    "get_weather_forecast",
    "get_historical_weather",
    "get_crop_growth_stages",
    "get_crop_assessment",
    "search_agricultural_knowledge",
    "get_official_warnings",
    "explain_risk_assessment",
}


class ToolInput(BaseModel):
    model_config = ConfigDict(extra="forbid")


class LocationInput(ToolInput):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    district: Optional[str] = Field(default=None, max_length=80)


class WeatherInput(LocationInput):
    days: int = Field(default=7, ge=1, le=7)


class HistoryInput(LocationInput):
    start_date: str = Field(max_length=10)
    end_date: str = Field(max_length=10)


class CropInput(ToolInput):
    crop_id: str = Field(min_length=1, max_length=40)


class AssessmentInput(ToolInput):
    assessment_id: str = Field(min_length=1, max_length=40)
    owner_id: str = Field(min_length=1, max_length=64)


class KnowledgeInput(ToolInput):
    query: str = Field(min_length=1, max_length=200)
    crop_id: Optional[str] = Field(default=None, max_length=40)
    growth_stage_id: Optional[str] = Field(default=None, max_length=60)
    district: Optional[str] = Field(default=None, max_length=80)


class WarningInput(ToolInput):
    district: str = Field(min_length=1, max_length=80)


def _location(location: Optional[dict]) -> Optional[dict]:
    if location is None:
        return None
    return LocationInput.model_validate({key: value for key, value in location.items()
                                         if key in {"latitude", "longitude", "district"}}).model_dump()


def _current_weather_args(location: dict) -> dict:
    return WeatherInput.model_validate(location).model_dump()


def _history_args(location: dict) -> dict:
    end = date.today() - timedelta(days=6)
    start = end - timedelta(days=29)
    return HistoryInput.model_validate({**location, "start_date": start.isoformat(), "end_date": end.isoformat()}).model_dump()


def plan_tools(message: str, *, location: Optional[dict], crop_id: Optional[str], stage_id: Optional[str],
               assessment_id: Optional[str], assessment_stale: bool = False) -> list[tuple[str, dict]]:
    """Choose from fixed tools using intent cues; the model cannot choose arbitrary functions or arguments."""
    loc = _location(location)
    text = message.lower()
    telugu = any("\u0c00" <= char <= "\u0c7f" for char in message)
    weather_intent = bool(re.search(r"\b(weather|forecast|temperature|rain|rainfall|today|current)\b", text)) or (
        telugu and any(term in message for term in ("వాతావరణ", "వర్ష", "ఉష్ణోగ్రత", "ఈ రోజు")))
    history_intent = bool(re.search(r"\b(history|historical|past|previous|last month|last 30 days)\b", text)) or (
        telugu and any(term in message for term in ("చరిత్ర", "గత నెల", "గత వాతావరణం")))
    warning_intent = bool(re.search(r"\b(warning|warnings|alert|alerts|imd)\b", text)) or (
        telugu and any(term in message for term in ("హెచ్చరిక", "వార్త")))
    stage_intent = bool(re.search(r"\b(stage|growth|flowering|tillering|pegging|pod development|seedling)\b", text)) or (
        telugu and any(term in message for term in ("దశ", "పూత", "ఊడలు")))
    calls: list[tuple[str, dict]] = []
    if history_intent and loc:
        calls.append(("get_historical_weather", _history_args(loc)))
    elif weather_intent and loc and (assessment_id is None or assessment_stale):
        calls.append(("get_current_weather", _current_weather_args(loc)))
        calls.append(("get_weather_forecast", _current_weather_args(loc)))
    if warning_intent and loc and loc.get("district"):
        calls.append(("get_official_warnings", {"district": loc["district"]}))
    if stage_intent and crop_id:
        calls.append(("get_crop_growth_stages", {"crop_id": crop_id}))
    if assessment_id and (re.search(r"\b(risk|assessment|insufficient|why)\b", text) or
                          (telugu and any(term in message for term in ("ముప్పు", "అంచనా", "ఎందుకు")))):
        calls.append(("explain_risk_assessment", {"assessment_id": assessment_id}))
    calls.append(("search_agricultural_knowledge", {
        "query": message, "crop_id": crop_id, "growth_stage_id": stage_id,
        "district": loc.get("district") if loc else None,
    }))
    return calls[:MAX_TOOL_CALLS]


async def _dispatch(name: str, arguments: dict, owner_id: Optional[str] = None) -> dict:
    if name not in TOOL_NAMES:
        raise AppError(422, "assistant_tool_not_allowed", "This assistant tool is not available.")
    if name in {"get_current_weather", "get_weather_forecast"}:
        args = WeatherInput.model_validate(arguments)
        bundle = await weather_service.fetch_weather(args.latitude, args.longitude, args.days)
        if name == "get_current_weather":
            current = bundle.current.model_dump() if bundle.current else None
            return {"kind": "weather_observation_or_model_analysis", "current": current, "provider": bundle.provider,
                    "retrieved_at": bundle.retrieved_at, "data_quality": bundle.data_quality.model_dump(),
                    "spatial_note": bundle.spatial_note}
        return {"kind": "forecast", "daily": [point.model_dump() for point in bundle.daily[:args.days]],
                "hourly": [point.model_dump() for point in bundle.hourly[:24]], "provider": bundle.provider,
                "timezone": bundle.timezone, "retrieved_at": bundle.retrieved_at,
                "data_quality": bundle.data_quality.model_dump(), "spatial_note": bundle.spatial_note}
    if name == "get_historical_weather":
        args = HistoryInput.model_validate(arguments)
        return await history_service.fetch_history(args.latitude, args.longitude, args.start_date, args.end_date)
    if name == "get_crop_growth_stages":
        args = CropInput.model_validate(arguments)
        cfg = crop_config_service.get_crop(args.crop_id)
        return {"crop_id": args.crop_id,
                "stages": [{"stage_id": stage["stage_id"], "name": stage["name"]} for stage in cfg["growth_stages"]],
                "review_status": cfg.get("review_status"), "review_note": cfg.get("review_note")}
    if name in {"get_crop_assessment", "explain_risk_assessment"}:
        if not owner_id:
            raise AppError(401, "authentication_required", "Assessment access requires the current browser session.")
        args = AssessmentInput.model_validate({**arguments, "owner_id": owner_id})
        assessment = assessment_service.get_assessment(args.assessment_id, args.owner_id)
        return {"assessment_id": assessment["assessment_id"], "assessment_time": assessment.get("assessment_time"),
                "crop_id": assessment.get("crop_id"), "growth_stage_id": assessment.get("growth_stage_id"),
                "overall_risk": assessment.get("overall_risk"), "risk_categories": assessment.get("risk_categories"),
                "coverage": assessment.get("coverage"), "data_quality": assessment.get("data_quality"),
                "warnings_status": assessment.get("warnings_status"), "forecast_window": assessment.get("forecast_window"),
                "explanations": assessment.get("explanations")}
    if name == "search_agricultural_knowledge":
        args = KnowledgeInput.model_validate(arguments)
        if args.crop_id:
            cfg = crop_config_service.get_crop(args.crop_id)
            crop_config_service.validate_stage(cfg, args.growth_stage_id)
        return {"results": knowledge_service.search(args.query, crop_id=args.crop_id, stage_id=args.growth_stage_id,
                                                     region="Andhra Pradesh", state="Andhra Pradesh",
                                                     district=args.district, limit=4,
                                                     include_unverified=False)}
    if name == "get_official_warnings":
        args = WarningInput.model_validate(arguments)
        response = await imd_service.get_warnings(args.district)
        return response.model_dump()
    raise AppError(422, "assistant_tool_not_allowed", "This assistant tool is not available.")


async def execute_tools(calls: list[tuple[str, dict]], owner_id: Optional[str] = None) -> list[dict]:
    """Execute at most three fixed tools, each with a strict timeout and explicit unavailable result."""
    async def execute_one(name: str, arguments: dict) -> dict:
        try:
            data = await asyncio.wait_for(_dispatch(name, arguments, owner_id), timeout=TOOL_TIMEOUT_SECONDS)
        except asyncio.TimeoutError:
            log.warning("assistant tool timed out: %s", name)
            return {"name": name, "status": "unavailable", "message": "The data service did not respond in time."}
        except AppError as exc:
            log.info("assistant tool unavailable: %s (%s)", name, exc.code)
            return {"name": name, "status": "unavailable", "message": exc.message}
        result = {"name": name, "status": "available", "data": data}
        result["evidence"] = evidence_for_tool_results([result])
        return result

    return await asyncio.gather(*(execute_one(name, arguments) for name, arguments in calls[:MAX_TOOL_CALLS]))


def evidence_for_tool_results(results: list[dict]) -> list[dict]:
    evidence = []
    for result in results:
        if result["status"] != "available":
            continue
        name, data = result["name"], result["data"]
        if name == "get_current_weather":
            evidence.append({"evidence_id": "EV-TOOL-CURRENT-WEATHER", "kind": "forecast", "title": "Open-Meteo current model analysis",
                             "publisher": data["provider"], "publication_date": data.get("retrieved_at"),
                             "excerpt": "Provider model analysis, not a station observation.", "source_url": "https://open-meteo.com",
                             "verification_status": "official"})
        elif name == "get_weather_forecast":
            evidence.append({"evidence_id": "EV-TOOL-WEATHER-FORECAST", "kind": "forecast", "title": "Open-Meteo weather forecast",
                             "publisher": data["provider"], "publication_date": data.get("retrieved_at"),
                             "excerpt": f"Forecast for {len(data['daily'])} local calendar days.", "source_url": "https://open-meteo.com",
                             "verification_status": "official"})
        elif name == "get_historical_weather":
            evidence.append({"evidence_id": "EV-TOOL-HISTORICAL-WEATHER", "kind": "forecast", "title": "Open-Meteo ERA5 historical reanalysis",
                             "publisher": data["provider"], "publication_date": data.get("retrieved_at"),
                             "excerpt": "Modelled reanalysis, not station observations.", "source_url": "https://open-meteo.com",
                             "verification_status": "official"})
        elif name == "get_official_warnings":
            status = data.get("source_status")
            evidence.append({"evidence_id": "EV-TOOL-OFFICIAL-WARNINGS", "kind": "official_warning",
                             "title": "Configured CAP warning feed status", "publisher": "Configured CAP feed",
                             "publication_date": data.get("retrieved_at"),
                             "excerpt": data.get("source_status_message") or "Official feed retrieved.",
                             "verification_status": "official" if status == "available" else status or "unavailable"})
            for warning in data.get("warnings", []):
                evidence.append({"evidence_id": f"EV-TOOL-WARNING-{warning['warning_id']}", "kind": "official_warning",
                                 "title": warning.get("title", "Official warning"), "publisher": warning.get("source"),
                                 "publication_date": warning.get("issued_at"), "excerpt": warning.get("description"),
                                 "source_url": warning.get("source_url"), "verification_status": "official"})
        elif name == "get_crop_growth_stages":
            evidence.append({"evidence_id": f"EV-TOOL-CROP-{data['crop_id']}", "kind": "crop_configuration",
                             "title": f"{data['crop_id']} stage catalogue", "publisher": "FarmShield configuration",
                             "verification_status": data.get("review_status", "needs_review")})
        elif name == "search_agricultural_knowledge":
            evidence.extend(data["results"])
    return evidence
