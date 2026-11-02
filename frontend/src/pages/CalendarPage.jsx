import { useEffect } from 'react'
import { CalendarDays } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, Spinner, StateMessage } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

export default function CalendarPage() {
  const { t, language, crops } = useApp()
  const cals = useAsync()
  useEffect(() => { if (crops.length) cals.run(() => Promise.all(crops.map((c) => api.calendar(c.crop_id)))) }, [crops])  // eslint-disable-line
  return (
    <>
      <ModuleNote id="calendar" />
      {cals.loading && <Spinner />}<ErrorState error={cals.error} />
      {cals.data?.map((c) => (
        <Panel key={c.crop_id} title={`${t('cal.title')} — ${crops.find((x) => x.crop_id === c.crop_id)?.name_i18n?.[language] || c.crop_id}`} icon={CalendarDays}>
          {c.calendar_status === 'unavailable' && <StateMessage kind="unavailable">{t('cal.unavailable')}</StateMessage>}
          <h3 className="font-semibold mt-3 mb-1">{t('cal.stages')}</h3>
          <ol className="list-decimal ml-5 text-sm space-y-1">{c.stages.map((s) => <li key={s.stage_id}>{s.name[language] || s.name.en}</li>)}</ol>
          {c.stage_catalogue_review_status === 'needs_review' && <p className="muted mt-2">⚠ {t('cal.review')}</p>}
        </Panel>
      ))}
    </>
  )
}
