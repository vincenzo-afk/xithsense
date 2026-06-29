import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getPlayer, getPlayerMatchups } from '../api/client'

export default function PlayerPage() {
  const { playerId } = useParams()
  const { data: player, isLoading } = useQuery({
    queryKey: ['player', playerId],
    queryFn: () => getPlayer(playerId),
    retry: false,
  })
  const { data: matchupsData } = useQuery({
    queryKey: ['matchups', playerId],
    queryFn: () => getPlayerMatchups(playerId),
    retry: false,
  })

  if (isLoading) return (
    <div className="page"><div className="container"><div className="skeleton" style={{ height: 300 }} /></div></div>
  )

  if (!player) return (
    <div className="page"><div className="container">
      <div className="card text-center" style={{ padding: 'var(--sp-12)' }}>
        <div style={{ fontSize: 48, marginBottom: 'var(--sp-4)' }}>❓</div>
        <h3>Player not found</h3>
        <Link to="/matches" className="btn btn-primary mt-4">← Back to Matches</Link>
      </div>
    </div></div>
  )

  const form = player.recent_form

  return (
    <div className="page">
      <div className="container" style={{ maxWidth: 800 }}>
        <Link to="/matches" style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)', display: 'inline-flex', alignItems: 'center', gap: 4, marginBottom: 'var(--sp-6)' }}>
          ← Back
        </Link>

        {/* Player header */}
        <div className="card mb-6">
          <div className="flex items-center gap-4">
            <div style={{
              width: 80, height: 80, borderRadius: '50%',
              background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 36, flexShrink: 0,
            }}>
              {player.primary_role === 'WK' ? '🧤' : player.primary_role === 'BOWL' ? '⚡' : player.primary_role === 'AR' ? '🔥' : '🏏'}
            </div>
            <div>
              <h1 style={{ marginBottom: 8 }}>{player.full_name}</h1>
              <div className="flex gap-2 flex-wrap">
                <span className={`badge badge-${(player.primary_role || 'bat').toLowerCase()}`}>{player.primary_role}</span>
                {player.nationality && <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>🌍 {player.nationality}</span>}
                {player.batting_style && <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>{player.batting_style}</span>}
                {player.bowling_style && <span className="badge" style={{ background: 'var(--bg-elevated)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}>{player.bowling_style}</span>}
              </div>
            </div>
          </div>
        </div>

        {/* Recent form */}
        {form && (
          <div className="card mb-6">
            <h3 style={{ marginBottom: 'var(--sp-4)' }}>📊 Recent Form</h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 'var(--sp-4)' }}>
              {[
                { label: 'Last 3 FP Avg', value: form.last_3_fp_avg?.toFixed(1) },
                { label: 'Last 5 FP Avg', value: form.last_5_fp_avg?.toFixed(1) },
                { label: 'Last 10 FP Avg', value: form.last_10_fp_avg?.toFixed(1) },
                { label: 'FP Ceiling', value: form.fp_ceiling?.toFixed(1), color: 'var(--color-success)' },
                { label: 'FP Floor', value: form.fp_floor?.toFixed(1), color: 'var(--color-danger)' },
                { label: 'Consistency', value: form.fp_consistency ? `${(form.fp_consistency * 100).toFixed(0)}%` : 'N/A', color: 'var(--color-warning)' },
              ].map(s => (
                <div key={s.label} className="metric-card">
                  <div className="metric-value" style={{ color: s.color || 'var(--color-primary-light)' }}>{s.value ?? 'N/A'}</div>
                  <div className="metric-label">{s.label}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Matchups */}
        {matchupsData?.matchups?.length > 0 && (
          <div className="card">
            <h3 style={{ marginBottom: 'var(--sp-4)' }}>🎯 Matchup Breakdown</h3>
            <div style={{ overflowX: 'auto' }}>
              <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border)' }}>
                    {['Bowler Type', 'Balls Faced', 'Strike Rate', 'Avg Runs', 'Boundary %'].map(h => (
                      <th key={h} style={{ padding: 'var(--sp-3)', textAlign: 'left', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {matchupsData.matchups.map(m => (
                    <tr key={m.bowler_type} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                      <td style={{ padding: 'var(--sp-3)', fontWeight: 600 }}>{m.bowler_type.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}</td>
                      <td style={{ padding: 'var(--sp-3)', fontFamily: 'var(--font-mono)' }}>{m.balls_faced}</td>
                      <td style={{ padding: 'var(--sp-3)', fontFamily: 'var(--font-mono)', color: m.strike_rate > 130 ? 'var(--color-success)' : m.strike_rate < 80 ? 'var(--color-danger)' : 'var(--text-primary)' }}>{m.strike_rate?.toFixed(1)}</td>
                      <td style={{ padding: 'var(--sp-3)', fontFamily: 'var(--font-mono)' }}>{m.avg_runs?.toFixed(1)}</td>
                      <td style={{ padding: 'var(--sp-3)', fontFamily: 'var(--font-mono)' }}>{m.boundary_rate ? `${(m.boundary_rate * 100).toFixed(0)}%` : '-'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
