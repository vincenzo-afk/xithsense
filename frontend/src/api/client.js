import axios from 'axios'
import { useAuthStore } from '../store/authStore'

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
})

// Attach token on every request
api.interceptors.request.use((config) => {
  const token = useAuthStore.getState().token
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      useAuthStore.getState().logout()
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ──────────────────────────────────────────────────────────────
export const register = (data) => api.post('/auth/register', data).then(r => r.data)
export const login = (data) => api.post('/auth/login', data).then(r => r.data)
export const getMe = () => api.get('/auth/me').then(r => r.data)

// ── Matches ───────────────────────────────────────────────────────────
export const getUpcomingMatches = (params) => api.get('/matches/upcoming', { params }).then(r => r.data)
export const getMatch = (matchId) => api.get(`/matches/${matchId}`).then(r => r.data)

// ── Players ───────────────────────────────────────────────────────────
export const searchPlayers = (params) => api.get('/players/search', { params }).then(r => r.data)
export const getPlayer = (playerId) => api.get(`/players/${playerId}`).then(r => r.data)
export const getPlayerMatchups = (playerId) => api.get(`/players/${playerId}/matchups`).then(r => r.data)

// ── Predictions ────────────────────────────────────────────────────────
export const predictTeam = (data) => api.post('/predict/team', data).then(r => r.data)
export const predictCaptain = (data) => api.post('/predict/captain', data).then(r => r.data)
export const getDifferentials = (matchId) => api.get(`/predict/differentials/${matchId}`).then(r => r.data)
export const explainPlayer = (matchId, playerId) => api.get(`/predict/explain/${matchId}/${playerId}`).then(r => r.data)

// ── Chat ──────────────────────────────────────────────────────────────
export const sendChat = (data) => api.post('/chat', data).then(r => r.data)

// ── Admin ─────────────────────────────────────────────────────────────
export const getAdminMetrics = () => api.get('/admin/metrics').then(r => r.data)
export const triggerIngest = (data) => api.post('/admin/ingest', data).then(r => r.data)
export const triggerRetrain = (data) => api.post('/admin/retrain', data).then(r => r.data)
export const createRule = (data) => api.post('/admin/rules', data).then(r => r.data)

// ── Payments ──────────────────────────────────────────────────────────
export const createSubscription = (data) => api.post('/payments/create-subscription', data).then(r => r.data)

export default api
