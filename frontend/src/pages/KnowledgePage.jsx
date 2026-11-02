import { useEffect, useState } from 'react'
import { BookOpen } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { useAsync } from '../hooks/useAsync'
import { ErrorState, Panel, Spinner, StateMessage } from '../components/ui'
import EvidenceList from '../components/EvidenceList'

const SEASONS = ['Kharif', 'Rabi', 'Summer']
const CONCERNS = ['rainfall', 'rainfall_classification', 'excess_rainfall', 'dry_spell', 'water_stress', 'water_management', 'submergence', 'cultivation', 'variety_selection', 'pest_disease', 'high_temperature', 'low_temperature', 'humidity', 'wind', 'severe_weather_warning']
const STATUSES = ['source_verified', 'source_unverified', 'expert_review_required', 'expert_approved', 'conflicting_evidence', 'insufficient_evidence']

export default function KnowledgePage() {
  const { t, crops, language, regions, location } = useApp()
  const [q, setQ] = useState('')
  const [crop, setCrop] = useState('')
  const [stage, setStage] = useState('')
  const [state, setState] = useState('Andhra Pradesh')
  const [district, setDistrict] = useState(location?.district || '')
  const [season, setSeason] = useState('')
  const [concern, setConcern] = useState('')
  const [evidenceStatus, setEvidenceStatus] = useState('')
  const search = useAsync()
  const docs = useAsync()
  const registry = useAsync()
  const selectedCrop = crops.find((item) => item.crop_id === crop)
  const filters = {
    crop_id: crop || undefined,
    growth_stage_id: stage || undefined,
    state: state || undefined,
    district: district || undefined,
    season: season || undefined,
    concern: concern || undefined,
    evidence_status: evidenceStatus || undefined,
  }

  useEffect(() => {
    docs.run(() => api.knowledgeDocs(filters))
  }, [crop, stage, state, district, season, concern, evidenceStatus]) // eslint-disable-line
  useEffect(() => {
    registry.run(() => api.evidenceRegistry({ crop_id: crop || undefined }))
  }, [crop]) // eslint-disable-line

  const go = (event) => {
    event?.preventDefault()
    search.run(() => api.knowledgeSearch({ ...filters, q }))
  }
  const formatStage = (cropId, stageId) => {
    const item = crops.find((candidate) => candidate.crop_id === cropId)?.supported_stages?.find((candidate) => candidate.stage_id === stageId)
    return item?.name_i18n?.[language] || item?.name?.[language] || stageId
  }

  return (
    <>
      <Panel title={t('kb.title')} icon={BookOpen}>
        <form onSubmit={go} className="flex flex-wrap gap-2 items-end">
          <div className="flex-1 min-w-[12rem]"><label className="label" htmlFor="kq">{t('kb.search')}</label><input id="kq" className="input" value={q} onChange={(event) => setQ(event.target.value)} placeholder={t('kb.search_ph')} /></div>
          <div><label className="label" htmlFor="kc">{t('kb.crop')}</label><select id="kc" className="input" value={crop} onChange={(event) => { setCrop(event.target.value); setStage('') }}><option value="">{t('kb.all')}</option>{crops.map((item) => <option key={item.crop_id} value={item.crop_id}>{item.name_i18n?.[language] || item.name}</option>)}</select></div>
          <div><label className="label" htmlFor="kst">{t('kb.stage')}</label><select id="kst" className="input" value={stage} onChange={(event) => setStage(event.target.value)} disabled={!crop}><option value="">{t('kb.all')}</option>{selectedCrop?.supported_stages?.map((item) => <option key={item.stage_id} value={item.stage_id}>{item.name?.[language] || item.name?.en}</option>)}</select></div>
          <div><label className="label" htmlFor="kstate">{t('kb.state')}</label><select id="kstate" className="input" value={state} onChange={(event) => setState(event.target.value)}><option value="">{t('kb.all')}</option><option value="Andhra Pradesh">Andhra Pradesh</option></select></div>
          <div><label className="label" htmlFor="kd">{t('kb.district')}</label><select id="kd" className="input" value={district} onChange={(event) => setDistrict(event.target.value)}><option value="">{t('kb.all')}</option>{regions?.districts?.map((item) => <option key={item} value={item}>{item}</option>)}</select></div>
          <div><label className="label" htmlFor="kseason">{t('kb.season')}</label><select id="kseason" className="input" value={season} onChange={(event) => setSeason(event.target.value)}><option value="">{t('kb.all')}</option>{SEASONS.map((item) => <option key={item} value={item}>{t(`kb.season.${item.toLowerCase()}`)}</option>)}</select></div>
          <div><label className="label" htmlFor="kconcern">{t('kb.concern')}</label><select id="kconcern" className="input" value={concern} onChange={(event) => setConcern(event.target.value)}><option value="">{t('kb.all')}</option>{CONCERNS.map((item) => <option key={item} value={item}>{t(`kb.concern.${item}`)}</option>)}</select></div>
          <div><label className="label" htmlFor="kstatus">{t('kb.status')}</label><select id="kstatus" className="input" value={evidenceStatus} onChange={(event) => setEvidenceStatus(event.target.value)}><option value="">{t('kb.all')}</option>{STATUSES.map((item) => <option key={item} value={item}>{t(`ev.status.${item}`)}</option>)}</select></div>
          <button className="btn-primary" type="submit">{t('kb.search')}</button>
        </form>
        {search.loading && <Spinner />}
        <ErrorState error={search.error} />
        {search.data && (search.data.count === 0 ? <div className="mt-3"><StateMessage kind="info">{t('kb.none')}</StateMessage></div> : <div className="mt-3"><p className="muted mb-2">{search.data.count} {t('kb.results')}</p><EvidenceList items={search.data.results} /></div>)}
      </Panel>
      <Panel title={t('kb.coverage')} icon={BookOpen}>
        {registry.loading && <Spinner />}
        <ErrorState error={registry.error} />
        {registry.data && <>
          <p className="muted">{t('kb.coverage_summary', { count: registry.data.coverage_gaps.length })}</p>
          <details className="mt-2">
            <summary className="cursor-pointer text-sm font-medium">{t('kb.coverage_details')}</summary>
            <ul className="mt-2 max-h-80 overflow-y-auto space-y-1 text-sm">
              {registry.data.coverage_gaps.map((item) => <li key={`${item.crop_id}-${item.growth_stage_id}-${item.concern}`} className="border-t py-1">
                <strong>{crops.find((candidate) => candidate.crop_id === item.crop_id)?.name_i18n?.[language] || item.crop_id}</strong>
                {' · '}{formatStage(item.crop_id, item.growth_stage_id)}{' · '}{t(`kb.concern.${item.concern}`)}
                {' · '}<span className="text-amber-800">{t(`ev.status.${item.evidence_status}`)}</span>
              </li>)}
            </ul>
          </details>
          <p className="text-xs muted mt-2">{t('kb.coverage_note')}</p>
        </>}
      </Panel>
      <Panel title={t('kb.guidance')} icon={BookOpen}>
        {registry.loading && <Spinner />}
        <ErrorState error={registry.error} />
        {registry.data && <EvidenceList items={(registry.data.general_guidance || []).map((item) => ({
          ...item,
          title: item.source_title,
          publisher: item.institution,
          publication_date: item.publication_date,
          source_url: item.original_url,
          source_section: item.page_reference
            ? `${item.page_reference}${item.source_section ? ` · ${item.source_section}` : ''}`
            : item.source_section,
          excerpt: item.source_fact,
          evidence_status: item.expert_review_status,
          verification_status: 'needs_review',
          kind: 'agricultural_reference',
        }))} />}
      </Panel>
      <Panel title={t('kb.documents')} icon={BookOpen}>
        {docs.loading && <Spinner />}
        <ErrorState error={docs.error} />
        {docs.data && <EvidenceList items={docs.data.documents.map((item) => ({
          ...item,
          evidence_id: item.evidence_id || `EV-KB-${item.document_id}`,
          kind: item.source_type === 'agricultural_reference' ? 'agricultural_reference' : 'meteorological_reference',
        }))} />}
      </Panel>
    </>
  )
}
