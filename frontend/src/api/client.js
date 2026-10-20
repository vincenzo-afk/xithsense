import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({ baseURL: '/api/v1', headers: { 'Content-Type': 'application/json' } })

api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Transparent access-token refresh (single in-flight refresh shared by all callers)
let refreshing = null
api.interceptors.response.use(
  (res) => res,
  async (err) => {
    const original = err.config
    const status = err.response?.status
    const code = err.response?.data?.error?.code
    const { refreshToken, logout, setAuth } = useAuthStore.getState()
    if (status === 401 && refreshToken && !original._retry && !original.url?.includes('/auth/')) {
      original._retry = true
      try {
        refreshing = refreshing || axios.post('/api/v1/auth/refresh', { refresh_token: refreshToken })
        const { data } = await refreshing
        setAuth(data.user, data.access_token, data.refresh_token)
        original.headers.Authorization = `Bearer ${data.access_token}`
        return api(original)
      } catch {
        logout()
        window.location.assign('/login?expired=1')
      } finally {
        refreshing = null
      }
    } else if (status === 401 && code !== 'INVALID_CREDENTIALS' && !original.url?.includes('/auth/login')) {
      logout()
      window.location.assign('/login?expired=1')
    }
    return Promise.reject(err)
  },
)

/** Human-readable message + code from an API error. */
export function apiError(err) {
  const e = err?.response?.data?.error
  return {
    code: e?.code || (err?.response ? 'HTTP_ERROR' : 'NETWORK_ERROR'),
    message: e?.message || (err?.response ? 'Something went wrong' : 'Cannot reach the XithSense API — is the backend running?'),
    status: err?.response?.status,
    details: e?.details || {},
  }
}

const d = (r) => r.data

// ── Auth ──────────────────────────────────────────────────────────────
export const register = (body) => api.post('/auth/register', body).then(d)
export const login = (body) => api.post('/auth/login', body).then(d)
export const logoutApi = (refresh_token) => api.post('/auth/logout', refresh_token ? { refresh_token } : null).catch(() => {})
export const getMe = () => api.get('/auth/me').then(d)
export const updateMe = (body) => api.patch('/auth/me', body).then(d)
export const changePassword = (body) => api.post('/auth/change-password', body).then(d)

// ── Matches ───────────────────────────────────────────────────────────
export const getUpcomingMatches = (params) => api.get('/matches/upcoming', { params }).then(d)
export const getRecentMatches = (params) => api.get('/matches/recent', { params }).then(d)
export const getMatch = (matchId) => api.get(`/matches/${matchId}`).then(d)

// ── Players ───────────────────────────────────────────────────────────
export const searchPlayers = (params) => api.get('/players/search', { params }).then(d)
export const getPlayer = (playerId) => api.get(`/players/${playerId}`).then(d)
export const getPlayerMatchups = (playerId) => api.get(`/players/${playerId}/matchups`).then(d)

// ── Predictions ───────────────────────────────────────────────────────
export const predictTeam = (body) => api.post('/predict/team', body).then(d)
export const predictPortfolio = (match_id) => api.post('/predict/team/portfolio', { match_id }).then(d)
export const predictCaptain = (body) => api.post('/predict/captain', body).then(d)
export const getDifferentials = (matchId) => api.get(`/predict/differentials/${matchId}`).then(d)
export const explainPlayer = (matchId, playerId) => api.get(`/explain/${matchId}/${playerId}`).then(d)

// ── Chat ──────────────────────────────────────────────────────────────
export const sendChat = (body) => api.post('/chat', body).then(d)
export const getChatSessions = () => api.get('/chat/sessions').then(d)
export const getChatMessages = (id) => api.get(`/chat/sessions/${id}`).then(d)
export const deleteChatSession = (id) => api.delete(`/chat/sessions/${id}`).then(d)

// ── Notifications ─────────────────────────────────────────────────────
export const getNotifications = () => api.get('/notifications').then(d)
export const markNotificationsRead = () => api.post('/notifications/read').then(d)
export const getNotificationPrefs = () => api.get('/notifications/preferences').then(d)
export const updateNotificationPrefs = (body) => api.patch('/notifications/preferences', body).then(d)

// ── Payments ──────────────────────────────────────────────────────────
export const createSubscription = (body) => api.post('/payments/create-subscription', body).then(d)
export const verifyPayment = (body) => api.post('/payments/verify', body).then(d)
export const getPaymentStatus = () => api.get('/payments/status').then(d)
export const cancelSubscription = (body) => api.post('/payments/cancel', body || {}).then(d)

// ── Admin ─────────────────────────────────────────────────────────────
export const getAdminMetrics = () => api.get('/admin/metrics').then(d)
export const triggerIngest = (body) => api.post('/admin/ingest', body).then(d)
export const triggerFeatures = () => api.post('/admin/features/rebuild').then(d)
export const triggerRetrain = (body) => api.post('/admin/retrain', body).then(d)
export const triggerBacktest = (body) => api.post('/admin/backtest', body).then(d)
export const getJobs = () => api.get('/admin/jobs').then(d)
export const getModels = () => api.get('/admin/models').then(d)
export const activateModel = (id) => api.post(`/admin/models/${id}/activate`).then(d)
export const getBacktests = () => api.get('/admin/backtests').then(d)
export const getBacktest = (id) => api.get(`/admin/backtests/${id}`).then(d)
export const getRules = (params) => api.get('/admin/rules', { params }).then(d)
export const createRule = (body) => api.post('/admin/rules', body).then(d)
export const updateRule = (id, body) => api.patch(`/admin/rules/${id}`, body).then(d)
export const deleteRule = (id) => api.delete(`/admin/rules/${id}`).then(d)
export const getUsers = (params) => api.get('/admin/users', { params }).then(d)
export const setUserRole = (id, role) => api.patch(`/admin/users/${id}/role`, { role }).then(d)
export const updateMatchAdmin = (id, body) => api.patch(`/admin/matches/${id}`, body).then(d)
export const getAuditLog = (params) => api.get('/admin/audit', { params }).then(d)

// ── Live data (CricketData) ───────────────────────────────────────────
export const getLiveData = () => api.get('/admin/live-data').then(d)
export const getSeries = () => api.get('/admin/live-data/series').then(d)
export const setPinnedSeries = (ids) => api.put('/admin/live-data/pinned', { ids }).then(d)
export const syncFixtures = (refresh = false) => api.post('/admin/fixtures/sync', null, { params: { refresh } }).then(d)
export const createFixture = (body) => api.post('/admin/fixtures', body).then(d)
export const rebuildSquad = (id, official = false) => api.post(`/admin/matches/${id}/squad`, null, { params: { official } }).then(d)

/** WebSocket URL for the live feed (token passed as query param per WEBSOCKET_SPEC). */
export function liveSocketUrl(matchId) {
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const token = useAuthStore.getState().token
  return `${proto}//${window.location.host}/api/v1/live/${matchId}?token=${encodeURIComponent(token || '')}`
}

export default api
