import { useState } from 'react'
import { Link, useNavigate, useSearchParams } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Eye, EyeOff, KeyRound, Mail } from 'lucide-react'
import { apiError, login } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { Logo } from '../components/Layout'
import { Alert, Button } from '../components/ui'
import AuthArt from './AuthArt'
import './public.css'

export default function LoginPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [params] = useSearchParams()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ email: '', password: '' })
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(null) // 'form' while submitting

  const next = params.get('next')
  const destination = next && next.startsWith('/') && !next.startsWith('//') ? next : '/matches'

  const submit = async (creds, key = 'form') => {
    setLoading(key)
    setError('')
    try {
      const data = await login(creds)
      qc.clear()
      setAuth(data.user, data.access_token, data.refresh_token)
      navigate(destination, { replace: true })
    } catch (err) {
      setError(apiError(err).message)
      setLoading(null)
    }
  }

  const onSubmit = (e) => {
    e.preventDefault()
    submit(form)
  }

  return (
    <div className="auth">
      <div className="auth-form">
        <div className="fade-in">
          <Link to="/" className="show-mobile mb-24" style={{ display: 'inline-block' }}><Logo /></Link>
          <h1>Welcome back</h1>
          <p className="mt-8">Sign in to see today’s projections and build your XI.</p>

          <div className="col gap-16 mt-24">
            {params.get('expired') && <Alert tone="warning">Your session expired — please sign in again.</Alert>}
            {error && <Alert tone="danger">{error}</Alert>}
          </div>

          <form onSubmit={onSubmit} className="col gap-16 mt-16" noValidate>
            <div className="field">
              <label className="label" htmlFor="email">Email</label>
              <div className="input-wrap">
                <Mail size={16} />
                <input id="email" className="input" type="email" autoComplete="email" placeholder="you@example.com" required
                  value={form.email} onChange={(e) => setForm((f) => ({ ...f, email: e.target.value }))} />
              </div>
            </div>
            <div className="field">
              <label className="label" htmlFor="password">Password</label>
              <div className="input-wrap">
                <KeyRound size={16} />
                <input id="password" className="input" type={show ? 'text' : 'password'} autoComplete="current-password" placeholder="••••••••" required
                  value={form.password} onChange={(e) => setForm((f) => ({ ...f, password: e.target.value }))} style={{ paddingRight: 46 }} />
                <button type="button" className="input-action btn btn-ghost btn-icon btn-sm" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>
            <Button type="submit" size="lg" block loading={loading === 'form'} disabled={!form.email || !form.password || !!loading}>
              Sign in <ArrowRight size={16} />
            </Button>
          </form>

          <p className="small text-center mt-24">
            New to XithSense? <Link to="/register" className="text-primary bold">Create a free account</Link>
          </p>
        </div>
      </div>
      <AuthArt quote="Every pick comes with its reasons — form, venue, matchup and the rules that fired." />
    </div>
  )
}
