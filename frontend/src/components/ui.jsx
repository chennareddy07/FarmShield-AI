import { AlertOctagon, AlertTriangle, CheckCircle2, HelpCircle, Loader2, ShieldAlert, WifiOff, Info } from 'lucide-react'
import { useApp } from '../context/AppContext'

export const RISK_STYLES = {
  low: { cls: 'bg-green-100 text-green-900 border-green-400', Icon: CheckCircle2 },
  moderate: { cls: 'bg-amber-100 text-amber-900 border-amber-400', Icon: AlertTriangle },
  high: { cls: 'bg-orange-100 text-orange-900 border-orange-500', Icon: AlertOctagon },
  critical: { cls: 'bg-red-100 text-red-900 border-red-600 font-bold', Icon: ShieldAlert },
  insufficient_data: { cls: 'bg-gray-100 text-gray-800 border-gray-400', Icon: HelpCircle },
}

/** Risk is always conveyed by icon + text + colour (never colour alone). */
export function RiskBadge({ risk, label, large = false }) {
  const { t } = useApp()
  const s = RISK_STYLES[risk] || RISK_STYLES.insufficient_data
  const Icon = s.Icon
  return (
    <span data-testid="risk-badge" data-risk={risk} className={`inline-flex items-center gap-2 rounded-full border-2 px-3 py-1 ${large ? 'text-xl px-4 py-2' : 'text-sm'} ${s.cls}`}>
      <Icon aria-hidden="true" size={large ? 24 : 16} />
      <span>{label || t(`risk.${risk}`)}</span>
    </span>
  )
}

export function Spinner({ label }) {
  const { t } = useApp()
  return <div role="status" className="flex items-center gap-2 text-gray-600 py-4"><Loader2 className="animate-spin" size={18} aria-hidden="true" />{label || t('state.loading')}</div>
}

export function StateMessage({ kind = 'empty', children, onRetry }) {
  const { t } = useApp()
  const map = { empty: ['bg-gray-50 border-gray-200 text-gray-700', Info], error: ['bg-red-50 border-red-300 text-red-900', AlertOctagon], unavailable: ['bg-amber-50 border-amber-300 text-amber-900', AlertTriangle],
    stale: ['bg-amber-50 border-amber-300 text-amber-900', AlertTriangle], partial: ['bg-amber-50 border-amber-300 text-amber-900', AlertTriangle], connection: ['bg-red-50 border-red-300 text-red-900', WifiOff], info: ['bg-blue-50 border-blue-200 text-blue-900', Info] }
  const [cls, Icon] = map[kind] || map.empty
  return (
    <div role={kind === 'error' || kind === 'connection' ? 'alert' : 'status'} className={`rounded-xl border p-3 flex gap-3 items-start ${cls}`}>
      <Icon size={18} className="mt-0.5 shrink-0" aria-hidden="true" />
      <div className="flex-1 text-sm">{children}{onRetry && <div className="mt-2"><button className="btn-ghost !min-h-[36px] text-sm" onClick={onRetry}>{t('state.retry')}</button></div>}</div>
    </div>
  )
}

/** Maps a normalised API error to a user-facing message (never raw stack/technical text). */
export function ErrorState({ error, onRetry }) {
  const { t } = useApp()
  if (!error) return null
  if (error.network) return <StateMessage kind="connection" onRetry={onRetry}>{t('state.connection')}</StateMessage>
  const unavailable = ['weather_unavailable', 'geocoding_unavailable', 'history_unavailable', 'database_unavailable'].includes(error.code)
  const text = error.code === 'weather_unavailable' ? t('wx.unavailable') : error.message
  return <StateMessage kind={unavailable ? 'unavailable' : 'error'} onRetry={onRetry}>{text}{error.requestId && <div className="text-xs opacity-70 mt-1">ref: {error.requestId}</div>}</StateMessage>
}

export function Panel({ title, icon: Icon, right, children, id, className = '' }) {
  return (
    <section id={id} className={`card ${className}`} aria-label={title}>
      <header className="flex items-center justify-between gap-2 mb-3">
        <h2 className="text-lg font-semibold flex items-center gap-2">{Icon && <Icon size={20} className="text-brand" aria-hidden="true" />}{title}</h2>
        {right}
      </header>
      {children}
    </section>
  )
}

export function Notices({ items }) {
  const { t } = useApp()
  if (!items || !items.length) return null
  return (
    <div className="rounded-xl bg-blue-50 border border-blue-200 p-3 text-sm text-blue-900" aria-label={t('common.notices')}>
      <ul className="list-disc ml-5 space-y-1">{items.map((n, i) => <li key={i}>{n}</li>)}</ul>
    </div>
  )
}

export function Chip({ children, tone = 'gray' }) {
  const tones = { gray: 'bg-gray-100 text-gray-800', green: 'bg-green-100 text-green-900', amber: 'bg-amber-100 text-amber-900', red: 'bg-red-100 text-red-900', blue: 'bg-blue-100 text-blue-900' }
  return <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>
}

export const fmt = (v, unit = '', digits = 1) => (v === null || v === undefined ? '—' : `${typeof v === 'number' ? Number(v.toFixed(digits)) : v}${unit ? ' ' + unit : ''}`)
export const fmtTime = (iso, lang) => { if (!iso) return '—'; try { return new Date(iso).toLocaleString(lang === 'te' ? 'te-IN' : 'en-IN', { dateStyle: 'medium', timeStyle: 'short' }) } catch { return iso } }
export const fmtDate = (iso, lang) => { if (!iso) return '—'; try { return new Date(iso.length === 10 ? iso + 'T00:00:00' : iso).toLocaleDateString(lang === 'te' ? 'te-IN' : 'en-IN', { weekday: 'short', day: 'numeric', month: 'short' }) } catch { return iso } }
