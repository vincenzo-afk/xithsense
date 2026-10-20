import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, Cell, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Activity, BrainCircuit, Database, Gauge, IndianRupee, Layers, ScrollText, Server, Target, TrendingUp, Trophy, Users,
} from 'lucide-react'
import { apiError, getAdminMetrics, getBacktests } from '../../api/client'
import { Alert, Badge, Card, ChartTip, Skeleton, Stat } from '../ui'
import { fmt, fmtDate, fmtInt, pct } from '../../lib/format'

const ROLE_COLORS = { free: '#64748b', premium: '#f59e0b', admin: '#6366f1' }

function Kpi({ label, value, display, max = 1, marks = [], hint }) {
  return (
    <div className="kpi-row">
      <div className="row between">
        <span className="small bold">{label}</span>
        <span className="mono bold">{display}</span>
      </div>
      <div className="kpi-track" style={{ marginBottom: marks.length ? 18 : 0 }}>
        <div className="kpi-fill" style={{ width: `${Math.min(100, (value / max) * 100)}%` }} />
        {marks.map((m) => (
          <span key={m.label} className="kpi-mark" data-label={m.label} style={{ left: `${(m.value / max) * 100}%`, background: m.color }} />
        ))}
      </div>
      {hint && <div className="xs muted mt-4">{hint}</div>}
    </div>
  )
}

