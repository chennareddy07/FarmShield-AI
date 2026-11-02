import { useEffect, useState } from 'react'
import { AppProvider, useApp } from './context/AppContext'
import AppLayout, { NAV } from './layouts/AppLayout'
import DashboardPage from './pages/DashboardPage'
import WeatherPage from './pages/WeatherPage'
import CropRiskPage from './pages/CropRiskPage'
import AdvisorPage from './pages/AdvisorPage'
import HistoryPage from './pages/HistoryPage'
import KnowledgePage from './pages/KnowledgePage'
import CalendarPage from './pages/CalendarPage'
import MarketPage from './pages/MarketPage'
import CropHealthPage from './pages/CropHealthPage'
import ReportsPage from './pages/ReportsPage'
import NotificationsPage from './pages/NotificationsPage'
import SatellitePage from './pages/SatellitePage'
import VoicePage from './pages/VoicePage'
import RegionalPage from './pages/RegionalPage'
import DataStatusPage from './pages/DataStatusPage'
import SettingsPage from './pages/SettingsPage'
import AdminPage from './pages/AdminPage'
import PlannedPage from './pages/PlannedPage'

const PAGES = { dashboard: DashboardPage, weather: WeatherPage, crop_risk: CropRiskPage, advisor: AdvisorPage, history: HistoryPage, knowledge: KnowledgePage, calendar: CalendarPage, market: MarketPage,
  crop_health: CropHealthPage, reports: ReportsPage, notifications: NotificationsPage, satellite: SatellitePage, voice: VoicePage, regional: RegionalPage, data_status: DataStatusPage, settings: SettingsPage, admin: AdminPage }

const fromHash = () => { const h = window.location.hash.replace('#', ''); return NAV.includes(h) ? h : 'dashboard' }

function Shell() {
  const { modules } = useApp()
  const [route, setRoute] = useState(fromHash())
  useEffect(() => { const on = () => setRoute(fromHash()); window.addEventListener('hashchange', on); return () => window.removeEventListener('hashchange', on) }, [])
  const go = (id) => { window.location.hash = id; setRoute(id); window.scrollTo?.(0, 0) }
  const m = modules.find((x) => x.id === route)
  const Page = m?.nav_state === 'planned' ? null : PAGES[route]
  return <AppLayout route={route} go={go}>{Page ? <Page /> : <PlannedPage id={route} />}</AppLayout>
}

export default function App() {
  return <AppProvider><Shell /></AppProvider>
}
