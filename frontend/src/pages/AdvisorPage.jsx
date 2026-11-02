import { useApp } from '../context/AppContext'
import SelectionPanel from '../components/SelectionPanel'
import AdvisoryPanel from '../components/AdvisoryPanel'
import { StateMessage } from '../components/ui'

export default function AdvisorPage() {
  const { t, analysis } = useApp()
  return (
    <>
      <SelectionPanel />
      {analysis.status === 'idle' && <StateMessage kind="info">{t('state.analyze_first')}</StateMessage>}
      <AdvisoryPanel />
    </>
  )
}
