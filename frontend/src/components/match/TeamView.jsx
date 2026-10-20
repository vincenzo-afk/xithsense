import { useState } from 'react'
import { Activity, Coins, Copy, Gauge, LayoutGrid, Layers, List, Star, Target, Zap } from 'lucide-react'
import { ConfidenceRing, PlayerAvatar, RoleBadge, Stat } from '../ui'
import { ROLE_COLORS, ROLE_NAMES, ROLE_ORDER, fmt, team, teamToText } from '../../lib/format'
import { toast } from '../../store/uiStore'

const WEIGHTS = [
  ['ml', 'ML models', 'var(--primary)'],
  ['human_rules', 'Analyst rules', 'var(--captain)'],
  ['form', 'Recent form', 'var(--success)'],
  ['live', 'Live context', 'var(--cyan)'],
]

const surname = (n) => {
  const parts = n.split(' ')
  return parts.length > 1 ? parts.slice(-1)[0] : n
}

function PitchPlayer({ p, isC, isVC, onClick }) {
  return (
    <div className="pp" onClick={() => onClick(p)} role="button" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && onClick(p)}
      title={`${p.full_name} — ${fmt(p.predicted_fp, 0)} pts projected`}>
      <div className="disc" style={{ '--team': team(p.team).color }}>
        {team(p.team).short}
        {isC && <span className="cvc cvc-c">C</span>}
        {isVC && <span className="cvc cvc-vc">VC</span>}
        {p.is_differential && <span className="diff">DIFF</span>}
      </div>
      <div className="plate">
        <div className="n">{surname(p.full_name)}</div>
        <div className="p">{fmt(p.predicted_fp, 0)} pts <span className="cr">{fmt(p.credits)}cr</span></div>
      </div>
    </div>
  )
}

export function Pitch({ t, onPlayer }) {
  return (
    <div className="pitch">
      {ROLE_ORDER.map((r) => {
        const ps = t.players.filter((p) => p.role === r)
        if (!ps.length) return null
        return (
          <div key={r}>
            <div className="pitch-label">{ROLE_NAMES[r].toUpperCase()}</div>
            <div className="pitch-row">
              {ps.map((p) => (
                <PitchPlayer key={p.player_id} p={p} isC={p.player_id === t.captain.player_id}
                  isVC={p.player_id === t.vice_captain.player_id} onClick={onPlayer} />
              ))}
            </div>
          </div>
        )
      })}
    </div>
  )
}

export function PlayerList({ t, onPlayer }) {
  return (
    <div className="card pad-0">
      {ROLE_ORDER.map((r) => {
        const ps = t.players.filter((p) => p.role === r)
        if (!ps.length) return null
        return (
          <div key={r}>
            <div className="role-group-title"><i style={{ background: ROLE_COLORS[r] }} />{ROLE_NAMES[r]}<span className="mono">{ps.length}</span></div>
            {ps.map((p) => {
              const isC = p.player_id === t.captain.player_id
              const isVC = p.player_id === t.vice_captain.player_id
              return (
                <div key={p.player_id} className="player-row" onClick={() => onPlayer(p)}>
                  <PlayerAvatar name={p.full_name} role={p.role} />
                  <div style={{ minWidth: 0 }}>
                    <div className="row gap-6">
                      <span className="bold truncate">{p.full_name}</span>
                      {isC && <span className="cvc cvc-c">C</span>}
                      {isVC && <span className="cvc cvc-vc">VC</span>}
                      {p.is_differential && <span className="badge" style={{ background: 'rgba(34,211,238,.12)', color: 'var(--cyan)' }}>DIFF</span>}
                    </div>
                    <div className="row gap-6 mt-4 xs muted"><RoleBadge role={p.role} /><span>{team(p.team).short}</span><span className="dot-sep mono">{fmt(p.credits)} cr</span></div>
                  </div>
                  <div className="player-stats">
                    <div className="ps"><b className="text-success">{fmt(p.predicted_fp, 0)}</b><span>Proj</span></div>
                    <div className="ps hide-mobile"><b>{fmt(p.fp_ceiling, 0)}</b><span>Ceil</span></div>
                    <div className="ps hide-mobile"><b style={{ color: 'var(--cyan)' }}>{p.ownership_estimate}</b><span>Own</span></div>
                    <ConfidenceRing value={p.confidence} size={38} />
                  </div>
                </div>
              )
            })}
          </div>
        )
      })}
    </div>
  )
}

