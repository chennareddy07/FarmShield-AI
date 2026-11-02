import { useState } from 'react'
import { LayoutDashboard } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, RiskBadge, Spinner } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

export default function AdminPage() {
  const { t, crops, language } = useApp()
  const [token, setToken] = useState(''); const [crop, setCrop] = useState('')
  const r = useAsync(); const d = r.data
  return (
    <>
      <ModuleNote id="admin" />
      <Panel title={t('adm.title')} icon={LayoutDashboard}>
        <p className="muted mb-3">{t('adm.note')}</p>
        <div className="flex flex-wrap items-end gap-3">
          <div><label className="label" htmlFor="at">{t('adm.token')}</label><input id="at" type="password" autoComplete="off" className="input" value={token} onChange={(e) => setToken(e.target.value)} /></div>
          <div><label className="label" htmlFor="ac">{t('rg.crop')}</label><select id="ac" className="input" value={crop} onChange={(e) => setCrop(e.target.value)}><option value="">{t('sel.crop_ph')}</option>{crops.map((c) => <option key={c.crop_id} value={c.crop_id}>{c.name_i18n?.[language] || c.name}</option>)}</select></div>
          <button className="btn-primary" disabled={!token || !crop || r.loading} onClick={() => r.run(() => api.adminSummary({ crop_id: crop }, token))}>{t('adm.load')}</button>
        </div>
        {r.loading && <Spinner />}<ErrorState error={r.error} />
        {d && (
          <div className="mt-4 space-y-3 text-sm">
            <p>{d.districts_with_data}/{d.districts_total} · {t('rg.unavailable')}: {d.districts_unavailable}</p>
            <div><h3 className="font-semibold mb-1">{t('adm.dist')}</h3><div className="flex flex-wrap gap-2">{Object.entries(d.risk_distribution).map(([k, v]) => <span key={k} className="inline-flex items-center gap-1"><RiskBadge risk={k} /> × {v}</span>)}</div></div>
            <div><h3 className="font-semibold mb-1">{t('adm.fresh')}</h3><p>{JSON.stringify(d.data_freshness)}</p></div>
            <div><h3 className="font-semibold mb-1">{t('adm.triggered')}</h3><p>{d.districts_with_triggered_rules.join(', ') || t('common.none')}</p></div>
            <p className="muted">{d.resolution_note}</p>
          </div>)}
      </Panel>
    </>
  )
}
