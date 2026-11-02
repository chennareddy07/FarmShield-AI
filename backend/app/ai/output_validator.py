"""Validates LLM output against the structured contract (L10). Unknown evidence ids => rejection (AC13)."""
import re
from typing import Any, Dict, List, Optional, Set, Tuple

MAX_SUMMARY, MAX_ITEM, MAX_ITEMS = 900, 450, 8
REQUIRED = {"summary": str, "risk_explanation": str, "recommended_actions": list, "preventive_actions": list,
            "when_to_act": str, "uncertainties": list, "evidence_ids": list}
FORBIDDEN_KEYS = {"overall_risk", "risk_level", "risk", "risk_categories", "risk_percentage"}
CHEMICAL = re.compile(r"\b(pesticide|insecticide|fungicide|herbicide|weedicide|fertili[sz]er|urea|dap\b|npk|spray(ing)?|dose|dosage|kg/ha|ml/l|g/l|mancozeb|chlorpyrifos|imidacloprid|carbendazim)\b", re.I)
ACTION = re.compile(r"\b(you should|recommend(?:ed)?|advise(?:d)?|try to|monitor|irrigate|water|drain|sow|plant|apply|avoid|treat|increase|reduce|harvest)\b", re.I)
RISK_CLAIM = re.compile(r"(overall\s+)?(crop\s+)?risk(\s+level)?\s*(is|:|of|=)\s*(low|moderate|high|critical)\b", re.I)
TELUGU = re.compile(r"[\u0c00-\u0c7f]")
LETTER = re.compile(r"[A-Za-z\u0c00-\u0c7f]")


def telugu_ratio(text: str) -> float:
    letters = LETTER.findall(text)
    return len(TELUGU.findall(text)) / len(letters) if letters else 0.0


def _strings(v: Any) -> List[str]:
    return [x for x in v if isinstance(x, str)] if isinstance(v, list) else []


def check_text_safety(texts: List[str], engine_overall: Optional[str], errors: List[str]) -> None:
    for t in texts:
        if CHEMICAL.search(t):
            errors.append("contains chemical/fertiliser/dose recommendation language, which is not allowed")
            break
    if engine_overall:
        for t in texts:
            m = RISK_CLAIM.search(t)
            if m and m.group(5).lower() != engine_overall:
                errors.append(f"contradicts the deterministic risk level '{engine_overall}'")
                break


def validate_advisory(obj: Dict[str, Any], valid_ids: Set[str], language: str, engine_overall: Optional[str] = None,
                      allow_crop_actions: bool = False) -> Tuple[bool, Dict[str, Any], List[str]]:
    errors: List[str] = []
    if not isinstance(obj, dict):
        return False, {}, ["output is not a JSON object"]
    bad_keys = FORBIDDEN_KEYS & set(obj)
    if bad_keys:
        errors.append(f"must not contain risk fields: {sorted(bad_keys)}")
    for k, t in REQUIRED.items():
        if k not in obj:
            errors.append(f"missing field {k}")
        elif not isinstance(obj[k], t):
            errors.append(f"field {k} has wrong type")
    if errors:
        return False, {}, errors
    if not obj["summary"].strip() or len(obj["summary"]) > MAX_SUMMARY:
        errors.append("summary empty or too long")
    if len(obj["risk_explanation"]) > MAX_SUMMARY * 2:
        errors.append("risk_explanation too long")
    for k in ("recommended_actions", "preventive_actions", "uncertainties"):
        items = obj[k]
        if len(items) > MAX_ITEMS or any(not isinstance(i, str) or len(i) > MAX_ITEM for i in items):
            errors.append(f"{k} violates size limits")
    if not allow_crop_actions and (obj["recommended_actions"] or obj["preventive_actions"]):
        errors.append("crop actions require verified, crop- and stage-matching agricultural evidence")
    ids = [i for i in obj["evidence_ids"] if isinstance(i, str)]
    unknown = [i for i in ids if i not in valid_ids]
    if len(ids) != len(obj["evidence_ids"]):
        errors.append("evidence_ids must be strings")
    if unknown:
        errors.append(f"unknown evidence ids: {unknown}")                 # AC13 / E16
    body = [obj["summary"], obj["risk_explanation"], obj["when_to_act"]] + _strings(obj["recommended_actions"]) + _strings(obj["preventive_actions"])
    check_text_safety(body, engine_overall, errors)
    ratio = telugu_ratio(obj["summary"])
    if language == "te" and ratio < 0.3:
        errors.append("summary is not in Telugu")
    if language == "en" and ratio > 0.3:
        errors.append("summary is not in English")
    if errors:
        return False, {}, errors
    clean = {k: obj[k] for k in REQUIRED}
    clean["evidence_ids"] = list(dict.fromkeys(ids))
    return True, clean, []


def validate_chat(obj: Dict[str, Any], valid_ids: Set[str], language: str, engine_overall: Optional[str] = None,
                  allow_crop_actions: bool = False) -> Tuple[bool, Dict[str, Any], List[str]]:
    errors: List[str] = []
    if not isinstance(obj, dict) or not isinstance(obj.get("answer"), str) or not obj["answer"].strip():
        return False, {}, ["missing answer"]
    if len(obj["answer"]) > 2500:
        errors.append("answer too long")
    if not allow_crop_actions and ACTION.search(obj["answer"]):
        errors.append("crop actions require verified, crop- and stage-matching agricultural recommendation evidence")
    ids = obj.get("evidence_ids", [])
    if not isinstance(ids, list) or any(not isinstance(i, str) for i in ids):
        errors.append("evidence_ids invalid")
    else:
        unknown = [i for i in ids if i not in valid_ids]
        if unknown:
            errors.append(f"unknown evidence ids: {unknown}")
        if valid_ids and not ids:
            errors.append("answers based on application context must cite at least one evidence id")
    check_text_safety([obj["answer"]], engine_overall, errors)
    ratio = telugu_ratio(obj["answer"])
    if language == "te" and ratio < 0.3:
        errors.append("answer is not in Telugu")
    if errors:
        return False, {}, errors
    return True, {"answer": obj["answer"], "in_scope": bool(obj.get("in_scope", True)), "evidence_ids": list(dict.fromkeys(obj.get("evidence_ids", []))),
                  "uncertainties": _strings(obj.get("uncertainties", []))[:MAX_ITEMS]}, []
