import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis, Legend } from 'recharts'
import { History } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Notices, Panel, Spinner, StateMessage, fmt } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

const iso = (d) => d.toISOString().slice(0, 10)
const daysAgo = (n) => iso(new Date(Date.now() - n * 864e5))

export default function HistoryPage() {
  const { t, location } = useApp()
  const [start, setStart] = useState(daysAgo(97))
  const [end, setEnd] = useState(daysAgo(7))
  const [sm, setSm] = useState(6); const [em, setEm] = useState(9); const [by, setBy] = useState(10)
  const hist = useAsync(); const seas = useAsync()
  if (!location) return <Panel title={t('hist.title')} icon={History}><StateMessage kind="info">{t('hist.need_location')}</StateMessage></Panel>
  const d = hist.data
  const series = d?.series?.map((s) => ({ x: s.date.slice(5), tmax: s.temperature_max_c, tmin: s.temperature_min_c, rain: s.precipitation_sum_mm })) || []
  const c = seas.data?.comparison
  return (
    <>
      <ModuleNote id="history" />
      <Panel title={t('hist.title')} icon={History}>
        <p className="muted mb-2">{location.name}</p>
        <div className="flex flex-wrap items-end gap-3">
          <div><label className="label" htmlFor="hs">{t('hist.start')}</label><input id="hs" type="date" className="input" value={start} onChange={(e) => setStart(e.target.value)} /></div>
          <div><label className="label" htmlFor="he">{t('hist.end')}</label><input id="he" type="date" className="input" value={end} onChange={(e) => setEnd(e.target.value)} /></div>
          <button className="btn-primary" onClick={() => hist.run(() => api.history({ latitude: location.latitude, longitude: location.longitude, start_date: start, end_date: end }))} disabled={hist.loading}>{t('hist.load')}</button>
        </div>
        {hist.loading && <Spinner />}
        <ErrorState error={hist.error} />
        {d && (
          <div className="mt-4 space-y-4">
            <StateMessage kind="info">{t('hist.reanalysis')}</StateMessage>
            <p className="text-sm">{t('hist.coverage')}: {t('hist.rain_cov')} {d.coverage.rainfall_coverage_pct}% ({d.coverage.days_with_rainfall}/{d.coverage.expected_days})</p>
            <Notices items={d.notes} />
            <div style={{ height: 240 }}><ResponsiveContainer><LineChart data={series}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="x" tick={{ fontSize: 11 }} minTickGap={24} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Legend />
              <Line dataKey="tmax" name={`${t('hist.tmax')} °C`} stroke="#C84630" dot={false} /><Line dataKey="tmin" name={`${t('hist.tmin')} °C`} stroke="#E9A23B" dot={false} /></LineChart></ResponsiveContainer></div>
            <div style={{ height: 220 }}><ResponsiveContainer><BarChart data={d.monthly}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="month" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip /><Bar dataKey="rainfall_total_mm" name={t('hist.monthly')} fill="#3478A5" /></BarChart></ResponsiveContainer></div>
            <details><summary className="cursor-pointer text-sm font-medium">{t('hist.limits')}</summary><ul className="list-disc ml-5 text-sm mt-1">{d.limitations.map((l) => <li key={l}>{l}</li>)}</ul></details>
            <p className="muted">{d.provider} · {d.attribution}</p>
          </div>
        )}
      </Panel>
      <Panel title={t('hist.seasonal')} icon={History}>
        <div className="flex flex-wrap items-end gap-3">
          <div><label className="label" htmlFor="sm">{t('hist.season')} {t('hist.start')}</label><input id="sm" type="number" min="1" max="12" className="input !w-24" value={sm} onChange={(e) => setSm(+e.target.value)} /></div>
          <div><label className="label" htmlFor="em">{t('hist.end')}</label><input id="em" type="number" min="1" max="12" className="input !w-24" value={em} onChange={(e) => setEm(+e.target.value)} /></div>
          <div><label className="label" htmlFor="by">{t('hist.baseline')}</label><input id="by" type="number" min="5" max="30" className="input !w-24" value={by} onChange={(e) => setBy(+e.target.value)} /></div>
          <button className="btn-primary" onClick={() => seas.run(() => api.seasonal({ latitude: location.latitude, longitude: location.longitude, start_month: sm, end_month: em, baseline_years: by }))} disabled={seas.loading}>{t('hist.compare')}</button>
        </div>
        {seas.loading && <Spinner />}
        <ErrorState error={seas.error} />
        {c && c.status === 'available' && (
          <dl className="mt-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
            <div className="card !p-3"><dt className="muted">{t('hist.observed')}</dt><dd className="text-xl font-semibold">{fmt(c.observed_total_mm, 'mm')}</dd></div>
            <div className="card !p-3"><dt className="muted">{t('hist.mean')}</dt><dd className="text-xl font-semibold">{fmt(c.baseline_mean_mm, 'mm')}</dd></div>
            <div className="card !p-3"><dt className="muted">{t('hist.deviation')}</dt><dd className="text-xl font-semibold">{c.deviation_mm > 0 ? '+' : ''}{fmt(c.deviation_mm, 'mm')} ({c.deviation_pct > 0 ? '+' : ''}{fmt(c.deviation_pct, '%')})</dd></div>
          </dl>
        )}
        {c && c.status !== 'available' && <div className="mt-3"><StateMessage kind="unavailable"><strong>{t('hist.unavailable_comparison')}.</strong> {c.reason}</StateMessage></div>}
        {c && <p className="muted mt-2"><strong>{t('hist.method')}:</strong> {c.method}</p>}
      </Panel>
    </>
  )
}
