import { useState } from 'react'
import { LocateFixed, MapPin, Search } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useGeolocation } from '../hooks/useGeolocation'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, Spinner, StateMessage } from './ui'

export default function SelectionPanel({ compact = false }) {
  const { t, language, regions, crops, selectedCrop, location, setLocation, cropId, setCropId, stageId, setStageId, runAnalysis, analysis, health } = useApp()
  const [q, setQ] = useState('')
  const search = useAsync()
  const geo = useGeolocation()
  const [emptyMsg, setEmptyMsg] = useState(false)

  const doSearch = async (e) => {
    e?.preventDefault()
    setEmptyMsg(false)
    const r = await search.run(() => api.searchLocations(q))
    if (r && r.results.length === 0) setEmptyMsg(true)
  }
  const pick = (r) => { setLocation({ name: r.name, district: r.district || null, latitude: r.latitude, longitude: r.longitude, source: 'search', state: r.state }); search.reset() }
  const useDeviceLocation = async () => {
    const pos = await geo.locate()
    if (!pos) return
    const loc = { name: `${pos.latitude.toFixed(3)}, ${pos.longitude.toFixed(3)}`, district: null, latitude: pos.latitude, longitude: pos.longitude, source: 'geolocation' }
    setLocation(loc)
    if (health?.services?.official_warnings !== 'not_configured') {          // only needed when official warnings are connected
      api.nearestDistrict(pos.latitude, pos.longitude).then((r) => r.result && setLocation((l) => (l && l.latitude === pos.latitude ? { ...l, district: r.result.district, districtApprox: true } : l))).catch(() => {})
    }
  }
  const pickDistrict = async (name) => {
    if (!name) return
    setEmptyMsg(false)
    const r = await search.run(() => api.searchLocations(name))
    const hit = r?.results?.[0]
    if (hit) { setLocation({ name, district: name, latitude: hit.latitude, longitude: hit.longitude, source: 'search', state: hit.state }); search.reset() } else setEmptyMsg(true)
  }
  const stageName = (s) => s.name[language] || s.name.en

  return (
    <Panel title={t('sel.title')} icon={MapPin}>
      <div className="grid gap-4 md:grid-cols-2">
        <div>
          <form onSubmit={doSearch} role="search" className="space-y-2">
            <label className="label" htmlFor="loc-q">{t('sel.search')}</label>
            <div className="flex gap-2">
              <input id="loc-q" className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t('sel.search_ph')} maxLength={100} />
              <button className="btn-primary" type="submit" disabled={search.loading}><Search size={18} aria-hidden="true" /><span className="sr-only md:not-sr-only">{t('sel.search_btn')}</span></button>
            </div>
          </form>
          {search.loading && <Spinner />}
          <ErrorState error={search.error} onRetry={doSearch} />
          {search.data?.results?.length > 0 && (
            <ul className="mt-2 border rounded-xl divide-y bg-white" aria-label={t('sel.search')}>
              {search.data.results.map((r) => (
                <li key={r.location_id}><button className="w-full text-left px-3 py-2 hover:bg-green-50" onClick={() => pick(r)}>
                  <span className="font-medium">{r.name}</span> <span className="muted">{[r.district, r.state].filter(Boolean).join(', ')} · {r.latitude.toFixed(2)}, {r.longitude.toFixed(2)}</span>
                </button></li>
              ))}
            </ul>
          )}
          {emptyMsg && <div className="mt-2"><StateMessage kind="info">{t('sel.no_results')}</StateMessage></div>}
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <button className="btn-ghost" onClick={useDeviceLocation} disabled={geo.loading}><LocateFixed size={18} aria-hidden="true" />{geo.loading ? t('sel.locating') : t('sel.use_current')}</button>
            <label className="sr-only" htmlFor="district">{t('sel.districts')}</label>
            <select id="district" className="input !w-auto" defaultValue="" onChange={(e) => pickDistrict(e.target.value)} aria-label={t('sel.districts')}>
              <option value="">{t('sel.district_ph')}</option>
              {regions?.districts?.map((d) => <option key={d} value={d}>{d}</option>)}
            </select>
          </div>
          {geo.error && <div className="mt-2"><StateMessage kind="info">{geo.error === 'denied' ? t('sel.geo_denied') : geo.error === 'unsupported' ? t('sel.geo_unsupported') : t('sel.geo_denied')}</StateMessage></div>}
          <p className="muted mt-2">{t('sel.geo_why')}</p>
        </div>

        <div className="space-y-3">
          <div>
            <label className="label" htmlFor="crop">{t('sel.crop')}</label>
            <select id="crop" className="input" value={cropId} onChange={(e) => { setCropId(e.target.value); setStageId('') }}>
              <option value="">{t('sel.crop_ph')}</option>
              {crops.map((c) => <option key={c.crop_id} value={c.crop_id}>{c.name_i18n?.[language] || c.name}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="stage">{t('sel.stage')}</label>
            <select id="stage" className="input" value={stageId} onChange={(e) => setStageId(e.target.value)} disabled={!selectedCrop}>
              <option value="">{t('sel.stage_ph')}</option>
              {selectedCrop?.supported_stages.map((s) => <option key={s.stage_id} value={s.stage_id}>{stageName(s)}</option>)}
            </select>
            <p className="muted mt-1">{t('sel.stage_optional_note')}</p>
            {selectedCrop?.review_status === 'needs_review' && <p className="muted mt-1">⚠ {t('sel.review_note')}</p>}
          </div>
          {location && (
            <div className="rounded-xl bg-green-50 border border-green-200 p-3 text-sm" data-testid="selected-location">
              <div className="font-medium">{t('sel.selected')}: {location.name}{location.district && location.district !== location.name ? `, ${location.district}` : ''}{location.districtApprox ? ` (${t('sel.approx_district')})` : ''}</div>
              <div className="muted">{t('sel.coords')}: {location.latitude.toFixed(3)}, {location.longitude.toFixed(3)} · {t(`sel.source.${location.source}`)}</div>
              <div className="muted">{t('sel.resolution')}</div>
            </div>
          )}
          <button className="btn-primary w-full" onClick={runAnalysis} disabled={!location || analysis.status === 'loading'} aria-describedby="analyze-hint">
            {analysis.status === 'loading' ? t('state.loading') : t('sel.analyze')}
          </button>
          {!location && <p id="analyze-hint" className="muted">{t('sel.need_location')}</p>}
        </div>
      </div>
    </Panel>
  )
}
