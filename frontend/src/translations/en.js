// English UI dictionary (canonical). Every key must exist in te.js (enforced by a test).
export default {
  'app.name': 'FarmShield AI',
  'app.tagline': 'Weather-aware crop risk decision support',
  'app.disclaimer': 'FarmShield AI is a decision-support tool, not an official warning or a substitute for professional advice. Consult your local agricultural officer for important decisions.',
  'app.attribution': 'Weather data by Open-Meteo.com (CC BY 4.0)',
  'app.skip': 'Skip to content',

  'nav.dashboard': 'Dashboard', 'nav.weather': 'Weather', 'nav.crop_risk': 'Crop Risk', 'nav.advisor': 'AI Advisor', 'nav.history': 'Historical Analysis',
  'nav.knowledge': 'Knowledge', 'nav.calendar': 'Crop Calendar', 'nav.market': 'Market Intelligence', 'nav.crop_health': 'Crop Health', 'nav.reports': 'Reports',
  'nav.notifications': 'Notifications', 'nav.satellite': 'Satellite', 'nav.voice': 'Voice Assistant', 'nav.regional': 'Regional Map', 'nav.data_status': 'Data Status',
  'nav.settings': 'Settings', 'nav.admin': 'Regional Dashboard', 'nav.multi_region': 'More regions & languages', 'nav.integrations': 'Integrations',
  'nav.menu': 'Menu', 'nav.badge.planned': 'Planned', 'nav.badge.limited': 'Needs setup', 'nav.badge.beta': 'Unverified',

  'header.guest': 'Guest', 'header.profile': 'Profile', 'header.no_location': 'No location selected', 'header.language': 'Language', 'header.notifications': 'Notifications',

  'sel.title': 'Location and crop', 'sel.search': 'Search location', 'sel.search_ph': 'Village, town or district in Andhra Pradesh', 'sel.search_btn': 'Search',
  'sel.use_current': 'Use current location', 'sel.locating': 'Locating…', 'sel.geo_denied': 'Location permission was denied. Please search for your location instead.',
  'sel.geo_unsupported': 'This browser does not support location. Please search instead.', 'sel.geo_why': 'Your location is used only to fetch weather for that point. It is not stored unless you save a profile.',
  'sel.districts': 'Or choose a district', 'sel.district_ph': 'Select district', 'sel.crop': 'Crop', 'sel.crop_ph': 'Select crop', 'sel.stage': 'Growth stage',
  'sel.stage_ph': 'Select growth stage', 'sel.analyze': 'Analyze', 'sel.change': 'Change location', 'sel.coords': 'Coordinates', 'sel.no_results': 'No supported Andhra Pradesh location matched. Try a broader name such as the district.',
  'sel.need_location': 'Please select a location first.', 'sel.need_crop': 'Select a crop and growth stage to view crop-specific risk.', 'sel.stage_optional_note': 'Without a growth stage only a general weather assessment is shown.',
  'sel.resolution': 'Weather is modelled on a grid (about 1–25 km). A district or town centre does not represent every village.', 'sel.selected': 'Selected', 'sel.source.search': 'search', 'sel.source.geolocation': 'device location',
  'sel.review_note': 'Crop stage catalogue has not yet been reviewed by an agronomist.', 'sel.approx_district': 'Nearest district centre (approximate)',

  'wx.title': 'Current weather', 'wx.temp': 'Temperature', 'wx.feels': 'Feels like', 'wx.humidity': 'Humidity', 'wx.rain': 'Rainfall (now)', 'wx.wind': 'Wind', 'wx.cloud': 'Cloud cover', 'wx.status': 'Condition',
  'wx.provider': 'Provider', 'wx.observed': 'Analysis time', 'wx.updated': 'Last update', 'wx.units': 'Units', 'wx.model_note': 'Current values are model analyses, not station observations.', 'wx.missing': 'Not available',
  'wx.unavailable': 'Live weather information is currently unavailable. Please try again later.', 'wx.min': 'Min', 'wx.max': 'Max', 'wx.rain_total': 'Rain',

  'fc.title': 'Forecast', 'fc.hourly': 'Next 24 hours', 'fc.daily': '7-day', 'fc.temp': 'Temperature (°C)', 'fc.rain': 'Rainfall (mm)', 'fc.humidity': 'Humidity (%)', 'fc.wind': 'Wind (km/h)',
  'fc.note': 'Values are forecasts, not observations.', 'fc.empty': 'No forecast data.', 'fc.day': 'Day', 'fc.hour': 'Hour',

  'warn.title': 'Official weather warnings', 'warn.none': 'No active official warning was found for this district in the retrieved feed.', 'warn.not_configured': 'Live IMD warnings are not connected. No warning has been assessed.',
  'warn.unavailable': 'The official warning source could not be retrieved. No warning has been assessed.', 'warn.official_links': 'Check official sources', 'warn.severity': 'Severity (as supplied)', 'warn.issued': 'Issued',
  'warn.valid': 'Valid', 'warn.area': 'Area', 'warn.source': 'Source', 'warn.until': 'until', 'warn.from': 'from',

  'risk.title': 'Crop risk', 'risk.overall': 'Overall risk', 'risk.categories': 'Risk categories', 'risk.why': 'Why this result', 'risk.triggered': 'Triggered rules', 'risk.none_triggered': 'No enabled, verified rule was triggered.',
  'risk.low': 'Low', 'risk.moderate': 'Moderate', 'risk.high': 'High', 'risk.critical': 'Critical', 'risk.insufficient_data': 'Insufficient data',
  'risk.crop_stage': 'Crop and stage', 'risk.period': 'Forecast period', 'risk.coverage': 'Categories assessed', 'risk.coverage_note': 'Categories without a verified rule are not assessed. A "Low" result only covers the assessed categories.',
  'risk.confidence': 'Confidence', 'risk.conf.none': 'None', 'risk.conf.limited': 'Limited', 'risk.conf.partial': 'Partial', 'risk.conf.good': 'Good', 'risk.method': 'Rule-based classification from documented rules. Not a machine-learning prediction.',
  'risk.details': 'Details', 'risk.hide': 'Hide', 'risk.rule': 'Rule', 'risk.variable': 'Weather variable', 'risk.threshold': 'Threshold', 'risk.actual': 'Actual value', 'risk.period_examined': 'Period examined', 'risk.source': 'Source',
  'risk.severity': 'Severity', 'risk.reason': 'Reason', 'risk.timeline': 'Expected risk timeline', 'risk.no_timeline': 'No risk period in the forecast.', 'risk.actions': 'Recommended actions', 'risk.no_actions': 'No verified crop-specific action is available.',
  'risk.disabled_rules': 'Rules awaiting expert review (disabled)', 'risk.need_selection': 'Select a crop and growth stage to view crop-specific risk.', 'risk.not_assessed': 'Not assessed', 'risk.general_only': 'General weather assessment (no growth stage selected).',
  'risk.unvalidated': 'FarmShield currently cannot calculate a scientifically validated crop-specific risk level for this condition. The following agricultural guidance is provided for general reference.',
  'risk.review': 'needs review', 'risk.verified': 'verified',

  'adv.title': 'AI advisory', 'adv.summary': 'Summary', 'adv.explanation': 'Why', 'adv.immediate': 'Immediate precautions', 'adv.preventive': 'Preventive recommendations', 'adv.when': 'Relevant period',
  'adv.uncertainty': 'Uncertainty and limitations', 'adv.evidence': 'Evidence', 'adv.generated': 'Generated', 'adv.status.ai_generated': 'AI-generated explanation (validated)', 'adv.status.fallback_ai_unavailable': 'AI unavailable – rule-based explanation',
  'adv.status.fallback_invalid_output': 'AI output could not be validated – rule-based explanation', 'adv.status.fallback_no_provider': 'AI not configured – rule-based explanation', 'adv.ask': 'Ask a follow-up question', 'adv.ask_ph': 'e.g. Why does heavy rain matter at this stage?',
  'adv.send': 'Send', 'adv.thinking': 'Thinking…', 'adv.you': 'You', 'adv.assistant': 'FarmShield', 'adv.none_yet': 'Run an analysis to see the advisory.', 'adv.regenerate': 'Regenerate', 'adv.generate': 'Generate AI advisory', 'adv.none_list': 'None',
  'adv.chat_status.out_of_scope': 'Outside verified knowledge', 'adv.chat_status.retrieval_only': 'Available context only (AI unavailable)', 'adv.chat_status.ai_generated': 'AI answer grounded in evidence', 'adv.chat_status.fallback_invalid_output': 'AI answer rejected by validation',
  'adv.personalised': 'Personalisation context',

  'ev.title': 'Evidence and sources', 'ev.none': 'No evidence attached.', 'ev.publisher': 'Publisher', 'ev.date': 'Published', 'ev.open': 'Open source', 'ev.kind.risk_rule': 'Risk rule source', 'ev.kind.agricultural_reference': 'Agricultural reference', 'ev.kind.meteorological_reference': 'Meteorological reference',
  'ev.kind.official_warning': 'Official warning', 'ev.kind.forecast': 'Forecast', 'ev.status.verified': 'Verified', 'ev.status.needs_review': 'Not yet reviewed', 'ev.status.outdated': 'Outdated', 'ev.status.official': 'Official',
  'ev.status.source_verified': 'Source verified; expert review pending', 'ev.status.source_unverified': 'Source not verified', 'ev.status.expert_review_required': 'Expert review required', 'ev.status.expert_approved': 'Expert approved', 'ev.status.conflicting_evidence': 'Conflicting evidence', 'ev.status.insufficient_evidence': 'Insufficient evidence',
  'ev.window.aligned': 'measurement windows aligned', 'ev.window.not_aligned': 'measurement windows not aligned', 'ev.window.not_assessed': 'window not assessed', 'ev.window.not_applicable': 'not applicable', 'ev.window.unknown': 'window unknown',
  'ev.scope': 'Applicability', 'ev.crop_stage': 'Crop stage', 'ev.general_stage': 'General / not stage-specific', 'ev.source_window': 'Source window', 'ev.input_window': 'Weather input window', 'ev.limitations': 'Limitations', 'ev.page_section': 'Page / section', 'ev.source_access': 'Source access',
  'ev.unreviewed_note': 'Source access does not imply agronomic approval; confirm local suitability before acting.',

  'q.title': 'Data sources and quality', 'q.weather': 'Weather provider', 'q.warnings': 'Official warning provider', 'q.knowledge': 'Agricultural references', 'q.retrieved': 'Retrieved', 'q.freshness': 'Freshness',
  'q.fresh': 'Fresh', 'q.stale': 'Stale', 'q.unavailable': 'Unavailable', 'q.partial': 'Partial', 'q.missing': 'Missing variables', 'q.age': 'Age', 'q.min': 'min', 'q.notes': 'Notes',

  'state.loading': 'Loading…', 'state.empty': 'Nothing to show yet.', 'state.error': 'Something went wrong.', 'state.retry': 'Retry', 'state.unavailable': 'Service unavailable.', 'state.stale': 'Data may be out of date.',
  'state.partial': 'Some data is missing.', 'state.connection': 'Cannot reach the FarmShield server. Check your connection and try again.', 'state.planned': 'This module is planned and not available yet.',
  'state.needs_setup': 'This module needs configuration by the operator before it can show data.', 'state.analyze_first': 'Choose a location and crop, then press Analyze.',

  'hist.title': 'Historical analysis', 'hist.range': 'Date range', 'hist.start': 'Start', 'hist.end': 'End', 'hist.load': 'Load history', 'hist.temp': 'Temperature (°C)', 'hist.rain': 'Daily rainfall (mm)', 'hist.monthly': 'Monthly rainfall (mm)',
  'hist.coverage': 'Data coverage', 'hist.reanalysis': 'Reanalysis data (ERA5), not station observations.', 'hist.seasonal': 'Seasonal rainfall comparison', 'hist.season': 'Season (months)', 'hist.baseline': 'Baseline years', 'hist.compare': 'Compare',
  'hist.observed': 'Observed total', 'hist.mean': 'Baseline mean', 'hist.deviation': 'Difference', 'hist.method': 'Method', 'hist.limits': 'Limitations', 'hist.unavailable_comparison': 'A valid comparison is not possible', 'hist.rain_cov': 'Rainfall coverage',
  'hist.tmax': 'Max', 'hist.tmin': 'Min', 'hist.need_location': 'Select a location on the Dashboard first.',

  'kb.title': 'Agricultural knowledge', 'kb.search': 'Search', 'kb.search_ph': 'e.g. heat stress flowering', 'kb.crop': 'Crop', 'kb.stage': 'Growth stage', 'kb.topic': 'Topic', 'kb.all': 'All', 'kb.results': 'results', 'kb.none': 'No matching material found.', 'kb.guidance': 'Source-backed general guidance',
  'kb.state': 'State', 'kb.district': 'District', 'kb.season': 'Season', 'kb.season.kharif': 'Kharif', 'kb.season.rabi': 'Rabi', 'kb.season.summer': 'Summer',
  'kb.concern': 'Concern', 'kb.status': 'Evidence status', 'kb.concern.rainfall': 'Rainfall', 'kb.concern.rainfall_classification': 'Rainfall class', 'kb.concern.excess_rainfall': 'Excess rainfall / waterlogging', 'kb.concern.dry_spell': 'Dry spell', 'kb.concern.water_stress': 'Water stress', 'kb.concern.water_management': 'Water management', 'kb.concern.high_temperature': 'High temperature', 'kb.concern.low_temperature': 'Low temperature', 'kb.concern.humidity': 'Humidity / disease', 'kb.concern.wind': 'Wind', 'kb.concern.severe_weather_warning': 'Severe-weather warning', 'kb.concern.cultivation': 'Cultivation practices', 'kb.concern.pest_disease': 'Pests and diseases', 'kb.concern.variety_selection': 'Variety selection', 'kb.concern.submergence': 'Submergence',
  'kb.coverage': 'Evidence coverage and gaps', 'kb.coverage_summary': '{count} crop-stage-concern combinations have insufficient evidence.', 'kb.coverage_details': 'Show stage-by-stage gaps', 'kb.coverage_note': 'Unvalidated risk rules remain disabled. A source being accessible does not mean its findings are locally approved.',
  'dash.guidance': 'Agricultural guidance', 'dash.guidance_note': 'Source-backed information for general reference; it is not a validated crop-risk result. Check the source date, scope and limitations.', 'dash.guidance_none': 'No source-backed guidance was retrieved for this crop and stage. Open Agricultural knowledge to search available sources.',
  'kb.documents': 'Documents in the knowledge base',

  'cal.title': 'Crop calendar', 'cal.stages': 'Growth stages', 'cal.unavailable': 'Verified regional sowing and harvest dates are not configured. Planting dates differ by district and season; consult your local agricultural officer.',
  'cal.review': 'Stage catalogue is awaiting agronomist review.',

  'mkt.title': 'Market intelligence', 'mkt.subtitle': 'Select a state, optional district, and a commodity actually present in the live provider data.', 'mkt.dashboard_title': 'Nearby market prices', 'mkt.dashboard_select': 'Select a supported crop and location to see market information.', 'mkt.loading': 'Loading market information…',
  'mkt.state': 'State', 'mkt.select_state': 'Select state', 'mkt.district': 'District', 'mkt.all_districts': 'All available districts', 'mkt.select_commodity': 'Select available commodity', 'mkt.options_loading': 'Checking live market options…', 'mkt.options_unavailable': 'Could not load live states, districts, and commodities.', 'mkt.options_partial': 'The provider response was paginated to a safe limit; listed choices may not include every current record.', 'mkt.options_source': 'Options retrieved from live source:',
  'mkt.load': 'Load live prices', 'mkt.market': 'Market', 'mkt.commodity': 'Commodity', 'mkt.variety': 'Variety', 'mkt.grade': 'Grade', 'mkt.date': 'Arrival date', 'mkt.min': 'Min', 'mkt.max': 'Max', 'mkt.modal': 'Modal', 'mkt.unit': 'Price unit', 'mkt.unit_unconfirmed': 'Unit unconfirmed', 'mkt.records': 'Records',
  'mkt.latest': 'Latest arrival date', 'mkt.source': 'Source', 'mkt.none': 'No prices returned for this selection.', 'mkt.chart': 'Reported mandi prices by market', 'mkt.freshness': 'Freshness', 'mkt.fresh': 'Recent', 'mkt.stale': 'Stale', 'mkt.stale_notice': 'These records have arrival dates older than 7 days and may not represent current market prices.',
  'mkt.wholesale_note': 'Reported mandi wholesale prices are not guaranteed farmer selling prices.',
  'mkt.ai_title': 'Market comparison assistant', 'mkt.ai_disclaimer': 'AI is called only when you request it. It explains comparable provider records; it cannot account for travel costs, fees, quality, buyer terms, or guarantee a selling price.',
  'mkt.ai_generate': 'Explain these prices', 'mkt.ai_loading': 'Preparing source-based explanation…', 'mkt.highest_quote': 'Highest reported modal quote among comparable fresh records (not a sell recommendation):',
  'mkt.question_label': 'Ask a market follow-up question', 'mkt.question_placeholder': 'Ask about the displayed data or its limitations', 'mkt.ask': 'Ask',
  'mkt.ai_status.not_configured': 'LLM is not configured. Live prices and the data-based comparison above remain available.', 'mkt.ai_status.unavailable': 'The configured LLM is temporarily unavailable; no AI explanation was generated.', 'mkt.ai_status.invalid_output': 'The AI response did not pass safety checks and was not shown.', 'mkt.ai_status.insufficient_comparable_data': 'Live records exist, but two markets do not share the same commodity, variety, and arrival date for a fair comparison.',

  'ch.title': 'Crop health (preliminary)', 'ch.upload': 'Upload or capture a photo', 'ch.formats': 'JPEG, PNG or WebP, up to 10 MB', 'ch.consent': 'I consent to this image being sent for analysis. It is not stored.', 'ch.symptoms': 'Symptoms (optional)',
  'ch.analyze': 'Analyze photo', 'ch.preview': 'Preview', 'ch.result': 'Possible issues', 'ch.confidence': 'Confidence', 'ch.limits': 'Limitations', 'ch.next': 'Suggested next steps', 'ch.preliminary': 'Preliminary AI-assisted identification – not a diagnosis.',
  'ch.unavailable': 'Image analysis needs a configured vision-capable AI model.', 'ch.uncertain': 'The result is uncertain. Please have the crop inspected by an expert.', 'ch.too_big': 'The image is larger than 10 MB.', 'ch.bad_type': 'Only JPEG, PNG or WebP images are accepted.',
  'ch.none': 'No possible issue identified.',

  'rep.title': 'Reports', 'rep.language': 'Report language', 'rep.include_ai': 'Include AI advisory', 'rep.generate': 'Download report', 'rep.note': 'The report is an HTML file. Open it and use your browser’s Print → Save as PDF.',
  'rep.te_note': 'Telugu text has not yet been verified by an agricultural-domain reviewer.', 'rep.need_assessment': 'Run an analysis on the Dashboard first.', 'rep.preview': 'Report will contain', 'rep.preview_list': 'Location, crop and stage, weather summary, forecast, risk assessment, reasons, recommendations, evidence and creation time.',

  'nt.title': 'Notifications', 'nt.list': 'Alerts', 'nt.none': 'No alerts.', 'nt.prefs': 'Alert preferences', 'nt.enable': 'Enable in-app alerts for the selected location and crop', 'nt.consent': 'I consent to receive in-app alerts. I can turn this off at any time.',
  'nt.levels': 'Alert for risk levels', 'nt.save': 'Save preferences', 'nt.disable': 'Disable alerts', 'nt.refresh': 'Check now', 'nt.mark_read': 'Mark read', 'nt.unread': 'unread', 'nt.channels_note': 'Email and SMS alerts are planned and not available yet.',
  'nt.quiet': 'Quiet hours (optional)', 'nt.saved': 'Preferences saved.', 'nt.created': 'new alerts', 'nt.need_selection': 'Select a location and crop first.', 'nt.active': 'Active', 'nt.expired': 'Expired',

  'sat.title': 'Satellite vegetation (NDVI)', 'sat.load': 'Load vegetation index', 'sat.observed': 'Observation date', 'sat.provider': 'Provider', 'sat.resolution': 'Spatial resolution', 'sat.limits': 'Data-quality notes', 'sat.chart': 'NDVI over time',

  'vo.title': 'Voice assistant', 'vo.start': 'Start speaking', 'vo.stop': 'Stop', 'vo.listening': 'Listening…', 'vo.heard': 'Recognised text (edit if wrong)', 'vo.ask': 'Ask', 'vo.speak': 'Read aloud', 'vo.unsupported': 'Speech input is not supported in this browser. Please type your question.',
  'vo.error': 'Could not recognise speech. Please retry or type your question.', 'vo.uncertain': 'Speech recognition can be wrong. Please check the text before sending.', 'vo.text_alt': 'Type instead', 'vo.no_tts': 'Spoken replies are not supported on this device.',
  'vo.lang': 'Speech language',

  'rg.title': 'Regional risk map', 'rg.crop': 'Crop', 'rg.stage': 'Growth stage (optional)', 'rg.filter': 'Filter by risk', 'rg.load': 'Load map', 'rg.res': 'Each marker is one point per district, not a district-wide measurement.', 'rg.unavailable': 'Unavailable districts',
  'rg.table': 'District comparison', 'rg.rain_max': 'Max forecast daily rain (mm)', 'rg.all': 'All', 'rg.warnings_status': 'Official warnings',
  'rg.no_risk': 'No scientifically validated crop-risk category is available for these districts. The displayed rainfall and weather freshness are provider data, not a crop-risk classification.',
  'rg.legend': 'Map legend', 'rg.weather_status': 'Weather data status', 'rg.retrieved': 'Retrieved',

  'ds.title': 'Data status and reliability', 'ds.providers': 'Providers', 'ds.success': 'Last success', 'ds.failure': 'Last failure', 'ds.counts': 'Successes / failures', 'ds.policy': 'Freshness policy', 'ds.never': 'never', 'ds.services': 'Services',
  'ds.modules': 'Module status', 'ds.refresh': 'Refresh',

  'set.title': 'Settings and farm profile', 'set.language': 'Language', 'set.profile': 'Farm profile (optional)', 'set.profile_note': 'Saving a profile is optional. Only what you enter here is stored. You can delete it at any time.',
  'set.nickname': 'Farm nickname', 'set.area': 'Farm area (optional)', 'set.unit': 'Unit', 'set.acre': 'acre', 'set.hectare': 'hectare', 'set.save': 'Save profile', 'set.delete': 'Delete saved profile', 'set.saved': 'Profile saved.',
  'set.deleted': 'Profile deleted.', 'set.use_selection': 'Use current location, crop and stage', 'set.none': 'No profile saved. The app works fully as a guest.', 'set.te_review': 'Telugu text is awaiting review by an agricultural-domain reviewer.',

  'adm.title': 'Regional intelligence dashboard', 'adm.token': 'Admin token', 'adm.load': 'Load summary', 'adm.note': 'Aggregated data only. Access requires an operator-configured token.', 'adm.dist': 'Risk distribution',
  'adm.fresh': 'Data freshness', 'adm.triggered': 'Districts with triggered rules',

  'plan.title': 'Planned module', 'plan.text': 'This part of the FarmShield roadmap is designed in the architecture but is not implemented yet.',

  'common.close': 'Close', 'common.none': 'None', 'common.source': 'Source', 'common.open': 'Open', 'common.status': 'Status', 'common.module_note': 'Note', 'common.notices': 'Notices',

  'code.0': 'Clear sky', 'code.1': 'Mainly clear', 'code.2': 'Partly cloudy', 'code.3': 'Overcast', 'code.45': 'Fog', 'code.48': 'Rime fog', 'code.51': 'Light drizzle', 'code.53': 'Moderate drizzle', 'code.55': 'Dense drizzle',
  'code.56': 'Freezing drizzle', 'code.57': 'Dense freezing drizzle', 'code.61': 'Slight rain', 'code.63': 'Moderate rain', 'code.65': 'Heavy rain', 'code.66': 'Freezing rain', 'code.67': 'Heavy freezing rain',
  'code.71': 'Slight snow', 'code.73': 'Moderate snow', 'code.75': 'Heavy snow', 'code.77': 'Snow grains', 'code.80': 'Slight rain showers', 'code.81': 'Moderate rain showers', 'code.82': 'Violent rain showers',
  'code.85': 'Slight snow showers', 'code.86': 'Heavy snow showers', 'code.95': 'Thunderstorm', 'code.96': 'Thunderstorm with slight hail', 'code.99': 'Thunderstorm with heavy hail',
}
