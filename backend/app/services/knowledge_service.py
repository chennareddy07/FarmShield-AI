"""Agricultural knowledge base (F8, F15): ingestion, chunking, BM25 retrieval with metadata filters, outdating."""
import json
import logging
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from sqlalchemy import delete, select

from ..core.config import PROJECT_DIR
from ..core.db import session
from ..models.tables import KnowledgeChunk, KnowledgeDocument

log = logging.getLogger("farmshield.knowledge")
METADATA_DIR = PROJECT_DIR / "knowledge" / "metadata"
EVIDENCE_REGISTRY_PATH = METADATA_DIR / "evidence_registry.json"
QUALITY_WEIGHT = {"verified": 1.0, "needs_review": 0.6, "outdated": 0.0}
EVIDENCE_STATUSES = {"source_verified", "source_unverified", "expert_review_required", "expert_approved",
                    "conflicting_evidence", "insufficient_evidence"}
SOURCE_ACCESS_STATUSES = {"not_checked", "source_verified", "abstract_only", "page_verified", "pdf_verified",
                          "inaccessible_http_401", "inaccessible_http_406", "unavailable"}
EVIDENCE_CLASSES = {"source_fact", "farmshield_interpretation", "expert_review", "coverage_gap"}
WINDOW_STATUSES = {"aligned", "not_aligned", "not_assessed", "not_applicable", "unknown"}
EVIDENCE_WEIGHT = {"expert_approved": 1.0, "source_verified": 0.9, "expert_review_required": 0.65,
                   "source_unverified": 0.25, "conflicting_evidence": 0.2, "insufficient_evidence": 0.0}
LEGACY_STATUS_BY_EVIDENCE = {"expert_approved": "verified", "source_verified": "needs_review",
                             "expert_review_required": "needs_review", "source_unverified": "needs_review",
                             "conflicting_evidence": "needs_review", "insufficient_evidence": "needs_review"}
SOURCE_TYPES = {"agricultural_reference", "meteorological_reference"}
SOURCE_TYPE_ALIASES = {"official_warning_reference": "meteorological_reference"}
CONTENT_TYPES = {"recommendation", "educational"}
CHUNK_CHARS, OVERLAP = 800, 120
STOP = set("the a an and or of to in on for with is are was were be by as at from that this it its".split())
TOPIC_FOR_CATEGORY = {"rainfall": "rainfall_classification", "excess_rainfall": "rainfall", "dry_spell": "water_stress",
                      "high_temperature": "heat_stress", "low_temperature": "cold_stress", "humidity": "disease", "wind": "wind",
                      "severe_weather_warning": "rainfall_classification"}
REQUIRED_META = ["document_id", "title", "publisher", "topic", "source_url"]


def tokenize(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9\u0c00-\u0c7f]+", text.lower()) if t not in STOP and len(t) > 1]


