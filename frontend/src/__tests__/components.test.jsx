import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, expect, it, vi, beforeEach } from 'vitest'

vi.mock('../services/api', () => {
  const api = {
    session: vi.fn(), crops: vi.fn(), regions: vi.fn(), modules: vi.fn(), health: vi.fn(), searchLocations: vi.fn(), current: vi.fn(), forecast: vi.fn(), warnings: vi.fn(), assess: vi.fn(), advisory: vi.fn(), chat: vi.fn(), chatHistory: vi.fn(), notifications: vi.fn(), getAssessment: vi.fn(),
    knowledgeDocs: vi.fn(), knowledgeSearch: vi.fn(), evidenceRegistry: vi.fn(), market: vi.fn(), marketOptions: vi.fn(), marketAdvice: vi.fn(),
  }
  return { default: api, api, normalizeError: (e) => e }
})
import api from '../services/api'
import { AppProvider, useApp } from '../context/AppContext'
import { RiskBadge, ErrorState } from '../components/ui'
import ForecastCharts from '../components/ForecastCharts'
import SelectionPanel from '../components/SelectionPanel'
import RiskPanel from '../components/RiskPanel'
import AgriculturalGuidancePanel from '../components/AgriculturalGuidancePanel'
import AdvisoryPanel from '../components/AdvisoryPanel'
import WarningsPanel from '../components/WarningsPanel'
import EvidenceList from '../components/EvidenceList'
import App from '../App'
import ChatBox from '../components/ChatBox'
import KnowledgePage from '../pages/KnowledgePage'
import DashboardPage from '../pages/DashboardPage'
import MarketPage from '../pages/MarketPage'

const CROPS = [{ crop_id: 'paddy', name: 'Paddy', name_i18n: { en: 'Paddy', te: 'వరి' }, review_status: 'needs_review', supported_stages: [{ stage_id: 'flowering', order: 1, name: { en: 'Flowering', te: 'పూత దశ' } }] },
  { crop_id: 'groundnut', name: 'Groundnut', name_i18n: { en: 'Groundnut', te: 'వేరుశనగ' }, supported_stages: [{ stage_id: 'pegging', order: 1, name: { en: 'Pegging', te: 'ఊడలు దిగే దశ' } }] }]

beforeEach(() => {
  vi.clearAllMocks()
  localStorage.clear()
  sessionStorage.clear()
  api.session.mockResolvedValue({ mode: 'anonymous' })
  api.crops.mockResolvedValue(CROPS)
  api.regions.mockResolvedValue({ districts: ['Guntur', 'Krishna'] })
  api.modules.mockResolvedValue([{ id: 'dashboard', nav_state: 'active', status: 'implemented', features: [], level: 1 }, { id: 'multi_region', nav_state: 'planned', status: 'planned', features: ['F24'], level: 3, note: 'x' },
    { id: 'market', nav_state: 'limited', status: 'needs_config', features: ['F19'], level: 3 }])
  api.health.mockResolvedValue({ services: { official_warnings: 'not_configured' } })
  api.notifications.mockResolvedValue({ unread_count: 0, notifications: [] })
  api.chatHistory.mockResolvedValue({ messages: [] })
  api.chat.mockResolvedValue({ conversation_id: 'conv-test', answer: 'Available information.', evidence: [], uncertainties: [], status: 'retrieval_only' })
  api.knowledgeDocs.mockResolvedValue({ documents: [] })
  api.knowledgeSearch.mockResolvedValue({ results: [], count: 0 })
  api.evidenceRegistry.mockResolvedValue({ coverage_gaps: [] })
  api.market.mockResolvedValue({ status: 'not_configured', prices: [], message: 'Market data unavailable.' })
  api.marketOptions.mockResolvedValue({
    status: 'available', states: ['Andhra Pradesh', 'Punjab'], districts: ['Guntur'],
    commodities: ['Dhan', 'Maize', 'Paddy(Common)'], complete: true, retrieved_at: '2026-11-02T00:00:00Z',
  })
  api.marketAdvice.mockResolvedValue({ status: 'available', ai_status: 'not_configured', comparison_markets: [], limitations: [] })
})

