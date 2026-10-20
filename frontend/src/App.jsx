import { lazy, Suspense, useEffect } from 'react'
import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getMe } from './api/client'
import { useAuthStore } from './store/authStore'
import { useUiStore } from './store/uiStore'
import Layout from './components/Layout'
import { PageLoader, Toasts, UpgradeModal } from './components/ui'

const LandingPage = lazy(() => import('./pages/LandingPage'))
const LoginPage = lazy(() => import('./pages/LoginPage'))
const RegisterPage = lazy(() => import('./pages/RegisterPage'))
const MatchListPage = lazy(() => import('./pages/MatchListPage'))
const MatchDetailPage = lazy(() => import('./pages/MatchDetailPage'))
const LivePage = lazy(() => import('./pages/LivePage'))
const PlayerPage = lazy(() => import('./pages/PlayerPage'))
const ChatPage = lazy(() => import('./pages/ChatPage'))
const AccountPage = lazy(() => import('./pages/AccountPage'))
const SubscribePage = lazy(() => import('./pages/SubscribePage'))
const AdminPage = lazy(() => import('./pages/AdminPage'))
const NotFoundPage = lazy(() => import('./pages/NotFoundPage'))

function Protected({ children, plan = 'free' }) {
  const { user, token } = useAuthStore()
  const location = useLocation()
  if (!user || !token) return <Navigate to={`/login?next=${encodeURIComponent(location.pathname)}`} replace />
  if (plan === 'premium' && !['premium', 'admin'].includes(user.role)) return <Navigate to="/subscribe" replace state={{ from: location.pathname }} />
  if (plan === 'admin' && user.role !== 'admin') return <Navigate to="/matches" replace />
  return children
}

function PublicOnly({ children }) {
  const { user } = useAuthStore()
  return user ? <Navigate to="/matches" replace /> : children
}

/** Keep the cached user (role, subscription) fresh after upgrades or admin changes. */
function SessionSync() {
  const { token, setUser } = useAuthStore()
  const { data } = useQuery({ queryKey: ['me'], queryFn: getMe, enabled: !!token, staleTime: 60_000, retry: false })
  useEffect(() => { if (data) setUser(data) }, [data, setUser])
  return null
}

export default function App() {
  const theme = useUiStore((s) => s.theme)
  useEffect(() => { document.documentElement.dataset.theme = theme }, [theme])

  return (
    <>
      <SessionSync />
      <Suspense fallback={<PageLoader />}>
        <Routes>
          <Route path="/" element={<PublicOnly><LandingPage /></PublicOnly>} />
          <Route path="/login" element={<PublicOnly><LoginPage /></PublicOnly>} />
          <Route path="/register" element={<PublicOnly><RegisterPage /></PublicOnly>} />
          <Route element={<Protected><Layout /></Protected>}>
            <Route path="/matches" element={<MatchListPage />} />
            <Route path="/matches/:matchId" element={<MatchDetailPage />} />
            <Route path="/matches/:matchId/live" element={<Protected plan="premium"><LivePage /></Protected>} />
            <Route path="/players/:playerId" element={<PlayerPage />} />
            <Route path="/chat" element={<Protected plan="premium"><ChatPage /></Protected>} />
            <Route path="/account" element={<AccountPage />} />
            <Route path="/subscribe" element={<SubscribePage />} />
            <Route path="/admin" element={<Protected plan="admin"><AdminPage /></Protected>} />
          </Route>
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </Suspense>
      <Toasts />
      <UpgradeModal />
    </>
  )
}
