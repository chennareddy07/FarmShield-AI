"""Backend message dictionaries (L11). English is canonical. Telugu strings are flagged NEEDS_REVIEW:
agricultural terminology must be reviewed by a native / agri-domain speaker before production use."""
from typing import Tuple

SUPPORTED_LANGUAGES = ["en", "te"]
TRANSLATION_REVIEW_STATUS = {"en": "canonical", "te": "needs_review"}

RISK_LABELS = {
    "en": {"low": "Low", "moderate": "Moderate", "high": "High", "critical": "Critical", "insufficient_data": "Insufficient data"},
    "te": {"low": "తక్కువ", "moderate": "మధ్యస్థం", "high": "అధికం", "critical": "తీవ్రం", "insufficient_data": "తగినంత సమాచారం లేదు"},
}

CATEGORY_LABELS = {
    "en": {"rainfall": "Rainfall risk", "excess_rainfall": "Excess rainfall / waterlogging risk",
           "dry_spell": "Dry spell / low rainfall risk", "high_temperature": "High-temperature risk",
           "low_temperature": "Low-temperature risk", "humidity": "Humidity-related risk",
           "wind": "Wind-related risk", "severe_weather_warning": "Severe-weather warning exposure"},
    "te": {"rainfall": "వర్షపాత ముప్పు", "excess_rainfall": "అధిక వర్షం / నీరు నిలవడం ముప్పు",
           "dry_spell": "వర్షాభావం / పొడి వాతావరణ ముప్పు", "high_temperature": "అధిక ఉష్ణోగ్రత ముప్పు",
           "low_temperature": "తక్కువ ఉష్ణోగ్రత ముప్పు", "humidity": "తేమ సంబంధిత ముప్పు",
           "wind": "గాలి సంబంధిత ముప్పు", "severe_weather_warning": "తీవ్ర వాతావరణ హెచ్చరిక ప్రభావం"},
}

CROP_NAMES = {"en": {"paddy": "Paddy", "groundnut": "Groundnut"}, "te": {"paddy": "వరి (Paddy)", "groundnut": "వేరుశనగ (Groundnut)"}}