const wrap = (ui) => render(<AppProvider>{ui}</AppProvider>)

describe('Assessment workflow integration', () => {
  it('uses the assessment response snapshots instead of requesting weather and warnings again', async () => {
    api.assess.mockResolvedValue({
      assessment_id: 'as-workflow',
      crop_id: 'paddy',
      weather_snapshot: { current: { current: { temperature_c: 30 } }, forecast: { daily: [{ forecast_for: '2026-03-01' }] } },
      warnings_snapshot: { source_status: 'not_configured', warnings: [] },
      evidence: [{
        evidence_id: 'EV-KB-PADDY-REFERENCE', kind: 'agricultural_reference', crop_id: 'paddy',
        growth_stage_id: 'flowering', title: 'Paddy source guidance', publisher: 'ICAR',
        excerpt: 'Source-checked guidance excerpt.', evidence_status: 'expert_review_required',
        source_access_status: 'pdf_verified', verification_status: 'needs_review',
        source_url: 'https://example.org/paddy.pdf',
      }],
    })

    api.advisory.mockResolvedValue({ answer: 'Based on the calculated assessment.' })

    function WorkflowHarness() {
      const { setLocation, setCropId, setStageId, runAnalysis, requestAdvisory, analysis } = useApp()
      return <>
        <button onClick={() => {
          setLocation({ name: 'Guntur', district: 'Guntur', latitude: 16.3, longitude: 80.4 })
          setCropId('paddy')
          setStageId('flowering')
        }}>Select crop and location</button>
        <button onClick={runAnalysis}>Analyze</button>
        <button onClick={requestAdvisory}>Generate advisory</button>
        <output data-testid="workflow-snapshots">
          {analysis.weather?.current?.temperature_c}:{analysis.forecast?.daily?.length}:{analysis.warnings?.source_status}
        </output>
        <AdvisoryPanel withChat={false} />
      </>
    }

    wrap(<WorkflowHarness />)
    await waitFor(() => expect(api.session).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByText('Select crop and location'))
    fireEvent.click(screen.getByText('Analyze'))
    await waitFor(() => expect(api.assess).toHaveBeenCalledOnce())
    expect(api.advisory).not.toHaveBeenCalled()
    expect(api.current).not.toHaveBeenCalled()
    expect(api.forecast).not.toHaveBeenCalled()
    expect(api.warnings).not.toHaveBeenCalled()
    expect(screen.getByTestId('workflow-snapshots').textContent).toBe('30:1:not_configured')
    expect(screen.getByText('Paddy source guidance')).toBeInTheDocument()
    expect(screen.getByText('Source-checked guidance excerpt.')).toBeInTheDocument()
    expect(screen.getByText('Expert review required')).toBeInTheDocument()
    fireEvent.click(screen.getByText('Generate advisory'))
    await waitFor(() => expect(api.advisory).toHaveBeenCalledOnce())
  })
})

describe('Dashboard market summary', () => {
  it('requests nearby prices using the selected crop and district', async () => {
    api.market.mockResolvedValue({
      status: 'available', latest_price_date: '2026-11-02', price_unit_confirmed: false,
      source: 'data.gov.in / Agmarknet',
      prices: [{ market_id: 'Andhra Pradesh/Guntur/Guntur', market_name: 'Guntur', district: 'Guntur',
        commodity: 'Paddy(Dhan)(Common)', variety: 'Common', arrival_date: '2026-11-02',
        modal_price: 2400, stale: false, source_url: 'https://data.gov.in/resource/test' }],
    })
    function DashboardMarketHarness() {
      const { setLocation, setCropId } = useApp()
      return <>
        <button onClick={() => {
          setCropId('paddy')
          setLocation({ name: 'Guntur', district: 'Guntur', latitude: 16.3, longitude: 80.4 })
        }}>Choose dashboard market</button>
        <DashboardPage />
      </>
    }

    wrap(<DashboardMarketHarness />)
    fireEvent.click(await screen.findByText('Choose dashboard market'))
    await waitFor(() => expect(api.market).toHaveBeenCalledWith({ crop_id: 'paddy', district: 'Guntur', limit: 5 }))
    expect(await screen.findByText(/Paddy\(Dhan\)\(Common\)/)).toBeInTheDocument()
    expect(screen.getByText(/Unit unconfirmed/)).toBeInTheDocument()
    expect(screen.getByText(/Reported mandi wholesale prices/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'data.gov.in / Agmarknet' })).toHaveAttribute('href', 'https://data.gov.in/resource/test')
  })
})

