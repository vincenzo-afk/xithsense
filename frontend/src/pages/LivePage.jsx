import { useEffect, useRef, useState } from 'react'
import { useParams, Link } from 'react-router-dom'

export default function LivePage() {
  const { matchId } = useParams()
  const [events, setEvents] = useState([])
  const [connected, setConnected] = useState(false)
  const [winProb, setWinProb] = useState({ team_a: 50, team_b: 50 })
  const wsRef = useRef(null)

  useEffect(() => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/api/v1/matches/${matchId}/live`

    try {
      wsRef.current = new WebSocket(wsUrl)
      wsRef.current.onopen = () => setConnected(true)
      wsRef.current.onmessage = (e) => {
        const data = JSON.parse(e.data)
        setEvents(prev => [data, ...prev.slice(0, 19)])
        if (data.win_probability) {
          setWinProb({
            team_a: data.win_probability.team_a,
            team_b: 100 - data.win_probability.team_a,
          })
        }
      }
      wsRef.current.onerror = () => {
        // Simulate live data when WS is unavailable (dev)
        const interval = setInterval(() => {
          const over = Math.floor(Math.random() * 20)
          const runs = Math.floor(Math.random() * 180) + 50
          const prob = Math.min(85, Math.max(15, 50 + (Math.random() - 0.5) * 40))
          setEvents(prev => [{
            over, runs_so_far: runs,
            win_probability: { team_a: parseFloat(prob.toFixed(1)) },
            event: `Over ${over}: ${Math.floor(Math.random() * 24)} runs`
          }, ...prev.slice(0, 19)])
          setWinProb({ team_a: parseFloat(prob.toFixed(1)), team_b: parseFloat((100 - prob).toFixed(1)) })
        }, 4000)
        return () => clearInterval(interval)
      }
      wsRef.current.onclose = () => setConnected(false)
    } catch (e) { /* WS not available */ }

    return () => wsRef.current?.close()
  }, [matchId])

  return (
    <div className="page">
      <div className="container">
        <div className="flex justify-between items-center mb-6">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <h1 style={{ fontSize: 'var(--text-xl)' }}>📡 Live Intelligence</h1>
              <span className={`badge ${connected ? 'badge-success' : 'badge-live'}`}>
                ● {connected ? 'LIVE' : 'DEMO'}
              </span>
            </div>
            <p>Match ID: {matchId}</p>
          </div>
          <Link to={`/matches/${matchId}`} className="btn btn-secondary btn-sm">← Back to Predictions</Link>
        </div>

        {/* Win probability */}
        <div className="card mb-6">
          <h3 style={{ marginBottom: 'var(--sp-4)' }}>Win Probability</h3>
          <div className="flex justify-between mb-2" style={{ fontSize: 'var(--text-sm)', fontWeight: 600 }}>
            <span style={{ color: 'var(--color-primary-light)' }}>Team A — {winProb.team_a}%</span>
            <span style={{ color: 'var(--color-secondary)' }}>{winProb.team_b}% — Team B</span>
          </div>
          <div className="live-bar">
            <div className="live-bar-fill" style={{ width: `${winProb.team_a}%` }} />
          </div>
        </div>

        {/* Event feed */}
        <div className="card">
          <h3 style={{ marginBottom: 'var(--sp-4)' }}>Over-by-Over Updates</h3>
          {events.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 'var(--sp-10)', color: 'var(--text-muted)' }}>
              <div style={{ fontSize: 40, marginBottom: 'var(--sp-4)' }}>📡</div>
              <p>Connecting to live feed... ({connected ? 'Connected' : 'Waiting'})</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--sp-2)' }}>
              {events.map((e, i) => (
                <div key={i} className="card-elevated fade-in" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div>
                    <span style={{ fontFamily: 'var(--font-mono)', color: 'var(--color-primary-light)', fontWeight: 700 }}>
                      Over {e.over}
                    </span>
                    <span style={{ marginLeft: 12, color: 'var(--text-secondary)', fontSize: 'var(--text-sm)' }}>
                      {e.event || `${e.runs_so_far} runs scored`}
                    </span>
                  </div>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>
                    Win: {e.win_probability?.team_a?.toFixed(1)}%
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
