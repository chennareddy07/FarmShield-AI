import { BellRing, ExternalLink } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Chip, ErrorState, Panel, Spinner, StateMessage, fmtTime } from './ui'

export default function WarningsPanel({ data, error, loading }) {
  const { t, language } = useApp()
  const status = data?.source_status
  return (
    <Panel title={t('warn.title')} icon={BellRing}>
      {loading && <Spinner />}
      {error && <ErrorState error={error} />}
      {data && (
        <>
          {status === 'not_configured' && <StateMessage kind="unavailable">{t('warn.not_configured')}</StateMessage>}
          {status === 'unavailable' && <StateMessage kind="unavailable">{t('warn.unavailable')}</StateMessage>}
          {status === 'available' && data.warnings.length === 0 && <StateMessage kind="info">{t('warn.none')}</StateMessage>}
          {data.warnings.map((w) => (
            <article key={w.warning_id} className="rounded-xl border-2 border-orange-300 bg-orange-50 p-3 mb-2">
              <div className="flex flex-wrap items-center gap-2"><strong>{w.title}</strong>{w.severity && <Chip tone="amber">{t('warn.severity')}: {w.severity}</Chip>}{w.severity_color && <Chip tone="amber">{w.severity_color}</Chip>}</div>
              {w.description && <p className="text-sm mt-1">{w.description}</p>}
              <p className="muted mt-1">{t('warn.source')}: {w.source}{w.affected_area ? ` · ${t('warn.area')}: ${w.affected_area}` : ''}{w.valid_until ? ` · ${t('warn.until')} ${fmtTime(w.valid_until, language)}` : ''}</p>
              {w.source_url && <a className="text-sm text-brand-blue underline" href={w.source_url} target="_blank" rel="noreferrer">{t('ev.open')}</a>}
            </article>
          ))}
          {status !== 'available' && (
            <div className="mt-3"><div className="text-sm font-medium mb-1">{t('warn.official_links')}</div>
              <ul className="space-y-1">{data.official_links.map((l) => <li key={l.url}><a className="text-sm text-brand-blue underline inline-flex items-center gap-1" href={l.url} target="_blank" rel="noreferrer">{l.label}<ExternalLink size={12} aria-hidden="true" /></a></li>)}</ul></div>
          )}
        </>
      )}
    </Panel>
  )
}
