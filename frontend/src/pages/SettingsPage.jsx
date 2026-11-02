import { useEffect, useState } from 'react'
import { Settings } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { LANGUAGES } from '../translations'
import { ErrorState, Panel, StateMessage } from '../components/ui'

export default function SettingsPage() {
  const { t, language, setLanguage, location, cropId, stageId, profileId, saveProfileId } = useApp()
  const [nick, setNick] = useState(''); const [area, setArea] = useState(''); const [unit, setUnit] = useState('acre')
  const [msg, setMsg] = useState(null); const [error, setError] = useState(null)
  useEffect(() => {
    if (!profileId) return
    api.profileGet(profileId).then((p) => { setNick(p.nickname || ''); setArea(p.farm_area ?? ''); setUnit(p.farm_area_unit || 'acre') }).catch((e) => { if (e.status === 404) saveProfileId(null) })
  }, [profileId])  // eslint-disable-line
  const body = () => ({ nickname: nick || null, farm_area: area === '' ? null : Number(area), farm_area_unit: area === '' ? null : unit, language,
    preferred_location: location ? { name: location.name, latitude: location.latitude, longitude: location.longitude, district: location.district } : null,
    preferred_crop: cropId || null, preferred_growth_stage: cropId && stageId ? stageId : null })
  const save = async () => {
    setError(null); setMsg(null)
    try { const p = profileId ? await api.profileUpdate(profileId, body()) : await api.profileCreate(body()); saveProfileId(p.profile_id); setMsg(t('set.saved')) } catch (e) { setError(e) }
  }
  const del = async () => { setError(null); try { await api.profileDelete(profileId); saveProfileId(null); setNick(''); setArea(''); setMsg(t('set.deleted')) } catch (e) { setError(e) } }
  return (
    <>
      <Panel title={t('set.title')} icon={Settings}>
        <label className="label" htmlFor="slang">{t('set.language')}</label>
        <select id="slang" className="input !w-auto" value={language} onChange={(e) => setLanguage(e.target.value)}>{LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select>
        <p className="muted mt-2">{t('set.te_review')}</p>
      </Panel>
      <Panel title={t('set.profile')} icon={Settings}>
        <p className="muted mb-3">{t('set.profile_note')}</p>
        {!profileId && <p className="muted mb-3">{t('set.none')}</p>}
        <div className="grid md:grid-cols-3 gap-3">
          <div><label className="label" htmlFor="nick">{t('set.nickname')}</label><input id="nick" className="input" maxLength={80} value={nick} onChange={(e) => setNick(e.target.value)} /></div>
          <div><label className="label" htmlFor="area">{t('set.area')}</label><input id="area" type="number" min="0" step="0.1" className="input" value={area} onChange={(e) => setArea(e.target.value)} /></div>
          <div><label className="label" htmlFor="unit">{t('set.unit')}</label><select id="unit" className="input" value={unit} onChange={(e) => setUnit(e.target.value)}><option value="acre">{t('set.acre')}</option><option value="hectare">{t('set.hectare')}</option></select></div>
        </div>
        <p className="muted mt-2">{t('set.use_selection')}: {location ? location.name : '—'} / {cropId || '—'} / {stageId || '—'}</p>
        <div className="flex gap-2 mt-3"><button className="btn-primary" onClick={save}>{t('set.save')}</button>{profileId && <button className="btn-ghost" onClick={del}>{t('set.delete')}</button>}</div>
        {msg && <div className="mt-3"><StateMessage kind="info">{msg}</StateMessage></div>}
        <ErrorState error={error} />
      </Panel>
    </>
  )
}
