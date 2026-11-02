import { useApp } from '../context/AppContext'
import SelectionPanel from '../components/SelectionPanel'
import RiskPanel from '../components/RiskPanel'
import EvidenceList from '../components/EvidenceList'
import SourcesPanel from '../components/SourcesPanel'
import { Panel, Spinner, StateMessage } from '../components/ui'
import { BookOpen } from 'lucide-react'

export default function CropRiskPage() {
  const { t, analysis, cropId } = useApp()
  return (
    <>
      <SelectionPanel />
      {analysis.status === 'loading' && <Spinner />}
      {analysis.status === 'idle' && <StateMessage kind="info">{t('state.analyze_first')}</StateMessage>}
      {analysis.status === 'done' && (
        <>
          <RiskPanel assessment={analysis.assessment} needSelection={!cropId} />
          {analysis.assessment && <Panel title={t('ev.title')} icon={BookOpen}><EvidenceList items={analysis.assessment.evidence} /></Panel>}
          <SourcesPanel assessment={analysis.assessment} weather={analysis.weather} />
        </>
      )}
    </>
  )
}
