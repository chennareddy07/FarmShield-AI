import { useCallback, useEffect, useState } from 'react'
import { Bell } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { Chip, ErrorState, Panel, RiskBadge, Spinner, StateMessage, fmtTime } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

export default function NotificationsPage() {
  const { t, language, sessionReady, location, cropId, stageId } = useApp()
  const list = useAsync()
  const [levels, setLevels] = useState(['high', 'critical']); const [consent, setConsent] = useState(false)
  const [qs, setQs] = useState(''); const [qe, setQe] = useState('')
  const [msg, setMsg] = useState(null); const [error, setError] = useState(null); const [subs, setSubs] = useState([])
  const load = useCallback(() => {
    list.run(() => api.notifications())
    api.notificationPrefs().then((r) => setSubs(r.subscriptions)).catch(() => {})
  }, []) // eslint-disable-line
  useEffect(() => { if (sessionReady) load() }, [sessionReady, load])
  const toggle = (l) => setLevels((s) => (s.includes(l) ? s.filter((x) => x !== l) : [...s, l]))
  const save = async (enabled) => {
    setError(null); setMsg(null)
    try {
      await api.saveNotificationPrefs({ location: { location_id: `${location.latitude.toFixed(2)},${location.longitude.toFixed(2)}`, latitude: location.latitude, longitude: location.longitude, district: location.district, name: location.name },
        crop_id: cropId, growth_stage_id: stageId || null, enabled, consent: enabled ? consent : false, channels: ['in_app'], risk_levels: levels, quiet_hours: qs && qe ? { start: qs, end: qe, utc_offset_minutes: -new Date().getTimezoneOffset() } : null })
      setMsg(t('nt.saved')); load()
    } catch (e) { setError(e) }
  }
  const refresh = async () => { setError(null); try { const r = await api.refreshNotifications(); setMsg(`${r.created} ${t('nt.created')}`); load() } catch (e) { setError(e) } }
  const read = async (id) => { try { await api.markRead(id); load() } catch (e) { setError(e) } }
  const items = list.data?.notifications || []
  return (
    <>
      <ModuleNote id="notifications" />
      <Panel title={t('nt.list')} icon={Bell} right={<button className="btn-ghost" onClick={refresh}>{t('nt.refresh')}</button>}>
        {list.loading && <Spinner />}<ErrorState error={list.error} onRetry={load} />
        {list.data && items.length === 0 && <p className="muted">{t('nt.none')}</p>}
        <ul className="space-y-2">{items.map((n) => (
          <li key={n.notification_id} className={`border rounded-xl p-3 text-sm ${n.read ? 'bg-white' : 'bg-green-50'}`}>
            <div className="flex flex-wrap items-center gap-2"><RiskBadge risk={n.severity} /><strong>{n.title}</strong><Chip tone={n.status === 'active' ? 'green' : 'gray'}>{t(n.status === 'active' ? 'nt.active' : 'nt.expired')}</Chip></div>
            <p className="mt-1">{n.body}</p><p className="muted">{n.source} · {fmtTime(n.created_at, language)}</p>
            {!n.read && <button className="btn-ghost !min-h-[36px] mt-1" onClick={() => read(n.notification_id)}>{t('nt.mark_read')}</button>}
          </li>))}</ul>
      </Panel>
      <Panel title={t('nt.prefs')} icon={Bell}>
        {(!location || !cropId) ? <StateMessage kind="info">{t('nt.need_selection')}</StateMessage> : (
          <div className="space-y-3">
            <p className="text-sm">{location.name} · {cropId}{stageId ? ` · ${stageId}` : ''}</p>
            <fieldset><legend className="label">{t('nt.levels')}</legend>
              {['moderate', 'high', 'critical'].map((l) => <label key={l} className="inline-flex items-center gap-2 mr-4 text-sm"><input type="checkbox" className="!min-h-0" checked={levels.includes(l)} onChange={() => toggle(l)} />{t(`risk.${l}`)}</label>)}</fieldset>
            <div className="flex flex-wrap gap-3"><div><label className="label" htmlFor="qs">{t('nt.quiet')}</label><input id="qs" type="time" className="input" value={qs} onChange={(e) => setQs(e.target.value)} /></div><div><label className="label" htmlFor="qe">&nbsp;</label><input id="qe" type="time" className="input" value={qe} onChange={(e) => setQe(e.target.value)} /></div></div>
            <label className="flex items-start gap-2 text-sm"><input type="checkbox" className="mt-1 !min-h-0" checked={consent} onChange={(e) => setConsent(e.target.checked)} />{t('nt.consent')}</label>
            <p className="muted">{t('nt.channels_note')}</p>
            <div className="flex gap-2"><button className="btn-primary" onClick={() => save(true)} disabled={!consent || levels.length === 0}>{t('nt.save')}</button>{subs.some((s) => s.enabled) && <button className="btn-ghost" onClick={() => save(false)}>{t('nt.disable')}</button>}</div>
            {msg && <StateMessage kind="info">{msg}</StateMessage>}<ErrorState error={error} />
          </div>)}
      </Panel>
    </>
  )
}
