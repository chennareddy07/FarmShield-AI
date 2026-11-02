import { useCallback, useRef, useState } from 'react'

/** Tracks loading / data / error for an async function; ignores results of superseded calls. */
export function useAsync() {
  const [state, setState] = useState({ loading: false, data: null, error: null })
  const token = useRef(0)
  const run = useCallback(async (fn) => {
    const mine = ++token.current
    setState((s) => ({ ...s, loading: true, error: null }))
    try {
      const data = await fn()
      if (mine === token.current) setState({ loading: false, data, error: null })
      return data
    } catch (error) {
      if (mine === token.current) setState({ loading: false, data: null, error })
      return null
    }
  }, [])
  const reset = useCallback(() => { token.current++; setState({ loading: false, data: null, error: null }) }, [])
  return { ...state, run, reset }
}
