import { NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

const icons = { home: '🏠', matches: '🏏', chat: '💬', account: '👤' }

export default function BottomNav() {
  const { isPremium } = useAuthStore()
  return (
    <nav className="bottom-nav">
      <NavLink to="/matches" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
        <span style={{ fontSize: 20 }}>{icons.matches}</span>
        <span>Matches</span>
      </NavLink>
      <NavLink to="/chat" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
        <span style={{ fontSize: 20 }}>{icons.chat}</span>
        <span>AI Chat</span>
        {!isPremium() && <span style={{ fontSize: 8, color: 'var(--color-secondary)' }}>PRO</span>}
      </NavLink>
      <NavLink to="/account" className={({ isActive }) => `bottom-nav-item${isActive ? ' active' : ''}`}>
        <span style={{ fontSize: 20 }}>{icons.account}</span>
        <span>Account</span>
      </NavLink>
    </nav>
  )
}
