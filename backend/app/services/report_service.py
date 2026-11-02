"""F27 downloadable report (self-contained HTML; print to PDF in the browser so Telugu fonts render correctly)."""
from html import escape

from ..core import i18n
from ..utils.timeutil import iso, utcnow

L = {
    "en": {"title": "FarmShield AI - Agricultural Weather Risk Report", "location": "Location", "crop": "Crop / growth stage", "created": "Report created", "weather": "Weather summary",
           "forecast": "Forecast (daily)", "risk": "Risk assessment", "reasons": "Main reasons", "actions": "Recommendations", "evidence": "Evidence and sources", "overall": "Overall risk",
           "category": "Category", "date": "Date", "tmax": "Max °C", "tmin": "Min °C", "rain": "Rain mm", "none": "None", "coverage": "Categories assessed", "advisory": "AI advisory",
           "t_review": "Note: Telugu text in this report has not been verified by an agricultural-domain reviewer.", "provider": "Weather provider", "retrieved": "Retrieved"},
    "te": {"title": "FarmShield AI - వ్యవసాయ వాతావరణ ముప్పు నివేదిక", "location": "ప్రాంతం", "crop": "పంట / పెరుగుదల దశ", "created": "నివేదిక సృష్టించిన సమయం", "weather": "వాతావరణ సారాంశం",
           "forecast": "సూచన (రోజువారీ)", "risk": "ముప్పు అంచనా", "reasons": "ప్రధాన కారణాలు", "actions": "సిఫార్సులు", "evidence": "ఆధారాలు మరియు మూలాలు", "overall": "మొత్తం ముప్పు",
           "category": "వర్గం", "date": "తేదీ", "tmax": "గరిష్ఠ °C", "tmin": "కనిష్ఠ °C", "rain": "వర్షం మి.మీ", "none": "లేదు", "coverage": "అంచనా వేసిన వర్గాలు", "advisory": "AI సలహా",
           "t_review": "గమనిక: ఈ నివేదికలోని తెలుగు పాఠాన్ని వ్యవసాయ నిపుణులు ఇంకా ధృవీకరించలేదు.", "provider": "వాతావరణ వనరు", "retrieved": "పొందిన సమయం"},
}


def build_report(assessment: dict, language: str, advisory: dict | None = None) -> str:
    lang = language if language in L else "en"
    t = L[lang]
    e = lambda x: escape(str(x if x is not None else "-"))
    w = (assessment.get("_inputs") or {}).get("weather") or {}
    cur = w.get("current") or {}
    loc = assessment["location"]
    rows = "".join(f"<tr><td>{e(d['forecast_for'])}</td><td>{e(d.get('temperature_max_c'))}</td><td>{e(d.get('temperature_min_c'))}</td><td>{e(d.get('precipitation_sum_mm'))}</td></tr>" for d in (w.get("daily") or []))
    cats = "".join(f"<tr><td>{e(c['label'])}</td><td><b>{e(c['risk_label'])}</b></td><td>{e(c['reason'])}</td></tr>" for c in assessment["risk_categories"])
    reasons = "".join(f"<li>{e(x)}</li>" for x in assessment["explanations"]) or f"<li>{t['none']}</li>"
    acts = "".join(f"<li>{e(a['text'])}</li>" for a in assessment["recommended_actions"]) or f"<li>{t['none']}</li>"
    ev = "".join(f"<li><b>{e(x['title'])}</b> - {e(x.get('publisher'))} ({e(x.get('publication_date'))}) <i>[{e(x['kind'])}; {e(x.get('verification_status'))}]</i><br>{e(x.get('excerpt'))}<br><a href='{escape(x.get('source_url') or '#')}'>{e(x.get('source_url'))}</a></li>" for x in assessment["evidence"]) or f"<li>{t['none']}</li>"
    adv = ""
    if advisory:
        adv = f"<h2>{t['advisory']}</h2><p>{e(advisory['summary'])}</p><p>{e(advisory['risk_explanation'])}</p>"
    note = f"<p><i>{t['t_review']}</i></p>" if lang == "te" else ""
    return f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8"><title>{t['title']}</title>
<style>body{{font-family:'Noto Sans Telugu','Noto Sans',Arial,sans-serif;max-width:860px;margin:24px auto;color:#1F2933;line-height:1.5}}h1{{color:#246B45}}h2{{color:#246B45;border-bottom:1px solid #ddd;padding-bottom:4px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:6px;text-align:left}}.box{{background:#F7F9F6;border:1px solid #cfd8cf;padding:10px;border-radius:8px}}</style></head><body>
<h1>{t['title']}</h1>{note}
<p>{t['created']}: {e(iso(utcnow()))} (assessment {e(assessment['assessment_id'])}, rule version {e(assessment['rule_version'])})</p>
<p>{t['location']}: {e(loc.get('name'))} ({e(loc['latitude'])}, {e(loc['longitude'])})<br>{t['crop']}: {e(assessment['crop_name'])} / {e(assessment.get('growth_stage_name'))}</p>
<h2>{t['weather']}</h2><p>{t['provider']}: {e(w.get('provider', 'Open-Meteo'))} - {t['retrieved']}: {e(w.get('retrieved_at'))}<br>
{e(cur.get('temperature_c'))} °C, {e(cur.get('relative_humidity_pct'))} %, {e(cur.get('wind_speed_kmh'))} km/h, {e(cur.get('precipitation_mm'))} mm ({e(cur.get('weather_summary'))})</p>
<h2>{t['forecast']}</h2><table><tr><th>{t['date']}</th><th>{t['tmax']}</th><th>{t['tmin']}</th><th>{t['rain']}</th></tr>{rows}</table>
<h2>{t['risk']}</h2><div class="box"><b>{t['overall']}: {e(assessment['overall_risk_label'])}</b> - {t['coverage']}: {e(assessment['coverage']['assessed_count'])}/{e(assessment['coverage']['required_count'])}</div>
<table><tr><th>{t['category']}</th><th>{t['overall']}</th><th></th></tr>{cats}</table>
<h2>{t['reasons']}</h2><ul>{reasons}</ul><h2>{t['actions']}</h2><ul>{acts}</ul>{adv}
<h2>{t['evidence']}</h2><ol>{ev}</ol><p><small>{e(assessment['disclaimer'])}<br>{e(assessment.get('method_note'))}<br>Weather data by Open-Meteo.com (CC BY 4.0)</small></p></body></html>"""