describe('Market page', () => {
  it('shows returned commodity details, stale status, source, and unconfirmed units', async () => {
    api.market.mockResolvedValue({
      status: 'stale', latest_price_date: '2026-10-20', price_unit_confirmed: false,
      source: 'data.gov.in / Agmarknet',
      prices: [{ market_id: 'Andhra Pradesh/Guntur/Guntur', market_name: 'Guntur', district: 'Guntur',
        commodity: 'Dhan', variety: 'Common', arrival_date: '2026-10-20', min_price: 2300,
        max_price: 2500, modal_price: 2400, price_unit: 'Unit unconfirmed',
        price_unit_confirmed: false, stale: true, source_url: 'https://data.gov.in/resource/test' }],
    })
    wrap(<MarketPage />)
    await screen.findByLabelText('Commodity')
    fireEvent.change(screen.getByLabelText('Commodity'), { target: { value: 'Dhan' } })
    fireEvent.click(screen.getByRole('button', { name: 'Load live prices' }))
    await waitFor(() => expect(api.market).toHaveBeenCalledWith({
      state: 'Andhra Pradesh', district: undefined, commodity: 'Dhan', limit: 100,
    }))
    expect((await screen.findAllByText('Dhan')).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Unit unconfirmed/).length).toBeGreaterThan(0)
    expect(screen.getAllByText('Stale').length).toBeGreaterThan(0)
    expect(screen.getByText('Common')).toBeInTheDocument()
    expect(screen.getByText(/Reported mandi wholesale prices/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: 'data.gov.in / Agmarknet' })).toHaveAttribute('href', 'https://data.gov.in/resource/test')
  })

  it('uses only states and commodities returned by the live source', async () => {
    api.marketOptions.mockImplementation(async ({ state } = {}) => ({
      status: 'available', states: ['Andhra Pradesh', 'Punjab'],
      districts: state === 'Punjab' ? ['Amritsar', 'Ludhiana'] : ['Guntur'],
      commodities: state === 'Punjab' ? ['Maize', 'Wheat'] : ['Paddy(Common)'],
      complete: true,
    }))
    wrap(<MarketPage />)
    await screen.findByLabelText('State')
    fireEvent.change(screen.getByLabelText('State'), { target: { value: 'Punjab' } })
    await waitFor(() => expect(screen.getByLabelText('District').querySelectorAll('option')).toHaveLength(3))
    fireEvent.change(screen.getByLabelText('District'), { target: { value: 'Ludhiana' } })
    await waitFor(() => expect(api.marketOptions).toHaveBeenCalledWith({ state: 'Punjab', district: 'Ludhiana' }))
    await waitFor(() => expect(screen.getByLabelText('Commodity').querySelectorAll('option')).toHaveLength(3))
    expect([...screen.getByLabelText('Commodity').querySelectorAll('option')].map((option) => option.value)).toEqual(['', 'Maize', 'Wheat'])
  })

  it('calls market LLM only when the user explicitly requests an explanation', async () => {
    api.market.mockResolvedValue({
      status: 'available', latest_price_date: '2026-11-02', price_unit_confirmed: false,
      source: 'data.gov.in / Agmarknet',
      prices: [{ market_id: 'Punjab/Ludhiana/Mandi A', market_name: 'Mandi A', district: 'Ludhiana',
        commodity: 'Maize', variety: 'Hybrid', arrival_date: '2026-11-02', min_price: 10,
        max_price: 12, modal_price: 11, price_unit_confirmed: false, stale: false,
        source_url: 'https://data.gov.in/resource/test' }],
    })
    api.marketAdvice.mockResolvedValue({
      status: 'available', ai_status: 'available',
      highest_reported_quote: { market_name: 'Mandi A', district: 'Ludhiana', commodity: 'Maize',
        variety: 'Hybrid', arrival_date: '2026-11-02', modal_price: 11, price_unit_confirmed: false },
      ai_summary: 'Compare records with transport and buyer terms.',
      follow_up_questions: ['Would you like another district comparison?'],
      limitations: ['Reported wholesale prices are not guaranteed.'],
    })
    wrap(<MarketPage />)
    await screen.findByLabelText('Commodity')
    fireEvent.change(screen.getByLabelText('Commodity'), { target: { value: 'Maize' } })
    fireEvent.click(screen.getByRole('button', { name: 'Load live prices' }))
    await waitFor(() => expect(api.market).toHaveBeenCalled())
    expect(api.marketAdvice).not.toHaveBeenCalled()
    fireEvent.click(screen.getByRole('button', { name: 'Explain these prices' }))
    await waitFor(() => expect(api.marketAdvice).toHaveBeenCalledWith({
      state: 'Andhra Pradesh', district: undefined, commodity: 'Maize', language: 'en', question: undefined,
    }))
    expect(await screen.findByText(/Compare records with transport/)).toBeInTheDocument()
  })
})

