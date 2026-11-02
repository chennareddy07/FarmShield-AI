import { useEffect, useRef, useState } from 'react'
import { Send } from 'lucide-react'
import api from '../services/api'
import { useApp } from '../context/AppContext'
import { ErrorState, Notices, Spinner } from './ui'
import EvidenceList from './EvidenceList'

export default function ChatBox({ initialText = '', onAnswer }) {
  const { t, language, analysis, cropId, stageId, location } = useApp()
  const [text, setText] = useState(initialText)
  const [msgs, setMsgs] = useState([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const conv = useRef(readConversationId())

  useEffect(() => {
    if (!conv.current || typeof api.chatHistory !== 'function') return undefined
    let active = true
    api.chatHistory(conv.current).then((result) => {
      if (active) setMsgs((result.messages || []).map((item) => ({
        role: item.role, text: item.content, status: item.status, evidence: item.evidence, uncertainties: item.uncertainties,
      })))
    }).catch((err) => {
      if (!active) return
      if (err?.status === 404) {
        clearConversationId()
        conv.current = null
      } else setError(err)
    })
    return () => { active = false }
  }, [])

  const send = async (e, override) => {
    e?.preventDefault()
    const message = (override ?? text).trim()
    if (!message || busy) return
    setBusy(true); setError(null)
    setMsgs((m) => [...m, { role: 'user', text: message }])
    setText('')
    try {
      const r = await api.chat({ message, language, location: location ? { latitude: location.latitude, longitude: location.longitude, name: location.name, district: location.district } : undefined,
        assessment_id: analysis.assessment?.assessment_id, crop_id: cropId || undefined, growth_stage_id: stageId || undefined, conversation_id: conv.current || undefined })
      conv.current = r.conversation_id
      saveConversationId(conv.current)
      setMsgs((m) => [...m, { role: 'assistant', text: r.answer, status: r.status, evidence: r.evidence, uncertainties: r.uncertainties }])
      onAnswer?.(r.answer)
    } catch (err) { setError(err) } finally { setBusy(false) }
  }

  return (
    <div>
      <h3 className="font-semibold mb-2">{t('adv.ask')}</h3>
      <div className="space-y-3 mb-3" aria-live="polite">
        {msgs.map((m, i) => (
          <div key={i} className={`rounded-xl p-3 text-sm ${m.role === 'user' ? 'bg-green-50 border border-green-200' : 'bg-white border'}`}>
            <div className="font-medium mb-1">{m.role === 'user' ? t('adv.you') : t('adv.assistant')}</div>
            <p className="whitespace-pre-line">{m.text}</p>
            {m.status && <p className="muted mt-1">{t(`adv.chat_status.${m.status}`)}</p>}
            {m.uncertainties?.length > 0 && <div className="mt-2"><Notices items={m.uncertainties} /></div>}
            {m.evidence?.length > 0 && <details className="mt-2"><summary className="cursor-pointer text-sm">{t('adv.evidence')} ({m.evidence.length})</summary><div className="mt-2"><EvidenceList items={m.evidence} /></div></details>}
          </div>
        ))}
        {busy && <Spinner label={t('adv.thinking')} />}
      </div>
      <ErrorState error={error} />
      <form onSubmit={send} className="flex gap-2">
        <label className="sr-only" htmlFor="chat-in">{t('adv.ask')}</label>
        <input id="chat-in" className="input" value={text} onChange={(e) => setText(e.target.value)} placeholder={t('adv.ask_ph')} maxLength={800} />
        <button className="btn-primary" type="submit" disabled={busy || !text.trim()}><Send size={18} aria-hidden="true" /><span className="sr-only md:not-sr-only">{t('adv.send')}</span></button>
      </form>
    </div>
  )
}

const CONVERSATION_KEY = 'farmshield_chat_conversation'
function readConversationId() {
  try { return window.sessionStorage.getItem(CONVERSATION_KEY) } catch { return null }
}
function saveConversationId(id) {
  try { window.sessionStorage.setItem(CONVERSATION_KEY, id) } catch { /* session storage unavailable */ }
}
function clearConversationId() {
  try { window.sessionStorage.removeItem(CONVERSATION_KEY) } catch { /* session storage unavailable */ }
}