export function TeamSummary({ t }) {
  return (
    <div className="stat-row stagger">
      <Stat label="Credits used" icon={Coins} value={<>{fmt(t.total_credits)}<span className="muted" style={{ fontSize: 13 }}> /100</span></>} />
      <Stat label="Projected pts" icon={Target} tone="var(--success)" value={fmt(t.predicted_total_fp, 0)} hint="incl. C 2× / VC 1.5×" />
      <Stat label="Team ceiling" icon={Zap} tone="var(--captain)" value={fmt(t.team_ceiling, 0)} />
      <Stat label="Avg confidence" icon={Gauge} tone="var(--primary-light)" value={`${t.team_confidence}%`} />
      <Stat label="Solver" icon={Activity} value={<span style={{ fontSize: 16 }}>{t.solver_used === 'lp' ? 'Linear prog.' : 'Local search'}</span>} hint={`${t.solve_time_ms} ms · Dream11 valid`} />
    </div>
  )
}

export function CaptainCards({ t, onPlayer }) {
  const find = (id) => t.players.find((p) => p.player_id === id)
  return (
    <div>
      {[['c', 'Captain · 2×', t.captain], ['vc', 'Vice-captain · 1.5×', t.vice_captain]].map(([k, label, c]) => {
        const p = find(c.player_id)
        return (
          <div key={k} className={`cv-card ${k}`} onClick={() => p && onPlayer(p)}>
            <span className={`cvc cvc-${k}`} style={{ width: 32, height: 32, fontSize: 12 }}>{k.toUpperCase()}</span>
            <div style={{ minWidth: 0 }}>
              <div className="xs upper muted">{label}</div>
              <div className="bold truncate">{c.full_name}</div>
              <div className="xs secondary mt-4" style={{ lineHeight: 1.45 }}>{c.reasoning}</div>
            </div>
            <ConfidenceRing value={c.confidence} size={40} />
          </div>
        )
      })}
    </div>
  )
}

export function Splits({ t }) {
  return (
    <div className="col gap-16">
      <div>
        <div className="upper muted mb-8">Team split</div>
        <div className="row wrap gap-8">
          {Object.entries(t.team_split).map(([name, n]) => (
            <span key={name} className="split-chip" style={{ '--team': team(name).color }}><span className="dot" />{team(name).short} <span className="mono">{n}</span></span>
          ))}
        </div>
      </div>
      <div>
        <div className="upper muted mb-8">Role split</div>
        <div className="row wrap gap-8">
          {ROLE_ORDER.map((r) => <span key={r} className="split-chip" style={{ '--team': ROLE_COLORS[r] }}><span className="dot" />{r} <span className="mono">{t.role_split[r] || 0}</span></span>)}
        </div>
      </div>
    </div>
  )
}

export function WeightsBar({ weights, phase }) {
  return (
    <div>
      <div className="row between mb-8"><span className="upper muted">Ensemble weights</span><span className="xs muted">{phase === 'live' ? 'Live' : phase === 'post_toss' ? 'Post-toss' : 'Pre-toss'}</span></div>
      <div className="stack-bar">
        {WEIGHTS.map(([k, , c]) => weights[k] > 0 && <span key={k} style={{ width: `${weights[k] * 100}%`, background: c }} />)}
      </div>
      <div className="legend">
        {WEIGHTS.map(([k, l, c]) => <span key={k}><i style={{ background: c }} />{l} <b className="mono">{Math.round((weights[k] || 0) * 100)}%</b></span>)}
      </div>
      {phase !== 'live' && <p className="xs muted mt-8">Live weight is 0 until the match starts; the other components are re-normalised.</p>}
    </div>
  )
}

export default function TeamView({ match, mode, t, weights, phase, onPlayer }) {
  const [view, setView] = useState('pitch')
  const copy = async () => {
    try {
      await navigator.clipboard.writeText(teamToText(match, mode, t))
      toast.success('Team copied', 'Paste it into Dream11 or share with friends.')
    } catch {
      toast.error('Copy failed', 'Your browser blocked clipboard access.')
    }
  }
  return (
    <div className="fade-in">
      <TeamSummary t={t} />
      <div className="team-layout">
        <div>
          <div className="row between mb-12">
            <h3 className="row gap-8"><Layers size={17} className="text-primary" />Your XI</h3>
            <div className="row gap-8">
              <div className="view-toggle">
                <button className={view === 'pitch' ? 'active' : ''} onClick={() => setView('pitch')} aria-label="Pitch view"><LayoutGrid size={15} /></button>
                <button className={view === 'list' ? 'active' : ''} onClick={() => setView('list')} aria-label="List view"><List size={15} /></button>
              </div>
              <button className="btn btn-secondary btn-sm" onClick={copy}><Copy size={14} />Copy team</button>
            </div>
          </div>
          {view === 'pitch' ? <Pitch t={t} onPlayer={onPlayer} /> : <PlayerList t={t} onPlayer={onPlayer} />}
          <p className="xs muted mt-8 row gap-6"><Star size={12} />Tap any player for the full reasoning behind the pick.</p>
        </div>
        <div className="col gap-16">
          <div className="card"><CaptainCards t={t} onPlayer={onPlayer} /></div>
          <div className="card"><Splits t={t} /></div>
          {weights && <div className="card"><WeightsBar weights={weights} phase={phase} /></div>}
        </div>
      </div>
    </div>
  )
}
