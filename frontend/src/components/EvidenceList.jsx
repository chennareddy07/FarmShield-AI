import { ExternalLink } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Chip, fmt } from './ui'

const TONE = {
  verified: 'green', needs_review: 'amber', outdated: 'red', official: 'blue',
  source_verified: 'blue', source_unverified: 'red', expert_review_required: 'amber',
  expert_approved: 'green', conflicting_evidence: 'red', insufficient_evidence: 'gray',
}

export default function EvidenceList({ items }) {
  const { t } = useApp()
  if (!items || items.length === 0) return <p className="muted">{t('ev.none')}</p>
  return (
    <ol className="space-y-3">
      {items.map((e) => {
        const status = e.evidence_status || e.verification_status
        const needsReview = e.evidence_status ? e.evidence_status !== 'expert_approved' : e.verification_status === 'needs_review'
        const stage = e.crop_stage || e.growth_stage_id?.replace(/_/g, ' ') || t('ev.general_stage')
        return (
        <li key={e.evidence_id} className="rounded-xl border p-3" data-testid="evidence-item">
          <div className="flex flex-wrap items-center gap-2">
            <strong className="text-sm">{e.title}</strong>
            <Chip tone="blue">{t(`ev.kind.${e.kind}`)}</Chip>
            {status && <Chip tone={TONE[status] || 'gray'}>{t(`ev.status.${status}`)}</Chip>}
          </div>
          <div className="muted mt-1">{t('ev.publisher')}: {fmt(e.publisher)} · {t('ev.date')}: {fmt(e.publication_date)} · <code className="text-xs">{e.evidence_id}</code></div>
          {e.kind === 'agricultural_reference' && <p className="text-xs mt-1"><strong>{t('ev.crop_stage')}:</strong> {stage}</p>}
          {(e.state || e.districts?.length || e.seasons?.length) && <div className="muted mt-1">{t('ev.scope')}: {[e.state, e.districts?.join(', '), e.seasons?.join(', ')].filter(Boolean).join(' · ')}</div>}
          {e.excerpt && <p className="text-sm mt-1 text-gray-800">{e.excerpt.length > 320 ? e.excerpt.slice(0, 320) + '…' : e.excerpt}</p>}
          {e.source_section && <p className="text-xs mt-1"><strong>{t('ev.page_section')}:</strong> {e.source_section}</p>}
          {e.source_access_status && <p className="text-xs mt-1"><strong>{t('ev.source_access')}:</strong> {e.source_access_status}</p>}
          {e.source_time_window && <p className="text-xs mt-1"><strong>{t('ev.source_window')}:</strong> {e.source_time_window}</p>}
          {e.weather_input_time_window && <p className="text-xs mt-1"><strong>{t('ev.input_window')}:</strong> {e.weather_input_time_window} {e.measurement_window_status && e.measurement_window_status !== 'not_assessed' && `(${t(`ev.window.${e.measurement_window_status}`)})`}</p>}
          {e.limitations && <p className="text-xs text-amber-900 mt-1"><strong>{t('ev.limitations')}:</strong> {e.limitations}</p>}
          {needsReview && <p className="text-xs text-amber-800 mt-1">⚠ {t('ev.unreviewed_note')}</p>}
          {e.source_url && <a className="text-sm text-brand-blue underline inline-flex items-center gap-1 mt-1" href={e.source_url} target="_blank" rel="noreferrer">{t('ev.open')}<ExternalLink size={12} aria-hidden="true" /></a>}
        </li>
        )
      })}
    </ol>
  )
}
