import { useEffect } from 'react'
import { Activity } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { Chip, ErrorState, Panel, Spinner, fmtTime } from '../components/ui'

const TONE = { available: 'green', configured: 'green', unknown: 'gray', unavailable: 'red', not_configured: 'amber', implemented: 'green', planned: 'gray', needs_config: 'amber', partial: 'amber', implemented_unverified: 'amber', implemented_ai_not_configured: 'amber' }

export default function DataStatusPage() {
  const { t, language, modules } = useApp()
  const h = useAsync(); const m = useAsync()
  const load = () => { h.run(() => api.health()); m.run(() => api.monitoring()) }
  useEffect(load, [])  // eslint-disable-line
  return (
    <>
      <Panel title={t('ds.title')} icon={Activity} right={<button className="btn-ghost" onClick={load}>{t('ds.refresh')}</button>}>
        {(h.loading || m.loading) && <Spinner />}<ErrorState error={h.error || m.error} onRetry={load} />
        {h.data && (<><h3 className="font-semibold mb-2">{t('ds.services')}</h3>
          <ul className="grid sm:grid-cols-2 gap-2 text-sm">{Object.entries(h.data.services).map(([k, v]) => <li key={k} className="flex items-center justify-between border rounded-xl px-3 py-2"><span>{k.replaceAll('_', ' ')}</span><Chip tone={TONE[v] || 'gray'}>{v.replaceAll('_', ' ')}</Chip></li>)}</ul></>)}
        {m.data && (<><h3 className="font-semibold mt-4 mb-2">{t('ds.providers')}</h3>
          {Object.keys(m.data.providers).length === 0 ? <p className="muted">{t('state.empty')}</p> : (
            <div className="overflow-x-auto"><table className="w-full text-sm"><thead><tr className="text-left text-gray-600"><th>{t('ds.providers')}</th><th>{t('ds.success')}</th><th>{t('ds.failure')}</th><th>{t('ds.counts')}</th></tr></thead>
              <tbody>{Object.entries(m.data.providers).map(([k, v]) => <tr key={k} className="border-t"><td className="py-1">{k}</td><td>{v.last_success ? fmtTime(v.last_success, language) : t('ds.never')}</td><td>{v.last_failure ? `${fmtTime(v.last_failure, language)} (${v.last_error})` : t('ds.never')}</td><td>{v.successes} / {v.failures}</td></tr>)}</tbody></table></div>)}
          <p className="muted mt-3">{t('ds.policy')}: {JSON.stringify(m.data.freshness_policy)}</p></>)}
      </Panel>
      <Panel title={t('ds.modules')} icon={Activity}>
        <ul className="space-y-2 text-sm">{modules.map((x) => <li key={x.id} className="border rounded-xl px-3 py-2"><div className="flex flex-wrap items-center gap-2"><strong>{t(`nav.${x.id}`)}</strong><span className="muted">{x.features.join(', ')} · L{x.level}</span><Chip tone={TONE[x.status] || 'gray'}>{x.status.replaceAll('_', ' ')}</Chip></div>{x.note && <div className="muted mt-1">{x.note}</div>}</li>)}</ul>
      </Panel>
    </>
  )
}
