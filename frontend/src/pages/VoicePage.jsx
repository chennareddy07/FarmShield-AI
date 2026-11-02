import { useState } from 'react'
import { Mic, Square, Volume2 } from 'lucide-react'
import { useApp } from '../context/AppContext'
import { speechInputSupported, speechOutputSupported, useSpeech } from '../hooks/useSpeech'
import { Panel, StateMessage } from '../components/ui'
import ChatBox from '../components/ChatBox'
import ModuleNote from '../components/ModuleNote'

export default function VoicePage() {
  const { t, language } = useApp()
  const [lang, setLang] = useState(language)
  const sp = useSpeech(lang)
  const [lastAnswer, setLastAnswer] = useState('')
  return (
    <>
      <ModuleNote id="voice" />
      <Panel title={t('vo.title')} icon={Mic}>
        {!speechInputSupported && <StateMessage kind="unavailable">{t('vo.unsupported')}</StateMessage>}
        <div className="flex flex-wrap items-end gap-3 mt-2">
          <div><label className="label" htmlFor="vl">{t('vo.lang')}</label><select id="vl" className="input" value={lang} onChange={(e) => setLang(e.target.value)}><option value="en">English</option><option value="te">తెలుగు</option></select></div>
          {speechInputSupported && (sp.listening ? <button className="btn-primary" onClick={sp.stop}><Square size={16} aria-hidden="true" />{t('vo.stop')}</button> : <button className="btn-primary" onClick={sp.start}><Mic size={16} aria-hidden="true" />{t('vo.start')}</button>)}
          {sp.listening && <span role="status" className="text-sm text-brand">{t('vo.listening')}</span>}
        </div>
        {sp.error && sp.error !== 'unsupported' && <div className="mt-2"><StateMessage kind="error">{t('vo.error')}</StateMessage></div>}
        <p className="muted mt-3">{t('vo.uncertain')}</p>
        <div className="mt-3"><ChatBox key={sp.transcript} initialText={sp.transcript} onAnswer={setLastAnswer} /></div>
        {lastAnswer && (speechOutputSupported ? <button className="btn-ghost mt-3" onClick={() => sp.speak(lastAnswer)}><Volume2 size={16} aria-hidden="true" />{t('vo.speak')}</button> : <p className="muted mt-3">{t('vo.no_tts')}</p>)}
      </Panel>
    </>
  )
}
