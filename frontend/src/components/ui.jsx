/**
 * XithSense UI primitives. Every page composes these — keep styling in index.css.
 */
import { useEffect, useState } from 'react'
import { createPortal } from 'react-dom'
import { Link } from 'react-router-dom'
import clsx from 'clsx'
import {
  AlertTriangle, CheckCircle2, Crown, Info, Loader2, Lock, Sparkles, X, XCircle,
} from 'lucide-react'
import { confidenceLevel, countdownParts, initials, team } from '../lib/format'
import { useUiStore } from '../store/uiStore'

export function Button({ variant = 'primary', size, icon: Icon, loading, block, className, children, ...props }) {
  return (
    <button
      className={clsx('btn', `btn-${variant}`, size && `btn-${size}`, block && 'btn-block', !children && 'btn-icon', className)}
      disabled={loading || props.disabled}
      {...props}
    >
      {loading ? <Loader2 size={16} className="spin" /> : Icon && <Icon size={size === 'sm' ? 14 : 16} />}
      {children}
    </button>
  )
}

export function ButtonLink({ to, variant = 'primary', size, icon: Icon, block, className, children, ...props }) {
  return (
    <Link to={to} className={clsx('btn', `btn-${variant}`, size && `btn-${size}`, block && 'btn-block', className)} {...props}>
      {Icon && <Icon size={size === 'sm' ? 14 : 16} />}
      {children}
    </Link>
  )
}

export function Card({ title, subtitle, icon: Icon, actions, className, children, pad, ...props }) {
  return (
    <div className={clsx('card', pad && `pad-${pad}`, className)} {...props}>
      {(title || actions) && (
        <div className="card-head">
          <div className="grow">
            {title && <h3>{Icon && <Icon size={17} className="text-primary" />}{title}</h3>}
            {subtitle && <div className="sub">{subtitle}</div>}
          </div>
          {actions}
        </div>
      )}
      {children}
    </div>
  )
}

export function Badge({ tone, size, className, children, ...props }) {
  return <span className={clsx('badge', tone && `badge-${tone}`, size === 'lg' && 'badge-lg', className)} {...props}>{children}</span>
}

export const LiveBadge = ({ label = 'LIVE' }) => <span className="badge badge-live"><span className="dot" />{label}</span>
export const ProBadge = () => <span className="badge badge-pro"><Crown size={11} />PRO</span>
export const RoleBadge = ({ role }) => <span className={clsx('badge role', `role-${role}`)}>{role}</span>

export function ConfidenceBadge({ value }) {
  const c = confidenceLevel(value)
  return <span className={clsx('badge', c.badge)}>{value}% · {c.label}</span>
}

export function ConfidenceBar({ value, height = 6 }) {
  const c = confidenceLevel(value)
  return <div className="meter" style={{ height }}><span className={c.cls} style={{ width: `${Math.min(100, value)}%` }} /></div>
}

export function ConfidenceRing({ value, size = 42, stroke = 4 }) {
  const c = confidenceLevel(value)
  const r = (size - stroke) / 2
  const circ = 2 * Math.PI * r
  return (
    <div className="conf-ring" style={{ width: size, height: size }} title={`${value}% confidence (${c.label})`}>
      <svg width={size} height={size}>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--bg-elevated)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke={c.color} strokeWidth={stroke}
          strokeDasharray={circ} strokeDashoffset={circ * (1 - value / 100)} strokeLinecap="round"
          style={{ transition: 'stroke-dashoffset 700ms cubic-bezier(.2,.8,.2,1)' }} />
      </svg>
      <span className="val">{value}</span>
    </div>
  )
}

export function Meter({ value, max = 100, color = 'var(--primary)', height = 6 }) {
  return <div className="meter" style={{ height }}><span style={{ width: `${Math.max(0, Math.min(100, (value / max) * 100))}%`, background: color }} /></div>
}

export function TeamCrest({ name, size, className }) {
  const t = team(name)
  const [broken, setBroken] = useState(false)
  if (t.img && !broken) {
    return (
      <div className={clsx('crest crest-img', size, className)} style={{ '--team': t.color }} title={name}>
        <img src={t.img} alt={t.short} loading="lazy" onError={() => setBroken(true)} />
      </div>
    )
  }
  return <div className={clsx('crest', size, className)} style={{ '--team': t.color }} title={name}>{t.short}</div>
}

