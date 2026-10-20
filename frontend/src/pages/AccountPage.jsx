import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bell, Calendar, Crown, KeyRound, LogOut, Mail, Moon, Palette, Phone, Send, ShieldCheck, Smartphone, Sun, User,
} from 'lucide-react'
import {
  apiError, cancelSubscription, changePassword, getMe, getNotificationPrefs, logoutApi, updateMe, updateNotificationPrefs,
} from '../api/client'
import { useAuthStore } from '../store/authStore'
import { toast, useUiStore } from '../store/uiStore'
import { Alert, Badge, Button, ButtonLink, Card, Modal, PageHead, ProBadge, Skeleton, Switch } from '../components/ui'
import { fmtDate } from '../lib/format'
import './public.css'

const PLAN_NAMES = { free: 'Free', premium_monthly: 'Premium Monthly', premium_annual: 'Premium Annual' }
const EVENTS = [
  ['EVT-01', 'Playing XI confirmed', 'When both line-ups are announced'],
  ['EVT-02', 'Toss result', 'Predictions refresh after the toss'],
  ['EVT-03', 'Injury alerts', 'A player in your team is ruled out'],
  ['EVT-05', 'Captain change', 'Our top captain pick changes'],
  ['EVT-07', 'Prediction ready', 'Teams are ready for a match you follow'],
]

function ProfileCard({ user }) {
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [form, setForm] = useState({ full_name: user?.full_name || '', phone: user?.phone || '' })
  useEffect(() => setForm({ full_name: user?.full_name || '', phone: user?.phone || '' }), [user?.full_name, user?.phone])
  const dirty = form.full_name !== (user?.full_name || '') || form.phone !== (user?.phone || '')
  const m = useMutation({
    mutationFn: () => updateMe({ full_name: form.full_name.trim() || null, phone: form.phone.trim() || null }),
    onSuccess: (u) => { setUser(u); qc.setQueryData(['me'], u); toast.success('Profile updated') },
    onError: (e) => toast.error('Could not update profile', apiError(e).message),
  })
  const premium = ['premium', 'admin'].includes(user?.role)
  return (
    <Card>
      <div className="profile-hero">
        <span className="avatar">{(user?.full_name || user?.email || '?')[0].toUpperCase()}</span>
        <div className="grow">
          <h2 className="truncate">{user?.full_name || 'Fantasy player'}</h2>
          <div className="secondary small truncate">{user?.email}</div>
          <div className="row wrap gap-6 mt-8">
            {premium ? <ProBadge /> : <Badge>Free plan</Badge>}
            {user?.role === 'admin' && <Badge tone="danger"><ShieldCheck size={11} />Admin</Badge>}
            {user?.is_verified && <Badge tone="success">Verified</Badge>}
          </div>
        </div>
      </div>
      <div className="divider" />
      <form className="col gap-16" onSubmit={(e) => { e.preventDefault(); m.mutate() }}>
        <div className="field">
          <label className="label" htmlFor="pname">Full name</label>
          <div className="input-wrap"><User size={16} /><input id="pname" className="input" maxLength={200} value={form.full_name} onChange={(e) => setForm((f) => ({ ...f, full_name: e.target.value }))} /></div>
        </div>
        <div className="field">
          <label className="label" htmlFor="pphone">Phone <span className="muted">(optional)</span></label>
          <div className="input-wrap"><Phone size={16} /><input id="pphone" className="input" maxLength={20} placeholder="+91 98765 43210" value={form.phone} onChange={(e) => setForm((f) => ({ ...f, phone: e.target.value }))} /></div>
        </div>
        <div className="row between wrap">
          <span className="row gap-6 small muted"><Calendar size={14} />Member since {fmtDate(user?.created_at, { month: 'long', year: 'numeric' })}</span>
          <Button type="submit" size="sm" loading={m.isPending} disabled={!dirty}>Save changes</Button>
        </div>
      </form>
    </Card>
  )
}

