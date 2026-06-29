import { useAuthStore } from '../store/authStore'
import { Link, useNavigate } from 'react-router-dom'

export default function AccountPage() {
  const { user, logout, isPremium } = useAuthStore()
  const navigate = useNavigate()

  const handleLogout = () => { logout(); navigate('/') }

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 600 }}>
        <h1 className="page-title">Account</h1>

        {/* Profile Card */}
        <div className="card mb-6">
          <div className="flex items-center gap-4 mb-6">
            <div style={{
              width: 72, height: 72, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 32, fontWeight: 700, flexShrink: 0,
            }}>
              {user?.full_name?.[0] || user?.email?.[0]?.toUpperCase()}
            </div>
            <div>
              <h2>{user?.full_name || 'User'}</h2>
              <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>{user?.email}</div>
              <div style={{ marginTop: 6, display: 'flex', gap: 8 }}>
                {isPremium() ? (
                  <span className="badge badge-premium">⚡ Premium</span>
                ) : (
                  <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>Free Plan</span>
                )}
                {user?.is_verified && <span className="badge badge-success">✓ Verified</span>}
              </div>
            </div>
          </div>

          <div className="divider" />

          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
            <div className="flex justify-between items-center">
              <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>Role</span>
              <span style={{ fontWeight: 600, textTransform: 'capitalize' }}>{user?.role}</span>
            </div>
            <div className="flex justify-between items-center">
              <span style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>Member since</span>
              <span style={{ fontWeight: 600 }}>
                {user?.created_at ? new Date(user.created_at).toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : 'N/A'}
              </span>
            </div>
          </div>
        </div>

        {/* Subscription */}
        {!isPremium() && (
          <div className="card mb-6" style={{ border: '1px solid var(--color-primary)', background: 'linear-gradient(135deg, rgba(99,102,241,0.1), rgba(245,158,11,0.05))' }}>
            <h3 style={{ marginBottom: 'var(--sp-2)' }}>⚡ Upgrade to Premium</h3>
            <p style={{ fontSize: 'var(--text-sm)', marginBottom: 'var(--sp-4)' }}>
              Get unlimited teams, all 4 modes, Grand League differentials, AI chat, and live match intelligence.
            </p>
            <Link to="/subscribe" className="btn btn-primary">
              🚀 Upgrade for ₹299/month
            </Link>
          </div>
        )}

        {/* Actions */}
        <div className="card">
          <h3 style={{ marginBottom: 'var(--sp-4)' }}>Account Actions</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-3)' }}>
            <button className="btn btn-secondary w-full" style={{ justifyContent: 'flex-start' }}>
              🔑 Change Password
            </button>
            <button className="btn btn-secondary w-full" style={{ justifyContent: 'flex-start' }}>
              🔔 Notification Settings
            </button>
            <div className="divider" />
            <button className="btn btn-danger w-full" onClick={handleLogout}>
              🚪 Sign Out
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
