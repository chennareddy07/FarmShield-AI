import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import api from '../services/api'
import { translate } from '../translations'

const Ctx = createContext(null)
export const useApp = () => useContext(Ctx)

const LS = {
  get: (k) => { try { return window.localStorage.getItem(k) } catch { return null } },
  set: (k, v) => { try { window.localStorage.setItem(k, v) } catch { /* storage unavailable */ } },
  del: (k) => { try { window.localStorage.removeItem(k) } catch { /* ignore */ } },
}
const idle = { status: 'idle', weather: null, forecast: null, warnings: null, assessment: null, advisory: null, errors: {} }

export function AppProvider({ children }) {
  const [language, setLanguageState] = useState(LS.get('fs_lang') || 'en')
  const [location, setLocation] = useState(null)           // {name, district, latitude, longitude, source}
  const [cropId, setCropId] = useState('')
  const [stageId, setStageId] = useState('')
  const [crops, setCrops] = useState([])
  const [regions, setRegions] = useState(null)
  const [modules, setModules] = useState([])
  const [analysis, setAnalysis] = useState(idle)
  const [advisoryLoading, setAdvisoryLoading] = useState(false)
  const [profileId, setProfileId] = useState(LS.get('fs_profile') || null)
  const [sessionReady, setSessionReady] = useState(false)
  const [bootError, setBootError] = useState(null)
  const [health, setHealth] = useState(null)
  const runId = useRef(0)

  const t = useCallback((key, vars) => translate(language, key, vars), [language])

  const setLanguage = (l) => { setLanguageState(l); LS.set('fs_lang', l); document.documentElement.lang = l }
  useEffect(() => { document.documentElement.lang = language }, [])  // eslint-disable-line

  const boot = useCallback(async () => {
    setBootError(null)
    try {
      await api.session()
      setSessionReady(true)
      const [c, r, m] = await Promise.all([api.crops(), api.regions(), api.modules()])
      setCrops(c); setRegions(r); setModules(m)
      api.health().then(setHealth).catch(() => {})
    } catch (e) { setBootError(e) }
  }, [])
  useEffect(() => { boot() }, [boot])

  const loadAdvisory = useCallback(async (assessmentId, lang, myRun) => {
    setAdvisoryLoading(true)
    try {
      const advisory = await api.advisory(assessmentId, lang, profileId || undefined)
      if (myRun === runId.current) setAnalysis((a) => ({ ...a, advisory, errors: { ...a.errors, advisory: null } }))
    } catch (e) {
      if (myRun === runId.current) setAnalysis((a) => ({ ...a, errors: { ...a.errors, advisory: e } }))
    } finally { if (myRun === runId.current) setAdvisoryLoading(false) }
  }, [profileId])

  const runAnalysis = useCallback(async () => {
    if (!location) return
    const my = ++runId.current
    setAnalysis({ ...idle, status: 'loading' })
    const { latitude, longitude, district, name } = location
    const jobs = cropId
      ? { assessment: api.assess({ latitude, longitude, crop_id: cropId, growth_stage_id: stageId || null, language, district, location_name: name, profile_id: profileId }) }
      : { weather: api.current(latitude, longitude), forecast: api.forecast(latitude, longitude, 7), warnings: api.warnings(district) }
    const keys = Object.keys(jobs)
    const results = await Promise.allSettled(keys.map((k) => jobs[k]))
    if (my !== runId.current) return
    const next = { ...idle, status: 'done', errors: {} }
    results.forEach((r, i) => { if (r.status === 'fulfilled') next[keys[i]] = r.value; else next.errors[keys[i]] = r.reason })
    if (next.assessment?.weather_snapshot) {
      next.weather = next.assessment.weather_snapshot.current
      next.forecast = next.assessment.weather_snapshot.forecast
      next.warnings = next.assessment.warnings_snapshot
    }
    setAnalysis(next)
  }, [location, cropId, stageId, language, profileId])

  // Language changes localise the deterministic result; AI generation remains an explicit user action.
  const lastLang = useRef(language)
  useEffect(() => {
    if (lastLang.current === language) return
    lastLang.current = language
    const a = analysis.assessment
    if (!a) return
    const my = ++runId.current
    api.getAssessment(a.assessment_id, language).then((assessment) => {
      if (my !== runId.current) return
      setAnalysis((s) => ({ ...s, assessment, advisory: null, errors: { ...s.errors, advisory: null } }))
    }).catch((e) => setAnalysis((s) => ({ ...s, errors: { ...s.errors, assessment: e } })))
  }, [language])  // eslint-disable-line

  const saveProfileId = (id) => { setProfileId(id); if (id) LS.set('fs_profile', id); else LS.del('fs_profile') }
  const selectedCrop = useMemo(() => crops.find((c) => c.crop_id === cropId) || null, [crops, cropId])
  const requestAdvisory = useCallback(() => {
    if (analysis.assessment) return loadAdvisory(analysis.assessment.assessment_id, language, runId.current)
  }, [analysis.assessment, language, loadAdvisory])

  const value = {
    t, language, setLanguage, location, setLocation, cropId, setCropId, stageId, setStageId, crops, regions, modules, analysis, runAnalysis,
    advisoryLoading, requestAdvisory, reloadAdvisory: requestAdvisory,
    profileId, saveProfileId, sessionReady, bootError, boot, selectedCrop, health,
  }
  return <Ctx.Provider value={value}>{children}</Ctx.Provider>
}