function SubscriptionCard({ user }) {
  const qc = useQueryClient()
  const setUser = useAuthStore((s) => s.setUser)
  const [confirm, setConfirm] = useState(false)
  const sub = user?.subscription
  const paid = sub && sub.plan !== 'free'
  const m = useMutation({
    mutationFn: () => cancelSubscription({ reason: 'user_requested' }),
    onSuccess: async () => {
      setConfirm(false)
      const me = await getMe().catch(() => null)
      if (me) { setUser(me); qc.setQueryData(['me'], me) }
      toast.success('Subscription cancelled', 'You keep Premium until the end of your current period.')
    },
    onError: (e) => toast.error('Could not cancel', apiError(e).message),
  })
  const end = sub?.current_period_end
  return (
    <Card title="Subscription" icon={Crown} subtitle="Your plan and billing">
      {!paid ? (
        <div className="col gap-16">
          <div className="card-elevated row between">
            <div><div className="bold">Free plan</div><div className="small muted">One Safe team per request · basic explanations</div></div>
            <Badge>Active</Badge>
          </div>
          <div className="upgrade-card" style={{ marginBottom: 0 }}>
            <div className="row gap-8 bold"><Crown size={16} className="text-captain" />Unlock every strategy</div>
            <p className="small mt-4">Grand League, Aggressive & Small League modes, differentials, AI chat and the live feed.</p>
            <ButtonLink to="/subscribe" variant="gold" size="sm" className="mt-12" icon={Crown}>See Premium plans</ButtonLink>
          </div>
        </div>
      ) : (
        <div className="col gap-12">
          <div className="card-elevated">
            <div className="row between">
              <div className="bold">{PLAN_NAMES[sub.plan] || sub.plan}</div>
              <Badge tone={sub.status === 'active' ? 'success' : sub.status === 'cancelled' ? 'warning' : 'gray'} style={{ textTransform: 'capitalize' }}>{sub.status}</Badge>
            </div>
            <div className="kv mt-8"><span>Started</span><span>{fmtDate(sub.current_period_start, { day: 'numeric', month: 'short', year: 'numeric' })}</span></div>
            <div className="kv"><span>{sub.status === 'cancelled' ? 'Access until' : 'Renews on'}</span><span>{end ? fmtDate(end, { day: 'numeric', month: 'short', year: 'numeric' }) : '—'}</span></div>
          </div>
          {sub.status === 'cancelled' && <Alert tone="info">Cancelled on {fmtDate(sub.cancelled_at)}. Premium stays active until {fmtDate(end)}.</Alert>}
          {sub.status === 'active' && user?.role !== 'admin' && (
            <div className="row between wrap">
              <span className="small muted">Need a break? You can cancel any time.</span>
              <Button variant="danger" size="sm" onClick={() => setConfirm(true)}>Cancel subscription</Button>
            </div>
          )}
        </div>
      )}
      <Modal open={confirm} onClose={() => !m.isPending && setConfirm(false)} title="Cancel Premium?" width={440}
        footer={<><Button variant="secondary" onClick={() => setConfirm(false)} disabled={m.isPending}>Keep Premium</Button><Button variant="danger" loading={m.isPending} onClick={() => m.mutate()}>Cancel subscription</Button></>}>
        <p>You’ll keep every Premium feature until <b style={{ color: 'var(--text)' }}>{fmtDate(end, { day: 'numeric', month: 'long', year: 'numeric' })}</b>. After that your account moves to the Free plan — no further charges.</p>
      </Modal>
    </Card>
  )
}

function NotificationsCard({ premium }) {
  const qc = useQueryClient()
  const { data, isLoading, isError } = useQuery({ queryKey: ['notification-prefs'], queryFn: getNotificationPrefs })
  const [prefs, setPrefs] = useState(null)
  useEffect(() => { if (data) setPrefs(data) }, [data])
  const m = useMutation({
    mutationFn: updateNotificationPrefs,
    onSuccess: (p) => { setPrefs(p); qc.setQueryData(['notification-prefs'], p) },
    onError: (e) => { setPrefs(data); toast.error('Could not save preferences', apiError(e).message) },
  })
  const save = (next) => { setPrefs(next); m.mutate(next) }
  const channels = [
    ['email_enabled', 'Email', 'Match alerts to your inbox', Mail, false],
    ['telegram_enabled', 'Telegram', 'Instant alerts via the XithSense bot', Send, true],
    ['push_enabled', 'Push', 'Browser & mobile push notifications', Smartphone, true],
  ]
  return (
    <Card title="Notifications" icon={Bell} subtitle="Choose how and when we alert you" actions={m.isPending && <span className="xs muted">Saving…</span>}>
      {isLoading || !prefs ? (
        isError ? <Alert tone="danger">Could not load preferences.</Alert> : <div className="col gap-12">{[0, 1, 2, 3].map((i) => <Skeleton key={i} h={40} />)}</div>
      ) : (
        <>
          <div className="upper muted mb-8">Channels</div>
          {channels.map(([key, label, desc, Icon, pro]) => {
            const locked = pro && !premium
            return (
              <div className="pref-row" key={key}>
                <div className="row grow"><span className="pref-icon"><Icon size={16} /></span><div className="grow"><div className="bold small row gap-6">{label}{locked && <ProBadge />}</div><div className="xs muted">{desc}</div></div></div>
                <Switch label={label} checked={!!prefs[key] && !locked} disabled={locked} onChange={(v) => save({ ...prefs, [key]: v })} />
              </div>
            )
          })}
          <div className="upper muted mb-8 mt-16">Events</div>
          {EVENTS.map(([id, label, desc]) => (
            <div className="pref-row" key={id}>
              <div className="grow"><div className="bold small">{label}</div><div className="xs muted">{desc}</div></div>
              <Switch label={label} checked={prefs.events?.[id] ?? false} onChange={(v) => save({ ...prefs, events: { ...(prefs.events || {}), [id]: v } })} />
            </div>
          ))}
        </>
      )}
    </Card>
  )
}