describe('Assistant conversation', () => {
  it('sends the selected location with a chat question', async () => {
    function ChatHarness() {
      const { setLocation } = useApp()
      return <>
        <button onClick={() => setLocation({ name: 'Guntur', district: 'Guntur', latitude: 16.3, longitude: 80.4 })}>Set location</button>
        <ChatBox />
      </>
    }

    wrap(<ChatHarness />)
    await waitFor(() => expect(api.session).toHaveBeenCalledOnce())
    fireEvent.click(screen.getByText('Set location'))
    fireEvent.change(screen.getByLabelText('Ask a follow-up question'), { target: { value: 'What is the weather?' } })
    fireEvent.click(screen.getByRole('button', { name: 'Send' }))
    await waitFor(() => expect(api.chat).toHaveBeenCalledOnce())
    expect(api.chat.mock.calls[0][0].location).toEqual({ latitude: 16.3, longitude: 80.4, name: 'Guntur', district: 'Guntur' })
  })

  it('restores persisted owner-scoped conversation messages', async () => {
    sessionStorage.setItem('farmshield_chat_conversation', 'conv-existing')
    api.chatHistory.mockResolvedValue({ messages: [{ role: 'user', content: 'Earlier question' }, { role: 'assistant', content: 'Earlier response' }] })
    wrap(<ChatBox />)
    expect(await screen.findByText('Earlier question')).toBeInTheDocument()
    expect(api.chatHistory).toHaveBeenCalledWith('conv-existing')
  })
})

describe('RiskBadge', () => {
  it.each(['low', 'moderate', 'high', 'critical', 'insufficient_data'])('shows text, not colour only: %s', (r) => {
    wrap(<RiskBadge risk={r} />)
    const el = screen.getByTestId('risk-badge')
    expect(el.textContent.trim().length).toBeGreaterThan(2)
    expect(el.querySelector('svg')).toBeTruthy()
    expect(el.dataset.risk).toBe(r)
  })
})

