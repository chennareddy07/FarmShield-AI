import axios from 'axios'

const http = axios.create({ baseURL: import.meta.env.VITE_API_BASE_URL || '', timeout: 45000, withCredentials: true })

/** Normalise every failure into { code, message, status, requestId, details, network }. */
export function normalizeError(err) {
  if (err && err.__normalized) return err
  const res = err?.response
  const body = res?.data
  const out = {
    __normalized: true,
    network: !res,
    status: res?.status ?? 0,
    code: body?.error_code || (res ? 'http_error' : 'network_error'),
    message: body?.message || err?.message || 'Request failed',
    requestId: body?.request_id || res?.headers?.['x-request-id'] || null,
    details: body?.details ?? null,
  }
  return out
}

http.interceptors.response.use((r) => r, (e) => Promise.reject(normalizeError(e)))

const get = (url, params) => http.get(url, { params }).then((r) => r.data)
const post = (url, data, cfg) => http.post(url, data, cfg).then((r) => r.data)

export const api = {
  session: () => get('/api/session'),
  health: () => get('/api/health'),
  modules: () => get('/api/meta/modules').then((d) => d.modules),
  regions: () => get('/api/regions'),
  crops: () => get('/api/crops').then((d) => d.crops),
  calendar: (crop) => get(`/api/crops/${crop}/calendar`),
  searchLocations: (q) => get('/api/locations/search', { q }),
  nearestDistrict: (latitude, longitude) => get('/api/locations/nearest-district', { latitude, longitude }),
  current: (latitude, longitude) => get('/api/weather/current', { latitude, longitude }),
  forecast: (latitude, longitude, days = 7) => get('/api/weather/forecast', { latitude, longitude, days }),
  warnings: (district) => get('/api/warnings', { district }),
  assess: (body) => post('/api/risk/assess', body),
  getAssessment: (id, language) => get(`/api/risk/${id}`, { language }),
  advisory: (assessment_id, language, profile_id, question) => post('/api/advisory/generate', { assessment_id, language, profile_id, question }),
  chat: (body) => post('/api/assistant/chat', body),
  chatHistory: (conversationId) => get(`/api/assistant/conversations/${conversationId}`),
  history: (p) => get('/api/history', p),
  seasonal: (p) => get('/api/history/seasonal', p),
  knowledgeSearch: (p) => get('/api/knowledge/search', p),
  knowledgeDocs: (p) => get('/api/knowledge/documents', p),
  evidenceRegistry: (p) => get('/api/knowledge/evidence-registry', p),
  monitoring: () => get('/api/monitoring/status'),
  profileCreate: (b) => post('/api/profile', b),
  profileUpdate: (id, b) => http.put(`/api/profile/${id}`, b).then((r) => r.data),
  profileGet: (id) => get(`/api/profile/${id}`),
  profileDelete: (id) => http.delete(`/api/profile/${id}`).then((r) => r.data),
  market: (p) => get('/api/market/prices', p),
  marketOptions: (p) => get('/api/market/options', p),
  marketAdvice: (body) => post('/api/market/advice', body),
  analyzeImage: (form) => post('/api/crop-health/analyze', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  notifications: () => get('/api/notifications'),
  notificationPrefs: () => get('/api/notifications/preferences'),
  saveNotificationPrefs: (b) => post('/api/notifications/preferences', b),
  refreshNotifications: () => post('/api/notifications/refresh'),
  markRead: (id) => post(`/api/notifications/${id}/read`),
  satellite: (latitude, longitude) => get('/api/satellite/indicators', { latitude, longitude }),
  transcribe: (form) => post('/api/voice/transcribe', form, { headers: { 'Content-Type': 'multipart/form-data' } }),
  regional: (p) => get('/api/regional/risk', p),
  adminSummary: (p, token) => http.get('/api/admin/regional-summary', { params: p, headers: { Authorization: `Bearer ${token}` } }).then((r) => r.data),
  report: (body) => http.post('/api/reports/generate', body, { responseType: 'blob' }),
}

export default api