MESSAGES = {
    "en": {
        "disclaimer": "FarmShield AI is a decision-support tool, not an official warning or a substitute for professional advice. Please consult your local agricultural officer for important decisions.",
        "none": "none",
        "no_data": "no data available",
        "summary": "Rule-based assessment for {crop} ({stage}) near {location}: overall risk is {risk}. This is calculated from forecast data and documented rules; it is not an official warning.",
        "summary_general": "General weather assessment for {crop} near {location} (no growth stage selected, so no stage-specific rules were applied): overall risk is {risk}.",
        "triggered": "{rule}: {reason}",
        "none_triggered": "No enabled, verified rule was triggered by the forecast data.",
        "no_rules": "No verified rules are available for some risk categories, so they were not assessed.",
        "action_general": "Check the official IMD forecast and warnings for your district and consult your local agricultural officer before making field decisions.",
        "no_crop_action": "No expert-approved crop-specific action is available for this condition. Source-backed general references may still be shown, but they are not validated recommendations.",
        "ai_unavailable": "The AI advisory service is temporarily unavailable. Your weather and calculated risk information are still available.",
        "ai_invalid": "The AI response could not be validated, so a safe rule-based explanation is shown instead.",
        "no_evidence": "We could not find enough verified agricultural information to provide a reliable recommendation.",
        "translation_unavailable": "Translation to the requested language is not available for this content; it is shown in English.",
        "unverified_evidence": "Some source-checked agricultural references still require expert review and are not validated recommendations.",
        "warning_unavailable": "Official warning source is unavailable; no warning assessment was made.",
        "stale_weather": "Weather data is stale (retrieved {age} minutes ago).",
        "forecast_not_observation": "Values are forecasts or model analyses, not station observations.",
        "preventive_general": "Review the sources listed below and compare with local advisories.",
        "chat_out_of_scope": "I can only answer using the verified agricultural information available to me, and I could not find it for this question. Please consult your local agricultural officer.",
        "chat_no_llm": "The AI assistant is not configured. Here are the most relevant available references I found:",
        "chat_source_reference": "Source reference (not an expert-approved recommendation): {title} — {publisher}, {publication_date}, {section}: {excerpt} [{evidence_id}]",
        "chat_current_weather": "Open-Meteo current model analysis (not a station observation): {values}.",
        "chat_weather_missing": "The provider returned no usable weather values for the requested period.",
        "chat_weather_partial": "The weather provider returned partial data; missing variables remain unassessed.",
        "chat_forecast": "Open-Meteo forecast model data for {days} days; daily rainfall totals: {rainfall}.",
        "chat_history": "Open-Meteo ERA5 reanalysis (not station observations): rainfall total {total} mm across {days} days with rainfall data ({coverage}% coverage).",
        "chat_no_warnings": "The configured official feed reported no warning for this district at retrieval time.",
        "data_unavailable": "One or more requested data sources are unavailable; missing values were not estimated.",
        "when_period": "Expected risk period according to the forecast: {start} to {end}.",
        "outside_pilot": "This location appears to be outside the Andhra Pradesh pilot area; crop rules and knowledge are configured for Andhra Pradesh only.",
        "weather_down": "Live weather data was unavailable, so no weather-based risk could be assessed. Nothing has been estimated.",
        "stage_not_selected": "No growth stage was selected, so only a general weather assessment is shown and stage-specific rules were not applied.",
        "chat_assessment": "The saved FarmShield assessment from {time} reports {risk}. Categories not assessed: {unassessed}. This is the deterministic assessment result, not an official warning.",
        "chat_assessment_stale": "This saved assessment is historical and should not be treated as current. Rerun the assessment to refresh its weather inputs.",
        "chat_context_no_llm": "The AI provider is unavailable. I cannot explain this context further without inventing an answer.",
    },
    "te": {
        "disclaimer": "FarmShield AI నిర్ణయ సహాయక సాధనం మాత్రమే; ఇది అధికారిక హెచ్చరిక కాదు, నిపుణుల సలహాకు ప్రత్యామ్నాయం కాదు. ముఖ్యమైన నిర్ణయాల కోసం మీ స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి.",
        "none": "లేదు",
        "no_data": "డేటా అందుబాటులో లేదు",
        "summary": "{location} సమీపంలో {crop} ({stage}) కోసం నియమ-ఆధారిత అంచనా: మొత్తం ముప్పు స్థాయి {risk}. ఇది సూచన డేటా మరియు నమోదు చేసిన నియమాల ఆధారంగా లెక్కించబడింది; ఇది అధికారిక హెచ్చరిక కాదు.",
        "summary_general": "{location} సమీపంలో {crop} కోసం సాధారణ వాతావరణ అంచనా (పెరుగుదల దశ ఎంచుకోలేదు, కాబట్టి దశ-నిర్దిష్ట నియమాలు వర్తించలేదు): మొత్తం ముప్పు స్థాయి {risk}.",
        "triggered": "{rule}: {reason}",
        "none_triggered": "సూచన డేటా ద్వారా ఏ ధృవీకరించిన నియమమూ ప్రేరేపించబడలేదు.",
        "no_rules": "కొన్ని ముప్పు వర్గాలకు ధృవీకరించిన నియమాలు అందుబాటులో లేవు, కాబట్టి వాటిని అంచనా వేయలేదు.",
        "action_general": "మీ జిల్లాకు సంబంధించిన అధికారిక IMD సూచన మరియు హెచ్చరికలను చూడండి; పొలంలో నిర్ణయాలు తీసుకునే ముందు మీ స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి.",
        "no_crop_action": "ఈ పరిస్థితికి నిపుణులు ఆమోదించిన పంట-నిర్దిష్ట చర్య లేదు. మూలాధార సాధారణ సమాచారం చూపవచ్చు, కానీ అది ధృవీకరించిన సిఫార్సు కాదు.",
        "ai_unavailable": "AI సలహా సేవ తాత్కాలికంగా అందుబాటులో లేదు. మీ వాతావరణ మరియు లెక్కించిన ముప్పు సమాచారం ఇంకా అందుబాటులో ఉంది.",
        "ai_invalid": "AI ప్రతిస్పందనను ధృవీకరించలేకపోయాము, కాబట్టి బదులుగా సురక్షితమైన నియమ-ఆధారిత వివరణ చూపబడింది.",
        "no_evidence": "నమ్మదగిన సిఫార్సు ఇవ్వడానికి తగినంత ధృవీకరించిన వ్యవసాయ సమాచారం మాకు దొరకలేదు.",
        "translation_unavailable": "ఈ విషయం కోసం కోరిన భాషలో అనువాదం అందుబాటులో లేదు; ఇది ఆంగ్లంలో చూపబడింది.",
        "unverified_evidence": "మూలం తనిఖీ చేసిన కొన్ని వ్యవసాయ సూచనలకు ఇంకా నిపుణుల సమీక్ష అవసరం; అవి ధృవీకరించిన సిఫార్సులు కావు.",
        "warning_unavailable": "అధికారిక హెచ్చరిక మూలం అందుబాటులో లేదు; హెచ్చరిక అంచనా వేయలేదు.",
        "stale_weather": "వాతావరణ డేటా పాతబడింది ({age} నిమిషాల క్రితం పొందినది).",
        "forecast_not_observation": "ఈ విలువలు సూచనలు లేదా మోడల్ విశ్లేషణలు, కేంద్ర పరిశీలనలు కావు.",
        "preventive_general": "క్రింద ఇచ్చిన మూలాలను చూసి స్థానిక సలహాలతో పోల్చండి.",
        "chat_out_of_scope": "నాకు అందుబాటులో ఉన్న ధృవీకరించిన వ్యవసాయ సమాచారం ఆధారంగా మాత్రమే సమాధానం ఇవ్వగలను; ఈ ప్రశ్నకు అది దొరకలేదు. దయచేసి మీ స్థానిక వ్యవసాయ అధికారిని సంప్రదించండి.",
        "chat_no_llm": "AI సహాయకుడు కాన్ఫిగర్ చేయబడలేదు. నాకు లభించిన అత్యంత సంబంధిత సూచనలు ఇవి:",
        "chat_source_reference": "మూల సమాచారం (నిపుణుల ఆమోదించిన సిఫార్సు కాదు): {title} — {publisher}, {publication_date}, {section}: {excerpt} [{evidence_id}]",
        "chat_current_weather": "Open-Meteo ప్రస్తుత మోడల్ విశ్లేషణ (కేంద్ర పరిశీలన కాదు): {values}.",
        "chat_weather_missing": "అభ్యర్థించిన కాలానికి ఉపయోగించగల వాతావరణ విలువలు ప్రొవైడర్ ఇవ్వలేదు.",
        "chat_weather_partial": "వాతావరణ ప్రొవైడర్ కొంత డేటా మాత్రమే ఇచ్చింది; లేని చరరాశులను అంచనా వేయలేదు.",
        "chat_forecast": "{days} రోజుల Open-Meteo వాతావరణ సూచన మోడల్ డేటా; రోజువారీ వర్షపాతం మొత్తాలు: {rainfall}.",
        "chat_history": "Open-Meteo ERA5 పునర్విశ్లేషణ (కేంద్ర పరిశీలనలు కాదు): వర్షపాతం డేటా ఉన్న {days} రోజులలో మొత్తం {total} మిమీ వర్షపాతం ({coverage}% కవరేజ్).",
        "chat_no_warnings": "పొందిన సమయంలో కాన్ఫిగర్ చేసిన అధికారిక ఫీడ్ ఈ జిల్లాకు హెచ్చరిక లేదని తెలిపింది.",
        "data_unavailable": "అభ్యర్థించిన ఒకటి లేదా అంతకంటే ఎక్కువ డేటా మూలాలు అందుబాటులో లేవు; లేని విలువలను అంచనా వేయలేదు.",
        "when_period": "సూచన ప్రకారం అంచనా ముప్పు కాలం: {start} నుండి {end} వరకు.",
        "outside_pilot": "ఈ ప్రాంతం ఆంధ్రప్రదేశ్ పైలట్ ప్రాంతం వెలుపల ఉన్నట్లు కనిపిస్తోంది; పంట నియమాలు మరియు సమాచారం ఆంధ్రప్రదేశ్ కోసం మాత్రమే రూపొందించబడ్డాయి.",
        "weather_down": "ప్రత్యక్ష వాతావరణ డేటా అందుబాటులో లేదు, కాబట్టి వాతావరణ ఆధారిత ముప్పును అంచనా వేయలేకపోయాము. ఏదీ ఊహించలేదు.",
        "stage_not_selected": "పెరుగుదల దశను ఎంచుకోలేదు, కాబట్టి సాధారణ వాతావరణ అంచనా మాత్రమే చూపబడింది; దశ-నిర్దిష్ట నియమాలు వర్తించలేదు.",
        "chat_assessment": "{time} నాటి FarmShield సేవ్ చేసిన అంచనాలో ముప్పు స్థాయి {risk}. అంచనా వేయని వర్గాలు: {unassessed}. ఇది నిర్ణయ ఇంజిన్ ఫలితం మాత్రమే; అధికారిక హెచ్చరిక కాదు.",
        "chat_assessment_stale": "ఈ సేవ్ చేసిన అంచనా పాతది; ప్రస్తుత పరిస్థితిగా పరిగణించకండి. వాతావరణ డేటాను నవీకరించడానికి మళ్లీ అంచనా వేయండి.",
        "chat_context_no_llm": "AI సేవ అందుబాటులో లేదు. ఊహించి సమాధానం ఇవ్వకుండా ఈ సందర్భాన్ని మరింత వివరించలేను.",
    },
}


