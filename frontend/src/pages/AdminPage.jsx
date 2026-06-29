import { useQuery, useMutation } from '@tanstack/react-query'
import { getAdminMetrics, triggerIngest, triggerRetrain } from '../api/client'
import { RadarChart, Radar, PolarGrid, PolarAngleAxis, Tooltip, ResponsiveContainer } from 'recharts'

const MOCK_METRICS = {
  total_matches: 22062, total_players: 4831, total_users: 147, total_predictions: 2341,
  captain_accuracy: 0.38, correct_player_rate: 0.61, avg_fp_error: 8.2,
  active_model_version: 'v0.5-ensemble', system_health: 'ok',
}

const RADAR_DATA = [
  { metric: 'Captain Acc.', value: 38 },
  { metric: 'Player Rate', value: 61 },
  { metric: 'FP Accuracy', value: 72 },
  { metric: 'Coverage', value: 95 },
  { metric: 'Latency', value: 90 },
]

export default function AdminPage() {
  const { data: metrics = MOCK_METRICS } = useQuery({
    queryKey: ['admin-metrics'],
    queryFn: getAdminMetrics,
    retry: false,
  })

  const ingestMutation = useMutation({ mutationFn: () => triggerIngest({ source: 'cricsheet_latest', incremental: true }) })
  const retrainMutation = useMutation({ mutationFn: () => triggerRetrain({ format: 'T20', model_ids: ['M-01', 'M-02', 'M-03'] }) })

  const METRIC_CARDS = [
    { label: 'Total Matches', value: metrics.total_matches?.toLocaleString(), icon: '🏏', color: 'var(--color-primary-light)' },
    { label: 'Players Indexed', value: metrics.total_players?.toLocaleString(), icon: '👤', color: 'var(--color-success)' },
    { label: 'Total Users', value: metrics.total_users?.toLocaleString(), icon: '👥', color: 'var(--color-secondary)' },
    { label: 'Predictions Run', value: metrics.total_predictions?.toLocaleString(), icon: '🤖', color: 'var(--color-primary)' },
    { label: 'Captain Accuracy', value: metrics.captain_accuracy ? `${(metrics.captain_accuracy * 100).toFixed(1)}%` : 'N/A', icon: '⭐', color: 'var(--color-captain)' },
    { label: 'Player Accuracy', value: metrics.correct_player_rate ? `${(metrics.correct_player_rate * 100).toFixed(1)}%` : 'N/A', icon: '✅', color: 'var(--color-success)' },
    { label: 'Avg FP Error', value: metrics.avg_fp_error ? `${metrics.avg_fp_error.toFixed(1)} pts` : 'N/A', icon: '📊', color: 'var(--color-warning)' },
    { label: 'Active Model', value: metrics.active_model_version || 'None', icon: '🧠', color: 'var(--color-primary-light)' },
  ]

  return (
    <div className="page">
      <div className="container">
        <div className="flex justify-between items-center mb-8" style={{ flexWrap: 'wrap', gap: 'var(--sp-4)' }}>
          <div>
            <h1 className="page-title">🛠️ Admin Dashboard</h1>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
              <span className={`badge ${metrics.system_health === 'ok' ? 'badge-success' : 'badge-live'}`}>
                ● System {metrics.system_health?.toUpperCase()}
              </span>
            </div>
          </div>
          <div className="flex gap-3">
            <button className="btn btn-secondary" onClick={() => ingestMutation.mutate()} disabled={ingestMutation.isPending}>
              {ingestMutation.isPending ? '⏳' : '📥'} Ingest Data
            </button>
            <button className="btn btn-primary" onClick={() => retrainMutation.mutate()} disabled={retrainMutation.isPending}>
              {retrainMutation.isPending ? '⏳' : '🧠'} Retrain Models
            </button>
          </div>
        </div>

        {/* Metric cards */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))', gap: 'var(--sp-4)', marginBottom: 'var(--sp-8)' }}>
          {METRIC_CARDS.map(m => (
            <div key={m.label} className="metric-card fade-in">
              <div style={{ fontSize: 28, marginBottom: 8 }}>{m.icon}</div>
              <div className="metric-value" style={{ color: m.color }}>{m.value}</div>
              <div className="metric-label">{m.label}</div>
            </div>
          ))}
        </div>

        {/* Radar chart */}
        <div className="card mb-8">
          <h3 style={{ marginBottom: 'var(--sp-6)' }}>📈 Model Performance Radar</h3>
          <ResponsiveContainer width="100%" height={280}>
            <RadarChart data={RADAR_DATA}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="metric" tick={{ fill: 'var(--text-secondary)', fontSize: 12 }} />
              <Radar name="Performance" dataKey="value" stroke="var(--color-primary)" fill="var(--color-primary)" fillOpacity={0.2} />
              <Tooltip contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--border)', borderRadius: 8, color: 'var(--text-primary)' }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>

        {/* Task status */}
        {(ingestMutation.data || retrainMutation.data) && (
          <div className="card">
            <h3 style={{ marginBottom: 'var(--sp-4)' }}>⚙️ Task Status</h3>
            {ingestMutation.data && (
              <div style={{ padding: 'var(--sp-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--color-success)' }}>
                ✓ Ingest queued: {JSON.stringify(ingestMutation.data)}
              </div>
            )}
            {retrainMutation.data && (
              <div style={{ padding: 'var(--sp-3)', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--color-success)', marginTop: 8 }}>
                ✓ Retrain queued: {JSON.stringify(retrainMutation.data)}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
