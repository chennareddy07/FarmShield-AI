import { Sparkles } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Chip, ErrorState, Notices, Panel, Spinner, StateMessage, fmtTime } from './ui'
import EvidenceList from './EvidenceList'
import ChatBox from './ChatBox'

function List({ title, items, empty }) {
  const { t } = useApp()
  return (
    <div className="mt-3"><h3 className="font-semibold mb-1">{title}</h3>
      {items?.length ? <ul className="list-disc ml-5 text-sm space-y-1">{items.map((x, i) => <li key={i}>{x}</li>)}</ul> : <p className="text-sm text-gray-600">{empty || t('adv.none_list')}</p>}
    </div>
  )
}

export default function AdvisoryPanel({ withChat = true }) {
  const { t, language, analysis, advisoryLoading, requestAdvisory, reloadAdvisory } = useApp()
  const a = analysis.advisory
  const aiOk = a?.generation_status === 'ai_generated'
  const agriculturalReferences = (analysis.assessment?.evidence || a?.evidence || []).filter((item) =>
    item.kind === 'agricultural_reference' &&
    item.crop_id === analysis.assessment?.crop_id &&
    item.excerpt &&
    ['source_verified', 'page_verified', 'pdf_verified'].includes(item.source_access_status),
  )
  return (
    <Panel title={t('adv.title')} icon={Sparkles} right={a && <Chip tone={aiOk ? 'green' : 'amber'}>{t(`adv.status.${a.generation_status}`)}</Chip>}>
      {!analysis.assessment && <StateMessage kind="info">{t('adv.none_yet')}</StateMessage>}
      {advisoryLoading && <Spinner />}
      <ErrorState error={analysis.errors.advisory} onRetry={reloadAdvisory} />
      {analysis.assessment && !a && !advisoryLoading && !analysis.errors.advisory && (
        <button type="button" className="btn-primary mt-3" onClick={requestAdvisory}>{t('adv.generate')}</button>
      )}
      {a && !advisoryLoading && (
        <div data-testid="advisory">
          <p className="text-base font-medium">{a.summary}</p>
          <div className="mt-3"><h3 className="font-semibold mb-1">{t('adv.explanation')}</h3><p className="text-sm whitespace-pre-line">{a.risk_explanation}</p></div>
          <List title={t('adv.immediate')} items={a.recommended_actions} empty={t('risk.no_actions')} />
          <List title={t('adv.preventive')} items={a.preventive_actions} />
          {a.when_to_act && <div className="mt-3"><h3 className="font-semibold mb-1">{t('adv.when')}</h3><p className="text-sm">{a.when_to_act}</p></div>}
          <div className="mt-3"><h3 className="font-semibold mb-1">{t('adv.uncertainty')}</h3><Notices items={a.uncertainties} /></div>
          {a.personalisation_note && <p className="muted mt-2">{t('adv.personalised')}: {a.personalisation_note}</p>}
          <div className="mt-3"><Notices items={a.notices} /></div>
          <details className="mt-3"><summary className="cursor-pointer font-semibold">{t('adv.evidence')} ({a.evidence?.length || 0})</summary><div className="mt-2"><EvidenceList items={a.evidence} /></div></details>
          <p className="muted mt-3">{t('adv.generated')}: {fmtTime(a.generated_at, language)} · {a.model_provider}</p>
          <p className="text-xs text-gray-600 mt-1">{a.disclaimer}</p>
        </div>
      )}
      {analysis.assessment && agriculturalReferences.length > 0 && (
        <section className="mt-5 border-t pt-4" aria-label={t('dash.guidance')}>
          <h3 className="font-semibold mb-1">{t('dash.guidance')}</h3>
          <p className="muted mb-3">{t('dash.guidance_note')}</p>
          <EvidenceList items={agriculturalReferences} />
        </section>
      )}
      {withChat && <div className="mt-5 pt-4 border-t"><ChatBox /></div>}
    </Panel>
  )
}