def normalize_language(code: str | None) -> Tuple[str, bool]:
    """E29: invalid code -> English. Returns (language, was_invalid)."""
    if code in SUPPORTED_LANGUAGES:
        return code, False
    return "en", code is not None


def detect_language(text: str) -> str:
    """Detect Telugu script only when the caller did not provide an explicit language preference."""
    return "te" if any("\u0c00" <= char <= "\u0c7f" for char in text) else "en"


def msg(lang: str, key: str, **kw) -> str:
    lang = lang if lang in MESSAGES else "en"
    template = MESSAGES[lang].get(key) or MESSAGES["en"][key]
    return template.format(**kw) if kw else template


def risk_label(lang: str, risk: str) -> str:
    return RISK_LABELS.get(lang, RISK_LABELS["en"]).get(risk, risk)


def category_label(lang: str, cat: str) -> str:
    return CATEGORY_LABELS.get(lang, CATEGORY_LABELS["en"]).get(cat, cat)


def crop_name(lang: str, crop_id: str) -> str:
    return CROP_NAMES.get(lang, CROP_NAMES["en"]).get(crop_id, crop_id)


VARIABLE_LABELS = {
    "en": {"precipitation_sum_mm": "Forecast daily rainfall", "temperature_max_c": "Forecast daily maximum temperature",
           "temperature_min_c": "Forecast daily minimum temperature", "wind_speed_max_kmh": "Forecast daily maximum wind speed"},
    "te": {"precipitation_sum_mm": "సూచించిన రోజువారీ వర్షపాతం", "temperature_max_c": "సూచించిన రోజువారీ గరిష్ఠ ఉష్ణోగ్రత",
           "temperature_min_c": "సూచించిన రోజువారీ కనిష్ఠ ఉష్ణోగ్రత", "wind_speed_max_kmh": "సూచించిన రోజువారీ గరిష్ఠ గాలి వేగం"},
}

