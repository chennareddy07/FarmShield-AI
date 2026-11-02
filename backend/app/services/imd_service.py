"""Official warnings (F4). IMD programmatic access is NOT verified, so this adapter reads a CAP 1.2 feed ONLY when
IMD_CAP_FEED_URL is configured. Otherwise it reports `not_configured` with official links. It never invents a warning
and never scrapes around access controls (spec §5-C, §9-F)."""
import ipaddress
import logging
import re
import xml.etree.ElementTree as ET
from typing import List, Optional
from urllib.parse import urlsplit

from ..core import monitoring
from ..core.config import get_settings
from ..core.http import ProviderError, request_json
from ..schemas.warnings import Warning, WarningsResponse
from ..utils.timeutil import iso, utcnow

log = logging.getLogger("farmshield.imd")
PROVIDER = "IMD"
MAX_LINKED_ALERTS = 20


def validate_cap_url(url: str, trusted_origin: Optional[tuple] = None) -> tuple:
    """Allow HTTPS URLs only on the configured feed's public host and port."""
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        port = parsed.port if parsed.port is not None else 443
    except (TypeError, ValueError):
        raise ProviderError(PROVIDER, "bad_response", "The configured warning feed contains an invalid URL.")
    if (parsed.scheme.lower() != "https" or not host or parsed.username or parsed.password
            or parsed.fragment or any(char.isspace() for char in url) or not 1 <= port <= 65535):
        raise ProviderError(PROVIDER, "bad_response", "The warning feed URL is not an allowed HTTPS URL.")

    normalized_host = host.rstrip(".").lower()
    if normalized_host == "localhost" or normalized_host.endswith((".localhost", ".local", ".internal", ".lan", ".home.arpa")):
        raise ProviderError(PROVIDER, "bad_response", "The warning feed URL uses a local host.")
    try:
        address = ipaddress.ip_address(normalized_host)
    except ValueError:
        address = None
    if address is not None and not address.is_global:
        raise ProviderError(PROVIDER, "bad_response", "The warning feed URL uses a non-public IP address.")
    if address is None:
        ambiguous_numeric_host = re.fullmatch(r"(?:0x[0-9a-f]+|[0-9]+)(?:\.(?:0x[0-9a-f]+|[0-9]+))*", normalized_host)
        if "%" in normalized_host or ambiguous_numeric_host:
            raise ProviderError(PROVIDER, "bad_response", "The warning feed URL uses an invalid host.")
        try:
            normalized_host = normalized_host.encode("idna").decode("ascii")
        except UnicodeError:
            raise ProviderError(PROVIDER, "bad_response", "The warning feed URL uses an invalid host.")
        labels = normalized_host.split(".")
        if any(not re.fullmatch(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?", label) for label in labels):
            raise ProviderError(PROVIDER, "bad_response", "The warning feed URL uses an invalid host.")

    origin = (normalized_host, port)
    if trusted_origin is not None and origin != trusted_origin:
        raise ProviderError(PROVIDER, "bad_response", "The linked warning document is outside the configured feed host.")
    return origin


def _strip(tag: str) -> str:
    return tag.split("}", 1)[-1]


def _text(el: Optional[ET.Element], name: str) -> Optional[str]:
    if el is None:
        return None
    for c in el:
        if _strip(c.tag) == name and c.text and c.text.strip():
            return c.text.strip()
    return None


def parse_cap(xml_text: str, retrieved_at: str) -> List[Warning]:
    """Parses CAP 1.2 <alert> documents (single alert, or a wrapper containing several). Only fields present in the source are populated."""
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ProviderError(PROVIDER, "bad_response", f"Feed is not valid XML: {e}")
    alerts = [el for el in root.iter() if _strip(el.tag) == "alert"]
    out: List[Warning] = []
    for a in alerts:
        ident = _text(a, "identifier")
        sender = _text(a, "senderName") or _text(a, "sender")
        for info in [c for c in a if _strip(c.tag) == "info"]:
            area = next((c for c in info if _strip(c.tag) == "area"), None)
            color = None
            for p in [c for c in info if _strip(c.tag) == "parameter"]:
                if (_text(p, "valueName") or "").lower() in ("color", "colour", "alertcolor", "alert_color"):
                    color = _text(p, "value")
            out.append(Warning(
                warning_id=f"{ident or 'cap'}:{_text(info, 'event') or 'event'}"[:120], source=sender or "IMD (CAP feed)",
                title=_text(info, "headline") or _text(info, "event") or "Weather warning", description=_text(info, "description"),
                warning_type=_text(info, "event"), severity=_text(info, "severity"), severity_color=color,
                affected_area=_text(area, "areaDesc") if area is not None else None, issued_at=_text(a, "sent"),
                valid_from=_text(info, "effective") or _text(info, "onset"), valid_until=_text(info, "expires"),
                source_url=_text(info, "web"), retrieved_at=retrieved_at))
    return out


def filter_for_district(warnings: List[Warning], district: Optional[str]) -> List[Warning]:
    if not district:
        return warnings
    d = district.lower()
    return [w for w in warnings if w.affected_area and d in w.affected_area.lower()]


async def get_warnings(district: Optional[str]) -> WarningsResponse:
    s = get_settings()
    now = iso(utcnow())
    if not s.imd_cap_feed_url:
        monitoring.record_failure("imd", "not_configured")
        return WarningsResponse(
            warnings=[], source_status="not_configured", retrieved_at=now, district=district,
            source_status_message=("Live IMD warnings are not connected: no verified public machine-readable IMD feed has been configured. "
                                   "No warning has been assessed. Please check the official IMD pages linked below."))
    try:
        trusted_origin = validate_cap_url(s.imd_cap_feed_url)
        text = await request_json(PROVIDER, "GET", s.imd_cap_feed_url, expect="text")
        warnings = parse_cap(text, now)
        # Atom/RSS wrappers: follow bounded number of linked CAP documents
        if not warnings:
            try:
                root = ET.fromstring(text)
                links = [(el.get("href") or (el.text or "").strip()) for el in root.iter() if _strip(el.tag) == "link"]
                for url in [l for l in links if l and l.lower().endswith((".xml", ".cap"))][:MAX_LINKED_ALERTS]:
                    validate_cap_url(url, trusted_origin)
                    linked_text = await request_json(PROVIDER, "GET", url, expect="text")
                    try:
                        warnings += parse_cap(linked_text, now)
                    except ProviderError:
                        continue
            except ET.ParseError:
                pass
        monitoring.record_success("imd")
        filtered = filter_for_district(warnings, district)
        return WarningsResponse(warnings=filtered, source_status="available", retrieved_at=now, district=district,
                                source_status_message=None if filtered else "The feed was retrieved; it contains no warning for this district.")
    except ProviderError as e:
        monitoring.record_failure("imd", e.kind)
        return WarningsResponse(warnings=[], source_status="unavailable", retrieved_at=now, district=district,
                                source_status_message="The official warning source could not be retrieved. No warning has been assessed; see the official links.")
