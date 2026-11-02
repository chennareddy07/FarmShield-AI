import { useState } from 'react'
import { Bar, CartesianGrid, ComposedChart, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { CloudSun } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { ErrorState, Panel, Spinner, StateMessage, fmt, fmtDate } from './ui'

const hourLabel = (iso) => (iso ? iso.slice(11, 16) : '')

export default function ForecastCharts({ data, error, loading, onRetry }) {
  const { t, language } = useApp()
  const [tab, setTab] = useState('daily')
  const hourly = (data?.hourly || []).slice(0, 24).map((h) => ({ x: hourLabel(h.forecast_for), temp: h.temperature_c, rain: h.precipitation_mm, hum: h.relative_humidity_pct, wind: h.wind_speed_kmh }))
  const daily = (data?.daily || []).map((d) => ({ x: d.forecast_for.slice(5), tmax: d.temperature_max_c, tmin: d.temperature_min_c, rain: d.precipitation_sum_mm, wind: d.wind_speed_max_kmh, code: d.weather_code, date: d.forecast_for }))
  const tabs = [['daily', t('fc.daily')], ['hourly', t('fc.hourly')]]
  return (
    <Panel title={t('fc.title')} icon={CloudSun} right={
      <div role="tablist" className="flex gap-1">{tabs.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)} className={`px-3 py-1 rounded-lg text-sm border ${tab === k ? 'bg-brand text-white border-brand' : 'bg-white'}`}>{l}</button>)}</div>}>
      {loading && <Spinner />}
      {error && <ErrorState error={error} onRetry={onRetry} />}
      {data?.data_quality?.status === 'unavailable' && <StateMessage kind="unavailable">{t('state.unavailable')}</StateMessage>}
      {data && data.data_quality?.status !== 'unavailable' && (tab === 'hourly' ? hourly : daily).length === 0 && <p className="muted">{t('fc.empty')}</p>}
      {data && (tab === 'hourly' ? hourly : daily).length > 0 && (
        <>
          <div style={{ width: '100%', height: 260 }} role="img" aria-label={`${t('fc.temp')} / ${t('fc.rain')}`}>
            <ResponsiveContainer>
              <ComposedChart data={tab === 'hourly' ? hourly : daily} margin={{ top: 5, right: 10, left: -10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="x" tick={{ fontSize: 12 }} interval={tab === 'hourly' ? 3 : 0} />
                <YAxis yAxisId="t" tick={{ fontSize: 12 }} />
                <YAxis yAxisId="r" orientation="right" tick={{ fontSize: 12 }} />
                <Tooltip />
                <Legend />
                <Bar yAxisId="r" dataKey="rain" name={t('fc.rain')} fill="#3478A5" />
                {tab === 'hourly' ? <Line yAxisId="t" dataKey="temp" name={t('fc.temp')} stroke="#C84630" dot={false} strokeWidth={2} />
                  : (<><Line yAxisId="t" dataKey="tmax" name={`${t('wx.max')} °C`} stroke="#C84630" strokeWidth={2} /><Line yAxisId="t" dataKey="tmin" name={`${t('wx.min')} °C`} stroke="#E9A23B" strokeWidth={2} /></>)}
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          {tab === 'daily' && (
            <div className="overflow-x-auto mt-3">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-gray-600"><th className="py-1 pr-3">{t('fc.day')}</th><th className="pr-3">{t('wx.max')} °C</th><th className="pr-3">{t('wx.min')} °C</th><th className="pr-3">{t('fc.rain')}</th><th>{t('wx.status')}</th></tr></thead>
                <tbody>{data.daily.map((d) => (
                  <tr key={d.forecast_for} className="border-t"><td className="py-1 pr-3">{fmtDate(d.forecast_for, language)}</td><td>{fmt(d.temperature_max_c)}</td><td>{fmt(d.temperature_min_c)}</td><td>{fmt(d.precipitation_sum_mm)}</td><td>{d.weather_code != null ? t(`code.${d.weather_code}`) : '—'}</td></tr>))}</tbody>
              </table>
            </div>
          )}
          <p className="muted mt-2">{t('fc.note')} · {data.attribution}</p>
        </>
      )}
    </Panel>
  )
}
