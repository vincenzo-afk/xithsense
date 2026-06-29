import { Link } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { createSubscription } from '../api/client'

const PLANS = [
  {
    id: 'premium_monthly',
    label: 'Monthly',
    price: '₹299',
    period: '/month',
    savings: null,
    features: [
      'Unlimited teams per match',
      'All 4 team modes',
      'Grand League differentials',
      'Unlimited AI chat',
      'Live match WebSocket feed',
      'Portfolio generation (4 teams)',
      'Detailed player explanations',
    ],
  },
  {
    id: 'premium_annual',
    label: 'Annual',
    price: '₹2,499',
    period: '/year',
    savings: 'Save 30% · ₹208/month',
    features: [
      'Everything in Monthly, plus:',
      'Priority feature access',
      'Early beta features',
      'Email + Telegram alerts',
    ],
    featured: true,
  },
]

export default function SubscribePage() {
  const subMutation = useMutation({
    mutationFn: createSubscription,
    onSuccess: (data) => {
      // In production, open Razorpay checkout
      alert(`Order created: ${data.order_id}. Integrate Razorpay SDK to complete payment.`)
    },
    onError: () => {
      alert('Payment gateway not configured. Set RAZORPAY_KEY_ID and RAZORPAY_KEY_SECRET in .env')
    },
  })

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 800 }}>
        <div className="page-header text-center">
          <h1 className="page-title gradient-text">Upgrade to Premium</h1>
          <p style={{ maxWidth: 500, margin: '0 auto' }}>
            Access every feature, every mode, and every insight. Win bigger with XithSense Premium.
          </p>
        </div>

        <div className="pricing-grid" style={{ margin: '0 auto' }}>
          {PLANS.map(plan => (
            <div key={plan.id} className={`pricing-card ${plan.featured ? 'featured' : ''}`}>
              <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)', marginBottom: 8 }}>{plan.label}</div>
              <div className="price-amount">{plan.price}<span className="price-period">{plan.period}</span></div>
              {plan.savings && <div style={{ color: 'var(--color-success)', fontSize: 'var(--text-sm)', fontWeight: 600, marginBottom: 'var(--sp-4)' }}>{plan.savings}</div>}
              <ul className="price-features">
                {plan.features.map(f => (
                  <li key={f} className="price-feature">
                    <span className="check">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                className={`btn ${plan.featured ? 'btn-primary glow-primary' : 'btn-secondary'} w-full`}
                onClick={() => subMutation.mutate({ plan: plan.id })}
                disabled={subMutation.isPending}>
                {subMutation.isPending ? '⏳ Processing...' : `Subscribe ${plan.label}`}
              </button>
            </div>
          ))}
        </div>

        <div className="card mt-8 text-center">
          <p style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
            🔒 Payments secured by Razorpay. Cancel anytime. No hidden fees.
          </p>
          <div style={{ display: 'flex', justifyContent: 'center', gap: 24, marginTop: 'var(--sp-4)', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            <span>✓ SSL encrypted</span>
            <span>✓ Cancel anytime</span>
            <span>✓ 7-day refund</span>
          </div>
        </div>

        <div className="text-center mt-6">
          <Link to="/matches" style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            ← Continue with Free plan
          </Link>
        </div>
      </div>
    </div>
  )
}
