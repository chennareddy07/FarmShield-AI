"""Run this ONCE with internet access to verify every external dependency listed in specs/external-verification.md.
Usage:  python scripts/verify_providers.py            (from backend/, venv active)
Prints PASS / FAIL / SKIP per provider with the reason. Makes no changes."""
import asyncio
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.core.config import get_settings  # noqa: E402
from app.core.http import ProviderError, request_json  # noqa: E402

LAT, LON = 16.3067, 80.4365      # Guntur area, used only for connectivity checks
results = []


def report(name, ok, detail):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL' if ok is False else 'SKIP'}] {name}: {detail}")


async def check(name, coro):
    try:
        report(name, True, await coro)
    except ProviderError as e:
        report(name, False, f"{e.kind}: {e.message}")
    except Exception as e:                                  # noqa: BLE001
        report(name, False, f"{type(e).__name__}: {e}")


async def main():
    s = get_settings()

    async def forecast():
        d = await request_json("om", "GET", f"{s.open_meteo_base_url}/v1/forecast", params={"latitude": LAT, "longitude": LON, "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,rain,showers,weather_code,cloud_cover,wind_speed_10m,wind_direction_10m",
                                                                                           "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max,weather_code", "hourly": "temperature_2m,relative_humidity_2m,precipitation,cloud_cover,wind_speed_10m,wind_direction_10m,weather_code", "timezone": "auto"})
        missing = [k for k in ("current", "daily", "hourly", "utc_offset_seconds", "timezone") if k not in d]
        if missing:
            raise RuntimeError(f"response missing {missing}")
        return f"keys ok; current.time={d['current'].get('time')} units={d.get('current_units', {}).get('wind_speed_10m')}"

    async def geocode():
        d = await request_json("om", "GET", f"{s.open_meteo_geocoding_url}/v1/search", params={"name": "Guntur", "count": 10, "countryCode": "IN", "format": "json"})
        ap = [r for r in d.get("results", []) if r.get("admin1") == "Andhra Pradesh"]
        if not ap:
            raise RuntimeError("no Andhra Pradesh result for 'Guntur' - check admin1 field naming")
        return f"{len(ap)} AP results; fields={sorted(ap[0])[:8]}"

    async def archive():
        e = date.today() - timedelta(days=10)
        d = await request_json("om", "GET", f"{s.open_meteo_archive_url}/v1/archive", params={"latitude": LAT, "longitude": LON, "start_date": (e - timedelta(days=5)).isoformat(), "end_date": e.isoformat(), "daily": "temperature_2m_max,temperature_2m_min,temperature_2m_mean,precipitation_sum"})
        return f"{len(d['daily']['time'])} days returned"

    await check("Open-Meteo forecast", forecast())
    await check("Open-Meteo geocoding", geocode())
    await check("Open-Meteo historical (ERA5)", archive())

    if s.imd_cap_feed_url:
        from app.services import imd_service
        async def imd():
            text = await request_json("imd", "GET", s.imd_cap_feed_url, expect="text")
            n = len(imd_service.parse_cap(text, "now"))
            return f"feed reachable; parsed {n} CAP info blocks (0 may be legitimate if none active)"
        await check("IMD CAP feed", imd())
    else:
        report("IMD CAP feed", None, "IMD_CAP_FEED_URL not set - no verified public feed known; UI will show 'not configured'")

    if s.secret("data_gov_in_api_key") and s.agmarknet_resource_id:
        async def mkt():
            d = await request_json("dg", "GET", f"{s.data_gov_in_base_url}/resource/{s.agmarknet_resource_id}", params={"api-key": s.secret("data_gov_in_api_key"), "format": "json", "limit": 3, "filters[state]": "Andhra Pradesh"})
            recs = d.get("records") or []
            need = {"state", "district", "market", "commodity", "arrival_date", "min_price", "max_price", "modal_price"}
            miss = need - set(recs[0]) if recs else need
            if miss:
                raise RuntimeError(f"field names differ from the assumed schema; missing {sorted(miss)}; update app/services/market_service.py")
            return f"{len(recs)} records; schema matches"
        await check("data.gov.in Agmarknet", mkt())
    else:
        report("data.gov.in Agmarknet", None, "DATA_GOV_IN_API_KEY / AGMARKNET_RESOURCE_ID not set")

    if s.satellite_provider != "disabled":
        from app.services import satellite_service as sat
        async def modis():
            r = await sat.get_indicators(LAT, LON, 90)
            if r["status"] != "available":
                raise RuntimeError(f"status={r['status']} {r.get('message')}")
            return f"{len(r['indicators'])} observations; latest {r['observation_date']}"
        await check("MODIS NDVI (ORNL DAAC)", modis())

    ok = [r for r in results if r is not None]
    print(f"\n{sum(ok)}/{len(ok)} checks passed (skips not counted)")
    sys.exit(0 if all(ok) else 1)


asyncio.run(main())
