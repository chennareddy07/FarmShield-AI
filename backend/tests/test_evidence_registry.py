import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text

from app.core.db import upgrade_knowledge_evidence_columns
from app.engine.rule_loader import clear_cache, load_rules
from app.services import knowledge_service as ks


ROOT = Path(__file__).resolve().parents[2]


def test_seed_metadata_keeps_source_access_and_agronomic_review_separate():
    docs = {item["document_id"]: item for item in ks.list_documents()}
    rice = docs["KB-PADDY-HEAT-JIRCAS-JARQ"]
    assert rice["source_access_status"] == "pdf_verified"
    assert rice["evidence_status"] == "expert_review_required"
    assert rice["verification_status"] == "needs_review"
    assert rice["measurement_window_status"] == "not_aligned"
    assert "Controlled-environment" in rice["limitations"]

    groundnut = docs["KB-GNUT-HEAT-ICRISAT"]
    assert groundnut["source_access_status"] == "inaccessible_http_401"
    assert groundnut["evidence_status"] == "source_unverified"
    unverified_hits = ks.search("temperature", crop_id="groundnut", include_unverified=True)
    lead = next(item for item in unverified_hits if item["document_id"] == groundnut["document_id"])
    assert ">34" not in lead["excerpt"]
    assert all(item["document_id"] != groundnut["document_id"] for item in
               ks.search("unverified bibliography lead temperature", crop_id="groundnut", include_unverified=False))


def test_registry_emits_explicit_stage_concern_gaps_and_keeps_reviewable_evidence():
    registry = ks.load_evidence_registry()
    gaps = registry["coverage_gaps"]
    assert len(gaps) == 107
    assert all(item["evidence_status"] == "insufficient_evidence" for item in gaps)
    guidance = registry["general_guidance"]
    assert len(guidance) == 10
    assert all(item["source_verification_status"] == "source_verified" for item in guidance)
    assert all(item["expert_review_status"] == "expert_review_required" for item in guidance)
    assert all(item["original_url"].startswith("https://") for item in guidance)
    paddy_guidance = ks.load_evidence_registry("paddy")["general_guidance"]
    groundnut_guidance = ks.load_evidence_registry("groundnut")["general_guidance"]
    assert len(paddy_guidance) == 5 and len(groundnut_guidance) == 5
    assert all(item["publication_date"].startswith("2018") and "PDF p" in item["page_reference"]
               for item in groundnut_guidance)
    assert all(item["evidence_status"] == "expert_review_required" for item in groundnut_guidance)
    assert len({(item["crop_id"], item["growth_stage_id"], item["concern"]) for item in gaps}) == len(gaps)
    assert not any(item["crop_id"] == "paddy" and item["growth_stage_id"] == "flowering" and
                   item["concern"] == "high_temperature" for item in gaps)
    assert not any(item["crop_id"] == "groundnut" and item["growth_stage_id"] == "pod_development" and
                   item["concern"] == "dry_spell" for item in gaps)
    assert ks.load_evidence_registry("paddy")["coverage_gaps"]
    with pytest.raises(ValueError):
        ks.load_evidence_registry("wheat")


def test_rule_validation_records_match_shipped_rules_and_every_rule_stays_disabled():
    validation = json.loads((ROOT / "knowledge" / "metadata" / "rule_validation_records.json").read_text(encoding="utf-8"))
    rules = [rule for path in (ROOT / "backend" / "app" / "data" / "risk_rules").glob("*.json")
             for rule in json.loads(path.read_text(encoding="utf-8"))["rules"]]
    records = {item["rule_id"]: item for item in validation["records"]}
    assert set(records) == {rule["rule_id"] for rule in rules}
    assert all(item["operational_status"] == "disabled" for item in records.values())
    assert all(not item["measurement_window_compatible"] for item in records.values())
    loaded = load_rules()
    assert not loaded["enabled"]
    assert {item["rule_id"] for item in loaded["disabled"]} == set(records)
    clear_cache()


