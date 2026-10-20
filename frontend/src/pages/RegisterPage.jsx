import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, Eye, EyeOff, KeyRound, Mail, User, X } from 'lucide-react'
import { apiError, register } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/uiStore'
import { Logo } from '../components/Layout'
import { Alert, Button } from '../components/ui'
import AuthArt from './AuthArt'
import './public.css'

const RULES = [
  { key: 'len', label: 'At least 8 characters', test: (p) => p.length >= 8 },
  { key: 'upper', label: 'One uppercase letter', test: (p) => /[A-Z]/.test(p) },
  { key: 'digit', label: 'One number', test: (p) => /\d/.test(p) },
]
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/

export default function RegisterPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { setAuth } = useAuthStore()
  const [form, setForm] = useState({ full_name: '', email: '', password: '' })
  const [touched, setTouched] = useState({})
  const [show, setShow] = useState(false)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const passed = useMemo(() => RULES.map((r) => r.test(form.password)), [form.password])
  const score = passed.filter(Boolean).length
  const errors = {
    email: !form.email ? 'Email is required' : !EMAIL_RE.test(form.email) ? 'Enter a valid email address' : '',
    password: score < RULES.length ? 'Password does not meet the requirements' : '',
  }
  const valid = !errors.email && !errors.password
  const set = (k) => (e) => setForm((f) => ({ ...f, [k]: e.target.value }))
  const blur = (k) => () => setTouched((t) => ({ ...t, [k]: true }))

  const onSubmit = async (e) => {
    e.preventDefault()
    setTouched({ email: true, password: true })
    if (!valid) return
    setLoading(true)
    setError('')
    try {
      const data = await register({ ...form, full_name: form.full_name.trim() || undefined })
      qc.clear()
      setAuth(data.user, data.access_token, data.refresh_token)
      toast.success('Welcome to XithSense', 'Your free account is ready. Pick a match to build your first XI.')
      navigate('/matches', { replace: true })
    } catch (err) {
      const e2 = apiError(err)
      setError(e2.code === 'EMAIL_TAKEN' ? 'An account with this email already exists — try signing in.' : e2.message)
      setLoading(false)
    }
  }

  const strengthColor = ['var(--danger)', 'var(--danger)', 'var(--warning)', 'var(--success)'][score]

  return (
    <div className="auth">
      <div className="auth-form">
        <div className="fade-in">
          <Link to="/" className="show-mobile mb-24" style={{ display: 'inline-block' }}><Logo /></Link>
          <h1>Create your account</h1>
          <p className="mt-8">Free forever. Upgrade only if you want every strategy.</p>

          {error && <div className="mt-24"><Alert tone="danger" action={error.includes('signing in') ? <Link to="/login" className="bold small">Sign in</Link> : null}>{error}</Alert></div>}

          <form onSubmit={onSubmit} className="col gap-16 mt-24" noValidate>
            <div className="field">
              <label className="label" htmlFor="name">Full name <span className="muted">(optional)</span></label>
              <div className="input-wrap">
                <User size={16} />
                <input id="name" className="input" autoComplete="name" placeholder="Rahul Sharma" maxLength={200} value={form.full_name} onChange={set('full_name')} />
              </div>
            </div>
            <div className="field">
              <label className="label" htmlFor="email">Email</label>
              <div className="input-wrap">
                <Mail size={16} />
                <input id="email" className="input" type="email" autoComplete="email" placeholder="you@example.com" value={form.email}
                  onChange={set('email')} onBlur={blur('email')} aria-invalid={touched.email && !!errors.email}
                  style={touched.email && errors.email ? { borderColor: 'var(--danger)' } : undefined} />
              </div>
              {touched.email && errors.email && <span className="field-error">{errors.email}</span>}
            </div>
            <div className="field">
              <label className="label" htmlFor="password">Password</label>
              <div className="input-wrap">
                <KeyRound size={16} />
                <input id="password" className="input" type={show ? 'text' : 'password'} autoComplete="new-password" placeholder="Create a password"
                  value={form.password} onChange={set('password')} onBlur={blur('password')} style={{ paddingRight: 46, ...(touched.password && errors.password ? { borderColor: 'var(--danger)' } : {}) }} />
                <button type="button" className="input-action btn btn-ghost btn-icon btn-sm" onClick={() => setShow((s) => !s)} aria-label={show ? 'Hide password' : 'Show password'}>
                  {show ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
              <div className="pw-strength" aria-hidden>
                {RULES.map((_, i) => <span key={i} style={{ background: i < score ? strengthColor : undefined }} />)}
              </div>
              <ul className="pw-rules">
                {RULES.map((r, i) => (
                  <li key={r.key} className={passed[i] ? 'ok' : ''}>{passed[i] ? <Check size={13} /> : <X size={13} />}{r.label}</li>
                ))}
              </ul>
            </div>
            <Button type="submit" size="lg" block loading={loading}>Create free account <ArrowRight size={16} /></Button>
            <p className="xs muted text-center">By creating an account you agree to play responsibly. Projections are estimates, not guarantees.</p>
          </form>

          <p className="small text-center mt-24">
            Already have an account? <Link to="/login" className="text-primary bold">Sign in</Link>
          </p>
        </div>
      </div>
      <AuthArt quote="Four strategies, one match. Build the XI that fits your contest in seconds." />
    </div>
  )
}
