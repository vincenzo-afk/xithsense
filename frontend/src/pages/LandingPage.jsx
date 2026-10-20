import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight, BrainCircuit, Check, ChevronDown, Cpu, Crown, Database, Flame, Gauge, Layers, LineChart,
  MessageSquareText, Radio, Shield, ShieldCheck, Sparkles, Swords, Target, Trophy, X, Zap,
} from 'lucide-react'
import { Logo } from '../components/Layout'
import { Badge, ButtonLink, ConfidenceRing, TeamCrest } from '../components/ui'
import { team } from '../lib/format'
import './public.css'

const A = 'Royal Challengers Bengaluru'
const B = 'Mumbai Indians'

const PREVIEW = [
  { label: 'WICKET-KEEPER', players: [{ n: 'PD Salt', t: A, p: 48 }] },
  { label: 'BATTERS', players: [{ n: 'V Kohli', t: A, p: 61, c: 'C' }, { n: 'SA Yadav', t: B, p: 52, c: 'VC' }, { n: 'RG Sharma', t: B, p: 41 }, { n: 'Tilak Varma', t: B, p: 37, diff: true }] },
  { label: 'ALL-ROUNDERS', players: [{ n: 'HH Pandya', t: B, p: 44 }, { n: 'KH Pandya', t: A, p: 35 }] },
  { label: 'BOWLERS', players: [{ n: 'JJ Bumrah', t: B, p: 55 }, { n: 'JR Hazlewood', t: A, p: 46 }, { n: 'B Kumar', t: A, p: 39 }, { n: 'TA Boult', t: B, p: 38 }] },
]

const ini = (n) => n.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase()

