import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, Legend, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Bot, Store } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, Spinner, StateMessage, fmt, fmtTime } from '../components/ui'
import ModuleNote from '../components/ModuleNote'

const EMPTY_OPTIONS = []

export default function MarketPage() {
  const { t, language, location } = useApp()
  const [state, setState] = useState('')
  const [district, setDistrict] = useState('')
  const [commodity, setCommodity] = useState('')
  const [question, setQuestion] = useState('')
  const options = useAsync()
  const prices = useAsync()
  const advice = useAsync()
  const data = prices.data
  const hasPrices = data && ['available', 'stale'].includes(data.status)
  const availableStates = options.data?.states || EMPTY_OPTIONS
  const availableDistricts = options.data?.districts || EMPTY_OPTIONS
  const availableCommodities = options.data?.commodities || EMPTY_OPTIONS

  useEffect(() => {
    options.run(() => api.marketOptions()).then((result) => {
      if (!result?.states?.length) return
      const locationState = result.states.find((item) => item.toLowerCase() === location?.state?.toLowerCase())
      const apState = result.states.find((item) => item.toLowerCase() === 'andhra pradesh')
      setState((current) => current || locationState || apState || result.states[0])
    })
  }, [options.run, location?.state])

  useEffect(() => {
    if (!state) return
    prices.reset()
    advice.reset()
    options.run(() => api.marketOptions({ state, district: district || undefined }))
  }, [state, district, options.run, prices.reset, advice.reset])

  useEffect(() => {
    if (!options.data) return
    if (!availableCommodities.length) {
      setCommodity('')
      prices.reset()
      advice.reset()
      return
    }
    if (!availableCommodities.includes(commodity)) {
      setCommodity(availableCommodities[0])
      prices.reset()
      advice.reset()
    }
  }, [availableCommodities, commodity, prices.reset, advice.reset])

  const loadPrices = () => {
    advice.reset()
    prices.run(() => api.market({ state, district: district || undefined, commodity, limit: 100 }))
  }
  const requestAdvice = (followUp = question) => {
    if (!state || !commodity) return
    advice.run(() => api.marketAdvice({
      state, district: district || undefined, commodity, language,
      question: followUp?.trim() || undefined,
    }))
  }
  const adviceResult = advice.data
  const chartData = (data?.prices || []).slice(0, 20).map((price) => ({
    ...price,
    chart_label: `${price.market_name || 'Market'} · ${price.arrival_date}`,
  }))

  return (
    <>
      <ModuleNote id="market" />
      <Panel title={t('mkt.title')} icon={Store}>
        <p className="muted mb-4">{t('mkt.subtitle')}</p>
        {options.loading && <Spinner label={t('mkt.options_loading')} />}
        <ErrorState error={options.error} onRetry={() => options.run(() => api.marketOptions())} />
        {options.data?.status !== 'available' && !options.loading && (
          <div className="mb-4"><StateMessage kind={options.data?.status === 'empty' ? 'info' : 'unavailable'}>
            {options.data?.message || t('mkt.options_unavailable')}
          </StateMessage></div>
        )}
        {options.data?.complete === false && <p className="mb-3 text-sm text-amber-800">{t('mkt.options_partial')}</p>}

        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 items-end">
          <div>
            <label className="label" htmlFor="market-state">{t('mkt.state')}</label>
            <select id="market-state" className="input" value={state} onChange={(event) => {
              setState(event.target.value); setDistrict(''); setCommodity(''); prices.reset(); advice.reset()
            }} disabled={!availableStates.length}>
              <option value="">{t('mkt.select_state')}</option>
              {availableStates.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="market-district">{t('mkt.district')}</label>
            <select id="market-district" className="input" value={district} onChange={(event) => {
              setDistrict(event.target.value); setCommodity(''); prices.reset(); advice.reset()
            }} disabled={!state}>
              <option value="">{t('mkt.all_districts')}</option>
              {availableDistricts.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <div>
            <label className="label" htmlFor="market-commodity">{t('mkt.commodity')}</label>
            <select id="market-commodity" className="input" value={commodity} onChange={(event) => {
              setCommodity(event.target.value); prices.reset(); advice.reset()
            }} disabled={!state || !availableCommodities.length}>
              <option value="">{t('mkt.select_commodity')}</option>
              {availableCommodities.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </div>
          <button className="btn-primary" disabled={!state || !commodity || prices.loading} onClick={loadPrices}>
            {t('mkt.load')}
          </button>
        </div>

        <p className="muted mt-3 text-sm">{t('mkt.options_source')} {options.data?.retrieved_at && fmtTime(options.data.retrieved_at, language)}</p>
        {prices.loading && <Spinner />}
        <ErrorState error={prices.error} onRetry={loadPrices} />
        {data && !hasPrices && <div className="mt-3"><StateMessage kind={data.status === 'empty' ? 'info' : 'unavailable'}>{data.message}</StateMessage></div>}
        {data?.status === 'stale' && <div className="mt-3"><StateMessage kind="info">{t('mkt.stale_notice')}</StateMessage></div>}
        {data && !hasPrices && data.official_links && <ul className="mt-2 text-sm">{data.official_links.map((link) => <li key={link.url}><a className="text-brand-blue underline" href={link.url} target="_blank" rel="noreferrer">{link.label}</a></li>)}</ul>}

        {hasPrices && (
          <div className="mt-5 space-y-4">
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm">
              <span>{t('mkt.latest')}: <strong>{data.latest_price_date}</strong></span>
              <span>{t('mkt.records')}: <strong>{data.prices.length}</strong></span>
              <span>{t('mkt.source')}: <a className="text-brand-blue underline" href={data.prices[0]?.source_url} target="_blank" rel="noreferrer">{data.source}</a></span>
              <span>{t('mkt.unit')}: {data.price_unit_confirmed ? data.price_unit : t('mkt.unit_unconfirmed')}</span>
            </div>
            <p className="muted text-sm">{t('mkt.wholesale_note')}</p>
            <section aria-label={t('mkt.chart')} className="rounded-xl border bg-white p-3">
              <h3 className="font-semibold mb-2">{t('mkt.chart')}</h3>
              <div className="h-72 min-w-0">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 8, right: 12, bottom: 56, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="chart_label" angle={-30} textAnchor="end" interval={0} height={72} tick={{ fontSize: 10 }} />
                    <YAxis tick={{ fontSize: 11 }} />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="min_price" name={t('mkt.min')} fill="#9BC7A9" />
                    <Bar dataKey="max_price" name={t('mkt.max')} fill="#327B4F" />
                    <Line dataKey="modal_price" name={t('mkt.modal')} stroke="#B45309" strokeWidth={2} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </section>
            <div className="overflow-x-auto rounded-xl border">
              <table className="w-full min-w-[900px] text-sm">
                <thead className="bg-gray-50"><tr className="text-left text-gray-600">
                  <th className="p-2">{t('mkt.market')}</th><th>{t('mkt.state')}</th><th>{t('mkt.commodity')}</th><th>{t('mkt.variety')}</th>
                  <th>{t('mkt.grade')}</th><th>{t('mkt.date')}</th><th>{t('mkt.min')}</th><th>{t('mkt.max')}</th><th>{t('mkt.modal')}</th><th>{t('mkt.freshness')}</th>
                </tr></thead>
                <tbody>{data.prices.map((price, index) => <tr key={`${price.market_id}-${price.arrival_date}-${index}`} className="border-t">
                  <td className="p-2">{price.market_name} <span className="muted">{price.district}</span></td><td>{price.state}</td><td>{price.commodity}</td>
                  <td>{price.variety || '—'}</td><td>{price.grade || '—'}</td><td>{price.arrival_date}</td>
                  <td>{fmt(price.min_price, '', 0)}</td><td>{fmt(price.max_price, '', 0)}</td><td className="font-semibold">{fmt(price.modal_price, '', 0)}</td>
                  <td>{price.stale ? t('mkt.stale') : t('mkt.fresh')}</td>
                </tr>)}</tbody>
              </table>
            </div>

            <section className="rounded-xl border border-green-200 bg-green-50/50 p-4" aria-label={t('mkt.ai_title')}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h3 className="flex items-center gap-2 font-semibold"><Bot size={18} aria-hidden="true" />{t('mkt.ai_title')}</h3>
                <button className="btn-primary" disabled={advice.loading} onClick={() => requestAdvice()}>
                  {advice.loading ? t('mkt.ai_loading') : t('mkt.ai_generate')}
                </button>
              </div>
              <p className="muted mt-1 text-sm">{t('mkt.ai_disclaimer')}</p>
              {advice.loading && <Spinner />}
              <ErrorState error={advice.error} onRetry={() => requestAdvice()} />
              {adviceResult?.highest_reported_quote && (
                <div className="mt-3 rounded-lg bg-white p-3 text-sm">
                  <strong>{t('mkt.highest_quote')}</strong>
                  <span> {adviceResult.highest_reported_quote.market_name}, {adviceResult.highest_reported_quote.district}</span>
                  <span> · {adviceResult.highest_reported_quote.commodity} {adviceResult.highest_reported_quote.variety || ''}</span>
                  <span> · {t('mkt.modal')}: {fmt(adviceResult.highest_reported_quote.modal_price, '', 0)}</span>
                  <span> · {adviceResult.highest_reported_quote.arrival_date}</span>
                  <span> · {adviceResult.highest_reported_quote.price_unit_confirmed
                    ? adviceResult.highest_reported_quote.price_unit : t('mkt.unit_unconfirmed')}</span>
                </div>
              )}
              {adviceResult?.ai_status === 'available' && (
                <div className="mt-3 space-y-2 text-sm">
                  <p>{adviceResult.ai_summary}</p>
                  {adviceResult.follow_up_questions?.length > 0 && <div className="flex flex-wrap gap-2">
                    {adviceResult.follow_up_questions.map((item) => <button key={item} className="btn-ghost text-sm" onClick={() => {
                      setQuestion(item); requestAdvice(item)
                    }}>{item}</button>)}
                  </div>}
                </div>
              )}
              {adviceResult && adviceResult.ai_status !== 'available' && (
                <div className="mt-3"><StateMessage kind="info">{t(`mkt.ai_status.${adviceResult.ai_status}`)}</StateMessage></div>
              )}
              {adviceResult?.limitations?.length > 0 && <ul className="mt-3 list-disc space-y-1 pl-5 text-sm">
                {adviceResult.limitations.map((item) => <li key={item}>{item}</li>)}
              </ul>}
              <form className="mt-3 flex flex-col gap-2 sm:flex-row" onSubmit={(event) => {
                event.preventDefault()
                requestAdvice(question)
              }}>
                <label className="sr-only" htmlFor="market-question">{t('mkt.question_label')}</label>
                <input id="market-question" className="input flex-1" value={question} onChange={(event) => setQuestion(event.target.value)}
                  maxLength={300} placeholder={t('mkt.question_placeholder')} />
                <button className="btn-ghost" type="submit" disabled={advice.loading || !question.trim()}>{t('mkt.ask')}</button>
              </form>
            </section>
          </div>
        )}
      </Panel>
    </>
  )
}