function AppearanceCard() {
  const { theme, setTheme } = useUiStore()
  return (
    <Card title="Appearance" icon={Palette} subtitle="Pick the look that suits your screen">
      <div className="theme-options">
        {[['dark', 'Dark', Moon, '#0b1020'], ['light', 'Light', Sun, '#f4f6fb']].map(([v, label, Icon, sw]) => (
          <button key={v} className={`theme-opt${theme === v ? ' active' : ''}`} onClick={() => setTheme(v)} aria-pressed={theme === v}>
            <span className="theme-swatch" style={{ background: sw }} /><Icon size={15} />{label}
          </button>
        ))}
      </div>
    </Card>
  )
}

function SecurityCard() {
  const [f, setF] = useState({ current_password: '', new_password: '', confirm: '' })
  const [err, setErr] = useState('')
  const rules = [f.new_password.length >= 8, /[A-Z]/.test(f.new_password), /\d/.test(f.new_password)]
  const m = useMutation({
    mutationFn: () => changePassword({ current_password: f.current_password, new_password: f.new_password }),
    onSuccess: () => { setF({ current_password: '', new_password: '', confirm: '' }); toast.success('Password changed') },
    onError: (e) => setErr(apiError(e).message),
  })
  const submit = (e) => {
    e.preventDefault()
    setErr('')
    if (!rules.every(Boolean)) return setErr('New password needs 8+ characters, an uppercase letter and a number.')
    if (f.new_password !== f.confirm) return setErr('New passwords do not match.')
    m.mutate()
  }
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  return (
    <Card title="Security" icon={KeyRound} subtitle="Change your password">
      <form className="col gap-12" onSubmit={submit}>
        {err && <Alert tone="danger">{err}</Alert>}
        <div className="field"><label className="label" htmlFor="cp">Current password</label><input id="cp" className="input" type="password" autoComplete="current-password" value={f.current_password} onChange={set('current_password')} /></div>
        <div className="grid-2" style={{ gap: 12 }}>
          <div className="field"><label className="label" htmlFor="np">New password</label><input id="np" className="input" type="password" autoComplete="new-password" value={f.new_password} onChange={set('new_password')} /></div>
          <div className="field"><label className="label" htmlFor="np2">Confirm</label><input id="np2" className="input" type="password" autoComplete="new-password" value={f.confirm} onChange={set('confirm')} /></div>
        </div>
        <div className="row between wrap">
          <span className="xs muted">8+ characters, one uppercase letter, one number</span>
          <Button type="submit" size="sm" variant="secondary" loading={m.isPending} disabled={!f.current_password || !f.new_password}>Update password</Button>
        </div>
      </form>
    </Card>
  )
}

export default function AccountPage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user, logout, refreshToken, isPremium } = useAuthStore()
  const [signingOut, setSigningOut] = useState(false)
  const signOut = async () => {
    setSigningOut(true)
    await logoutApi(refreshToken)
    logout()
    qc.clear()
    window.location.assign('/')
  }
  return (
    <div className="fade-in">
      <PageHead title="Account" subtitle="Profile, subscription and preferences"
        actions={<Button variant="secondary" icon={LogOut} loading={signingOut} onClick={signOut}>Sign out</Button>} />
      <div className="account-grid">
        <div className="col gap-16" style={{ gap: 18 }}>
          <ProfileCard user={user} />
          <SubscriptionCard user={user} />
          <SecurityCard />
        </div>
        <div className="col" style={{ gap: 18 }}>
          <NotificationsCard premium={isPremium()} />
          <AppearanceCard />
        </div>
      </div>
    </div>
  )
}
