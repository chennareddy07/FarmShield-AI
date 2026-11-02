import { Construction } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Panel, StateMessage } from '../components/ui'

export default function PlannedPage({ id }) {
  const { t, modules } = useApp()
  const m = modules.find((x) => x.id === id)
  return (
    <Panel title={`${t(`nav.${id}`)} — ${t('plan.title')}`} icon={Construction}>
      <StateMessage kind="info">{t('plan.text')}{m?.note ? <div className="mt-1">{m.note}</div> : null}</StateMessage>
    </Panel>
  )
}
