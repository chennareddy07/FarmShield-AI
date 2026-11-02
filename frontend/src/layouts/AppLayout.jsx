import { useEffect, useState } from 'react'
import { Bell, Globe, Leaf, Menu, UserRound, X } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { LANGUAGES } from '../translations'
import { StateMessage } from '../components/ui'

export const NAV = ['dashboard', 'weather', 'crop_risk', 'advisor', 'history', 'knowledge', 'calendar', 'market', 'crop_health', 'reports', 'notifications', 'satellite', 'voice', 'regional', 'data_status', 'settings', 'admin', 'multi_region', 'integrations']

export function navBadge(m, t) {
  if (!m) return null
  if (m.nav_state === 'planned') return t('nav.badge.planned')
  if (m.nav_state === 'limited') return m.status === 'needs_config' ? t('nav.badge.limited') : m.status === 'implemented_unverified' ? t('nav.badge.beta') : null
  return null
}

export default function AppLayout({ route, go, children }) {
  const { t, language, setLanguage, modules, location, bootError, boot, sessionReady } = useApp()
  const [open, setOpen] = useState(false)
  const [unread, setUnread] = useState(0)
  const byId = Object.fromEntries(modules.map((m) => [m.id, m]))

  useEffect(() => {
    if (!sessionReady) return undefined
    let alive = true
    api.notifications().then((r) => alive && setUnread(r.unread_count)).catch(() => {})
    return () => { alive = false }
  }, [sessionReady, route])

  const items = NAV.map((id) => {
    const m = byId[id]
    const planned = m?.nav_state === 'planned'
    const badge = navBadge(m, t)
    return (
      <li key={id}>
        <button onClick={() => { go(id); setOpen(false) }} aria-current={route === id ? 'page' : undefined} disabled={false}
          className={`w-full text-left flex items-center justify-between gap-2 rounded-xl px-3 py-2 text-sm ${route === id ? 'bg-brand text-white' : planned ? 'text-gray-500 hover:bg-gray-100' : 'hover:bg-green-50'}`}>
          <span>{t(`nav.${id}`)}</span>
          {badge && <span className={`text-[11px] rounded-full px-2 py-0.5 ${route === id ? 'bg-white/20' : planned ? 'bg-gray-200 text-gray-700' : 'bg-amber-100 text-amber-900'}`}>{badge}</span>}
        </button>
      </li>
    )
  })

  return (
    <div className="min-h-screen flex flex-col">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2">{t('app.skip')}</a>
      <header className="bg-white border-b sticky top-0 z-30">
        <div className="max-w-7xl mx-auto px-3 md:px-6 py-2 flex items-center gap-3">
          <button className="md:hidden btn-ghost !px-2" onClick={() => setOpen(!open)} aria-label={t('nav.menu')} aria-expanded={open}>{open ? <X size={20} /> : <Menu size={20} />}</button>
          <div className="flex items-center gap-2 font-bold text-brand text-lg"><Leaf aria-hidden="true" /><span>{t('app.name')}</span></div>
          <span className="hidden lg:inline muted">{t('app.tagline')}</span>
          <div className="ml-auto flex items-center gap-2">
            <span className="hidden md:inline muted max-w-[14rem] truncate">{location ? location.name : t('header.no_location')}</span>
            <label className="sr-only" htmlFor="lang">{t('header.language')}</label>
            <div className="flex items-center gap-1"><Globe size={16} aria-hidden="true" />
              <select id="lang" className="input !w-auto !py-1" value={language} onChange={(e) => setLanguage(e.target.value)}>{LANGUAGES.map((l) => <option key={l.code} value={l.code}>{l.label}</option>)}</select></div>
            <button className="btn-ghost relative !px-2" onClick={() => go('notifications')} aria-label={`${t('header.notifications')}${unread ? ` (${unread})` : ''}`}><Bell size={18} />{unread > 0 && <span className="absolute -top-1 -right-1 bg-brand-red text-white text-[10px] rounded-full px-1.5">{unread}</span>}</button>
            <button className="btn-ghost !px-2" onClick={() => go('settings')} aria-label={t('header.profile')}><UserRound size={18} /></button>
          </div>
        </div>
      </header>
      <div className="flex-1 max-w-7xl w-full mx-auto md:flex gap-6 px-3 md:px-6 py-4">
        <nav className={`${open ? 'block' : 'hidden'} md:block md:w-60 shrink-0`} aria-label={t('nav.menu')}>
          <ul className="space-y-1 md:sticky md:top-20">{items}</ul>
        </nav>
        <main id="main" className="flex-1 min-w-0 space-y-4">
          {bootError && <StateMessage kind={bootError.network ? 'connection' : 'error'} onRetry={boot}>{bootError.network ? t('state.connection') : bootError.message}</StateMessage>}
          {children}
        </main>
      </div>
      <footer className="border-t bg-white text-xs text-gray-600 px-4 py-3 text-center">
        <p>{t('app.disclaimer')}</p><p className="mt-1">{t('app.attribution')}</p>
      </footer>
    </div>
  )
}
