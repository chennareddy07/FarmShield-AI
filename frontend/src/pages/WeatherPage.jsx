import { useApp } from '../context/AppContext'
import SelectionPanel from '../components/SelectionPanel'
import WeatherOverview from '../components/WeatherOverview'
import ForecastCharts from '../components/ForecastCharts'
import WarningsPanel from '../components/WarningsPanel'
import { StateMessage } from '../components/ui'

export default function WeatherPage() {
  const { t, analysis } = useApp()
  const loading = analysis.status === 'loading'
  return (
    <>
      <SelectionPanel />
      {analysis.status === 'idle' ? <StateMessage kind="info">{t('state.analyze_first')}</StateMessage> : (
        <>
          <WeatherOverview data={analysis.weather} error={analysis.errors.weather} loading={loading} />
          <ForecastCharts data={analysis.forecast} error={analysis.errors.forecast} loading={loading} />
          <WarningsPanel data={analysis.warnings} error={analysis.errors.warnings} loading={loading} />
        </>
      )}
    </>
  )
}
