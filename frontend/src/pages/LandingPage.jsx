import { Link } from 'react-router-dom'

const features = [
  { icon: '🏏', title: 'Ball-by-Ball Intelligence', desc: '22,062 Cricsheet matches analyzed — every delivery, wicket, and powerplay phase.' },
  { icon: '🤖', title: 'Multi-Model Ensemble', desc: 'XGBoost + LightGBM + CatBoost weighted 40/30/20/10 across ML, rules, form, and live context.' },
  { icon: '🧠', title: 'Human Intelligence Rules', desc: 'Analyst-curated conditional rules (e.g. Kohli chasing, Bumrah death overs) with confidence scores.' },
  { icon: '⚡', title: 'Smart Team Optimizer', desc: 'Linear programming generates Safe, Grand League, Aggressive, and Small League squads simultaneously.' },
  { icon: '💬', title: 'AI Explainability', desc: 'Every pick ships with a plain-English rationale powered by Claude, GPT, or Gemini.' },
  { icon: '📡', title: 'Live Match Intelligence', desc: 'WebSocket feed updates win probabilities and FP projections in real time every over.' },
]

const stats = [
  { value: '22,062+', label: 'Matches Analyzed' },
  { value: '38%+', label: 'Captain Accuracy' },
  { value: '60%+', label: 'Correct Player Rate' },
  { value: '3s', label: 'Team Generation' },
]

export default function LandingPage() {
  return (
    <div>
      {/* Navbar for landing */}
      <nav className="navbar">
        <div className="nav-logo">
          <span style={{ fontSize: 28 }}>🏏</span>
          <span className="gradient-text">XithSense</span>
        </div>
        <div className="nav-links">
          <Link to="/login" className="btn btn-ghost btn-sm">Login</Link>
          <Link to="/register" className="btn btn-primary btn-sm">Get Started Free</Link>
        </div>
      </nav>

      {/* Hero */}
      <section className="hero">
        <div className="hero-bg" />
        <div className="hero-grid" />
        <div className="hero-content">
          <div className="hero-badge">
            🤖 AI-Powered · 22,062 Matches · Dream11 Optimized
          </div>
          <h1 className="hero-title">
            Win at Fantasy Cricket<br />
            <span className="gradient-text">with AI Intelligence</span>
          </h1>
          <p className="hero-subtitle">
            XithSense turns 22,000+ ball-by-ball cricket matches into winning Dream11 teams.
            Multi-model predictions, human analyst rules, and real-time live context — all explained in plain English.
          </p>
          <div className="flex gap-4 justify-center" style={{ flexWrap: 'wrap' }}>
            <Link to="/register" className="btn btn-primary btn-lg glow-primary">
              🚀 Start Winning Free
            </Link>
            <Link to="/login" className="btn btn-secondary btn-lg">
              Sign In →
            </Link>
          </div>
        </div>
      </section>

      {/* Stats */}
      <section style={{ background: 'var(--bg-surface)', borderTop: '1px solid var(--border)', borderBottom: '1px solid var(--border)', padding: 'var(--sp-8) var(--sp-6)' }}>
        <div className="container">
          <div className="stats-strip">
            {stats.map(s => (
              <div key={s.label} className="stat-item fade-in">
                <div className="stat-value gradient-text">{s.value}</div>
                <div className="stat-label">{s.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Features */}
      <section style={{ padding: 'var(--sp-16) var(--sp-6)' }}>
        <div className="container">
          <div className="text-center mb-8">
            <h2>Everything you need to win</h2>
            <p style={{ marginTop: 'var(--sp-4)', maxWidth: 600, margin: 'var(--sp-4) auto 0' }}>
              Built on the deepest cricket data stack available, powered by three gradient-boosting models and an analyst-curated rule engine.
            </p>
          </div>
          <div className="feature-grid">
            {features.map(f => (
              <div key={f.title} className="feature-card fade-in">
                <div className="feature-icon">{f.icon}</div>
                <h3 style={{ marginBottom: 'var(--sp-2)' }}>{f.title}</h3>
                <p style={{ fontSize: 'var(--text-sm)' }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section style={{ background: 'var(--bg-surface)', padding: 'var(--sp-16) var(--sp-6)', borderTop: '1px solid var(--border)' }}>
        <div className="container">
          <div className="text-center mb-8">
            <h2>Simple, transparent pricing</h2>
            <p style={{ marginTop: 'var(--sp-4)' }}>Start free. Upgrade when you're ready to win big.</p>
          </div>
          <div className="pricing-grid">
            <div className="pricing-card">
              <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>Free</div>
              <div className="price-amount">₹<span>0</span></div>
              <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>Forever free</p>
              <ul className="price-features">
                {['1 team per match', 'Safe mode only', 'Basic insights', '5 AI chat messages/match', 'No live feed'].map((f, i) => (
                  <li key={i} className="price-feature">
                    <span className={i < 3 ? 'check' : 'cross'}>{i < 3 ? '✓' : '✗'}</span>
                    <span style={{ color: i < 3 ? 'var(--text-primary)' : 'var(--text-muted)' }}>{f}</span>
                  </li>
                ))}
              </ul>
              <Link to="/register" className="btn btn-secondary w-full">Get Started</Link>
            </div>

            <div className="pricing-card featured">
              <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>Premium</div>
              <div className="price-amount">
                <span className="price-currency">₹</span>299
                <span className="price-period">/month</span>
              </div>
              <p style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>or ₹2,499/year (save 30%)</p>
              <ul className="price-features">
                {['Unlimited teams per match', 'All 4 team modes', 'Detailed AI insights', 'Unlimited AI chat', 'Live match WebSocket feed', 'Grand League differentials', 'Portfolio generation (4 teams)'].map((f) => (
                  <li key={f} className="price-feature">
                    <span className="check">✓</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <Link to="/register" className="btn btn-primary w-full glow-primary">
                🚀 Get Premium
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ background: 'var(--bg-base)', padding: 'var(--sp-8) var(--sp-6)', borderTop: '1px solid var(--border)', textAlign: 'center' }}>
        <div className="flex justify-center gap-2 mb-4">
          <span style={{ fontSize: 24 }}>🏏</span>
          <span className="gradient-text" style={{ fontWeight: 800, fontSize: 'var(--text-lg)' }}>XithSense</span>
        </div>
        <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          Built with data from <a href="https://cricsheet.org" style={{ color: 'var(--color-primary-light)' }}>Cricsheet</a>.
          © 2026 XithSense. MIT License.
        </p>
      </footer>
    </div>
  )
}
