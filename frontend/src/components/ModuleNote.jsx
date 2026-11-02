import { useApp } from '../context/AppContext'
import { StateMessage } from './ui'

export default function ModuleNote({ id }) {
  const { t, modules } = useApp()
  const m = modules.find((x) => x.id === id)
  if (!m || !m.note) return null
  return <StateMessage kind={m.status === 'needs_config' ? 'unavailable' : 'info'}>{m.status === 'needs_config' ? t('state.needs_setup') + ' ' : ''}{m.note}</StateMessage>
}
