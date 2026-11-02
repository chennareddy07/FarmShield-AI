import { useCallback, useEffect, useRef, useState } from 'react'

const RECOGNITION = typeof window !== 'undefined' ? (window.SpeechRecognition || window.webkitSpeechRecognition) : null
export const speechInputSupported = Boolean(RECOGNITION)
export const speechOutputSupported = typeof window !== 'undefined' && 'speechSynthesis' in window

const BCP47 = { en: 'en-IN', te: 'te-IN' }

/** Browser Web Speech API wrapper (F23). Support for Telugu depends on browser/OS. */
export function useSpeech(lang) {
  const [listening, setListening] = useState(false)
  const [transcript, setTranscript] = useState('')
  const [error, setError] = useState(null)
  const rec = useRef(null)

  const start = useCallback(() => {
    if (!RECOGNITION) { setError('unsupported'); return }
    setError(null); setTranscript('')
    const r = new RECOGNITION()
    r.lang = BCP47[lang] || 'en-IN'
    r.interimResults = false
    r.maxAlternatives = 1
    r.onresult = (e) => setTranscript(e.results[0][0].transcript)
    r.onerror = () => { setError('failed'); setListening(false) }
    r.onend = () => setListening(false)
    rec.current = r
    setListening(true)
    try { r.start() } catch { setError('failed'); setListening(false) }
  }, [lang])

  const stop = useCallback(() => { try { rec.current?.stop() } catch { /* ignore */ } setListening(false) }, [])

  const speak = useCallback((text) => {
    if (!speechOutputSupported) return false
    window.speechSynthesis.cancel()
    const u = new SpeechSynthesisUtterance(text)
    u.lang = BCP47[lang] || 'en-IN'
    window.speechSynthesis.speak(u)
    return true
  }, [lang])

  useEffect(() => () => { try { rec.current?.abort() } catch { /* ignore */ } if (speechOutputSupported) window.speechSynthesis.cancel() }, [])
  return { listening, transcript, setTranscript, error, start, stop, speak }
}
