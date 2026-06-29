const roleColors = { WK: 'wk', BAT: 'bat', BOWL: 'bowl', AR: 'ar' }
const roleEmoji = { WK: '🧤', BAT: '🏏', BOWL: '⚡', AR: '🔥' }

function ConfidenceBar({ confidence }) {
  const cls = confidence >= 70 ? 'confidence-high' : confidence >= 50 ? 'confidence-medium' : 'confidence-low'
  return (
    <div className="confidence-bar" style={{ marginTop: 6 }}>
      <div className={`confidence-bar-fill ${cls}`} style={{ width: `${confidence}%` }} />
    </div>
  )
}

export default function PlayerCard({ player, isCaptain, isVC, onClick }) {
  const roleCls = roleColors[player.role] || 'bat'
  const cardCls = `player-card ${isCaptain ? 'captain-card' : isVC ? 'vc-card' : ''}`

  return (
    <div className={cardCls} onClick={() => onClick?.(player)}>
      {isCaptain && (
        <span className="badge badge-captain" style={{ position: 'absolute', top: 8, right: 8 }}>C</span>
      )}
      {isVC && !isCaptain && (
        <span className="badge badge-vc" style={{ position: 'absolute', top: 8, right: 8 }}>VC</span>
      )}
      {player.is_differential && (
        <span className="badge" style={{ position: 'absolute', top: 8, left: 8, background: 'rgba(245,158,11,0.1)', color: 'var(--color-secondary)', border: '1px solid rgba(245,158,11,0.3)', fontSize: 9 }}>
          DIFF
        </span>
      )}

      <div className="flex items-center gap-3" style={{ marginBottom: 8 }}>
        <div className={`player-avatar badge-${roleCls}`} style={{ background: `rgba(var(--color-${roleCls}-rgb, 96,165,250),0.15)` }}>
          {roleEmoji[player.role]}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 600, fontSize: 'var(--text-md)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {player.full_name}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginTop: 2 }}>
            <span className={`badge badge-${roleCls}`}>{player.role}</span>
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
              {player.credits}cr
            </span>
          </div>
        </div>
      </div>

      <div className="flex justify-between" style={{ fontSize: 'var(--text-sm)' }}>
        <div>
          <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Pred FP</div>
          <div style={{ fontWeight: 700, color: 'var(--color-primary-light)', fontFamily: 'var(--font-mono)' }}>
            {player.predicted_fp?.toFixed(1)}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Ceiling</div>
          <div style={{ fontWeight: 700, color: 'var(--color-success)', fontFamily: 'var(--font-mono)' }}>
            {player.fp_ceiling?.toFixed(0)}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ color: 'var(--text-muted)', fontSize: 10, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Own%</div>
          <div style={{ fontWeight: 600, color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>
            {player.ownership_estimate}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 8 }}>
        <div className="flex justify-between" style={{ fontSize: 10, color: 'var(--text-muted)', marginBottom: 2 }}>
          <span>Confidence</span>
          <span>{player.confidence}%</span>
        </div>
        <ConfidenceBar confidence={player.confidence} />
      </div>
    </div>
  )
}
