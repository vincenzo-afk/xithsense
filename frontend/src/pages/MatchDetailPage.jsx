import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery, useMutation } from '@tanstack/react-query'
import { predictTeam, getDifferentials, explainPlayer } from '../api/client'
import { useAuthStore } from '../store/authStore'
import PlayerCard from '../components/PlayerCard'

const MODES = [
  { id: 'safe', label: '🛡️ Safe', desc: 'High-confidence picks, low-risk team' },
  { id: 'grand_league', label: '🏆 Grand League', desc: 'Differentials + high-ceiling picks' },
  { id: 'aggressive', label: '⚡ Aggressive', desc: 'Maximum ceiling, high variance' },
  { id: 'small_league', label: '🎯 Small League', desc: 'Consistent players, 3-5 team contests' },
]

const DEMO_MATCH = {
  id: 'demo-001', match_type: 'IPL',
  team_a: 'Mumbai Indians', team_b: 'Royal Challengers Bengaluru',
  venue_name: 'Wankhede Stadium', match_date: '2026-04-15',
  event_name: 'Indian Premier League', toss_winner: 'Royal Challengers Bengaluru',
  toss_decision: 'bat',
}

export default function MatchDetailPage() {
  const { matchId } = useParams()
  const { isPremium } = useAuthStore()
  const [mode, setMode] = useState('safe')
  const [selectedTeam, setSelectedTeam] = useState(0)
  const [explainPlayerId, setExplainPlayerId] = useState(null)

  const predictMutation = useMutation({
    mutationFn: () => predictTeam({ match_id: matchId, mode, count: isPremium() ? 3 : 1 }),
  })

  const prediction = predictMutation.data
  const team = prediction?.teams?.[selectedTeam]

  return (
    <div className="page">
      <div className="container">
        {/* Match Header */}
        <div className="card mb-6" style={{ overflow: 'hidden' }}>
          <div style={{ height: 4, background: 'linear-gradient(90deg, var(--color-primary), var(--color-secondary))' }} />
          <div style={{ padding: 'var(--sp-6)' }}>
            <div className="flex justify-between items-center mb-4" style={{ flexWrap: 'wrap', gap: 'var(--sp-2)' }}>
              <div className="flex gap-2">
                <span className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: 'var(--color-primary-light)', border: '1px solid rgba(99,102,241,0.3)' }}>
                  {DEMO_MATCH.match_type}
                </span>
                <span className="badge badge-success">AI READY</span>
              </div>
              <Link to={`/matches/${matchId}/live`} className="btn btn-sm btn-secondary">
                📡 Live Feed →
              </Link>
            </div>

            <div className="flex items-center justify-between" style={{ marginBottom: 'var(--sp-4)' }}>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800 }}>MI</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 4 }}>{DEMO_MATCH.team_a}</div>
              </div>
              <div style={{ background: 'var(--bg-elevated)', padding: '12px 24px', borderRadius: 'var(--radius-lg)', fontWeight: 800, fontSize: 'var(--text-lg)', color: 'var(--text-muted)' }}>
                VS
              </div>
              <div style={{ textAlign: 'center', flex: 1 }}>
                <div style={{ fontSize: 'var(--text-2xl)', fontWeight: 800 }}>RCB</div>
                <div style={{ color: 'var(--text-secondary)', fontSize: 'var(--text-sm)', marginTop: 4 }}>{DEMO_MATCH.team_b}</div>
              </div>
            </div>

            <div className="flex gap-4" style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', flexWrap: 'wrap' }}>
              <span>📍 {DEMO_MATCH.venue_name}</span>
              <span>🏆 {DEMO_MATCH.event_name}</span>
              {DEMO_MATCH.toss_winner && <span>🪙 {DEMO_MATCH.toss_winner} won toss, chose to {DEMO_MATCH.toss_decision}</span>}
            </div>
          </div>
        </div>

        {/* Mode Selector */}
        <div className="mb-6">
          <h3 style={{ marginBottom: 'var(--sp-3)' }}>Team Strategy</h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--sp-3)' }}>
            {MODES.map(m => (
              <button key={m.id}
                onClick={() => !isPremium() && m.id !== 'safe' ? null : setMode(m.id)}
                className={`card ${mode === m.id ? 'glow-primary' : ''}`}
                style={{
                  textAlign: 'left',
                  cursor: !isPremium() && m.id !== 'safe' ? 'not-allowed' : 'pointer',
                  opacity: !isPremium() && m.id !== 'safe' ? 0.5 : 1,
                  border: mode === m.id ? '1px solid var(--color-primary)' : undefined,
                  padding: 'var(--sp-4)',
                }}>
                <div style={{ fontWeight: 600, marginBottom: 4 }}>{m.label}</div>
                <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>{m.desc}</div>
                {!isPremium() && m.id !== 'safe' && (
                  <span className="badge badge-premium" style={{ marginTop: 6 }}>PRO</span>
                )}
              </button>
            ))}
          </div>
        </div>

        {/* Generate Button */}
        <button
          className="btn btn-primary btn-lg w-full glow-primary mb-8"
          onClick={() => predictMutation.mutate()}
          disabled={predictMutation.isPending}
          style={{ maxWidth: 400, margin: '0 auto var(--sp-8)', display: 'flex' }}>
          {predictMutation.isPending ? '⏳ Generating teams...' : '🤖 Generate AI Team'}
        </button>

        {/* Results */}
        {prediction && (
          <div className="fade-in">
            {/* Team selector */}
            {prediction.teams.length > 1 && (
              <div className="tabs mb-6" style={{ maxWidth: 360 }}>
                {prediction.teams.map((_, i) => (
                  <button key={i} className={`tab${selectedTeam === i ? ' active' : ''}`} onClick={() => setSelectedTeam(i)}>
                    Team {i + 1}
                  </button>
                ))}
              </div>
            )}

            {team && (
              <>
                {/* Team stats */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--sp-3)', marginBottom: 'var(--sp-6)' }}>
                  <div className="metric-card">
                    <div className="metric-value" style={{ fontSize: 'var(--text-xl)' }}>
                      {team.total_credits?.toFixed(1)}
                    </div>
                    <div className="metric-label">Credits Used</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-value" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-success)' }}>
                      {team.predicted_total_fp?.toFixed(0)}
                    </div>
                    <div className="metric-label">Predicted FP</div>
                  </div>
                  <div className="metric-card">
                    <div className="metric-value" style={{ fontSize: 'var(--text-xl)', color: 'var(--color-secondary)' }}>
                      {team.team_ceiling?.toFixed(0)}
                    </div>
                    <div className="metric-label">Team Ceiling</div>
                  </div>
                </div>

                {/* Captain/VC */}
                <div className="flex gap-4 mb-6" style={{ flexWrap: 'wrap' }}>
                  {[{ label: '⭐ Captain', data: team.captain, cls: 'captain' }, { label: '⭐ Vice-Captain', data: team.vice_captain, cls: 'vc' }].map(({ label, data: d, cls }) => (
                    <div key={cls} className={`card flex-1`} style={{ minWidth: 240, border: `1px solid var(--color-${cls})` }}>
                      <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</div>
                      <div style={{ fontWeight: 700, fontSize: 'var(--text-lg)' }}>{d.full_name}</div>
                      <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 4 }}>{d.reasoning}</div>
                      <div style={{ marginTop: 8, display: 'flex', alignItems: 'center', gap: 4 }}>
                        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Confidence</span>
                        <div className="confidence-bar" style={{ flex: 1 }}>
                          <div className={`confidence-bar-fill ${d.confidence >= 70 ? 'confidence-high' : 'confidence-medium'}`} style={{ width: `${d.confidence}%` }} />
                        </div>
                        <span style={{ fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)' }}>{d.confidence}%</span>
                      </div>
                    </div>
                  ))}
                </div>

                {/* Players grid */}
                <h3 style={{ marginBottom: 'var(--sp-4)' }}>All 11 Players</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: 'var(--sp-3)' }}>
                  {team.players.map(player => (
                    <PlayerCard
                      key={player.player_id}
                      player={player}
                      isCaptain={player.player_id === team.captain.player_id}
                      isVC={player.player_id === team.vice_captain.player_id}
                      onClick={() => setExplainPlayerId(player.player_id)}
                    />
                  ))}
                </div>

                {/* Ensemble weights */}
                <div className="card mt-8">
                  <h4 style={{ marginBottom: 'var(--sp-4)' }}>🧪 Ensemble Weights</h4>
                  <div className="grid-4">
                    {Object.entries(prediction.ensemble_weights).map(([key, val]) => (
                      <div key={key} style={{ textAlign: 'center' }}>
                        <div style={{ fontWeight: 700, color: 'var(--color-primary-light)', fontFamily: 'var(--font-mono)' }}>{(val * 100).toFixed(0)}%</div>
                        <div style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'capitalize', marginTop: 2 }}>{key.replace('_', ' ')}</div>
                        <div className="confidence-bar" style={{ marginTop: 6 }}>
                          <div className="confidence-bar-fill confidence-high" style={{ width: `${val * 100}%` }} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