describe('ErrorState', () => {
  it('shows connection message for network errors, never raw technical text', () => {
    wrap(<ErrorState error={{ network: true, message: 'ECONNREFUSED 127.0.0.1:8000' }} />)
    expect(screen.getByRole('alert').textContent).toMatch(/Cannot reach the FarmShield server/)
    expect(screen.getByRole('alert').textContent).not.toMatch(/ECONNREFUSED/)
  })

  describe('KnowledgePage', () => {
    it('sends crop, stage, district, season and evidence-status filters to the real API client', async () => {
      api.evidenceRegistry.mockResolvedValue({ coverage_gaps: [{
        crop_id: 'paddy', growth_stage_id: 'flowering', concern: 'high_temperature', evidence_status: 'insufficient_evidence',
      }] })
      wrap(<KnowledgePage />)
      await waitFor(() => expect(api.evidenceRegistry).toHaveBeenCalled())
      fireEvent.change(screen.getByLabelText('Crop'), { target: { value: 'paddy' } })
      fireEvent.change(screen.getByLabelText('Growth stage'), { target: { value: 'flowering' } })
      fireEvent.change(screen.getByLabelText('District'), { target: { value: 'Guntur' } })
      fireEvent.change(screen.getByLabelText('Season'), { target: { value: 'Kharif' } })
      fireEvent.change(screen.getByLabelText('Evidence status'), { target: { value: 'expert_review_required' } })
      fireEvent.change(screen.getByLabelText('Search'), { target: { value: 'flowering heat' } })
      fireEvent.click(screen.getByRole('button', { name: 'Search' }))
      await waitFor(() => expect(api.knowledgeSearch).toHaveBeenCalled())
      expect(api.knowledgeSearch).toHaveBeenLastCalledWith({
        q: 'flowering heat', crop_id: 'paddy', growth_stage_id: 'flowering', state: 'Andhra Pradesh',
        district: 'Guntur', season: 'Kharif', concern: undefined, evidence_status: 'expert_review_required',
      })
      expect(await screen.findByText('1 crop-stage-concern combinations have insufficient evidence.')).toBeInTheDocument()
      expect(screen.getAllByText('High temperature').length).toBeGreaterThan(0)
    })
  })
  it('maps weather_unavailable', () => {
    wrap(<ErrorState error={{ code: 'weather_unavailable', message: 'x', status: 502 }} />)
    expect(screen.getByRole('status').textContent).toMatch(/currently unavailable/)
  })
})

describe('ForecastCharts', () => {
  it('distinguishes unavailable forecasts from an empty forecast', () => {
    wrap(<ForecastCharts data={{ hourly: [], daily: [], data_quality: { status: 'unavailable' } }} />)
    expect(screen.getByText('Service unavailable.')).toBeInTheDocument()
    expect(screen.queryByText('No forecast data.')).toBeNull()
  })
})

describe('SelectionPanel', () => {
  it('searches, shows results, selects a location, limits stages to chosen crop', async () => {
    api.searchLocations.mockResolvedValue({ results: [{ location_id: 'om-1', name: 'Guntur', district: 'Guntur', state: 'Andhra Pradesh', latitude: 16.3, longitude: 80.45 }] })
    wrap(<SelectionPanel />)
    await waitFor(() => expect(screen.getByLabelText('Crop')).toBeEnabled())
    fireEvent.change(screen.getByLabelText('Search location'), { target: { value: 'Guntur' } })
    fireEvent.submit(screen.getByRole('search'))
    fireEvent.click(await screen.findByText('Guntur', { selector: 'span.font-medium' }))
    expect(screen.getByTestId('selected-location').textContent).toMatch(/16\.300, 80\.450/)
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeEnabled()
    fireEvent.change(screen.getByLabelText('Crop'), { target: { value: 'groundnut' } })
    const opts = [...screen.getByLabelText('Growth stage').querySelectorAll('option')].map((o) => o.textContent)
    expect(opts).toContain('Pegging'); expect(opts).not.toContain('Flowering')
  })
  it('shows a helpful message for unresolved locations and disables Analyze with no location', async () => {
    api.searchLocations.mockResolvedValue({ results: [] })
    wrap(<SelectionPanel />)
    expect(screen.getByRole('button', { name: 'Analyze' })).toBeDisabled()
    fireEvent.change(screen.getByLabelText('Search location'), { target: { value: 'Nowhere' } })
    fireEvent.submit(screen.getByRole('search'))
    expect(await screen.findByText(/No supported Andhra Pradesh location matched/)).toBeInTheDocument()
  })
  it('Telugu labels appear after language switch', async () => {
    localStorage.setItem('fs_lang', 'te')
    wrap(<SelectionPanel />)
    expect(await screen.findByText('ప్రాంతం మరియు పంట')).toBeInTheDocument()
  })
})

