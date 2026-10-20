import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { BrainCircuit, ChevronRight, Crown, Lock, Minus, Sparkles, TrendingDown, TrendingUp } from 'lucide-react'
import { apiError, explainPlayer } from '../../api/client'
import { useUiStore } from '../../store/uiStore'
import { confidenceLevel, fmt } from '../../lib/format'
import {
  Alert, Badge, Button, ConfidenceRing, Drawer, Meter, PlayerAvatar, RoleBadge, Skeleton,
} from '../ui'

const SENTIMENT_ICON = { positive: TrendingUp, negative: TrendingDown, neutral: Minus }
const BREAKDOWN = [
  ['ml_score_norm', 'Model projection', 'var(--primary)'],
  ['human_rules_score_norm', 'Analyst rules', 'var(--captain)'],
  ['form_score_norm', 'Recent form', 'var(--success)'],
  ['live_score_norm', 'Live context', 'var(--cyan)'],
]

function RangeBar({ floor, predicted, ceiling }) {
  const max = Math.max(ceiling * 1.1, 10)
  const at = (v) => `${Math.max(0, Math.min(100, (v / max) * 100))}%`
  return (
    <div>
      <div className="range-track">
        <div className="fill" style={{ left: at(floor), right: `calc(100% - ${at(ceiling)})` }} />
        <div className="mark" style={{ left: at(predicted) }} />
      </div>
      <div className="row between xs muted mono"><span>Floor {fmt(floor, 0)}</span><span>Projected {fmt(predicted, 0)}</span><span>Ceiling {fmt(ceiling, 0)}</span></div>
    </div>
  )
}

export default function PlayerDrawer({ matchId, player, onClose }) {
  const showUpgrade = useUiStore((s) => s.showUpgrade)
  const open = !!player
  const { data, isLoading, error } = useQuery({
    queryKey: ['explain', matchId, player?.player_id],
    queryFn: () => explainPlayer(matchId, player.player_id),
    enabled: open,
    staleTime: 10 * 60_000,
  })
  const err = error && apiError(error)
  const limited = err?.status === 402

  const info = data ? { ...player, ...data } : player
  const header = info && (
    <div className="row" style={{ minWidth: 0 }}>
      <PlayerAvatar name={info.full_name} role={info.role} size={44} />
      <div className="grow">
        <div className="bold truncate" style={{ fontSize: 16 }}>{info.full_name}</div>
        <div className="row gap-6 mt-4">
          {info.role && <RoleBadge role={info.role} />}
          <span className="muted small truncate">{info.team}{info.credits ? ` · ${fmt(info.credits)} cr` : ''}</span>
        </div>
      </div>
    </div>
  )

  return (
    <Drawer open={open} onClose={onClose} header={header}>
      {isLoading && <div className="col"><Skeleton h={74} /><Skeleton h={40} /><Skeleton h={90} /><Skeleton h={56} /><Skeleton h={56} /></div>}

      {limited && (
        <div className="empty">
          <div className="empty-icon" style={{ background: 'var(--secondary-soft)', color: 'var(--captain)' }}><Lock size={22} /></div>
          <h3>Explanation limit reached</h3>
          <p>{err.message} Premium includes unlimited, full-depth explanations with analyst rules and the score breakdown.</p>
          <Button variant="gold" icon={Crown} onClick={() => { onClose(); showUpgrade({ feature: 'Unlimited explanations', message: err.message }) }}>Upgrade to Premium</Button>
        </div>
      )}
      {err && !limited && <Alert tone="danger" title="Couldn't load explanation">{err.message}</Alert>}

      {data && (
        <div className="col fade-in" style={{ gap: 20 }}>
          <div className="drawer-hero">
            <div><span>Projected</span><b className="text-success">{fmt(data.predicted_fp, 0)}</b></div>
            <div><span>Ceiling</span><b>{fmt(data.fp_ceiling, 0)}</b></div>
            <div><span>Ownership</span><b style={{ color: 'var(--cyan)' }}>{data.ownership_estimate}</b></div>
          </div>
          <RangeBar floor={data.fp_floor} predicted={data.predicted_fp} ceiling={data.fp_ceiling} />

          <div className="card-elevated row">
            <ConfidenceRing value={data.confidence} size={52} stroke={5} />
            <div className="grow">
              <div className="bold">{confidenceLevel(data.confidence).label} confidence</div>
              <div className="small muted">How sure XithSense is about this projection</div>
            </div>
          </div>

          <div>
            <div className="row between mb-8">
              <span className="upper muted">Why this pick</span>
              {data.explanation_source === 'llm'
                ? <Badge tone="primary"><Sparkles size={11} />AI written</Badge>
                : <Badge><BrainCircuit size={11} />Data summary</Badge>}
            </div>
            <p style={{ color: 'var(--text)', lineHeight: 1.65 }}>{data.explanation}</p>
            {data.depth === 'basic' && (
              <Alert tone="info">
                Basic view — showing the top factors only.{' '}
                <button className="text-primary bold" onClick={() => { onClose(); showUpgrade({ feature: 'Full explanations', message: 'See every factor, analyst rule and the full score breakdown.' }) }}>Unlock full depth</button>
              </Alert>
            )}
          </div>

          {data.factors?.length > 0 && (
            <div>
              <div className="upper muted mb-8">Key factors</div>
              {data.factors.map((f, i) => {
                const Icon = SENTIMENT_ICON[f.sentiment] || Minus
                return (
                  <div key={i} className={`factor f-${f.sentiment}`}>
                    <span className="f-icon"><Icon size={15} /></span>
                    <div style={{ minWidth: 0 }}><div className="bold small">{f.factor}</div><div className="xs muted">{f.detail}</div></div>
                    <span className="mono small bold text-right">{f.value}</span>
                  </div>
                )
              })}
            </div>
          )}

          {data.rules_detail?.length > 0 && (
            <div>
              <div className="upper muted mb-8">Analyst rules fired</div>
              {data.rules_detail.map((r) => (
                <div key={r.id} className="rule-item">
                  <Badge tone={r.impact >= 0 ? 'success' : 'danger'} className="mono">{r.id}</Badge>
                  <span className="secondary">{r.description}</span>
                  <b className={`mono ${r.impact >= 0 ? 'text-success' : 'text-danger'}`}>{r.impact > 0 ? '+' : ''}{fmt(r.impact)}</b>
                </div>
              ))}
            </div>
          )}

          {data.ensemble_breakdown && (
            <div>
              <div className="upper muted mb-8">Score breakdown <span className="xs" style={{ textTransform: 'none', letterSpacing: 0 }}>(0–100, relative to this match)</span></div>
              {BREAKDOWN.map(([k, label, color]) => (
                <div key={k} className="mini-bar">
                  <span className="secondary">{label}</span>
                  <Meter value={data.ensemble_breakdown[k] ?? 0} color={color} height={7} />
                  <span className="mono text-right">{fmt(data.ensemble_breakdown[k], 0)}</span>
                </div>
              ))}
            </div>
          )}

          <Link to={`/players/${data.player_id}`} className="btn btn-secondary btn-block" onClick={onClose}>
            View full profile <ChevronRight size={16} />
          </Link>
        </div>
      )}
    </Drawer>
  )
}
