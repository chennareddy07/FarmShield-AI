import { useEffect, useState } from 'react'
import { Camera } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { Chip, ErrorState, Notices, Panel, Spinner, StateMessage } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

const MAX = 10 * 1024 * 1024
const OK = ['image/jpeg', 'image/png', 'image/webp']

export default function CropHealthPage() {
  const { t, language, cropId, stageId } = useApp()
  const [file, setFile] = useState(null); const [preview, setPreview] = useState(null); const [consent, setConsent] = useState(false)
  const [symptoms, setSymptoms] = useState(''); const [localErr, setLocalErr] = useState(null)
  const r = useAsync()
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview])
  const choose = (e) => {
    const f = e.target.files?.[0]; setLocalErr(null); r.reset()
    if (!f) return
    if (!OK.includes(f.type)) { setLocalErr(t('ch.bad_type')); setFile(null); setPreview(null); return }
    if (f.size > MAX) { setLocalErr(t('ch.too_big')); setFile(null); setPreview(null); return }
    setFile(f); setPreview(URL.createObjectURL(f))
  }
  const submit = () => {
    const form = new FormData()
    form.append('image', file); form.append('consent', String(consent)); form.append('language', language)
    if (cropId) form.append('crop_id', cropId); if (cropId && stageId) form.append('growth_stage_id', stageId)
    if (symptoms) form.append('symptoms_description', symptoms)
    r.run(() => api.analyzeImage(form))
  }
  const d = r.data
  return (
    <>
      <ModuleNote id="crop_health" />
      <Panel title={t('ch.title')} icon={Camera}>
        <StateMessage kind="info">{t('ch.preliminary')}</StateMessage>
        <div className="mt-3 grid md:grid-cols-2 gap-4">
          <div>
            <label className="label" htmlFor="img">{t('ch.upload')}</label>
            <input id="img" className="input" type="file" accept="image/jpeg,image/png,image/webp" capture="environment" onChange={choose} />
            <p className="muted mt-1">{t('ch.formats')}</p>
            {localErr && <div className="mt-2"><StateMessage kind="error">{localErr}</StateMessage></div>}
            <label className="label mt-3" htmlFor="sym">{t('ch.symptoms')}</label>
            <textarea id="sym" className="input" rows={2} maxLength={500} value={symptoms} onChange={(e) => setSymptoms(e.target.value)} />
            <label className="flex items-start gap-2 mt-3 text-sm"><input type="checkbox" className="mt-1 !min-h-0" checked={consent} onChange={(e) => setConsent(e.target.checked)} />{t('ch.consent')}</label>
            <button className="btn-primary mt-3" disabled={!file || !consent || r.loading} onClick={submit}>{t('ch.analyze')}</button>
          </div>
          <div>{preview && <figure><img src={preview} alt={t('ch.preview')} className="rounded-xl max-h-64 border" /><figcaption className="muted">{t('ch.preview')}</figcaption></figure>}</div>
        </div>
        {r.loading && <Spinner />}<ErrorState error={r.error} />
        {d && (
          <div className="mt-4 space-y-3" data-testid="health-result">
            {d.status === 'analysis_unavailable' ? <StateMessage kind="unavailable">{d.message}</StateMessage> : (
              <>
                <h3 className="font-semibold">{t('ch.result')} <Chip tone="amber">{t('ch.preliminary')}</Chip></h3>
                {d.uncertain && <StateMessage kind="partial">{t('ch.uncertain')}</StateMessage>}
                {d.possible_issues.length === 0 ? <p className="text-sm">{t('ch.none')}</p> : (
                  <ul className="space-y-2">{d.possible_issues.map((i, k) => <li key={k} className="border rounded-xl p-3 text-sm"><strong>{i.category}</strong> <Chip tone={i.confidence === 'high' ? 'green' : i.confidence === 'medium' ? 'amber' : 'gray'}>{t('ch.confidence')}: {i.confidence}</Chip><p className="mt-1">{i.explanation}</p></li>)}</ul>)}
              </>
            )}
            <div><h3 className="font-semibold mb-1">{t('ch.limits')}</h3><Notices items={d.limitations} /></div>
            <div><h3 className="font-semibold mb-1">{t('ch.next')}</h3><ul className="list-disc ml-5 text-sm">{d.recommended_next_steps.map((s, i) => <li key={i}>{s}</li>)}</ul></div>
          </div>
        )}
      </Panel>
    </>
  )
}