export default function Overview() {
  const { data: m, isLoading, error } = useQuery({ queryKey: ['admin-metrics'], queryFn: getAdminMetrics, refetchInterval: 30_000 })
  const { data: bts } = useQuery({ queryKey: ['admin-backtests'], queryFn: getBacktests })
  const bt = bts?.backtests?.[0]

  if (error) return <Alert tone="danger" title="Could not load metrics">{apiError(error).message}</Alert>
  if (isLoading) return <div className="grid-4">{Array.from({ length: 8 }).map((_, i) => <Skeleton key={i} h={104} r={14} />)}</div>

  const roles = Object.entries(m.users_by_role || {}).map(([name, value]) => ({ name, value }))
  const days = (m.predictions_by_day || []).map((d) => ({ ...d, label: fmtDate(d.date) }))
  const maeGain = m.model_mae != null && m.baseline_mae ? (1 - m.model_mae / m.baseline_mae) : null

  return (
    <div className="col" style={{ gap: 20 }}>
      <div className="grid-4 stagger">
        <Stat label="Matches ingested" value={fmtInt(m.total_matches)} icon={Trophy} hint={`${fmtInt(m.upcoming_matches)} upcoming / live`} accent />
        <Stat label="Deliveries" value={fmtInt(m.total_deliveries)} icon={Database} hint={`${fmtInt(m.total_players)} players indexed`} />
        <Stat label="Users" value={fmtInt(m.total_users)} icon={Users} hint={`${fmtInt(m.premium_users)} premium`} tone="var(--captain)" />
        <Stat label="MRR" value={`₹${fmtInt(Math.round(m.mrr_inr))}`} icon={IndianRupee} hint="Monthly + annual/12" tone="var(--success)" />
        <Stat label="Predictions served" value={fmtInt(m.total_predictions)} icon={Layers} />
        <Stat label="Active rules" value={fmtInt(m.active_rules)} icon={ScrollText} hint="Analyst human-intelligence rules" />
        <Stat label="Holdout MAE" value={m.model_mae != null ? fmt(m.model_mae, 2) : '—'} icon={Gauge}
          hint={m.baseline_mae != null ? `Form baseline ${fmt(m.baseline_mae, 2)}${maeGain != null ? ` · ${(maeGain * 100).toFixed(1)}% better` : ''}` : 'No model trained'} tone="var(--primary-light)" />
        <Stat label="Spearman ρ" value={m.model_spearman != null ? fmt(m.model_spearman, 3) : '—'} icon={TrendingUp} hint="Rank correlation on holdout" />
      </div>

      <div className="grid-3">
        <Card title="System health" icon={Server} subtitle={m.active_model_version || 'No active model'}>
          {Object.entries(m.checks || {}).map(([k, v]) => {
            const ok = v === 'ok' || v === 'redis'
            const warn = v === 'memory' || v === 'memory-fallback'
            return (
              <div key={k} className="check-row">
                <span className="status-dot" style={{ background: ok ? 'var(--success)' : warn ? 'var(--warning)' : 'var(--danger)' }} />
                <span className="grow" style={{ textTransform: 'capitalize' }}>{k}</span>
                <Badge tone={ok ? 'success' : warn ? 'warning' : 'danger'}>{v === 'memory' ? 'in-memory' : v}</Badge>
              </div>
            )
          })}
          <div className="check-row">
            <Activity size={14} className="muted" />
            <span className="grow">Overall</span>
            <Badge tone={m.system_health === 'ok' ? 'success' : 'warning'}>{m.system_health}</Badge>
          </div>
        </Card>

        <Card title="Predictions / day" icon={BrainCircuit} subtitle="Last 14 days">
          <div style={{ height: 180 }}>
            {days.length ? (
              <ResponsiveContainer>
                <BarChart data={days} margin={{ top: 4, right: 4, left: -24, bottom: 0 }}>
                  <XAxis dataKey="label" tickLine={false} axisLine={false} minTickGap={10} />
                  <YAxis allowDecimals={false} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{ fill: 'var(--bg-hover)' }} content={<ChartTip />} />
                  <Bar dataKey="count" name="Predictions" fill="var(--primary)" radius={[6, 6, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : <div className="empty" style={{ padding: 30 }}><p className="small">No predictions yet.</p></div>}
          </div>
        </Card>

        <Card title="Users by plan" icon={Users}>
          <div className="row" style={{ height: 180 }}>
            <div style={{ width: 150, height: 150 }}>
              <ResponsiveContainer>
                <PieChart>
                  <Pie data={roles} dataKey="value" nameKey="name" innerRadius={44} outerRadius={70} paddingAngle={3} stroke="none">
                    {roles.map((r) => <Cell key={r.name} fill={ROLE_COLORS[r.name] || '#888'} />)}
                  </Pie>
                  <Tooltip content={<ChartTip render={(d) => <><div className="t" style={{ textTransform: 'capitalize' }}>{d.name}</div><b className="mono">{d.value}</b> users</>} />} />
                </PieChart>
              </ResponsiveContainer>
            </div>
            <div className="col grow" style={{ gap: 8 }}>
              {roles.map((r) => (
                <div key={r.name} className="row between small">
                  <span className="row gap-8" style={{ textTransform: 'capitalize' }}><i className="status-dot" style={{ background: ROLE_COLORS[r.name] }} />{r.name}</span>
                  <b className="mono">{r.value}</b>
                </div>
              ))}
            </div>
          </div>
        </Card>
      </div>

      <Card title="Latest backtest vs targets" icon={Target}
        subtitle={bt ? `${bt.name} · ${bt.total_matches} matches · ${fmtDate(bt.from_date)} → ${fmtDate(bt.to_date)}` : 'Run a backtest from the Jobs tab'}>
        {!bt ? <p className="small">No backtests yet.</p> : (
          <div className="grid-2" style={{ gap: 28 }}>
            <div>
              <Kpi label="Captain accuracy" value={bt.captain_accuracy} display={pct(bt.captain_accuracy, 1)} max={0.6}
                marks={[{ label: 'random 9.1%', value: 0.091, color: 'var(--text-muted)' }, { label: 'target 38%', value: 0.38, color: 'var(--captain)' }]}
                hint="Our captain was the match's top fantasy scorer" />
              <Kpi label="Top-3 captain rate" value={bt.top3_captain_rate} display={pct(bt.top3_captain_rate, 1)} max={1}
                marks={[{ label: 'random 27.3%', value: 0.273, color: 'var(--text-muted)' }, { label: 'target 70%', value: 0.7, color: 'var(--captain)' }]}
                hint="Top scorer was among our three captain options" />
            </div>
            <div>
              <Kpi label="Correct-player rate (≥7 of 11)" value={bt.correct_player_rate} display={pct(bt.correct_player_rate, 1)} max={1}
                marks={[{ label: 'random 31%', value: 0.312, color: 'var(--text-muted)' }, { label: 'target 60%', value: 0.6, color: 'var(--captain)' }]} />
              <Kpi label="Avg players in actual top-11" value={bt.avg_players_correct || 0} display={fmt(bt.avg_players_correct, 2)} max={11}
                marks={[{ label: '7', value: 7, color: 'var(--captain)' }]}
                hint={`Spearman ρ ${fmt(bt.spearman_rho, 3)} · team FP error ${fmt(bt.avg_fp_error, 1)} · simulated ROI ${pct(bt.simulated_roi, 1)}`} />
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
