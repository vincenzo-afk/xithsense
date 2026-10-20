import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  CloudRain, Crown, Dices, Droplets, Flame, Gauge, MapPin, RefreshCw, Shield, Sparkles, Swords, Target, Trophy, Zap,
} from 'lucide-react'
import { apiError, getDifferentials, predictCaptain } from '../../api/client'
import {
  Alert, Badge, Card, ConfidenceBadge, ConfidenceRing, EmptyState, LockedPanel, PlayerAvatar, RoleBadge,
  Skeleton, Stat, Tabs, TeamCrest,
} from '../ui'
import { MODES, ROLE_COLORS, ROLE_NAMES, ROLE_ORDER, fmt, fmtDate, pct, team } from '../../lib/format'
import { useUiStore } from '../../store/uiStore'

const CAP_META = {
  best_captain: { label: 'Best captain', icon: Crown, color: 'var(--captain)', cls: 'best' },
  safe_captain: { label: 'Safe captain', icon: Shield, color: 'var(--success)', cls: '' },
  risk_captain: { label: 'Risk captain', icon: Dices, color: 'var(--cyan)', cls: '' },
}

export function CaptaincyTab({ matchId, premium, onPlayer }) {
  const [mode, setMode] = useState('safe')
  const showUpgrade = useUiStore((s) => s.showUpgrade)
  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ['captain', matchId, mode],
    queryFn: () => predictCaptain({ match_id: matchId, mode }),
  })
  const tabs = Object.entries(MODES).map(([value, m]) => ({ value, label: m.label, locked: !premium && value !== 'safe' }))
  const pick = (v) => (premium || v === 'safe' ? setMode(v) : showUpgrade({ feature: `${MODES[v].label} captaincy`, message: 'Mode-specific captaincy is part of Premium.' }))
  return (
    <div className="fade-in">
      <div className="row between wrap mb-16">
        <Tabs tabs={tabs} value={mode} onChange={pick} />
        <button className="btn btn-ghost btn-sm" onClick={() => refetch()} disabled={isFetching}><RefreshCw size={14} className={isFetching ? 'spin' : ''} />Refresh</button>
      </div>
      {error && <Alert tone="danger" title="Couldn't rank captains">{apiError(error).message}</Alert>}
      <div className="cap-grid">
        {isLoading && [1, 2, 3].map((i) => <Skeleton key={i} h={230} r={14} />)}
        {data?.recommendations.map((c) => {
          const m = CAP_META[c.type] || CAP_META.best_captain
          return (
            <div key={c.player_id} className={`cap-card fade-in ${m.cls}`} style={{ cursor: 'pointer' }}
              onClick={() => onPlayer({ player_id: c.player_id, full_name: c.full_name, role: '', team: '' })}>
              <div className="row between">
                <span className="kind" style={{ color: m.color }}><m.icon size={14} />{m.label}</span>
                <span className="mono xs muted">#{c.rank}</span>
              </div>
              <div className="row mt-16">
                <PlayerAvatar name={c.full_name} size={46} />
                <div className="grow"><h3 className="truncate">{c.full_name}</h3><ConfidenceBadge value={c.confidence} /></div>
                <ConfidenceRing value={c.confidence} size={48} stroke={5} />
              </div>
              <div className="cap-stats">
                <div><b className="text-success">{fmt(c.predicted_fp, 0)}</b><span>Projected</span></div>
                <div><b>{fmt(c.ceiling_score, 0)}</b><span>Ceiling</span></div>
                <div><b style={{ color: 'var(--cyan)' }}>{c.ownership_estimate}</b><span>Owned</span></div>
              </div>
              <p className="small" style={{ lineHeight: 1.55 }}>{c.reasoning}</p>
              <div className="xs muted mt-12">As captain: <b className="mono" style={{ color: 'var(--text)' }}>{fmt((c.predicted_fp || 0) * 2, 0)}</b> projected pts</div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export function DifferentialsTab({ matchId, premium, onPlayer }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ['differentials', matchId],
    queryFn: () => getDifferentials(matchId),
    enabled: premium,
  })
  if (!premium) {
    return <LockedPanel feature="Grand League differentials">Low-ownership, high-ceiling picks that separate your team from the field — with expected ownership and the reasoning behind each one.</LockedPanel>
  }
  if (error) return <Alert tone="danger" title="Couldn't load differentials">{apiError(error).message}</Alert>
  return (
    <div className="fade-in">
      <Alert tone="info" title="How to use differentials">Pair one or two of these with a popular captain in grand leagues. Ownership is estimated from projected popularity across the match.</Alert>
      <div className="grid-3 mt-16 stagger">
        {isLoading && [1, 2, 3].map((i) => <Skeleton key={i} h={220} r={14} />)}
        {data?.differentials.length === 0 && <Card><EmptyState icon={Sparkles} title="No differentials">Every high-ceiling player here is popular.</EmptyState></Card>}
        {data?.differentials.map((d) => (
          <div key={d.player_id} className="card hover diff-card" onClick={() => onPlayer(d)}>
            <div className="row between">
              <span className="own-chip"><Target size={12} />{d.ownership_estimate} owned</span>
              <RoleBadge role={d.role} />
            </div>
            <div className="row">
              <PlayerAvatar name={d.full_name} role={d.role} size={44} />
              <div className="grow"><h3 className="truncate">{d.full_name}</h3><div className="xs muted">{d.team} · {fmt(d.credits)} cr</div></div>
            </div>
            <div className="grid-3" style={{ gap: 8 }}>
              <div className="card-elevated" style={{ padding: 10 }}><div className="xs muted">Ceiling</div><b className="mono text-captain">{fmt(d.ceiling_score, 0)}</b></div>
              <div className="card-elevated" style={{ padding: 10 }}><div className="xs muted">Projected</div><b className="mono text-success">{fmt(d.predicted_fp, 0)}</b></div>
              <div className="card-elevated" style={{ padding: 10 }}><div className="xs muted">Last 5</div><b className="mono">{fmt(d.fp_avg_5)}</b></div>
            </div>
            <p className="small" style={{ lineHeight: 1.55 }}><Flame size={13} className="text-warning" style={{ display: 'inline', verticalAlign: -2, marginRight: 4 }} />{d.reason}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export function SquadsTab({ match }) {
  const navigate = useNavigate()
  const teams = [match.team_a, match.team_b]
  return (
    <div className="grid-2 fade-in">
      {teams.map((name) => {
        const squad = match.squads?.[name] || []
        return (
          <Card key={name} pad="sm" title={<span className="row gap-8"><TeamCrest name={name} size="sm" />{name}</span>}
            actions={<Badge>{match.playing_xi_confirmed ? `${squad.filter((p) => p.is_playing).length} in XI` : `${squad.length} in squad`}</Badge>}>
            {squad.length === 0 && <p className="muted small">Squad not announced.</p>}
            {ROLE_ORDER.map((r) => {
              const ps = squad.filter((p) => p.role === r)
              if (!ps.length) return null
              return (
                <div key={r}>
                  <div className="role-group-title" style={{ paddingLeft: 12 }}><i style={{ background: ROLE_COLORS[r] }} />{ROLE_NAMES[r]}</div>
                  {ps.map((p) => (
                    <div key={p.player_id} className={`squad-player ${match.playing_xi_confirmed && !p.is_playing ? 'bench' : ''}`}
                      onClick={() => navigate(`/players/${p.player_id}`)}>
                      <PlayerAvatar name={p.full_name} role={p.role} size={34} />
                      <div style={{ minWidth: 0 }}>
                        <div className="bold small truncate">{p.full_name}</div>
                        <div className="xs muted truncate">{[p.batting_style, p.bowling_style].filter(Boolean).join(' · ')}</div>
                      </div>
                      <div className="row gap-8">
                        {match.playing_xi_confirmed && (p.is_playing ? <Badge tone="success">Playing</Badge> : <Badge>Bench</Badge>)}
                        <span className="mono small">{fmt(p.credits)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              )
            })}
          </Card>
        )
      })}
    </div>
  )
}

export function VenueTab({ match }) {
  const v = match.venue
  const h = match.head_to_head
  const spin = v?.spin_wicket_pct ?? null
  return (
    <div className="grid-2 fade-in">
      <Card title={v?.name || match.venue_name || 'Venue'} icon={MapPin} subtitle={v ? [v.city, v.country].filter(Boolean).join(', ') : null}>
        {!v ? <p className="muted">No venue profile yet.</p> : (
          <>
            <div className="grid-2" style={{ gap: 12 }}>
              <Stat label="Pitch" icon={Gauge} value={<span style={{ fontSize: 18, textTransform: 'capitalize' }}>{v.pitch_type || '—'}</span>} />
              <Stat label="Dew factor" icon={v.dew_factor ? Droplets : CloudRain} value={<span style={{ fontSize: 18 }}>{v.dew_factor ? 'Expected' : 'Low'}</span>} tone={v.dew_factor ? 'var(--cyan)' : undefined} />
              <Stat label="Avg 1st innings" icon={Zap} value={v.avg_first_innings_score ?? '—'} />
              <Stat label="Chasing wins" icon={Trophy} value={pct(v.chasing_win_pct)} hint={v.total_matches ? `${v.total_matches} matches` : null} />
            </div>
            {spin != null && (
              <div className="mt-24">
                <div className="row between mb-8"><span className="upper muted">Wickets by bowling type</span></div>
                <div className="stack-bar" style={{ height: 12 }}>
                  <span style={{ width: `${spin * 100}%`, background: 'var(--violet)' }} />
                  <span style={{ width: `${(v.pace_wicket_pct ?? 1 - spin) * 100}%`, background: 'var(--bowl)' }} />
                </div>
                <div className="legend"><span><i style={{ background: 'var(--violet)' }} />Spin <b className="mono">{pct(spin)}</b></span><span><i style={{ background: 'var(--bowl)' }} />Pace <b className="mono">{pct(v.pace_wicket_pct)}</b></span></div>
              </div>
            )}
          </>
        )}
      </Card>
      <Card title="Head to head" icon={Swords} subtitle={h ? `${h.matches} previous meetings` : null}>
        {!h || h.matches === 0 ? <p className="muted">These teams haven't met in the dataset yet.</p> : (
          <>
            <div className="row between" style={{ gap: 16 }}>
              <div className="col" style={{ alignItems: 'center', gap: 6 }}><TeamCrest name={match.team_a} size="lg" /><b className="mono" style={{ fontSize: 26 }}>{h.team_a_wins}</b></div>
              <div className="grow">
                <div className="stack-bar" style={{ height: 12 }}>
                  <span style={{ width: `${(h.team_a_wins / Math.max(1, h.team_a_wins + h.team_b_wins)) * 100}%`, background: team(match.team_a).color }} />
                  <span style={{ width: `${(h.team_b_wins / Math.max(1, h.team_a_wins + h.team_b_wins)) * 100}%`, background: team(match.team_b).color }} />
                </div>
                <div className="text-center xs muted mt-8">wins</div>
              </div>
              <div className="col" style={{ alignItems: 'center', gap: 6 }}><TeamCrest name={match.team_b} size="lg" /><b className="mono" style={{ fontSize: 26 }}>{h.team_b_wins}</b></div>
            </div>
            <div className="divider" />
            <div className="upper muted mb-8">Recent meetings</div>
            {h.last_results.map((r) => (
              <div key={r.match_id} className="kv">
                <span>{fmtDate(r.date, { day: 'numeric', month: 'short', year: 'numeric' })} · {r.venue}</span>
                <span><b>{r.winner ? team(r.winner).short : 'No result'}</b> <span className="muted">{r.winner ? `by ${r.margin}` : ''}</span></span>
              </div>
            ))}
          </>
        )}
      </Card>
    </div>
  )
}

