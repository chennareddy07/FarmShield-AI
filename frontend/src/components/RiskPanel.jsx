import { useState } from 'react'
import { ChevronDown, ChevronUp, ShieldCheck } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Chip, Notices, Panel, RiskBadge, StateMessage, fmt, fmtDate } from './ui'

function RuleDetail({ r }) {
  const { t } = useApp()
  const [open, setOpen] = useState(false)
  return (
    <li className="rounded-xl border p-3" data-testid="triggered-rule">
      <div className="flex flex-wrap items-center gap-2 justify-between">
        <div className="flex flex-wrap items-center gap-2"><RiskBadge risk={r.severity} /><code className="text-sm">{r.rule_id}</code></div>
        <button className="btn-ghost !min-h-[36px] text-sm" onClick={() => setOpen(!open)} aria-expanded={open}>{open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}{open ? t('risk.hide') : t('risk.details')}</button>
      </div>
      <p className="text-sm mt-2">{r.reason}</p>
      {open && (
        <dl className="mt-2 grid grid-cols-[auto,1fr] gap-x-3 gap-y-1 text-sm">
          <dt className="muted">{t('risk.variable')}</dt><dd>{r.weather_variable}</dd>
          <dt className="muted">{t('risk.threshold')}</dt><dd>{r.operator} {r.threshold}{r.operator === 'between' ? '' : ''} {r.threshold_unit}</dd>
          <dt className="muted">{t('risk.actual')}</dt><dd>{fmt(r.actual_value)} {r.threshold_unit}</dd>
          <dt className="muted">{t('risk.period_examined')}</dt><dd>{r.period}</dd>
          <dt className="muted">{t('risk.source')}</dt><dd>{r.source_reference?.title} — <a className="text-brand-blue underline" href={r.source_reference?.url} target="_blank" rel="noreferrer">{r.source_reference?.publisher}</a></dd>
          <dt className="muted">{t('common.status')}</dt><dd><Chip tone={r.review_status === 'verified' ? 'green' : 'amber'}>{r.review_status === 'verified' ? t('risk.verified') : t('risk.review')}</Chip></dd>
        </dl>
      )}
    </li>
  )
}

export function TriggerTimeline({ events }) {
  const { t, language } = useApp()
  if (!events?.length) return <p className="muted">{t('risk.no_timeline')}</p>
  return (
    <ol className="space-y-2" aria-label={t('risk.timeline')}>
      {events.map((e, i) => (
        <li key={i} className="flex flex-wrap items-center gap-2 text-sm">
          <RiskBadge risk={e.severity} /><span>{fmtDate(e.start, language)}{e.end !== e.start ? ` → ${fmtDate(e.end, language)}` : ''}</span><span className="muted">{e.label}: {fmt(e.actual_value)} {e.unit}</span>
        </li>
      ))}
    </ol>
  )
}

export default function RiskPanel({ assessment, needSelection }) {
  const { t } = useApp()
  const a = assessment
  if (!a) return <Panel title={t('risk.title')} icon={ShieldCheck}><StateMessage kind="info">{needSelection ? t('risk.need_selection') : t('state.analyze_first')}</StateMessage></Panel>
  return (
    <Panel title={t('risk.title')} icon={ShieldCheck}>
      <div className="flex flex-wrap items-center gap-3">
        <div><div className="muted">{t('risk.overall')}</div><RiskBadge risk={a.overall_risk} label={a.overall_risk_label} large /></div>
        <div className="text-sm"><div>{t('risk.crop_stage')}: <strong>{a.crop_name}{a.growth_stage_name ? ` — ${a.growth_stage_name}` : ''}</strong></div>
          <div className="muted">{t('risk.period')}: {a.forecast_window.start || '—'} → {a.forecast_window.end || '—'}</div>
          <div className="muted">{t('risk.coverage')}: {a.coverage.assessed_count}/{a.coverage.required_count} · {t('risk.confidence')}: {t(`risk.conf.${a.confidence_label}`)}</div></div>
      </div>
      {a.overall_risk === 'insufficient_data' && <div className="mt-3"><StateMessage kind="info">{t('risk.unvalidated')}</StateMessage></div>}
      {!a.stage_specific && <div className="mt-3"><StateMessage kind="info">{t('risk.general_only')}</StateMessage></div>}
      {a.coverage.not_assessed.length > 0 && <p className="muted mt-2">{t('risk.coverage_note')}</p>}

      <h3 className="font-semibold mt-4 mb-2">{t('risk.categories')}</h3>
      <ul className="space-y-2">
        {a.risk_categories.map((c) => (
          <li key={c.category} className="flex flex-wrap items-start gap-2 text-sm border-b pb-2 last:border-0" data-testid="risk-category">
            <div className="min-w-[13rem] font-medium">{c.label}</div><RiskBadge risk={c.risk} label={c.risk_label} /><div className="muted flex-1 basis-60">{c.reason}</div>
          </li>
        ))}
      </ul>

      <h3 className="font-semibold mt-4 mb-2">{t('risk.why')}</h3>
      {a.triggered_rules.length === 0 ? <p className="text-sm">{t('risk.none_triggered')}</p> : <ul className="space-y-2">{a.triggered_rules.map((r) => <RuleDetail key={r.rule_id} r={r} />)}</ul>}

      <h3 className="font-semibold mt-4 mb-2">{t('risk.timeline')}</h3>
      <TriggerTimeline events={a.timeline} />

      <h3 className="font-semibold mt-4 mb-2">{t('risk.actions')}</h3>
      {a.recommended_actions.length === 0 ? <p className="text-sm text-gray-700">{t('risk.no_actions')}</p> : <ul className="list-disc ml-5 text-sm space-y-1">{a.recommended_actions.map((x, i) => <li key={i}>{x.text}</li>)}</ul>}

      <div className="mt-4"><Notices items={a.notices} /></div>
      {a.disabled_rules?.length > 0 && (
        <details className="mt-3 text-sm"><summary className="cursor-pointer font-medium">{t('risk.disabled_rules')} ({a.disabled_rules.length})</summary>
          <ul className="mt-2 space-y-1">{a.disabled_rules.map((r) => <li key={r.rule_id}><code>{r.rule_id}</code> <Chip tone="amber">{t('risk.review')}</Chip> <span className="muted">{r.notes}</span></li>)}</ul></details>
      )}
      <p className="muted mt-3">{t('risk.method')} · v{a.rule_version}</p>
    </Panel>
  )
}