const ASSESSMENT = {
  assessment_id: 'as-1', overall_risk: 'high', overall_risk_label: 'High', crop_name: 'Paddy', growth_stage_name: 'Flowering', stage_specific: true, forecast_window: { start: '2026-11-01', end: '2026-11-07' },
  coverage: { assessed_count: 1, required_count: 8, not_assessed: [{ category: 'wind' }] }, confidence_label: 'limited', rule_version: '0.1.0', notices: ['Values are forecasts'],
  risk_categories: [{ category: 'rainfall', label: 'Rainfall risk', risk: 'high', risk_label: 'High', reason: 'Rain reached 130 mm' }, { category: 'wind', label: 'Wind-related risk', risk: 'insufficient_data', risk_label: 'Insufficient data', reason: 'No verified rule' }],
  triggered_rules: [{ rule_id: 'IMD-RAIN-VERYHEAVY', severity: 'high', reason: 'Rain reached 130 mm', weather_variable: 'precipitation_sum_mm', operator: 'between', threshold: 115.6, threshold_unit: 'mm', actual_value: 130, period: '2026-11-03', source_reference: { title: 'IMD PR', url: 'https://x', publisher: 'IMD' }, review_status: 'verified' }],
  timeline: [{ rule_id: 'IMD-RAIN-VERYHEAVY', severity: 'high', start: '2026-11-03', end: '2026-11-03', actual_value: 130, unit: 'mm', label: 'Rain' }], recommended_actions: [], disabled_rules: [{ rule_id: 'PADDY-HEAT-FLOWERING', notes: 'pending' }],
}

describe('RiskPanel', () => {
  it('renders overall risk, categories, triggered rule with expandable detail, coverage caveat and disabled rules', () => {
    wrap(<RiskPanel assessment={ASSESSMENT} />)
    expect(screen.getAllByTestId('risk-badge')[0].dataset.risk).toBe('high')
    expect(screen.getAllByTestId('risk-category')).toHaveLength(2)
    expect(screen.getByText(/Categories without a verified rule are not assessed/)).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: /Details/ }))
    expect(screen.getByText('precipitation_sum_mm')).toBeInTheDocument()
    expect(screen.getByText(/PADDY-HEAT-FLOWERING/)).toBeInTheDocument()
    expect(screen.getByText(/No verified crop-specific action/)).toBeInTheDocument()
  })
  it('prompts selection when no assessment', () => {
    wrap(<RiskPanel assessment={null} needSelection />)
    expect(screen.getByText(/Select a crop and growth stage/)).toBeInTheDocument()
  })
  it('states when no scientifically validated crop-specific risk level can be calculated', () => {
    wrap(<RiskPanel assessment={{ ...ASSESSMENT, overall_risk: 'insufficient_data' }} />)
    expect(screen.getByText(/FarmShield currently cannot calculate a scientifically validated crop-specific risk level/)).toBeInTheDocument()
  })
})

