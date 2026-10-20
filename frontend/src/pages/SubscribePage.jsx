import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { ArrowRight, Check, CreditCard, Crown, Lock, ShieldCheck, Sparkles, X, Zap } from 'lucide-react'
import { apiError, createSubscription, getMe, verifyPayment } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { toast } from '../store/uiStore'
import { Alert, Badge, Button, ButtonLink, Card, Modal, PageHead } from '../components/ui'
import { fmtDate } from '../lib/format'
import './public.css'

const PLANS = {
  premium_monthly: { id: 'premium_monthly', name: 'Premium Monthly', price: 299, period: 'month', perMonth: 299, note: 'Billed monthly · cancel any time' },
  premium_annual: { id: 'premium_annual', name: 'Premium Annual', price: 2499, period: 'year', perMonth: 208, note: 'Billed yearly · two months free' },
}

const COMPARE = [
  ['Safe-mode team', '1 per request', 'Up to 20 per match'],
  ['Grand League, Aggressive, Small League modes', false, true],
  ['4-mode portfolio in one click', false, true],
  ['Captain & vice-captain recommendations', true, true],
  ['Player explanations', 'Basic · 5 per match', 'Full, with analyst rules'],
  ['Differentials & ownership estimates', false, true],
  ['AI chat assistant', false, true],
  ['Live match intelligence feed', false, true],
  ['Telegram & push alerts', false, true],
]

const CONFETTI = Array.from({ length: 28 }, (_, i) => {
  const angle = (i / 28) * Math.PI * 2
  const dist = 90 + (i % 5) * 22
  return {
    x: `${Math.cos(angle) * dist}px`, y: `${Math.sin(angle) * dist}px`, r: `${(i * 47) % 360}deg`,
    bg: ['#6366f1', '#f59e0b', '#10b981', '#a78bfa', '#f87171', '#22d3ee'][i % 6], delay: `${(i % 7) * 30}ms`,
  }
})

function loadRazorpay() {
  return new Promise((resolve, reject) => {
    if (window.Razorpay) return resolve(window.Razorpay)
    const s = document.createElement('script')
    s.src = 'https://checkout.razorpay.com/v1/checkout.js'
    s.onload = () => resolve(window.Razorpay)
    s.onerror = () => reject(new Error('Could not load Razorpay checkout'))
    document.body.appendChild(s)
  })
}

function Cell({ v }) {
  if (v === true) return <Check size={17} className="text-success" style={{ margin: '0 auto' }} />
  if (v === false) return <X size={16} className="muted" style={{ margin: '0 auto' }} />
  return <span className="small secondary">{v}</span>
}