def chunk_text(text: str, size: int = CHUNK_CHARS, overlap: int = OVERLAP) -> List[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, i = [], 0
    while i < len(text):
        end = min(len(text), i + size)
        if end < len(text):                              # prefer to cut on a sentence boundary
            cut = text.rfind(". ", i + size // 2, end)
            end = cut + 1 if cut != -1 else end
        chunks.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return chunks


def extract_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8", errors="replace")
    if suffix == ".pdf":
        from pypdf import PdfReader
        return "\n".join((p.extract_text() or "") for p in PdfReader(str(path)).pages)
    raise ValueError(f"unsupported document type: {suffix}")


def upsert_document(meta: dict, content: str) -> int:
    """Insert or replace a document (replacement = update outdated documents, F15). Returns number of chunks."""
    missing = [k for k in REQUIRED_META if not meta.get(k)]
    if missing:
        raise ValueError(f"metadata missing {missing}")
    status = meta.get("verification_status")
    if status is not None and (not isinstance(status, str) or status not in QUALITY_WEIGHT):
        raise ValueError("verification_status must be verified | needs_review | outdated")
    raw_source_type = meta.get("source_type", "agricultural_reference")
    if not isinstance(raw_source_type, str):
        raise ValueError("source_type must be agricultural_reference | meteorological_reference")
    source_type = SOURCE_TYPE_ALIASES.get(raw_source_type, raw_source_type)
    if source_type not in SOURCE_TYPES:
        raise ValueError("source_type must be agricultural_reference | meteorological_reference")
    content_type = meta.get("content_type", "educational")
    if not isinstance(content_type, str) or content_type not in CONTENT_TYPES:
        raise ValueError("content_type must be recommendation | educational")
    evidence_status = meta.get("evidence_status")
    if evidence_status is None:
        evidence_status = {"verified": "source_verified", "outdated": "source_unverified"}.get(status, "expert_review_required")
    if not isinstance(evidence_status, str) or evidence_status not in EVIDENCE_STATUSES:
        raise ValueError(f"evidence_status must be one of {sorted(EVIDENCE_STATUSES)}")
    if status is None:
        status = LEGACY_STATUS_BY_EVIDENCE[evidence_status]
    if status == "outdated" and evidence_status != "source_unverified":
        raise ValueError("outdated documents must have evidence_status source_unverified")
    if source_type == "agricultural_reference" and status == "verified" and evidence_status != "expert_approved":
        raise ValueError("agricultural references require expert_approved evidence_status to be marked verified")
    source_access_status = meta.get("source_access_status", "not_checked")
    if not isinstance(source_access_status, str) or source_access_status not in SOURCE_ACCESS_STATUSES:
        raise ValueError(f"source_access_status must be one of {sorted(SOURCE_ACCESS_STATUSES)}")
    if source_access_status.startswith("inaccessible_") and evidence_status in {"source_verified", "expert_approved"}:
        raise ValueError("inaccessible sources cannot have source_verified or expert_approved evidence_status")
    evidence_class = meta.get("evidence_class", "source_fact")
    if not isinstance(evidence_class, str) or evidence_class not in EVIDENCE_CLASSES:
        raise ValueError(f"evidence_class must be one of {sorted(EVIDENCE_CLASSES)}")
    measurement_window_status = meta.get("measurement_window_status", "not_assessed")
    if not isinstance(measurement_window_status, str) or measurement_window_status not in WINDOW_STATUSES:
        raise ValueError(f"measurement_window_status must be one of {sorted(WINDOW_STATUSES)}")
    for field in ("districts", "seasons"):
        value = meta.get(field)
        if value is not None and (not isinstance(value, list) or any(not isinstance(item, str) or not item.strip() for item in value)):
            raise ValueError(f"{field} must be a list of non-empty strings")
    threshold_details = meta.get("threshold_details")
    if threshold_details is not None and not isinstance(threshold_details, dict):
        raise ValueError("threshold_details must be an object")
    chunks = chunk_text(content)
    with session() as db:
        db.execute(delete(KnowledgeChunk).where(KnowledgeChunk.document_id == meta["document_id"]))
        db.merge(KnowledgeDocument(
            document_id=meta["document_id"], title=meta["title"], publisher=meta["publisher"], crop_id=meta.get("crop_id"),
            growth_stage_id=meta.get("growth_stage_id"), region=meta.get("region"), topic=meta["topic"],
            publication_date=meta.get("publication_date"), retrieved_at=meta.get("retrieved_at") or datetime.now(timezone.utc).isoformat(),
            source_url=meta["source_url"], language=meta.get("language", "en"), verification_status=status,
            source_type=source_type, content_type=content_type, notes=meta.get("notes"),
            evidence_status=evidence_status, source_access_status=source_access_status,
            evidence_class=evidence_class, state=meta.get("state"), districts=meta.get("districts"),
            seasons=meta.get("seasons"), concern=meta.get("concern"), source_section=meta.get("source_section"),
            source_time_window=meta.get("source_time_window"), weather_input_time_window=meta.get("weather_input_time_window"),
            measurement_window_status=measurement_window_status, threshold_details=threshold_details,
            recommendation=meta.get("recommendation"), limitations=meta.get("limitations")))
        for i, c in enumerate(chunks):
            db.add(KnowledgeChunk(chunk_id=f"{meta['document_id']}#{i}", document_id=meta["document_id"], ordinal=i, content=c))
        db.commit()
    return len(chunks)


def ingest_file(path: Path, meta: dict) -> int:
    return upsert_document(meta, extract_text(path))


def seed_from_metadata_dir(directory: Optional[Path] = None) -> int:
    """Loads knowledge/metadata/*.json (each: {documents:[{...,content}]}). Idempotent."""
    n = 0
    for f in sorted(Path(directory or METADATA_DIR).glob("*.json")):
        data = json.loads(f.read_text(encoding="utf-8"))
        for d in data.get("documents", []):
            upsert_document({k: v for k, v in d.items() if k != "content"}, d["content"])
            n += 1
    return n


def load_evidence_registry(crop_id: Optional[str] = None) -> dict:
    """Return research provenance plus explicit insufficient-evidence rows for every uncovered stage/concern."""
    registry = json.loads(EVIDENCE_REGISTRY_PATH.read_text(encoding="utf-8"))
    if crop_id and crop_id not in {crop["crop_id"] for crop in registry["crops"]}:
        raise ValueError(f"unsupported evidence-registry crop: {crop_id}")
    crops = [crop for crop in registry["crops"] if not crop_id or crop["crop_id"] == crop_id]
    crop_ids = {crop["crop_id"] for crop in crops}
    stage_evidence = [item for item in registry["stage_evidence"] if item["crop_id"] in crop_ids]
    general_guidance = [
        item for item in registry.get("general_guidance", [])
        if not crop_id or item["crop_id"] == crop_id
    ]
    covered = {
        (item["crop_id"], item["growth_stage_id"], item["concern"])
        for item in stage_evidence
        if item["evidence_status"] in {"source_verified", "expert_review_required", "expert_approved", "conflicting_evidence"}
    }
    gaps = [
        {"crop_id": crop["crop_id"], "growth_stage_id": stage_id, "concern": concern,
         "evidence_status": "insufficient_evidence",
         "reason": "No verified, crop-stage-applicable source was located in this research pass."}
        for crop in crops
        for stage_id in crop["growth_stage_ids"]
        for concern in registry["required_concerns"]
        if (crop["crop_id"], stage_id, concern) not in covered
    ]
    return {
        "registry_version": registry["registry_version"],
        "reviewed_at": registry["reviewed_at"],
        "geographic_scope": registry["geographic_scope"],
        "status_definitions": registry["status_definitions"],
        "stage_evidence": stage_evidence,
        "general_guidance": general_guidance,
        "coverage_gaps": gaps,
        "source_catalog": registry["source_catalog"],
        "rule_validation_file": registry["rule_validation_file"],
        "rule_safety_invariant": registry["rule_safety_invariant"],
    }


def mark_outdated(document_id: str) -> bool:
    with session() as db:
        doc = db.get(KnowledgeDocument, document_id)
        if not doc:
            return False
        doc.verification_status = "outdated"
        db.commit()
        return True


def _doc_dict(d: KnowledgeDocument) -> dict:
    return {"document_id": d.document_id, "evidence_id": f"EV-KB-{d.document_id}",
            "title": d.title, "publisher": d.publisher, "crop_id": d.crop_id, "growth_stage_id": d.growth_stage_id,
            "region": d.region, "topic": d.topic, "publication_date": d.publication_date, "retrieved_at": d.retrieved_at, "source_url": d.source_url,
            "language": d.language, "verification_status": d.verification_status, "source_type": d.source_type, "content_type": d.content_type,
            "evidence_status": d.evidence_status, "source_access_status": d.source_access_status, "evidence_class": d.evidence_class,
            "state": d.state, "districts": d.districts or [], "seasons": d.seasons or [], "concern": d.concern,
            "source_section": d.source_section, "source_time_window": d.source_time_window,
            "weather_input_time_window": d.weather_input_time_window, "measurement_window_status": d.measurement_window_status,
            "threshold_details": d.threshold_details, "recommendation": d.recommendation, "limitations": d.limitations}


def _matches_context_filter(values: Optional[List[str]], requested: Optional[str], *, scoped: bool = False) -> bool:
    if not requested:
        return True
    if values:
        return requested.casefold() in {value.casefold() for value in values}
    return not scoped


def _matches_text_filter(value: Optional[str], requested: Optional[str]) -> bool:
    return not requested or value is None or value.casefold() == requested.casefold()


def _source_freshness_boost(document: KnowledgeDocument) -> float:
    if document.source_access_status not in {"source_verified", "abstract_only", "page_verified", "pdf_verified"}:
        return 0.0
    try:
        checked_at = datetime.fromisoformat(document.retrieved_at.replace("Z", "+00:00"))
        if checked_at.tzinfo is None:
            checked_at = checked_at.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return 0.0
    age_days = max(0.0, (datetime.now(timezone.utc) - checked_at).total_seconds() / 86400)
    if age_days <= 30:
        return 0.12
    if age_days <= 365:
        return 0.06
    return 0.0


def list_documents(crop_id: Optional[str] = None, topic: Optional[str] = None, stage_id: Optional[str] = None,
                   include_outdated: bool = False, *, state: Optional[str] = None, district: Optional[str] = None,
                   season: Optional[str] = None, concern: Optional[str] = None,
                   evidence_status: Optional[str] = None) -> List[dict]:
    with session() as db:
        docs = db.scalars(select(KnowledgeDocument)).all()
    out = []
    for d in docs:
        if d.verification_status == "outdated" and not include_outdated:
            continue
        if crop_id and d.crop_id not in (None, crop_id):
            continue
        if stage_id and d.growth_stage_id not in (None, stage_id):
            continue
        if topic and d.topic != topic:
            continue
        if not _matches_text_filter(d.state, state) or not _matches_context_filter(
                d.districts, district, scoped=bool(d.districts)):
            continue
        if not _matches_context_filter(d.seasons, season, scoped=bool(d.seasons)) or not _matches_text_filter(d.concern, concern):
            continue
        if evidence_status and d.evidence_status != evidence_status:
            continue
        out.append(_doc_dict(d))
    return sorted(out, key=lambda x: x["document_id"])


def search(query: str = "", *, crop_id: Optional[str] = None, stage_id: Optional[str] = None, region: Optional[str] = None,
           topics: Optional[List[str]] = None, limit: int = 5, state: Optional[str] = None,
           district: Optional[str] = None, season: Optional[str] = None, concern: Optional[str] = None,
           evidence_status: Optional[str] = None, include_unverified: bool = True) -> List[dict]:
    """BM25 over chunks + metadata filters/boosts + source-quality weight. Outdated documents are excluded (L8)."""
    with session() as db:
        docs = {d.document_id: d for d in db.scalars(select(KnowledgeDocument)).all()}
        chunks = db.scalars(select(KnowledgeChunk)).all()
    cand = []
    for c in chunks:
        d = docs.get(c.document_id)
        if d is None or d.verification_status == "outdated":
            continue
        if crop_id and d.crop_id not in (None, crop_id):
            continue
        if stage_id and d.growth_stage_id and d.growth_stage_id != stage_id:
            continue
        if region and d.region not in (None, region) and d.state != region:
            continue
        if not _matches_text_filter(d.state, state) or not _matches_context_filter(
                d.districts, district, scoped=bool(d.districts)):
            continue
        if not _matches_context_filter(d.seasons, season, scoped=bool(d.seasons)) or not _matches_text_filter(d.concern, concern):
            continue
        if evidence_status and d.evidence_status != evidence_status:
            continue
        if not include_unverified and d.evidence_status in {"source_unverified", "conflicting_evidence", "insufficient_evidence"}:
            continue
        cand.append((c, d, tokenize(c.content + " " + d.title)))
    if not cand:
        return []
    q = tokenize(query)
    N = len(cand)
    avg = sum(len(t) for _, _, t in cand) / N or 1
    df = Counter()
    for _, _, toks in cand:
        for term in set(toks):
            df[term] += 1
    best: Dict[str, dict] = {}
    for c, d, toks in cand:
        tf = Counter(toks)
        bm = 0.0
        for term in q:
            if term in tf:
                idf = math.log(1 + (N - df[term] + 0.5) / (df[term] + 0.5))
                bm += idf * tf[term] * 2.5 / (tf[term] + 1.5 * (0.25 + 0.75 * len(toks) / avg))
        boost = 0.0
        if stage_id and d.growth_stage_id == stage_id:
            boost += 1.0
        if crop_id and d.crop_id == crop_id:
            boost += 0.8
        if topics and d.topic in topics:
            boost += 1.2
        if state and d.state and d.state.casefold() == state.casefold():
            boost += 0.35
        if district and d.districts and district.casefold() in {x.casefold() for x in d.districts}:
            boost += 0.5
        if season and d.seasons and season.casefold() in {x.casefold() for x in d.seasons}:
            boost += 0.25
        if concern and d.concern and d.concern.casefold() == concern.casefold():
            boost += 0.35
        if q and bm == 0:
            continue
        if not q and boost == 0 and not (crop_id is None and not topics):
            continue
        score = (bm + boost + _source_freshness_boost(d) + 0.01) * QUALITY_WEIGHT.get(d.verification_status, 0.5) * EVIDENCE_WEIGHT.get(d.evidence_status, 0.5)
        cur = best.get(d.document_id)
        if cur is None or score > cur["score"]:
            best[d.document_id] = {"evidence_id": f"EV-KB-{d.document_id}",
                                   "kind": d.source_type if d.source_type in SOURCE_TYPES else "meteorological_reference",
                                   "document_id": d.document_id,
                                   "title": d.title, "publisher": d.publisher, "publication_date": d.publication_date, "excerpt": c.content,
                                   "source_url": d.source_url, "verification_status": d.verification_status, "topic": d.topic,
                                   "crop_id": d.crop_id, "growth_stage_id": d.growth_stage_id, "source_type": d.source_type,
                                   "content_type": d.content_type, "retrieved_at": d.retrieved_at,
                                   "evidence_status": d.evidence_status, "source_access_status": d.source_access_status,
                                   "evidence_class": d.evidence_class, "state": d.state, "districts": d.districts or [],
                                   "seasons": d.seasons or [], "concern": d.concern, "source_section": d.source_section,
                                   "source_time_window": d.source_time_window,
                                   "weather_input_time_window": d.weather_input_time_window,
                                   "measurement_window_status": d.measurement_window_status,
                                   "threshold_details": d.threshold_details, "recommendation": d.recommendation,
                                   "limitations": d.limitations, "score": round(score, 4)}
    return sorted(best.values(), key=lambda x: -x["score"])[:limit]


def retrieve_for_assessment(crop_id: str, stage_id: Optional[str], categories: List[str], limit: int = 8,
                            district: Optional[str] = None) -> List[dict]:
    topics = sorted({TOPIC_FOR_CATEGORY[c] for c in categories if c in TOPIC_FOR_CATEGORY})
    query = " ".join(topics).replace("_", " ")
    return search(query, crop_id=crop_id, stage_id=stage_id, region="Andhra Pradesh", state="Andhra Pradesh",
                  district=district, topics=topics, limit=limit, include_unverified=False)


def ensure_seeded() -> None:
    with session() as db:
        existing_ids = set(db.scalars(select(KnowledgeDocument.document_id)).all())
    try:
        seed_file = METADATA_DIR / "seed_documents.json"
        data = json.loads(seed_file.read_text(encoding="utf-8"))
        missing = [d for d in data.get("documents", []) if d.get("document_id") not in existing_ids]
        for document in missing:
            upsert_document({k: v for k, v in document.items() if k != "content"}, document["content"])
        if missing:
            log.info("seeded %d missing knowledge documents", len(missing))
    except Exception:
        log.exception("knowledge seeding failed")
