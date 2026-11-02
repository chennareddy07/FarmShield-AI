import { Database } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Chip, Panel, fmtTime } from './ui'

const TONE = { fresh: 'green', stale: 'amber', partial: 'amber', unavailable: 'red' }

export function QualityRow({ label, q }) {
  const { t, language } = useApp()
  if (!q) return null
  return (
    <div className="flex flex-wrap items-center gap-2 py-1 border-b last:border-0 text-sm">
      <span className="font-medium min-w-[9rem]">{label}</span>
      <Chip tone={TONE[q.status] || 'gray'}>{t(`q.${q.status}`)}</Chip>
      <span className="muted">{q.provider}{q.retrieved_at ? ` · ${t('q.retrieved')}: ${fmtTime(q.retrieved_at, language)}` : ''}{q.age_minutes != null ? ` · ${t('q.age')}: ${Math.round(q.age_minutes)} ${t('q.min')}` : ''}</span>
      {q.missing_variables?.length > 0 && <span className="muted w-full">{t('q.missing')}: {q.missing_variables.join(', ')}</span>}
    </div>
  )
}

export default function SourcesPanel({ assessment, weather }) {
  const { t } = useApp()
  const dq = assessment?.data_quality
  return (
    <Panel title={t('q.title')} icon={Database}>
      {!dq && !weather && <p className="muted">{t('state.analyze_first')}</p>}
      {dq && <><QualityRow label={t('q.weather')} q={dq.weather} /><QualityRow label={t('q.warnings')} q={dq.warnings} /></>}
      {!dq && weather && <QualityRow label={t('q.weather')} q={weather.data_quality} />}
      <p className="muted mt-2">{t('app.attribution')}</p>
    </Panel>
  )
}
