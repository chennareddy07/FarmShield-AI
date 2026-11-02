import { useEffect } from 'react'
import { Store } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import SelectionPanel from '../components/SelectionPanel'
import WeatherOverview from '../components/WeatherOverview'
import ForecastCharts from '../components/ForecastCharts'
import WarningsPanel from '../components/WarningsPanel'
import RiskPanel from '../components/RiskPanel'
import AdvisoryPanel from '../components/AdvisoryPanel'
import SourcesPanel from '../components/SourcesPanel'
import AgriculturalGuidancePanel from '../components/AgriculturalGuidancePanel'
import { ErrorState, Panel, StateMessage } from '../components/ui'

function DashboardMarketPanel() {
  const { t, cropId, location } = useApp()
  const market = useAsync()
  const district = location?.district || ''

  useEffect(() => {
    if (!cropId || !location) {
      market.reset()
      return
    }
    market.run(() => api.market({ crop_id: cropId, district: district || undefined, limit: 5 }))
  }, [cropId, district, Boolean(location), market.run, market.reset])

  const data = market.data
  const hasPrices = data && ['available', 'stale'].includes(data.status)
  return (
    <Panel title={t('mkt.dashboard_title')} icon={Store}>
      {market.loading && <p className="text-sm text-gray-600">{t('mkt.loading')}</p>}
      <ErrorState error={market.error} />
      {!cropId || !location ? <StateMessage kind="info">{t('mkt.dashboard_select')}</StateMessage> : null}
      {data && !hasPrices && <StateMessage kind={data.status === 'empty' ? 'info' : 'unavailable'}>{data.message}</StateMessage>}
      {data?.status === 'stale' && <StateMessage kind="info">{t('mkt.stale_notice')}</StateMessage>}
      {hasPrices && (
        <div className="space-y-2 text-sm">
          <p>{t('mkt.latest')}: <strong>{data.latest_price_date}</strong> · {t('mkt.source')}: <a className="text-brand-blue underline" href={data.prices[0]?.source_url} target="_blank" rel="noreferrer">{data.source}</a> · {t('mkt.unit')}: {data.price_unit_confirmed ? data.price_unit : t('mkt.unit_unconfirmed')}</p>
          <p className="muted">{t('mkt.wholesale_note')}</p>
          <ul className="divide-y">
            {data.prices.slice(0, 3).map((price, index) => (
              <li className="py-2" key={`${price.market_id}-${price.arrival_date}-${index}`}>
                <strong>{price.market_name}</strong> <span className="muted">{price.district}</span>
                <span> · {price.commodity}{price.variety ? ` (${price.variety})` : ''} · {price.arrival_date}</span>
                <span> · {t('mkt.modal')}: {price.modal_price ?? '—'}</span>
                {price.stale && <span className="ml-1 text-amber-700">· {t('mkt.stale')}</span>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </Panel>
  )
}

export default function DashboardPage() {
  const { t, analysis, cropId, location } = useApp()
  const loading = analysis.status === 'loading'
  const done = analysis.status === 'done'
  return (
    <>
      <SelectionPanel />
      <DashboardMarketPanel />
      {analysis.status === 'idle' && <StateMessage kind="info">{t('state.analyze_first')}</StateMessage>}
      {(loading || done) && (
        <div className="grid gap-4 xl:grid-cols-2">
          <WeatherOverview data={analysis.weather} error={analysis.errors.weather} loading={loading} />
          <WarningsPanel data={analysis.warnings} error={analysis.errors.warnings} loading={loading} />
        </div>
      )}
      {done && <RiskPanel assessment={analysis.assessment} needSelection={!cropId} />}
      {done && <AgriculturalGuidancePanel assessment={analysis.assessment} />}
      {done && analysis.errors.assessment && <StateMessage kind="error">{analysis.errors.assessment.message}</StateMessage>}
      {(loading || done) && <ForecastCharts data={analysis.forecast} error={analysis.errors.forecast} loading={loading} />}
      {done && <AdvisoryPanel />}
      {done && <SourcesPanel assessment={analysis.assessment} weather={analysis.weather} />}
    </>
  )
}