export function PlayerAvatar({ name, role, size = 40 }) {
  const color = { WK: 'var(--wk)', BAT: 'var(--bat)', AR: 'var(--ar)', BOWL: 'var(--bowl)' }[role] || 'var(--primary-light)'
  return (
    <div className="player-avatar" style={{ width: size, height: size, color, borderColor: `color-mix(in srgb, ${color} 35%, transparent)`, background: `color-mix(in srgb, ${color} 12%, var(--bg-elevated))` }}>
      {initials(name)}
    </div>
  )
}

export function Stat({ label, value, icon: Icon, hint, tone, accent, className }) {
  return (
    <div className={clsx('stat', accent && 'accent', className)}>
      <div className="label-row"><span>{label}</span>{Icon && <span className="icon-bubble" style={tone ? { background: `color-mix(in srgb, ${tone} 15%, transparent)`, color: tone } : undefined}><Icon size={15} /></span>}</div>
      <div className="value" style={tone ? { color: tone } : undefined}>{value}</div>
      {hint && <div className="delta">{hint}</div>}
    </div>
  )
}

export function Skeleton({ h = 16, w = '100%', r, style, className }) {
  return <div className={clsx('skeleton', className)} style={{ height: h, width: w, borderRadius: r, ...style }} />
}

export function Spinner({ size = 20 }) {
  return <Loader2 size={size} className="spin" style={{ color: 'var(--primary-light)' }} />
}

export function PageLoader() {
  return <div className="page-loader"><Spinner size={28} /></div>
}

export function EmptyState({ icon: Icon = Info, title, children, action }) {
  return (
    <div className="empty">
      <div className="empty-icon"><Icon size={24} /></div>
      <h3>{title}</h3>
      {children && <p style={{ maxWidth: 420 }}>{children}</p>}
      {action && <div className="mt-8">{action}</div>}
    </div>
  )
}

export function Alert({ tone = 'info', title, children, action }) {
  const Icon = { danger: XCircle, warning: AlertTriangle, success: CheckCircle2, info: Info }[tone]
  return (
    <div className={`alert alert-${tone}`}>
      <Icon size={16} />
      <div className="grow">{title && <div className="bold">{title}</div>}{children}</div>
      {action}
    </div>
  )
}

export function Tabs({ tabs, value, onChange, className }) {
  return (
    <div className={clsx('tabs', className)} role="tablist">
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} className={clsx('tab', value === t.value && 'active')}
          onClick={() => onChange(t.value)}>
          {t.icon && <t.icon size={14} />}{t.label}{t.count != null && <span className="count">{t.count}</span>}
          {t.locked && <Lock size={12} className="muted" />}
        </button>
      ))}
    </div>
  )
}

export function UnderlineTabs({ tabs, value, onChange }) {
  return (
    <div className="underline-tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.value} role="tab" aria-selected={value === t.value} className={clsx(value === t.value && 'active')} onClick={() => onChange(t.value)}>
          {t.icon && <t.icon size={15} />}{t.label}{t.locked && <Lock size={12} className="muted" />}
        </button>
      ))}
    </div>
  )
}

export function Switch({ checked, onChange, disabled, label }) {
  return (
    <button type="button" role="switch" aria-checked={checked} aria-label={label} disabled={disabled}
      className={clsx('switch', checked && 'on')} onClick={() => onChange(!checked)} />
  )
}

function useEscape(onClose) {
  useEffect(() => {
    const h = (e) => e.key === 'Escape' && onClose?.()
    window.addEventListener('keydown', h)
    return () => window.removeEventListener('keydown', h)
  }, [onClose])
}

export function Modal({ open, onClose, title, children, footer, width }) {
  useEscape(open ? onClose : null)
  if (!open) return null
  return createPortal(
    <>
      <div className="overlay" onClick={onClose} />
      <div className="modal" role="dialog" aria-modal="true" style={width ? { width: `min(${width}px, calc(100vw - 32px))` } : undefined}>
        {title && <div className="modal-head"><h3>{title}</h3><Button variant="ghost" size="sm" icon={X} onClick={onClose} aria-label="Close" /></div>}
        <div className="modal-body">{children}</div>
        {footer && <div className="modal-foot">{footer}</div>}
      </div>
    </>,
    document.body,
  )
}

export function Drawer({ open, onClose, title, children, header }) {
  useEscape(open ? onClose : null)
  if (!open) return null
  return createPortal(
    <>
      <div className="overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-modal="true">
        <div className="modal-head">{header || <h3>{title}</h3>}<Button variant="ghost" size="sm" icon={X} onClick={onClose} aria-label="Close" /></div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>,
    document.body,
  )
}

