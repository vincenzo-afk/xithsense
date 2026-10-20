import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import {
  Bar, BarChart, CartesianGrid, Cell, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ReferenceLine,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import {
  Activity, ArrowLeft, Coins, Gauge, Globe, Layers, MapPin, Swords, Target, TrendingUp, UserRound, Zap,
} from 'lucide-react'
import { apiError, getPlayer, getPlayerMatchups } from '../api/client'
import {
  Badge, Card, ChartTip, EmptyState, Meter, PlayerAvatar, RoleBadge, Skeleton, Stat, TeamCrest,
} from '../components/ui'
import { BOWLER_TYPES, fmt, fmtDate, pct, team } from '../lib/format'

const DETAILED_TYPES = ['pace_right', 'pace_left', 'spin_off', 'spin_left', 'spin_wrist']
import './match.css'

const PHASES = [['powerplay', 'Powerplay', 'Overs 1–6'], ['middle', 'Middle', 'Overs 7–15'], ['death', 'Death', 'Overs 16–20']]
const ROLE_LABEL = { WK: 'Wicket-keeper', BAT: 'Batter', AR: 'All-rounder', BOWL: 'Bowler' }

function FormChart({ data }) {
  if (!data.length) return <EmptyState icon={Activity} title="No matches yet">Form appears once this player has match history.</EmptyState>
  const rows = data.map((d) => ({ ...d, label: fmtDate(d.match_date, { day: 'numeric', month: 'short' }) }))
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={rows} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}>
        <CartesianGrid vertical={false} strokeDasharray="3 3" />
        <XAxis dataKey="label" tickLine={false} axisLine={false} />
        <YAxis tickLine={false} axisLine={false} />
        <ReferenceLine y={30} stroke="var(--captain)" strokeDasharray="4 4" label={{ value: '30 pts', position: 'insideTopRight', fill: 'var(--captain)', fontSize: 11 }} />
        <Tooltip cursor={{ fill: 'var(--bg-hover)' }} content={<ChartTip render={(p) => (
          <>
            <div className="t">vs {team(p.opposition).short || p.opposition} · {p.label}</div>
            <div className="muted">{p.venue}</div>
            <div className="mt-4"><b className="mono">{fmt(p.fantasy_points)}</b> fantasy pts</div>
            <div className="muted">{p.runs} ({p.balls}) {p.overs > 0 ? ` · ${p.wickets}/${fmt(p.overs, 1)} ov` : ''}</div>
          </>
        )} />} />
        <Bar dataKey="fantasy_points" name="Fantasy pts" radius={[6, 6, 0, 0]} maxBarSize={38}>
          {rows.map((r, i) => <Cell key={i} fill={r.fantasy_points >= 60 ? 'var(--success)' : r.fantasy_points >= 30 ? 'var(--primary)' : 'var(--border-strong)'} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function Matchups({ data, loading }) {
  if (loading) return <Skeleton h={300} />
  const list = data?.matchups || []
  if (!list.length) return <EmptyState icon={Swords} title="Not enough balls faced">Matchups appear after 30+ balls against a bowling type.</EmptyState>
  const detailed = DETAILED_TYPES.filter((k) => list.some((x) => x.bowler_type === k)).length >= 3
  const radar = DETAILED_TYPES.map((k) => {
    const m = list.find((x) => x.bowler_type === k)
    return { type: BOWLER_TYPES[k].replace('Left-arm orthodox', 'Left-arm spin'), sr: m?.strike_rate ? Math.round(m.strike_rate) : 0 }
  })
  // Styles inferred from Cricsheet data are pace / spin only — compare those two directly
  const bars = list.map((m) => ({
    type: BOWLER_TYPES[m.bowler_type] || m.bowler_type,
    sr: Math.round(m.strike_rate || 0),
    outEvery: m.dismissal_rate ? Math.round(1 / m.dismissal_rate) : 0,
  }))
  return (
    <div className="grid-2" style={{ alignItems: 'center' }}>
      <ResponsiveContainer width="100%" height={280}>
        {detailed ? (
          <RadarChart data={radar} outerRadius="72%">
            <PolarGrid stroke="var(--border)" />
            <PolarAngleAxis dataKey="type" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
            <PolarRadiusAxis tick={false} axisLine={false} />
            <Radar dataKey="sr" name="Strike rate" stroke="var(--primary-light)" fill="var(--primary)" fillOpacity={0.3} strokeWidth={2} />
            <Tooltip content={<ChartTip />} />
          </RadarChart>
        ) : (
          <BarChart data={bars} margin={{ top: 10, right: 10, left: -10, bottom: 0 }} barGap={6}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="type" tickLine={false} axisLine={false} />
            <YAxis tickLine={false} axisLine={false} />
            <Tooltip content={<ChartTip />} cursor={{ fill: 'var(--bg-hover)' }} />
            <Bar dataKey="sr" name="Strike rate" fill="var(--primary)" radius={[6, 6, 0, 0]} maxBarSize={56} />
            <Bar dataKey="outEvery" name="Balls per dismissal" fill="var(--wk)" radius={[6, 6, 0, 0]} maxBarSize={56} />
          </BarChart>
        )}
      </ResponsiveContainer>
      <div className="table-wrap">
        <table className="table">
          <thead><tr><th>Bowling</th><th className="num">Balls</th><th className="num">SR</th><th className="num">Out every</th><th>Sample</th></tr></thead>
          <tbody>
            {list.map((m) => (
              <tr key={m.bowler_type}>
                <td className="bold">{BOWLER_TYPES[m.bowler_type] || m.bowler_type}</td>
                <td className="num mono">{m.balls_faced}</td>
                <td className="num mono" style={{ color: m.strike_rate >= 140 ? 'var(--success)' : m.strike_rate < 115 ? 'var(--danger)' : undefined }}>{fmt(m.strike_rate, 0)}</td>
                <td className="num mono">{m.dismissal_rate ? `${Math.round(1 / m.dismissal_rate)} b` : '—'}</td>
                <td style={{ width: 90 }}><Meter value={m.confidence * 100} color="var(--primary-light)" /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

function Phases({ split }) {
  const any = PHASES.some(([k]) => split?.[k])
  if (!any) return <p className="muted small">No phase data yet.</p>
  return (
    <div className="phase-grid">
      {PHASES.map(([k, label, overs]) => {
        const s = split[k] || {}
        return (
          <div key={k} className="card-elevated">
            <div className="row between"><b>{label}</b><span className="xs muted">{overs}</span></div>
            <div className="grid-2 mt-12" style={{ gap: 10 }}>
              <div><div className="xs muted">Bat SR</div><b className="mono" style={{ fontSize: 18 }}>{s.bat_sr != null ? fmt(s.bat_sr, 0) : '—'}</b><div className="xs muted">{s.bat_balls ? `${s.bat_balls} balls` : ''}</div></div>
              <div><div className="xs muted">Bowl econ</div><b className="mono" style={{ fontSize: 18 }}>{s.bowl_econ != null ? fmt(s.bowl_econ, 2) : '—'}</b><div className="xs muted">{s.bowl_balls ? `${s.bowl_wkts} wkts` : ''}</div></div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

function PlayerSkeleton() {
  return (
    <div className="col gap-16">
      <Skeleton h={130} r={14} />
      <div className="grid-4">{[1, 2, 3, 4].map((i) => <Skeleton key={i} h={92} r={14} />)}</div>
      <Skeleton h={320} r={14} />
    </div>
  )
}

export default function PlayerPage() {
  const { playerId } = useParams()
  const navigate = useNavigate()
  const { data: p, isLoading, error } = useQuery({ queryKey: ['player', playerId], queryFn: () => getPlayer(playerId), staleTime: 30 * 60_000 })
  const mu = useQuery({ queryKey: ['matchups', playerId], queryFn: () => getPlayerMatchups(playerId), enabled: !!p, staleTime: 30 * 60_000 })

  const back = <button className="back-link" onClick={() => navigate(-1)}><ArrowLeft size={15} />Back</button>
  if (isLoading) return <>{back}<PlayerSkeleton /></>
  if (error || !p) {
    const e = error ? apiError(error) : { status: 404 }
    return <>{back}<Card><EmptyState icon={UserRound} title={e.status === 404 || e.status === 422 ? 'Player not found' : 'Couldn\'t load player'}>{e.message}</EmptyState></Card></>
  }

  const f = p.recent_form || {}
  const c = p.career || {}
  const bats = c.runs > 0
  const bowls = c.wickets > 0 || c.economy != null

  return (
    <div className="fade-in">
      {back}
      <div className="card mb-24" style={{ background: p.current_team ? `radial-gradient(80% 140% at 0% 0%, color-mix(in srgb, ${team(p.current_team).color} 22%, transparent), transparent 60%), var(--bg-surface)` : undefined }}>
        <div className="profile-hero">
          <PlayerAvatar name={p.full_name} role={p.primary_role} size={84} />
          <div className="grow">
            <div className="row gap-8"><h1>{p.full_name}</h1></div>
            <div className="meta">
              {p.primary_role && <><RoleBadge role={p.primary_role} /><Badge>{ROLE_LABEL[p.primary_role]}</Badge></>}
              {p.nationality && <Badge><Globe size={11} />{p.nationality}</Badge>}
              {p.batting_style && <Badge>{p.batting_style}</Badge>}
              {p.bowling_style && <Badge>{p.bowling_style}</Badge>}
            </div>
          </div>
          <div className="row gap-16">
            {p.current_team && <div className="row gap-8"><TeamCrest name={p.current_team} /><div><div className="xs muted">Team</div><b className="small">{p.current_team}</b></div></div>}
            {p.base_credits != null && <div className="text-center"><div className="xs muted">Credits</div><b className="mono" style={{ fontSize: 24 }}>{fmt(p.base_credits)}</b></div>}
          </div>
        </div>
      </div>

      <div className="grid-4 mb-24 stagger" style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
        <Stat label="Last 5 avg" icon={TrendingUp} value={fmt(f.last_5_fp_avg)} hint={`Last 3: ${fmt(f.last_3_fp_avg)} · Last 10: ${fmt(f.last_10_fp_avg)}`} accent />
        <Stat label="Ceiling (P90)" icon={Zap} tone="var(--captain)" value={fmt(f.fp_ceiling, 0)} />
        <Stat label="Floor (P10)" icon={Target} tone="var(--danger)" value={fmt(f.fp_floor, 0)} />
        <Stat label="Consistency" icon={Gauge} value={f.fp_consistency != null ? fmt(f.fp_consistency, 2) : '—'} hint="std ÷ avg — lower is steadier" />
        <Stat label="30+ pt games" icon={Activity} tone="var(--success)" value={pct(f.fp_30plus_rate)} hint="of last 10" />
      </div>

      <div className="split">
        <div className="col gap-16">
          <Card title="Fantasy points — last 10" icon={Activity} subtitle="Green 60+, indigo 30+">
            <FormChart data={p.form_chart || []} />
          </Card>
          <Card title="Matchups vs bowling types" icon={Swords} subtitle="Strike rate by bowler type (T20)">
            <Matchups data={mu.data} loading={mu.isLoading} />
          </Card>
          <Card title="Phase split" icon={Layers}><Phases split={p.phase_split} /></Card>
        </div>
        <div className="col gap-16">
          <Card title="Career" icon={Coins} subtitle={`${c.matches || 0} matches in dataset`}>
            {!p.career ? <p className="muted small">No career data.</p> : (
              <div className="career-grid">
                <div><b>{fmt(c.fp_avg)}</b><span>Avg fantasy pts</span></div>
                <div><b>{fmt(c.fp_best, 0)}</b><span>Best fantasy pts</span></div>
                {bats && <>
                  <div><b>{c.runs}</b><span>Runs</span></div>
                  <div><b>{c.batting_avg != null ? fmt(c.batting_avg) : '—'}</b><span>Bat avg</span></div>
                  <div><b>{c.strike_rate != null ? fmt(c.strike_rate) : '—'}</b><span>Strike rate</span></div>
                  <div><b>{c.highest_score}</b><span>High score</span></div>
                  <div><b>{c.fifties}</b><span>50+ scores</span></div>
                  <div><b>{c.sixes}</b><span>Sixes</span></div>
                </>}
                {bowls && <>
                  <div><b>{c.wickets}</b><span>Wickets</span></div>
                  <div><b>{c.economy != null ? fmt(c.economy, 2) : '—'}</b><span>Economy</span></div>
                  <div><b>{c.bowling_avg != null ? fmt(c.bowling_avg) : '—'}</b><span>Bowl avg</span></div>
                </>}
                <div><b>{c.catches}</b><span>Catches</span></div>
              </div>
            )}
          </Card>
          <Card title="Best venues" icon={MapPin} subtitle="By average fantasy points (2+ matches)" pad="sm">
            {(p.venues || []).length === 0 ? <p className="muted small" style={{ padding: 8 }}>Not enough venue history.</p> : (
              <table className="table">
                <thead><tr><th>Venue</th><th className="num">M</th><th className="num">FP</th></tr></thead>
                <tbody>
                  {p.venues.map((v) => (
                    <tr key={v.venue}>
                      <td><div className="bold small">{v.venue.split(',')[0]}</div><div className="xs muted">{fmt(v.runs_avg)} runs · {fmt(v.wickets_avg, 2)} wkts</div></td>
                      <td className="num mono">{v.matches}</td>
                      <td className="num mono bold">{fmt(v.fp_avg)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
