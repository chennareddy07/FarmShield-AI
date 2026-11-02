import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Satellite } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Notices, Panel, Spinner, StateMessage } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

export default function SatellitePage() {
  const { t, location } = useApp()
  const r = useAsync(); const d = r.data
  return (
    <>
      <ModuleNote id="satellite" />
      <Panel title={t('sat.title')} icon={Satellite}>
        {!location ? <StateMessage kind="info">{t('hist.need_location')}</StateMessage> : (
          <>
            <p className="muted mb-2">{location.name}</p>
            <button className="btn-primary" disabled={r.loading} onClick={() => r.run(() => api.satellite(location.latitude, location.longitude))}>{t('sat.load')}</button>
            {r.loading && <Spinner />}<ErrorState error={r.error} />
            {d && d.status !== 'available' && <div className="mt-3"><StateMessage kind="unavailable">{d.message}</StateMessage></div>}
            {d?.status === 'available' && <div className="mt-3 space-y-3"><p className="text-sm">{t('sat.observed')}: <strong>{d.observation_date}</strong> · {t('sat.provider')}: {d.provider} · {t('sat.resolution')}: {d.spatial_resolution}</p>
              <div style={{ height: 220 }}><ResponsiveContainer><LineChart data={d.indicators}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="date" tick={{ fontSize: 11 }} /><YAxis domain={[0, 1]} tick={{ fontSize: 11 }} /><Tooltip /><Line dataKey="ndvi" name={t('sat.chart')} stroke="#246B45" strokeWidth={2} /></LineChart></ResponsiveContainer></div></div>}
            {d && <div className="mt-3"><h3 className="font-semibold mb-1">{t('sat.limits')}</h3><Notices items={d.quality_notes} /></div>}
          </>)}
      </Panel>
    </>
  )
}