describe('AgriculturalGuidancePanel', () => {
  it('shows source-backed paddy guidance with publication page and limitations', () => {
    wrap(<AgriculturalGuidancePanel assessment={{
      crop_id: 'paddy',
      evidence: [{
        evidence_id: 'EV-KB-ICAR', kind: 'agricultural_reference', title: 'ICAR paddy guidance',
        publisher: 'ICAR', publication_date: 'May 2025', crop_id: 'paddy',
        evidence_status: 'expert_review_required', source_access_status: 'pdf_verified',
        source_section: 'Printed p.76', source_url: 'https://icar.gov.in/source.pdf',
        excerpt: 'Submergence concern at source-named stages.',
        limitations: 'Not a risk threshold.',
      }],
    }} />)
    expect(screen.getByText('ICAR paddy guidance')).toBeInTheDocument()
    expect(screen.getByText(/Printed p.76/)).toBeInTheDocument()
    expect(screen.getByText(/Not a risk threshold/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source/ })).toHaveAttribute('href', 'https://icar.gov.in/source.pdf')
  })
  it('shows stage-specific groundnut guidance and its source', () => {
    wrap(<AgriculturalGuidancePanel assessment={{
      crop_id: 'groundnut',
      evidence: [{
        evidence_id: 'EV-KB-GNUT', kind: 'agricultural_reference', title: 'Groundnut package of practices',
        publisher: 'ICAR-IIGR', publication_date: '2018 (publication year not printed)',
        crop_id: 'groundnut', growth_stage_id: 'pegging', evidence_status: 'expert_review_required',
        source_access_status: 'pdf_verified', source_section: 'PDF p.2: irrigation management',
        source_url: 'https://icar-iigr.org.in/wp-content/uploads/2018/12/Package-of-Practices.pdf',
        excerpt: 'The source identifies peg penetration as a critical irrigation stage.',
        limitations: 'Older state-level source; not Guntur-specific.',
      }],
    }} />)
    expect(screen.getByText('Groundnut package of practices')).toBeInTheDocument()
    expect(screen.getByText('Crop stage:')).toBeInTheDocument()
    expect(screen.getByText('pegging')).toBeInTheDocument()
    expect(screen.getByText(/PDF p.2: irrigation management/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source/ })).toHaveAttribute('href', 'https://icar-iigr.org.in/wp-content/uploads/2018/12/Package-of-Practices.pdf')
  })
})

describe('WarningsPanel', () => {
  it('never shows warnings when not configured; shows official links', () => {
    wrap(<WarningsPanel data={{ source_status: 'not_configured', warnings: [], official_links: [{ label: 'IMD', url: 'https://mausam.imd.gov.in/' }] }} />)
    expect(screen.getByText(/not connected/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /IMD/ })).toHaveAttribute('href', 'https://mausam.imd.gov.in/')
    expect(screen.queryByText(/No active official warning/)).toBeNull()
  })
  it('shows supplied severity and source for real warnings', () => {
    wrap(<WarningsPanel data={{ source_status: 'available', official_links: [], warnings: [{ warning_id: 'w', title: 'Heavy rain', severity: 'Severe', source: 'IMD Amaravati', valid_until: '2026-11-04T00:00:00+05:30' }] }} />)
    expect(screen.getByText('Heavy rain')).toBeInTheDocument(); expect(screen.getByText(/Severe/)).toBeInTheDocument(); expect(screen.getByText(/IMD Amaravati/)).toBeInTheDocument()
  })
})

describe('EvidenceList', () => {
  it('flags unreviewed evidence and links to the source', () => {
    wrap(<EvidenceList items={[{ evidence_id: 'EV-1', kind: 'agricultural_reference', title: 'T', publisher: 'P', publication_date: null, source_url: 'https://s', verification_status: 'needs_review', excerpt: 'abc' }]} />)
    expect(screen.getByText(/Source access does not imply agronomic approval/)).toBeInTheDocument()
    expect(screen.getByRole('link', { name: /Open source/ })).toHaveAttribute('href', 'https://s')
  })
})

describe('App navigation honesty', () => {
  it('shows planned and needs-setup badges from the module registry', async () => {
    wrap(<App />)
    expect(await screen.findAllByText('Planned')).not.toHaveLength(0)
    expect(screen.getAllByText('Needs setup').length).toBeGreaterThan(0)
  })
})
