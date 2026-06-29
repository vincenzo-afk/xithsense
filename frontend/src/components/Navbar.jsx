import { Link, NavLink } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'

export default function Navbar() {
  const { user, logout, isPremium } = useAuthStore()

  return (
    <nav className="navbar">
      <Link to="/matches" className="nav-logo">
        <span style={{ fontSize: 28 }}>🏏</span>
        <span className="gradient-text">XithSense</span>
      </Link>

      <div className="nav-links">
        <NavLink to="/matches" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          Matches
        </NavLink>
        {isPremium() && (
          <NavLink to="/chat" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            AI Chat
          </NavLink>
        )}
        {user?.role === 'admin' && (
          <NavLink to="/admin" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
            Admin
          </NavLink>
        )}
        {!isPremium() && (
          <Link to="/subscribe" className="btn btn-secondary btn-sm" style={{ marginRight: 4 }}>
            ⚡ Upgrade
          </Link>
        )}
        <NavLink to="/account" className={({ isActive }) => `nav-link${isActive ? ' active' : ''}`}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 13, fontWeight: 700
            }}>
              {user?.full_name?.[0] || user?.email?.[0]?.toUpperCase() || 'U'}
            </div>
            {isPremium() && <span className="badge badge-premium">PRO</span>}
          </div>
        </NavLink>
      </div>
    </nav>
  )
}