REASONS = {
    "en": {
        "triggered": "{variable} reached {actual} {unit} on {period}; rule {rule_id} applies when {condition}. Source: {source}.",
        "not_triggered": "{variable} stayed outside the rule range over {period}.",
        "not_evaluable": "Could not evaluate: {why}.",
        "disabled_unverified": "Rule exists but is disabled because its threshold has not been verified by an authoritative reviewer.",
        "window_mismatch": "Rule is disabled because the source measurement window is not verified as aligned with the weather input window.",
        "not_applicable": "Not applicable: {why}.",
        "category_low": "No triggered rule among the enabled, verified rules for this category.",
        "category_no_rules": "No verified rule is available for this category, so it was not assessed.",
        "category_stage_needed": "Select a growth stage to evaluate stage-specific rules for this category.",
        "category_missing_data": "Required weather data was missing, so this category could not be assessed.",
        "warning_none": "No active official warning was found in the retrieved feed for this district.",
        "warning_partial": "The official warning feed was incomplete, so absence of an active warning could not be confirmed.",
        "warning_present": "Official warning issued by {source}: {title} (severity as supplied: {severity}).",
        "cond_between": "{lo} <= value < {hi} {unit}", "cond_gt": "value > {t} {unit}", "cond_ge": "value >= {t} {unit}",
        "cond_lt": "value < {t} {unit}", "cond_le": "value <= {t} {unit}",
    },
    "te": {
        "triggered": "{variable} {period} నాడు {actual} {unit} కు చేరింది; నియమం {rule_id} వర్తించే పరిస్థితి: {condition}. మూలం: {source}.",
        "not_triggered": "{period} కాలంలో {variable} నియమ పరిధి వెలుపల ఉంది.",
        "not_evaluable": "మూల్యాంకనం చేయలేకపోయాము: {why}.",
        "disabled_unverified": "నియమం ఉంది కానీ దాని పరిమితిని అధీకృత సమీక్షకుడు ధృవీకరించనందున నిలిపివేయబడింది.",
        "window_mismatch": "మూలంలోని కొలత కాలం వాతావరణ డేటా కాలంతో సరిపోతుందని ధృవీకరించనందున నియమం నిలిపివేయబడింది.",
        "not_applicable": "వర్తించదు: {why}.",
        "category_low": "ఈ వర్గంలో ప్రారంభించబడిన, ధృవీకరించిన నియమాలలో ఏదీ ప్రేరేపించబడలేదు.",
        "category_no_rules": "ఈ వర్గానికి ధృవీకరించిన నియమం అందుబాటులో లేదు, కాబట్టి అంచనా వేయలేదు.",
        "category_stage_needed": "ఈ వర్గంలో దశ-నిర్దిష్ట నియమాలను మూల్యాంకనం చేయడానికి పెరుగుదల దశను ఎంచుకోండి.",
        "category_missing_data": "అవసరమైన వాతావరణ డేటా లేనందున ఈ వర్గాన్ని అంచనా వేయలేకపోయాము.",
        "warning_none": "ఈ జిల్లాకు పొందిన ఫీడ్‌లో క్రియాశీల అధికారిక హెచ్చరిక కనబడలేదు.",
        "warning_partial": "అధికారిక హెచ్చరికల ఫీడ్ పాక్షికంగా మాత్రమే అందింది; హెచ్చరిక లేదని నిర్ధారించలేము.",
        "warning_present": "{source} జారీ చేసిన అధికారిక హెచ్చరిక: {title} (మూలం ఇచ్చిన తీవ్రత: {severity}).",
        "cond_between": "{lo} <= విలువ < {hi} {unit}", "cond_gt": "విలువ > {t} {unit}", "cond_ge": "విలువ >= {t} {unit}",
        "cond_lt": "విలువ < {t} {unit}", "cond_le": "విలువ <= {t} {unit}",
    },
}


def reason(lang: str, key: str, **kw) -> str:
    table = REASONS.get(lang, REASONS["en"])
    return (table.get(key) or REASONS["en"][key]).format(**kw)


def variable_label(lang: str, var: str) -> str:
    return VARIABLE_LABELS.get(lang, VARIABLE_LABELS["en"]).get(var) or VARIABLE_LABELS["en"].get(var, var)