def test_search_and_document_filters_apply_state_district_season_and_concern():
    common = {
        "title": "Registry filter marker",
        "publisher": "Test source",
        "crop_id": "groundnut",
        "growth_stage_id": "pegging",
        "topic": "water_stress",
        "source_url": "https://example.org/evidence",
        "verification_status": "needs_review",
        "evidence_status": "expert_review_required",
        "source_access_status": "page_verified",
        "concern": "water_stress",
        "seasons": ["Kharif"],
    }
    ks.upsert_document({**common, "document_id": "FILTER-AP", "state": "Andhra Pradesh", "districts": ["Guntur"]},
                       "unique registry marker for filter validation")
    ks.upsert_document({**common, "document_id": "FILTER-OTHER", "state": "Telangana", "districts": ["Nalgonda"]},
                       "unique registry marker for filter validation")

    result = ks.search("unique registry marker", crop_id="groundnut", state="Andhra Pradesh",
                       district="Guntur", season="Kharif", concern="water_stress")
    assert [item["document_id"] for item in result] == ["FILTER-AP"]
    listed = [item["document_id"] for item in ks.list_documents(
        crop_id="groundnut", state="Andhra Pradesh", district="Guntur",
        season="Kharif", concern="water_stress")]
    assert "FILTER-AP" in listed and "FILTER-OTHER" not in listed
    general_ap_docs = {
        item["document_id"] for item in ks.list_documents(state="Andhra Pradesh", district="Guntur")
    }
    assert "KB-GNUT-MOISTURE-ICAR-IIGR" in general_ap_docs
    general_ap = next(item for item in ks.list_documents(state="Andhra Pradesh", district="Guntur")
                      if item["document_id"] == "KB-GNUT-MOISTURE-ICAR-IIGR")
    assert general_ap["state"] == "Andhra Pradesh" and general_ap["districts"] == []


def test_new_evidence_metadata_is_validated_and_expert_approval_is_required_for_verified_agricultural_docs():
    base = {"document_id": "BAD-EVIDENCE", "title": "Test", "publisher": "Test",
            "topic": "test", "source_url": "https://example.org"}
    invalid_values = {
        "evidence_status": [],
        "source_access_status": [],
        "evidence_class": [],
        "measurement_window_status": [],
        "districts": [""],
        "seasons": [""],
        "threshold_details": [],
    }
    for field, value in invalid_values.items():
        with pytest.raises(ValueError):
            ks.upsert_document({**base, field: value}, "test")
    with pytest.raises(ValueError, match="expert_approved"):
        ks.upsert_document({**base, "verification_status": "verified",
                            "source_type": "agricultural_reference"}, "test")
    with pytest.raises(ValueError, match="inaccessible sources"):
        ks.upsert_document({**base, "evidence_status": "source_verified",
                            "source_access_status": "inaccessible_http_401"}, "test")


def test_legacy_knowledge_evidence_migration_is_additive_and_maps_old_statuses():
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(text(
            "CREATE TABLE knowledge_documents (document_id VARCHAR(80) PRIMARY KEY, verification_status VARCHAR(20))"))
        connection.execute(text(
            "INSERT INTO knowledge_documents (document_id, verification_status) VALUES "
            "('old-verified', 'verified'), ('old-review', 'needs_review')"))
    upgrade_knowledge_evidence_columns(engine)
    columns = {column["name"] for column in inspect(engine).get_columns("knowledge_documents")}
    assert {"evidence_status", "districts", "seasons", "measurement_window_status", "limitations"} <= columns
    with engine.connect() as connection:
        status_by_id = dict(connection.execute(text(
            "SELECT document_id, evidence_status FROM knowledge_documents")).all())
    assert status_by_id == {"old-verified": "source_verified", "old-review": "expert_review_required"}
    engine.dispose()


def test_evidence_registry_api_exposes_gaps_and_filter_parameters(client):
    response = client.get("/api/knowledge/evidence-registry?crop_id=paddy")
    assert response.status_code == 200
    assert all(item["crop_id"] == "paddy" for item in response.json()["coverage_gaps"])
    assert response.json()["coverage_gaps"][0]["evidence_status"] == "insufficient_evidence"
    assert len(response.json()["general_guidance"]) == 5
    groundnut = client.get("/api/knowledge/evidence-registry?crop_id=groundnut").json()
    assert len(groundnut["general_guidance"]) == 5
    assert client.get("/api/knowledge/evidence-registry?crop_id=wheat").status_code == 422


def test_knowledge_search_api_enforces_applicability_filters(client):
    ks.upsert_document({
        "document_id": "API-FILTER-AP", "title": "API marker evidence", "publisher": "Test",
        "crop_id": "groundnut", "growth_stage_id": "pegging", "topic": "water_stress",
        "source_url": "https://example.org/api-marker", "verification_status": "needs_review",
        "evidence_status": "expert_review_required", "source_access_status": "page_verified",
        "state": "Andhra Pradesh", "districts": ["Guntur"], "seasons": ["Kharif"],
        "concern": "water_stress",
    }, "unique api applicability marker")
    response = client.get(
        "/api/knowledge/search",
        params={"q": "unique api applicability marker", "crop_id": "groundnut",
                "growth_stage_id": "pegging", "state": "Andhra Pradesh", "district": "Guntur",
                "season": "Kharif", "concern": "water_stress", "evidence_status": "expert_review_required"},
    )
    assert response.status_code == 200
    assert [item["document_id"] for item in response.json()["results"]] == ["API-FILTER-AP"]