export default function SubscribePage() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { user, setUser, isPremium } = useAuthStore()
  const [plan, setPlan] = useState('premium_annual')
  const [order, setOrder] = useState(null)        // simulated order
  const [stage, setStage] = useState('idle')      // idle | creating | review | paying | success
  const [error, setError] = useState('')
  const timer = useRef(null)
  useEffect(() => () => clearTimeout(timer.current), [])

  const finish = async () => {
    setStage('success')
    try {
      const me = await getMe()
      setUser(me)
    } catch { /* SessionSync will refresh */ }
    qc.invalidateQueries({ queryKey: ['me'] })
    timer.current = setTimeout(() => navigate('/matches'), 2600)
  }

  const start = async () => {
    setError('')
    setStage('creating')
    try {
      const o = await createSubscription({ plan })
      if (o.checkout_mode === 'simulated') {
        setOrder(o)
        setStage('review')
        return
      }
      const Razorpay = await loadRazorpay()
      setStage('idle')
      const rzp = new Razorpay({
        key: o.razorpay_key_id, order_id: o.order_id, amount: o.amount, currency: o.currency,
        name: 'XithSense', description: PLANS[plan].name,
        prefill: { email: user?.email, name: user?.full_name || '' }, theme: { color: '#6366f1' },
        handler: async (resp) => {
          setOrder(o)
          setStage('paying')
          try {
            await verifyPayment({ order_id: resp.razorpay_order_id, payment_id: resp.razorpay_payment_id, signature: resp.razorpay_signature, plan })
            await finish()
          } catch (err) {
            setStage('review')
            setError(apiError(err).message)
          }
        },
      })
      rzp.on('payment.failed', (r) => toast.error('Payment failed', r?.error?.description))
      rzp.open()
    } catch (err) {
      setStage('idle')
      const e = apiError(err)
      toast.error('Checkout unavailable', e.message)
    }
  }

  const pay = async () => {
    setError('')
    setStage('paying')
    try {
      await verifyPayment({ order_id: order.order_id, plan })
      await finish()
    } catch (err) {
      setStage('review')
      setError(apiError(err).message)
    }
  }

  const closeModal = () => {
    if (stage === 'paying') return
    if (stage === 'success') { navigate('/matches'); return }
    setStage('idle')
    setOrder(null)
  }

  if (isPremium() && stage !== 'success') {
    const sub = user?.subscription
    return (
      <div className="fade-in" style={{ maxWidth: 640, margin: '0 auto' }}>
        <Card className="text-center" style={{ padding: '44px 28px', background: 'radial-gradient(80% 100% at 50% 0%, rgba(245,158,11,.16), transparent 70%), var(--bg-surface)' }}>
          <div className="col" style={{ alignItems: 'center', gap: 14 }}>
            <div className="brand-mark" style={{ width: 60, height: 60, borderRadius: 18 }}><Crown size={28} /></div>
            <h1>You’re Premium</h1>
            <p style={{ maxWidth: 440 }}>Every mode, differentials, AI chat and the live feed are unlocked. {user?.role === 'admin' && 'Admin accounts always include Premium.'}</p>
            {sub && sub.plan !== 'free' && (
              <div className="row wrap center gap-8">
                <Badge tone="primary" size="lg">{PLANS[sub.plan]?.name || sub.plan}</Badge>
                <Badge tone={sub.status === 'active' ? 'success' : 'warning'} size="lg" style={{ textTransform: 'capitalize' }}>{sub.status}</Badge>
                {sub.current_period_end && <Badge size="lg">{sub.status === 'cancelled' ? 'Ends' : 'Renews'} {fmtDate(sub.current_period_end, { day: 'numeric', month: 'short', year: 'numeric' })}</Badge>}
              </div>
            )}
            <div className="row wrap center mt-8">
              <ButtonLink to="/matches" icon={Zap}>Build a team</ButtonLink>
              <ButtonLink to="/account" variant="secondary">Manage subscription</ButtonLink>
            </div>
          </div>
        </Card>
      </div>
    )
  }

  const selected = PLANS[plan]

  return (
    <div className="fade-in">
      <PageHead eyebrow={<><Crown size={14} />XithSense Premium</>} title="Unlock every strategy"
        subtitle="All four team modes, differentials, AI chat and the live feed — for every match." />

      <div className="text-center mb-24">
        <div className="billing-toggle" role="tablist" aria-label="Billing period">
          <button className={plan === 'premium_monthly' ? 'active' : ''} onClick={() => setPlan('premium_monthly')}>Monthly</button>
          <button className={plan === 'premium_annual' ? 'active' : ''} onClick={() => setPlan('premium_annual')}>Annual <Badge tone="success">−30%</Badge></button>
        </div>
      </div>

      <div className="plans">
        {Object.values(PLANS).map((p) => {
          const on = plan === p.id
          return (
            <div key={p.id} role="radio" aria-checked={on} tabIndex={0} className={`price-card plan-card${on ? ' selected featured' : ''}`}
              onClick={() => setPlan(p.id)} onKeyDown={(e) => (e.key === 'Enter' || e.key === ' ') && (e.preventDefault(), setPlan(p.id))}>
              {p.id === 'premium_annual' && <span className="ribbon badge badge-pro badge-lg" style={{ position: 'absolute', top: -12, left: '50%', transform: 'translateX(-50%)' }}><Sparkles size={12} />Best value</span>}
              <div className="row between">
                <h3>{p.name}</h3>
                <span className={`radio-dot${on ? ' on' : ''}`} />
              </div>
              <div>
                <div className="price">₹{p.price.toLocaleString('en-IN')} <small>/ {p.period}</small></div>
                <div className="small secondary mt-4">{p.id === 'premium_annual' ? `≈ ₹${p.perMonth}/month · save ₹${(299 * 12 - 2499).toLocaleString('en-IN')} a year` : p.note}</div>
              </div>
              <ul className="check-list">
                {['All 4 team modes', 'Up to 20 teams per match', 'Differentials & ownership', 'AI chat assistant', 'Live match feed', 'Full explanations'].map((f) => (
                  <li key={f}><Check size={16} className="text-success" />{f}</li>
                ))}
              </ul>
            </div>
          )
        })}
      </div>

      <div className="text-center mt-24 col" style={{ alignItems: 'center', gap: 10 }}>
        <Button variant="gold" size="lg" icon={Crown} loading={stage === 'creating'} onClick={start} style={{ minWidth: 280 }}>
          Continue with {selected.name} · ₹{selected.price.toLocaleString('en-IN')}
        </Button>
        <span className="row gap-6 xs muted"><Lock size={12} />Secure checkout via Razorpay · cancel any time</span>
      </div>

      <div className="section-title"><h3>Free vs Premium</h3></div>
      <div className="table-wrap">
        <table className="table compare">
          <thead><tr><th>Feature</th><th>Free</th><th><span className="text-captain">Premium</span></th></tr></thead>
          <tbody>
            {COMPARE.map(([f, a, b]) => <tr key={f}><td>{f}</td><td><Cell v={a} /></td><td><Cell v={b} /></td></tr>)}
          </tbody>
        </table>
      </div>

      <div className="grid-3 mt-24">
        {[
          [ShieldCheck, 'Secure payments', 'Payments are processed by Razorpay and verified server-side with a signature check.'],
          [Zap, 'Instant access', 'Premium unlocks the moment your payment is confirmed — no waiting.'],
          [CreditCard, 'Cancel any time', 'Cancel from your account page; you keep Premium until the period ends.'],
        ].map(([Icon, t, d]) => (
          <div key={t} className="card-elevated row-start">
            <div className="pref-icon" style={{ width: 34, height: 34, borderRadius: 10, display: 'grid', placeItems: 'center', background: 'var(--primary-soft)', color: 'var(--primary-light)', flexShrink: 0 }}><Icon size={16} /></div>
            <div><div className="bold small">{t}</div><p className="small mt-4">{d}</p></div>
          </div>
        ))}
      </div>

      <p className="text-center small mt-24"><Link to="/matches" className="muted">Continue with the free plan →</Link></p>

      <Modal open={['review', 'paying', 'success'].includes(stage)} onClose={closeModal}
        title={stage === 'success' ? null : <span className="row gap-8"><CreditCard size={17} />Demo checkout</span>} width={460}>
        {stage === 'success' ? (
          <div className="text-center col" style={{ alignItems: 'center', gap: 10, padding: '8px 0' }}>
            <div className="success-burst">
              <div className="confetti">{CONFETTI.map((c, i) => <i key={i} style={{ '--x': c.x, '--y': c.y, '--r': c.r, background: c.bg, animationDelay: c.delay }} />)}</div>
              <div className="ring"><Check size={36} /></div>
            </div>
            <h2>Welcome to Premium!</h2>
            <p>All strategies are unlocked. Taking you to today’s matches…</p>
            <ButtonLink to="/matches" className="mt-8">Go to matches <ArrowRight size={16} /></ButtonLink>
          </div>
        ) : (
          <div className="col gap-16">
            <Alert tone="warning" title="Test mode">No real payment is taken — this simulated checkout is enabled because Razorpay keys are not configured.</Alert>
            <div className="cc-card">
              <div className="row between" style={{ position: 'relative', zIndex: 1 }}>
                <span className="chip-icon" />
                <span className="bold">XithSense</span>
              </div>
              <div className="cc-num">4111 1111 1111 1111</div>
              <div className="row between small" style={{ position: 'relative', zIndex: 1, opacity: 0.9 }}>
                <span>{(user?.full_name || user?.email || 'Card holder').toUpperCase()}</span><span className="mono">12/29</span>
              </div>
            </div>
            <div>
              <div className="kv"><span>Plan</span><b>{selected.name}</b></div>
              <div className="kv"><span>Order</span><span className="mono xs">{order?.order_id}</span></div>
              <div className="kv"><span>Total</span><b className="mono">₹{((order?.amount || selected.price * 100) / 100).toLocaleString('en-IN')}</b></div>
            </div>
            {error && <Alert tone="danger">{error}</Alert>}
            <Button variant="gold" size="lg" block loading={stage === 'paying'} onClick={pay} icon={Lock}>
              {stage === 'paying' ? 'Processing…' : `Pay ₹${selected.price.toLocaleString('en-IN')}`}
            </Button>
            <button className="small muted" onClick={closeModal} disabled={stage === 'paying'}>Cancel</button>
          </div>
        )}
      </Modal>
    </div>
  )
}
