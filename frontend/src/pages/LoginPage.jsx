import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { login } from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await login(form)
      setAuth(data.user, data.access_token, data.refresh_token)
      navigate('/matches')
    } catch (err) {
      setError(err.response?.data?.detail?.message || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--sp-6)', background: 'var(--bg-base)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 50%, rgba(99,102,241,0.15) 0%, transparent 60%)', pointerEvents: 'none' }} />
      <div style={{ width: '100%', maxWidth: 420, position: 'relative' }}>
        <div className="text-center mb-8">
          <Link to="/" className="nav-logo" style={{ justifyContent: 'center', marginBottom: 'var(--sp-4)' }}>
            <span style={{ fontSize: 40 }}>🏏</span>
            <span className="gradient-text" style={{ fontSize: 'var(--text-2xl)' }}>XithSense</span>
          </Link>
          <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--sp-2)' }}>Welcome back</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Sign in to your account</p>
        </div>

        <div className="card">
          {error && (
            <div style={{ background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger)', borderRadius: 'var(--radius-md)', padding: 'var(--sp-3)', marginBottom: 'var(--sp-4)', color: 'var(--color-danger)', fontSize: 'var(--text-sm)' }}>
              ⚠️ {error}
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="form-group mb-4">
              <label className="label">Email</label>
              <input className="input" type="email" placeholder="you@example.com" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div className="form-group mb-6">
              <label className="label">Password</label>
              <input className="input" type="password" placeholder="••••••••" value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
            </div>
            <button type="submit" className="btn btn-primary w-full btn-lg" disabled={loading}>
              {loading ? '⏳ Signing in...' : '🚀 Sign In'}
            </button>
          </form>
          <div className="divider" />
          <p style={{ textAlign: 'center', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'var(--color-primary-light)', fontWeight: 600 }}>Create one free</Link>
          </p>
        </div>

        {/* Demo login hint */}
        <div style={{ marginTop: 'var(--sp-4)', padding: 'var(--sp-3)', background: 'rgba(99,102,241,0.1)', borderRadius: 'var(--radius-md)', border: '1px solid rgba(99,102,241,0.2)', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', textAlign: 'center' }}>
          💡 Demo: Register a new account to explore the platform
        </div>
      </div>
    </div>
  )
}
