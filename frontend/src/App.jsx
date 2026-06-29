import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from './store/authStore'
import Navbar from './components/Navbar'
import BottomNav from './components/BottomNav'
import LandingPage from './pages/LandingPage'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import MatchListPage from './pages/MatchListPage'
import MatchDetailPage from './pages/MatchDetailPage'
import LivePage from './pages/LivePage'
import PlayerPage from './pages/PlayerPage'
import ChatPage from './pages/ChatPage'
import AccountPage from './pages/AccountPage'
import SubscribePage from './pages/SubscribePage'
import AdminPage from './pages/AdminPage'
import NotFoundPage from './pages/NotFoundPage'

function ProtectedRoute({ children, plan = 'free' }) {
  const { user } = useAuthStore()
  if (!user) return <Navigate to="/login" replace />
  if (plan === 'premium' && user.role !== 'premium' && user.role !== 'admin')
    return <Navigate to="/subscribe" replace />
  if (plan === 'admin' && user.role !== 'admin')
    return <Navigate to="/matches" replace />
  return children
}

export default function App() {
  const { user } = useAuthStore()
  const isPublicPage = !user

  return (
    <div className="app">
      {user && <Navbar />}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/matches" element={<ProtectedRoute><MatchListPage /></ProtectedRoute>} />
        <Route path="/matches/:matchId" element={<ProtectedRoute><MatchDetailPage /></ProtectedRoute>} />
        <Route path="/matches/:matchId/live" element={<ProtectedRoute plan="premium"><LivePage /></ProtectedRoute>} />
        <Route path="/players/:playerId" element={<ProtectedRoute><PlayerPage /></ProtectedRoute>} />
        <Route path="/chat" element={<ProtectedRoute plan="premium"><ChatPage /></ProtectedRoute>} />
        <Route path="/account" element={<ProtectedRoute><AccountPage /></ProtectedRoute>} />
        <Route path="/subscribe" element={<ProtectedRoute><SubscribePage /></ProtectedRoute>} />
        <Route path="/admin" element={<ProtectedRoute plan="admin"><AdminPage /></ProtectedRoute>} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
      {user && <BottomNav />}
    </div>
  )
}
