import { BookOpen } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { Panel, StateMessage } from './ui'
import EvidenceList from './EvidenceList'

export default function AgriculturalGuidancePanel({ assessment }) {
  const { t } = useApp()
  const items = (assessment?.evidence || []).filter(
    (item) => item.kind === 'agricultural_reference' && item.crop_id === assessment.crop_id,
  )

  return (
    <Panel title={t('dash.guidance')} icon={BookOpen}>
      <p className="muted mb-3">{t('dash.guidance_note')}</p>
      {items.length > 0
        ? <EvidenceList items={items} />
        : <StateMessage kind="info">{t('dash.guidance_none')} <a className="text-brand-blue underline" href="#knowledge">{t('nav.knowledge')}</a></StateMessage>}
    </Panel>
  )
}