function ProductPreview() {
  return (
    <div className="preview">
      <div className="preview-frame">
        <div className="preview-bar">
          <div className="dots"><i /><i /><i /></div>
          <div className="row gap-8">
            <TeamCrest name={A} size="sm" />
            <span className="mono xs muted">vs</span>
            <TeamCrest name={B} size="sm" />
          </div>
          <Badge tone="primary"><Shield size={11} />Safe XI</Badge>
        </div>
        <div className="pitch">
          {PREVIEW.map((row) => (
            <div key={row.label}>
              <div className="pitch-label">{row.label}</div>
              <div className="pitch-row">
                {row.players.map((pl) => (
                  <div key={pl.n} className="pp" style={{ '--team': team(pl.t).color }}>
                    <div className="disc">
                      {ini(pl.n)}
                      {pl.c && <span className={`cvc ${pl.c === 'C' ? 'cvc-c' : 'cvc-vc'}`}>{pl.c}</span>}
                      {pl.diff && <span className="diff">DIFF</span>}
                    </div>
                    <div className="plate"><div className="n">{pl.n}</div><div className="p">{pl.p} pts</div></div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="float-card captain">
        <div className="row between">
          <span className="upper muted">Best captain</span>
          <span className="cvc cvc-c">C</span>
        </div>
        <div className="row mt-12">
          <ConfidenceRing value={84} size={46} />
          <div className="grow">
            <div className="bold">V Kohli</div>
            <div className="xs muted">Proj. 61 · ceiling 112</div>
          </div>
        </div>
        <div className="xs secondary mt-12" style={{ lineHeight: 1.45 }}>Chasing tonight — analyst rule RULE-0001 fires (+19 pts).</div>
      </div>

      <div className="float-card diff">
        <div className="row between">
          <span className="upper muted">Differential</span>
          <Badge tone="warning">~6% owned</Badge>
        </div>
        <div className="row mt-12">
          <div className="crest sm" style={{ '--team': team(B).color }}>TV</div>
          <div className="grow">
            <div className="bold">Tilak Varma</div>
            <div className="xs muted">Ceiling 88 · trending up</div>
          </div>
        </div>
      </div>
    </div>
  )
}

const STEPS = [
  { icon: Database, title: 'Ingest ball-by-ball', text: 'Every delivery from Cricsheet JSON — runs, extras, wickets, fielders, phases — parsed into a relational store with Dream11 fantasy points per player.' },
  { icon: BrainCircuit, title: 'Features & ensemble', text: 'Leakage-free rolling form, venue and matchup features feed a gradient-boosting ensemble blended with analyst rules and recent form.', weights: true },
  { icon: Cpu, title: 'LP optimizer', text: 'An integer linear program picks the best legal XI — 100 credits, role limits, max 7 per side — plus captain and vice-captain, for each strategy.' },
  { icon: MessageSquareText, title: 'Plain-English why', text: 'Every pick ships with the factors behind it: form, venue record, matchup vs today’s attack, and which analyst rules fired.' },
]

const FEATURES = [
  { icon: LineChart, color: 'var(--primary-light)', title: 'Projection, ceiling & floor', text: 'Each player gets a projected score with P90 ceiling and P10 floor, so you can see upside and risk at a glance.' },
  { icon: Gauge, color: 'var(--success)', title: 'Confidence on every pick', text: 'Confidence blends model agreement, consistency and matchup sample size — High, Medium, Low, Very Low.' },
  { icon: Target, color: 'var(--captain)', title: 'Captaincy engine', text: 'Best, Safe and Risk captain options with reasoning, ownership and confidence — never a coin flip.' },
  { icon: Flame, color: 'var(--danger)', title: 'Differentials & ownership', text: 'Estimated ownership for every player surfaces low-owned, high-ceiling picks that win grand leagues.' },
  { icon: Radio, color: 'var(--cyan)', title: 'Live match intelligence', text: 'Live scores from CricketData, win probability and live fantasy points from the scorecard versus our pre-match projections.' },
  { icon: MessageSquareText, color: 'var(--violet)', title: 'AI chat assistant', text: 'Ask “Who should I captain?” or “Is Kohli worth it tonight?” — answers grounded in the same numbers.' },
]

const MODES = [
  { icon: Shield, color: '#10b981', name: 'Safe', text: 'Highest expected points with the lowest variance. Consistent performers get a bonus.', meta: 'Head-to-head & small contests' },
  { icon: Trophy, color: '#6366f1', name: 'Grand League', text: 'Ceiling-weighted with a bonus for low-ownership players and at least one differential.', meta: 'Mega contests', pro: true },
  { icon: Zap, color: '#f59e0b', name: 'Aggressive', text: 'Pure ceiling. Ignores consistency to chase the highest possible score.', meta: 'High-risk entries', pro: true },
  { icon: Swords, color: '#a78bfa', name: 'Small League', text: 'Balanced projection and ceiling with a moderate differential tilt.', meta: '3–20 player leagues', pro: true },
]

const FREE = [
  ['One Safe-mode team per request', true],
  ['Captain & vice-captain picks', true],
  ['Basic explanations (5 per match)', true],
  ['Player profiles, form & matchups', true],
  ['Grand League, Aggressive, Small League', false],
  ['Differentials, AI chat & live feed', false],
]
const PREMIUM = [
  'All 4 team modes',
  'Up to 20 unique teams per match',
  'One-click 4-mode portfolio',
  'Differentials with ownership estimates',
  'AI chat assistant',
  'Live match intelligence feed',
  'Full explanations with analyst rules',
]

const FAQ = [
  ['Where does the data come from?', 'History comes from Cricsheet’s open ball-by-ball JSON — 23,000+ men’s and women’s matches across T20, ODI and Test. Every delivery is converted into fantasy points and rolling form, venue and matchup features. Upcoming fixtures, toss and live scores come from CricketData.'],
  ['How are teams generated?', 'For each player we combine a machine-learning projection (40%), analyst-curated rules (30%), recent form (20%) and, during a match, live context (10%). An integer linear program then selects the best legal XI and captaincy for the strategy you choose.'],
  ['Is this a guarantee of winning?', 'No. Cricket is high-variance and no model can promise results. We show confidence levels, ceilings and floors precisely so you can judge risk yourself. Please play responsibly.'],
  ['What changes after the toss?', 'The toss tells us who is chasing, which activates context rules (e.g. chasing specialists, dew at certain venues). Predictions refresh automatically once the toss and playing XI are confirmed.'],
  ['Can I cancel Premium?', 'Yes, any time from your account page. You keep Premium until the end of the period you’ve paid for.'],
]

function FaqItem({ q, a }) {
  const [open, setOpen] = useState(false)
  return (
    <div className={`faq-item${open ? ' open' : ''}`}>
      <button onClick={() => setOpen((o) => !o)} aria-expanded={open}>{q}<ChevronDown size={18} /></button>
      {open && <div className="answer fade-in">{a}</div>}
    </div>
  )
}

export default function LandingPage() {
  return (
    <div className="landing">
      <nav className="landing-nav">
        <Link to="/"><Logo /></Link>
        <div className="nav-links">
          <a className="nav-anchor" href="#how">How it works</a>
          <a className="nav-anchor" href="#modes">Team modes</a>
          <a className="nav-anchor" href="#pricing">Pricing</a>
          <Link to="/login" className="btn btn-ghost btn-sm">Sign in</Link>
          <ButtonLink to="/register" size="sm">Get started</ButtonLink>
        </div>
      </nav>

      <div style={{ position: 'relative' }}>
        <div className="hero-glow" />
        <div className="hero-grid-bg" />
        <section className="hero">
          <div className="fade-in">
            <div className="pill-badge"><b>LIVE</b>Real fixtures & scores from CricketData</div>
            <h1>Smarter fantasy cricket, <span className="gradient-text">built on every ball.</span></h1>
            <p className="lead">
              XithSense learns from 23,000+ real Cricsheet matches, ball by ball, and turns today's fixtures into
              Dream11-ready teams — with projections, captain picks, differentials and a plain-English reason behind every choice.
            </p>
            <div className="hero-ctas">
              <ButtonLink to="/register" size="lg" icon={Sparkles}>Build my first team free</ButtonLink>
              <a href="#how" className="btn btn-secondary btn-lg">See how it works <ArrowRight size={16} /></a>
            </div>
            <div className="trust-row">
              <div className="t-item"><b>23k+</b><span>real matches learned</span></div>
              <div className="t-item"><b>4</b><span>team strategies</span></div>
              <div className="t-item"><b>40/30/20/10</b><span>ML · rules · form · live</span></div>
              <div className="t-item"><b>&lt;1s</b><span>to optimise an XI</span></div>
            </div>
          </div>
          <div className="fade-in" style={{ animationDelay: '120ms' }}><ProductPreview /></div>
        </section>
      </div>

      <div className="stats-strip">
        <div><b>23,000+</b><span>Cricsheet matches, ball by ball</span></div>
        <div><b>40+</b><span>features per player per match</span></div>
        <div><b>20</b><span>curated analyst rules</span></div>
        <div><b>Live</b><span>fixtures & scores via CricketData</span></div>
      </div>

      <section className="landing-section" id="how">
        <div className="section-head">
          <div className="eyebrow"><Layers size={14} />How it works</div>
          <h2>From raw deliveries to your best XI</h2>
          <p>Four stages, the same pipeline for every match — and every number you see is traceable back to the data.</p>
        </div>
        <div className="steps stagger">
          {STEPS.map((s, i) => (
            <div key={s.title} className="step">
              <span className="num-tag">0{i + 1}</span>
              <div className="step-icon"><s.icon size={20} /></div>
              <h3>{s.title}</h3>
              <p>{s.text}</p>
              {s.weights && (
                <>
                  <div className="weights">
                    <span style={{ width: '40%', background: 'var(--primary)' }} />
                    <span style={{ width: '30%', background: 'var(--violet)' }} />
                    <span style={{ width: '20%', background: 'var(--success)' }} />
                    <span style={{ width: '10%', background: 'var(--captain)' }} />
                  </div>
                  <div className="legend xs"><span><i style={{ background: 'var(--primary)' }} />ML</span><span><i style={{ background: 'var(--violet)' }} />Rules</span><span><i style={{ background: 'var(--success)' }} />Form</span><span><i style={{ background: 'var(--captain)' }} />Live</span></div>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="section-head">
          <div className="eyebrow"><Sparkles size={14} />Everything in one place</div>
          <h2>Built for the decisions that matter</h2>
        </div>
        <div className="grid-3 stagger">
          {FEATURES.map((f) => (
            <div key={f.title} className="feature-card">
              <div className="ficon" style={{ background: `color-mix(in srgb, ${f.color} 15%, transparent)`, color: f.color }}><f.icon size={20} /></div>
              <h3>{f.title}</h3>
              <p className="mt-8" style={{ fontSize: 13.5, lineHeight: 1.6 }}>{f.text}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="modes" style={{ paddingTop: 0 }}>
        <div className="section-head">
          <div className="eyebrow"><Trophy size={14} />Team modes</div>
          <h2>One match, four strategies</h2>
          <p>Different contests reward different risk. Pick the strategy that fits — or generate all four at once.</p>
        </div>
        <div className="mode-grid stagger">
          {MODES.map((m) => (
            <div key={m.name} className="mode-tile">
              <div className="glow-dot" style={{ background: m.color }} />
              <div className="row between">
                <div className="ficon" style={{ width: 42, height: 42, borderRadius: 12, display: 'grid', placeItems: 'center', background: `color-mix(in srgb, ${m.color} 16%, transparent)`, color: m.color }}><m.icon size={20} /></div>
                {m.pro ? <span className="badge badge-pro"><Crown size={11} />PRO</span> : <Badge tone="success">Free</Badge>}
              </div>
              <h3>{m.name}</h3>
              <p>{m.text}</p>
              <div className="meta">Best for: {m.meta}</div>
            </div>
          ))}
        </div>
      </section>

      <section className="landing-section" id="pricing" style={{ paddingTop: 0 }}>
        <div className="section-head">
          <div className="eyebrow"><Crown size={14} />Pricing</div>
          <h2>Start free. Upgrade when it clicks.</h2>
          <p>No hidden fees. Cancel any time — you keep Premium until your period ends.</p>
        </div>
        <div className="pricing-grid">
          <div className="price-card">
            <div><h3>Free</h3><p className="small mt-4">For casual players getting started.</p></div>
            <div className="price">₹0 <small>forever</small></div>
            <ul className="check-list">
              {FREE.map(([f, ok]) => (
                <li key={f} className={ok ? '' : 'off'}>{ok ? <Check size={16} className="text-success" /> : <X size={16} className="muted" />}<span className={ok ? '' : 'muted'}>{f}</span></li>
              ))}
            </ul>
            <ButtonLink to="/register" variant="secondary" block className="push">Get started</ButtonLink>
          </div>
          <div className="price-card featured">
            <span className="ribbon badge badge-pro badge-lg"><Sparkles size={12} />Most popular</span>
            <div><h3>Premium</h3><p className="small mt-4">Everything, every match.</p></div>
            <div className="price">₹299 <small>/ month</small></div>
            <ul className="check-list">
              {PREMIUM.map((f) => <li key={f}><Check size={16} className="text-success" />{f}</li>)}
            </ul>
            <ButtonLink to="/register" block className="push" icon={Crown}>Go Premium</ButtonLink>
          </div>
          <div className="price-card">
            <div className="row between"><h3>Annual</h3><Badge tone="success">Save 30%</Badge></div>
            <p className="small" style={{ marginTop: -10 }}>Premium for the whole season and beyond.</p>
            <div className="price">₹2,499 <small>/ year</small></div>
            <div className="small secondary" style={{ marginTop: -8 }}>Works out to ₹208 / month</div>
            <ul className="check-list">
              <li><Check size={16} className="text-success" />Everything in Premium</li>
              <li><Check size={16} className="text-success" />Two months free vs monthly</li>
              <li><Check size={16} className="text-success" />Priority access to new features</li>
            </ul>
            <ButtonLink to="/register" variant="secondary" block className="push">Choose annual</ButtonLink>
          </div>
        </div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="section-head"><h2>Questions, answered</h2></div>
        <div className="faq">{FAQ.map(([q, a]) => <FaqItem key={q} q={q} a={a} />)}</div>
      </section>

      <section className="landing-section" style={{ paddingTop: 0 }}>
        <div className="cta-band">
          <h2>Your next XI is one click away</h2>
          <p className="mt-12" style={{ fontSize: 16 }}>Create a free account and generate a team for the next fixture in seconds.</p>
          <div className="row center wrap mt-24">
            <ButtonLink to="/register" size="lg" icon={Sparkles}>Create free account</ButtonLink>
            <ButtonLink to="/login" size="lg" variant="secondary">I already have an account</ButtonLink>
          </div>
        </div>
      </section>

      <footer className="footer">
        <div className="footer-inner">
          <div style={{ maxWidth: 360 }}>
            <Logo />
            <p className="small mt-12">AI-powered fantasy cricket intelligence. Projections are estimates, not guarantees — please play responsibly.</p>
          </div>
          <div className="row gap-24 wrap">
            <div className="col gap-8">
              <span className="upper muted">Product</span>
              <a className="link" href="#how">How it works</a>
              <a className="link" href="#modes">Team modes</a>
              <a className="link" href="#pricing">Pricing</a>
            </div>
            <div className="col gap-8">
              <span className="upper muted">Account</span>
              <Link className="link" to="/login">Sign in</Link>
              <Link className="link" to="/register">Create account</Link>
            </div>
          </div>
        </div>
        <div className="footer-inner mt-32 small muted" style={{ alignItems: 'center' }}>
          <span className="row gap-6"><ShieldCheck size={14} />Ball-by-ball data from <a href="https://cricsheet.org" target="_blank" rel="noreferrer" className="text-primary">Cricsheet</a>, used under its licence.</span>
          <span>© {new Date().getFullYear()} XithSense · MIT License</span>
        </div>
      </footer>
    </div>
  )
}
