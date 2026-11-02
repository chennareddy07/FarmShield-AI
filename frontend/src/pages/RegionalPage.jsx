import { useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { Map } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, RiskBadge, Spinner, StateMessage, fmt, fmtTime } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

const COLORS = { low: '#2e8b57', moderate: '#E9A23B', high: '#e8590c', critical: '#9b1c1c', insufficient_data: '#6b7280' }

export default function RegionalPage() {
  const { t, language, crops, selectedCrop, cropId, stageId } = useApp()
  const [crop, setCrop] = useState(cropId || ''); const [stage, setStage] = useState(stageId || ''); const [filter, setFilter] = useState('all')
  const r = useAsync(); const d = r.data
  const stages = crops.find((c) => c.crop_id === crop)?.supported_stages || []
  const rows = useMemo(() => (d?.districts || []).filter((x) => x.status === 'ok' && (filter === 'all' || x.overall_risk === filter)), [d, filter])
  const bad = (d?.districts || []).filter((x) => x.status !== 'ok')
  const riskUnassessed = rows.length > 0 && rows.every((x) => x.overall_risk === 'insufficient_data')
  return (
    <>
      <ModuleNote id="regional" />
      <Panel title={t('rg.title')} icon={Map}>
        <div className="flex flex-wrap items-end gap-3">
          <div><label className="label" htmlFor="rc">{t('rg.crop')}</label><select id="rc" className="input" value={crop} onChange={(e) => { setCrop(e.target.value); setStage('') }}><option value="">{t('sel.crop_ph')}</option>{crops.map((c) => <option key={c.crop_id} value={c.crop_id}>{c.name_i18n?.[language] || c.name}</option>)}</select></div>
          <div><label className="label" htmlFor="rs">{t('rg.stage')}</label><select id="rs" className="input" value={stage} onChange={(e) => setStage(e.target.value)} disabled={!crop}><option value="">{t('sel.stage_ph')}</option>{stages.map((s) => <option key={s.stage_id} value={s.stage_id}>{s.name[language] || s.name.en}</option>)}</select></div>
          <div><label className="label" htmlFor="rf">{t('rg.filter')}</label><select id="rf" className="input" value={filter} onChange={(e) => setFilter(e.target.value)}><option value="all">{t('rg.all')}</option>{['low', 'moderate', 'high', 'critical'].map((x) => <option key={x} value={x}>{t(`risk.${x}`)}</option>)}</select></div>
          <button className="btn-primary" disabled={!crop || r.loading} onClick={() => r.run(() => api.regional({ crop_id: crop, growth_stage_id: stage || undefined }))}>{t('rg.load')}</button>
        </div>
        <p className="muted mt-2">{t('rg.res')}</p>
        {r.loading && <Spinner />}<ErrorState error={r.error} />
        {d && (
          <div className="mt-4 space-y-4">
            <p className="muted">{d.provider}: {d.resolution_note}</p>
            {riskUnassessed && <StateMessage kind="info">{t('rg.no_risk')}</StateMessage>}
            <div className="flex flex-wrap gap-3 text-xs" aria-label={t('rg.legend')}>
              {Object.entries(COLORS).map(([risk, color]) => (
                <span key={risk} className="inline-flex items-center gap-1">
                  <span aria-hidden="true" className="inline-block h-3 w-3 rounded-full" style={{ backgroundColor: color }} />
                  {t(`risk.${risk}`)}
                </span>
              ))}
            </div>
            <div role="img" aria-label={t('rg.title')}>
              <MapContainer center={[15.9, 79.7]} zoom={6} scrollWheelZoom={false}>
                <TileLayer attribution="&copy; OpenStreetMap contributors" url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
                {rows.map((x) => (
                  <CircleMarker key={x.district} center={[x.latitude, x.longitude]} radius={11} pathOptions={{ color: COLORS[x.overall_risk], fillColor: COLORS[x.overall_risk], fillOpacity: 0.75 }}>
                    <Popup><strong>{x.district}</strong><br />{t(`risk.${x.overall_risk}`)}<br />{t('rg.rain_max')}: {fmt(x.forecast_rain_max_mm)}<br />
                      {t('rg.weather_status')}: {x.data_status}<br />{t('rg.retrieved')}: {fmtTime(x.retrieved_at, language)}</Popup>
                  </CircleMarker>))}
              </MapContainer>
            </div>
            <p className="text-sm">{t('rg.warnings_status')}: {d.warnings_status}</p>
            <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-gray-600"><th>{t('rg.table')}</th><th>{t('risk.overall')}</th><th>{t('rg.rain_max')}</th><th>{t('rg.weather_status')}</th><th>{t('rg.retrieved')}</th><th>{t('risk.coverage')}</th></tr></thead>
              <tbody>{rows.map((x) => <tr key={x.district} className="border-t"><td className="py-1">{x.district}</td><td><RiskBadge risk={x.overall_risk} /></td><td>{fmt(x.forecast_rain_max_mm)}</td><td>{x.data_status}</td><td>{fmtTime(x.retrieved_at, language)}</td><td>{x.coverage}/8</td></tr>)}</tbody></table></div>
            {bad.length > 0 && <StateMessage kind="unavailable"><strong>{t('rg.unavailable')}:</strong> {bad.map((x) => x.district).join(', ')}</StateMessage>}
          </div>)}
      </Panel>
    </>
  )
}
