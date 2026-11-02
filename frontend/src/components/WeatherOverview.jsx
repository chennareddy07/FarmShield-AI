import { Cloud, Droplets, Thermometer, Wind, CloudRain, Gauge } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { ErrorState, Panel, Spinner, StateMessage, fmt, fmtTime } from './ui'

function Tile({ icon: Icon, label, value }) {
  return (
    <div className="rounded-xl bg-green-50/60 border border-green-100 p-3">
      <div className="flex items-center gap-2 text-sm text-gray-600"><Icon size={16} aria-hidden="true" />{label}</div>
      <div className="text-xl font-semibold mt-1">{value}</div>
    </div>
  )
}

export default function WeatherOverview({ data, error, loading, onRetry }) {
  const { t, language } = useApp()
  const c = data?.current
  const cond = c?.weather_code != null ? t(`code.${c.weather_code}`) : (c?.weather_summary || t('wx.missing'))
  const dq = data?.data_quality
  return (
    <Panel title={t('wx.title')} icon={Thermometer}>
      {loading && <Spinner />}
      {error && <ErrorState error={error} onRetry={onRetry} />}
      {data && !c && <StateMessage kind="unavailable">{t('state.unavailable')} {dq?.notes?.[0] || ''}</StateMessage>}
      {data && c && (
        <>
          {dq?.status === 'stale' && <div className="mb-3"><StateMessage kind="stale">{t('state.stale')} ({t('q.age')}: {Math.round(dq.age_minutes || 0)} {t('q.min')})</StateMessage></div>}
          {dq?.status === 'partial' && <div className="mb-3"><StateMessage kind="partial">{t('state.partial')} {dq.missing_variables?.join(', ')}</StateMessage></div>}
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            <Tile icon={Thermometer} label={t('wx.temp')} value={fmt(c.temperature_c, '°C')} />
            <Tile icon={Thermometer} label={t('wx.feels')} value={fmt(c.apparent_temperature_c, '°C')} />
            <Tile icon={Droplets} label={t('wx.humidity')} value={fmt(c.relative_humidity_pct, '%', 0)} />
            <Tile icon={CloudRain} label={t('wx.rain')} value={fmt(c.precipitation_mm, 'mm')} />
            <Tile icon={Wind} label={t('wx.wind')} value={`${fmt(c.wind_speed_kmh, 'km/h')} ${c.wind_direction_cardinal || ''}`} />
            <Tile icon={Cloud} label={t('wx.cloud')} value={fmt(c.cloud_cover_pct, '%', 0)} />
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
            <span className="inline-flex items-center gap-1 font-medium"><Gauge size={16} aria-hidden="true" />{t('wx.status')}: {cond}</span>
            <span className="muted">{t('wx.provider')}: {data.provider}</span>
            <span className="muted">{t('wx.observed')}: {fmtTime(data.observed_at, language)}</span>
            <span className="muted">{t('wx.updated')}: {fmtTime(data.retrieved_at, language)}</span>
          </div>
          <p className="muted mt-1">{t('wx.model_note')} {data.location?.spatial_note && ''}</p>
        </>
      )}
    </Panel>
  )
}
