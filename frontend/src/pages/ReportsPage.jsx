import { useState } from 'react'
import { FileText } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, StateMessage } from '../components/ui'

export default function ReportsPage() {
  const { t, language, analysis } = useApp()
  const [lang, setLang] = useState(language); const [ai, setAi] = useState(false)
  const r = useAsync()
  const a = analysis.assessment
  const download = () => r.run(async () => {
    const res = await api.report({ assessment_id: a.assessment_id, language: lang, include_advisory: ai })
    const url = URL.createObjectURL(res.data)
    const link = document.createElement('a'); link.href = url; link.download = `farmshield-report-${a.assessment_id}-${lang}.html`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
    return true
  })
  return (
    <Panel title={t('rep.title')} icon={FileText}>
      {!a ? <StateMessage kind="info">{t('rep.need_assessment')}</StateMessage> : (
        <div className="space-y-3">
          <p className="text-sm"><strong>{t('rep.preview')}:</strong> {t('rep.preview_list')}</p>
          <div className="flex flex-wrap items-end gap-3">
            <div><label className="label" htmlFor="rl">{t('rep.language')}</label><select id="rl" className="input" value={lang} onChange={(e) => setLang(e.target.value)}><option value="en">English</option><option value="te">తెలుగు</option></select></div>
            <label className="flex items-center gap-2 text-sm"><input type="checkbox" className="!min-h-0" checked={ai} onChange={(e) => setAi(e.target.checked)} />{t('rep.include_ai')}</label>
            <button className="btn-primary" onClick={download} disabled={r.loading}>{t('rep.generate')}</button>
          </div>
          {lang === 'te' && <p className="muted">⚠ {t('rep.te_note')}</p>}
          <p className="muted">{t('rep.note')}</p>
          <ErrorState error={r.error} />
        </div>
      )}
    </Panel>
  )
}
