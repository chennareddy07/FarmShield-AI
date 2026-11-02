"""Module registry: honest status of every feature module (spec §9-H, P8). The frontend builds navigation from this."""
from .config import get_settings
from ..ai.llm_provider import get_provider


def modules() -> list:
    s = get_settings()
    llm_status = s.llm_status
    llm_ok = llm_status == "operational"
    vision_available = bool(getattr(get_provider(), "supports_vision", False))
    advisor_status = {
        "not_configured": "implemented_ai_not_configured",
        "configured_not_tested": "implemented_configured_not_tested",
        "operational": "implemented",
        "temporarily_unavailable": "implemented_temporarily_unavailable",
        "invalid_configuration": "needs_config",
    }[llm_status]
    market_ok = bool(s.secret("data_gov_in_api_key") and s.agmarknet_resource_id)
    return [
        {"id": "dashboard", "level": 1, "features": ["F1", "F2", "F3", "F4", "F5", "F6", "F10"], "status": "implemented", "nav_state": "active"},
        {"id": "weather", "level": 1, "features": ["F2", "F3"], "status": "implemented", "nav_state": "active"},
        {"id": "crop_risk", "level": 1, "features": ["F6", "F10", "F12"], "status": "implemented", "nav_state": "active"},
        {"id": "advisor", "level": 1, "features": ["F7", "F14"], "status": advisor_status,
         "provider_status": llm_status, "nav_state": "limited" if llm_status in {"invalid_configuration", "temporarily_unavailable"} else "active",
         "note": None if llm_ok else "AI status: " + llm_status + ". Deterministic explanations and verified-passage retrieval remain available."},
        {"id": "history", "level": 2, "features": ["F11", "F25"], "status": "implemented_unverified", "nav_state": "active", "note": "Needs first-run verification against the live Open-Meteo Historical API."},
        {"id": "knowledge", "level": 2, "features": ["F8", "F15"], "status": "implemented", "nav_state": "active"},
        {"id": "calendar", "level": 2, "features": ["F16"], "status": "partial", "nav_state": "limited", "note": "Stage catalogue only; verified regional sowing/harvest dates are not configured."},
        {"id": "data_status", "level": 2, "features": ["F18"], "status": "implemented", "nav_state": "active"},
        {"id": "settings", "level": 2, "features": ["F13", "F9"], "status": "implemented", "nav_state": "active"},
        {"id": "market", "level": 3, "features": ["F19"], "status": "implemented_unverified" if market_ok else "needs_config", "nav_state": "active" if market_ok else "limited",
         "note": None if market_ok else "Requires DATA_GOV_IN_API_KEY and AGMARKNET_RESOURCE_ID."},
        {"id": "crop_health", "level": 3, "features": ["F20"], "status": "implemented_unverified" if vision_available else "needs_config", "nav_state": "active" if vision_available else "limited",
         "note": None if vision_available else "Upload validation works; the configured model is not known to support image input."},
        {"id": "notifications", "level": 3, "features": ["F21"], "status": "implemented", "nav_state": "active", "note": "In-app only; email/SMS are planned."},
        {"id": "satellite", "level": 3, "features": ["F22"], "status": "implemented_unverified" if s.satellite_provider != "disabled" else "needs_config", "nav_state": "limited",
         "note": "MODIS endpoint not yet verified against the live service."},
        {"id": "voice", "level": 3, "features": ["F23"], "status": "implemented", "nav_state": "active", "note": "Uses the browser's speech APIs; support for Telugu varies by device."},
        {"id": "regional", "level": 3, "features": ["F26", "F29"], "status": "implemented_unverified", "nav_state": "limited", "note": "District-level markers only."},
        {"id": "reports", "level": 3, "features": ["F27"], "status": "implemented", "nav_state": "active", "note": "HTML report; print to PDF from the browser."},
        {"id": "admin", "level": 3, "features": ["F29"], "status": "needs_config" if not s.secret("admin_api_token") else "implemented", "nav_state": "limited",
         "note": "Static admin token only; use an identity provider in production."},
        {"id": "multi_region", "level": 3, "features": ["F24"], "status": "planned", "nav_state": "planned", "note": "Registry-ready; only Andhra Pradesh, English and Telugu are configured."},
        {"id": "integrations", "level": 3, "features": ["F30"], "status": "planned", "nav_state": "planned", "note": "Adapter interface exists; no adapters are connected."},
    ]