export function Toasts() {
  const { toasts, dismiss } = useUiStore()
  return createPortal(
    <div className="toasts" aria-live="polite">
      {toasts.map((t) => {
        const Icon = { success: CheckCircle2, error: XCircle, info: Info }[t.type] || Info
        return (
          <div key={t.id} className={clsx('toast', t.type)} onClick={() => dismiss(t.id)}>
            <Icon size={18} />
            <div className="grow"><div className="t-title">{t.title}</div>{t.message && <div className="secondary small mt-4">{t.message}</div>}</div>
          </div>
        )
      })}
    </div>,
    document.body,
  )
}

/** Global "upgrade to Premium" modal, opened by useUiStore.showUpgrade(). */
export function UpgradeModal() {
  const { upgrade, hideUpgrade } = useUiStore()
  return (
    <Modal open={!!upgrade} onClose={hideUpgrade} width={460}>
      <div className="text-center col" style={{ alignItems: 'center', gap: 14, padding: '6px 4px' }}>
        <div className="brand-mark" style={{ width: 56, height: 56, borderRadius: 16 }}><Crown size={26} /></div>
        <h2>Unlock {upgrade?.feature || 'Premium'}</h2>
        <p>{upgrade?.message || 'This feature is part of XithSense Premium.'}</p>
        <ul className="check-list" style={{ textAlign: 'left', alignSelf: 'stretch', margin: '6px 0' }}>
          {['All 4 team modes + up to 20 teams per match', 'Grand League differentials & ownership', 'AI chat assistant and full explanations', 'Live match intelligence feed'].map((f) => (
            <li key={f}><Sparkles size={15} className="text-captain" />{f}</li>
          ))}
        </ul>
        <ButtonLink to="/subscribe" variant="gold" size="lg" block onClick={hideUpgrade} icon={Crown}>View plans — from ₹208/mo</ButtonLink>
        <button className="muted small" onClick={hideUpgrade}>Maybe later</button>
      </div>
    </Modal>
  )
}

export function LockedPanel({ feature, children }) {
  const show = useUiStore((s) => s.showUpgrade)
  return (
    <div className="card text-center" style={{ padding: '44px 24px', background: 'radial-gradient(80% 100% at 50% 0%, rgba(99,102,241,.14), transparent 70%), var(--bg-surface)' }}>
      <div className="empty" style={{ padding: 0 }}>
        <div className="empty-icon" style={{ background: 'var(--secondary-soft)', color: 'var(--captain)' }}><Lock size={22} /></div>
        <h3>{feature} is a Premium feature</h3>
        <p style={{ maxWidth: 440 }}>{children}</p>
        <div className="row mt-8"><Button variant="gold" icon={Crown} onClick={() => show({ feature })}>Upgrade to Premium</Button></div>
      </div>
    </div>
  )
}

export function Countdown({ to, compact }) {
  const [p, setP] = useState(() => countdownParts(to))
  useEffect(() => {
    const t = setInterval(() => setP(countdownParts(to)), 1000)
    return () => clearInterval(t)
  }, [to])
  if (p.done) return <span className="badge badge-warning">Starting</span>
  if (compact) {
    return <span className="mono">{p.d > 0 ? `${p.d}d ${p.h}h` : `${String(p.h).padStart(2, '0')}:${String(p.m).padStart(2, '0')}:${String(p.s).padStart(2, '0')}`}</span>
  }
  const units = p.d > 0 ? [['d', p.d], ['h', p.h], ['m', p.m]] : [['h', p.h], ['m', p.m], ['s', p.s]]
  return (
    <div className="countdown">
      {units.map(([k, v]) => <div key={k} className="unit"><b>{String(v).padStart(2, '0')}</b><span>{k}</span></div>)}
    </div>
  )
}

export function FormGuide({ results = [] }) {
  if (!results.length) return <span className="muted xs">No recent games</span>
  return <div className="row gap-4">{results.map((r, i) => <span key={i} className={`form-chip form-${r}`}>{r}</span>)}</div>
}

export function ChartTip({ active, payload, label, render }) {
  if (!active || !payload?.length) return null
  return <div className="chart-tip">{render ? render(payload[0].payload, label) : <><div className="t">{label}</div>{payload.map((p) => <div key={p.dataKey} style={{ color: p.color }}>{p.name}: <b className="mono">{typeof p.value === 'number' ? p.value.toFixed(1) : p.value}</b></div>)}</>}</div>
}

export function PageHead({ eyebrow, title, subtitle, actions }) {
  return (
    <div className="page-head">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {actions && <div className="row wrap">{actions}</div>}
    </div>
  )
}
