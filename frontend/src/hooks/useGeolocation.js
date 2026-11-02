import { useCallback, useState } from 'react'

export function useGeolocation() {
  const [state, setState] = useState({ loading: false, error: null })
  const locate = useCallback(() => new Promise((resolve) => {
    if (!('geolocation' in navigator)) { setState({ loading: false, error: 'unsupported' }); return resolve(null) }
    setState({ loading: true, error: null })
    navigator.geolocation.getCurrentPosition(
      (pos) => { setState({ loading: false, error: null }); resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }) },
      (err) => { setState({ loading: false, error: err.code === 1 ? 'denied' : 'failed' }); resolve(null) },
      { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
    )
  }), [])
  return { ...state, locate }
}
