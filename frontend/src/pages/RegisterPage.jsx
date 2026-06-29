import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { register } from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function RegisterPage() {
  const navigate = useNavigate()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const data = await register(form)
      setAuth(data.user, data.access_token, data.refresh_token)
      navigate('/matches')
    } catch (err) {
      setError(err.response?.data?.detail?.message || 'Registration failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--sp-6)', background: 'var(--bg-base)', position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 50% 30%, rgba(99,102,241,0.15) 0%, transparent 60%)', pointerEvents: 'none' }} />
      <div style={{ width: '100%', maxWidth: 420, position: 'relative' }}>
        <div className="text-center mb-8">
          <Link to="/" className="nav-logo" style={{ justifyContent: 'center', marginBottom: 'var(--sp-4)' }}>
            <span style={{ fontSize: 40 }}>🏏</span>
            <span className="gradient-text" style={{ fontSize: 'var(--text-2xl)' }}>XithSense</span>
          </Link>
          <h1 style={{ fontSize: 'var(--text-xl)', marginBottom: 'var(--sp-2)' }}>Create your account</h1>
          <p style={{ color: 'var(--text-secondary)' }}>Start winning at fantasy cricket for free</p>
        </div>

        <div className="card">
          {error && (
            <div style={{ background: 'var(--color-danger-bg)', border: '1px solid var(--color-danger)', borderRadius: 'var(--radius-md)', padding: 'var(--sp-3)', marginBottom: 'var(--sp-4)', color: 'var(--color-danger)', fontSize: 'var(--text-sm)' }}>
              ⚠️ {error}
            </div>
          )}
          <form onSubmit={handleSubmit}>
            <div className="form-group mb-4">
              <label className="label">Full Name</label>
              <input className="input" type="text" placeholder="Rahul Sharma" value={form.full_name}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))} />
            </div>
            <div className="form-group mb-4">
              <label className="label">Email</label>
              <input className="input" type="email" placeholder="you@example.com" value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required />
            </div>
            <div className="form-group mb-6">
              <label className="label">Password</label>
              <input className="input" type="password" placeholder="Min 8 chars, 1 uppercase, 1 digit" value={form.password}
                onChange={e => setForm(f => ({ ...f, password: e.target.value }))} required />
            </div>
            <button type="submit" className="btn btn-primary w-full btn-lg glow-primary" disabled={loading}>
              {loading ? '⏳ Creating account...' : '🚀 Create Free Account'}
            </button>
          </form>
          <div className="divider" />
          <p style={{ textAlign: 'center', fontSize: 'var(--text-sm)', color: 'var(--text-secondary)' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--color-primary-light)', fontWeight: 600 }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
