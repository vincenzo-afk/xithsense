export default function MatchCard({ match, onClick }) {
  const formatDate = (d) => new Date(d).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })

  return (
    <div className="match-card" onClick={() => onClick?.(match)}>
      <div className="flex justify-between items-center" style={{ marginBottom: 12 }}>
        <div className="flex gap-2 items-center">
          <span className="badge" style={{ background: 'rgba(99,102,241,0.15)', color: 'var(--color-primary-light)', border: '1px solid rgba(99,102,241,0.3)' }}>
            {match.match_type}
          </span>
          {match.is_live && <span className="badge badge-live">● LIVE</span>}
          {match.prediction_ready && !match.is_live && (
            <span className="badge badge-success">AI READY</span>
          )}
        </div>
        <span style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
          {formatDate(match.match_date)}
        </span>
      </div>

      <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
            {match.team_a?.split(' ').map(w => w[0]).join('').slice(0, 3)}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 2 }}>
            {match.team_a}
          </div>
        </div>
        <div style={{ padding: '8px 16px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontWeight: 800, fontSize: 'var(--text-md)', color: 'var(--text-muted)' }}>
          VS
        </div>
        <div style={{ textAlign: 'center', flex: 1 }}>
          <div style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
            {match.team_b?.split(' ').map(w => w[0]).join('').slice(0, 3)}
          </div>
          <div style={{ fontSize: 'var(--text-sm)', color: 'var(--text-secondary)', marginTop: 2 }}>
            {match.team_b}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2" style={{ color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
        <span>📍</span>
        <span>{match.venue_name || 'Venue TBD'}</span>
      </div>
      {match.event_name && (
        <div style={{ marginTop: 6, fontSize: 'var(--text-sm)', color: 'var(--color-primary-light)' }}>
          🏆 {match.event_name}
        </div>
      )}
    </div>
  )
}
