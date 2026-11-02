"""F30: contract every future external integration must satisfy (documented data contract + source-quality checks)."""
from dataclasses import dataclass, field
from typing import Any, Dict, List, Protocol


@dataclass
class DataContract:
    name: str
    version: str
    fields: Dict[str, str]                 # field -> type/description
    update_frequency: str
    licence: str
    spatial_resolution: str = "unspecified"


@dataclass
class QualityReport:
    passed: bool
    issues: List[str] = field(default_factory=list)


class IntegrationAdapter(Protocol):
    contract: DataContract

    async def fetch(self, **query) -> List[Dict[str, Any]]: ...
    def quality_check(self, records: List[Dict[str, Any]]) -> QualityReport: ...


def check_required_fields(records: List[Dict[str, Any]], contract: DataContract) -> QualityReport:
    issues = []
    for i, r in enumerate(records):
        missing = [k for k in contract.fields if k not in r]
        if missing:
            issues.append(f"record {i} missing {missing}")
    return QualityReport(passed=not issues and bool(records), issues=issues or ([] if records else ["no records returned"]))


REGISTRY: Dict[str, IntegrationAdapter] = {}


def register(name: str, adapter: IntegrationAdapter) -> None:
    if not getattr(adapter, "contract", None):
        raise ValueError("adapter must declare a DataContract")
    REGISTRY[name] = adapter
