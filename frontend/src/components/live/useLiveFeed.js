import { useEffect, useRef, useState } from 'react'
import { liveSocketUrl } from '../../api/client'

const MAX_EVENTS = 60
const PING_MS = 25_000

/**
 * Live match WebSocket backed by the CricketData feed (integrations/live_feed.py).
 * The server polls the provider (score ~every 4 min, scorecard ~every 45 min) and pushes:
 *   connection_established · match_update · scorecard_update · player_update · wicket_fell ·
 *   feed_status · match_ended · error
 * status: connecting | live | reconnecting | ended | error
 * closeCode is set when the server rejects the socket (4401 auth, 4402 premium, 4404 not live, 4429 too many).
 */
export default function useLiveFeed(matchId) {
  const [status, setStatus] = useState('connecting')
  const [state, setState] = useState(null)
  const [events, setEvents] = useState([])
  const [players, setPlayers] = useState({})
  const [winHistory, setWinHistory] = useState([])
  const [ended, setEnded] = useState(null)
  const [closeCode, setCloseCode] = useState(null)
  const [error, setError] = useState(null)
  const [feedStatus, setFeedStatus] = useState(null)
  const [scorecardAt, setScorecardAt] = useState(null)
  const evtSeq = useRef(0)
  const lastStatusText = useRef(null)

  useEffect(() => {
    let ws = null
    let pingTimer = null
    let retryTimer = null
    let attempt = 0
    let disposed = false
    let hadConnection = false
    let finished = false

    const pushEvent = (e) => setEvents((prev) => [{ id: ++evtSeq.current, ts: Date.now(), ...e }, ...prev].slice(0, MAX_EVENTS))

    const mergePlayers = (rows) => {
      if (!Array.isArray(rows)) return
      setPlayers((prev) => {
        const next = { ...prev }
        for (const p of rows) {
          const key = p.player_id || p.full_name
          next[key] = {
            ...next[key], ...p,
            live_fp: p.live_fantasy_points ?? next[key]?.live_fp ?? 0,
            predicted_fp: p.predicted_fp ?? p.prediction_accuracy?.predicted_fp ?? next[key]?.predicted_fp,
          }
        }
        return next
      })
    }

    const onMessage = (raw) => {
      let m
      try { m = JSON.parse(raw.data) } catch { return }
      if (m.action === 'pong') return
      switch (m.event) {
        case 'connection_established':
          setStatus('live')
          attempt = 0
          break
        case 'match_update': {
          const { players: snap, feed_note: note, event: _e, match_id: _m, timestamp: _t, ...rest } = m
          setState((prev) => ({ ...prev, ...rest }))
          mergePlayers(snap)
          if (note !== undefined) setFeedStatus((prev) => ({ ...prev, note }))
          if (rest.status_text && rest.status_text !== lastStatusText.current) {
            if (lastStatusText.current) pushEvent({ kind: 'status', text: rest.status_text })
            lastStatusText.current = rest.status_text
          }
          if (rest.win_probability && rest.innings) {
            const inn = rest.innings
            setWinHistory((prev) => {
              const label = `Inns ${inn.number} · ${inn.overs} ov`
              if (prev.length && prev[prev.length - 1].label === label) return prev
              return [...prev, { i: prev.length, label, wp: rest.win_probability }].slice(-200)
            })
          }
          if (rest.status === 'complete') setStatus('ended')
          break
        }
        case 'scorecard_update':
          mergePlayers(m.players)
          setScorecardAt(m.fetched_at || new Date().toISOString())
          break
        case 'player_update':
          mergePlayers([m])
          break
        case 'wicket_fell':
          pushEvent({ kind: 'wicket', over: m.over, text: `Wicket — ${m.team || 'batting side'} ${m.score_at_fall}` })
          break
        case 'toss_update':
          pushEvent({ kind: 'toss', text: `${m.toss_winner} won the toss and chose to ${m.toss_decision}` })
          break
        case 'feed_status':
          setFeedStatus({ usage: m.api_usage, note: m.note, nextPoll: m.next_poll_seconds, at: Date.now() })
          break
        case 'match_ended':
          finished = true
          setEnded(m)
          setStatus('ended')
          pushEvent({ kind: 'result', text: m.result || 'Match ended' })
          break
        case 'error':
          setError(m)
          if (m.code === 'MATCH_NOT_LIVE') { finished = true; setCloseCode(4404); setStatus('error') }
          if (m.code === 'PREMIUM_REQUIRED') { finished = true; setCloseCode(4402); setStatus('error') }
          break
        default:
          break
      }
    }

    const connect = () => {
      if (disposed) return
      try {
        ws = new WebSocket(liveSocketUrl(matchId))
      } catch {
        setStatus('error')
        return
      }
      ws.onopen = () => {
        if (hadConnection) ws.send(JSON.stringify({ action: 'request_state' }))
        hadConnection = true
        clearInterval(pingTimer)
        pingTimer = setInterval(() => ws?.readyState === 1 && ws.send(JSON.stringify({ action: 'ping' })), PING_MS)
      }
      ws.onmessage = onMessage
      ws.onclose = (e) => {
        clearInterval(pingTimer)
        if (disposed) return
        if ([4401, 4402, 4404, 4429].includes(e.code)) {
          setCloseCode(e.code)
          setStatus('error')
          return
        }
        if (finished) { setStatus('ended'); return }
        if (!hadConnection && attempt >= 3) { setStatus('error'); setCloseCode(e.code || 1006); return }
        setStatus(hadConnection ? 'reconnecting' : 'connecting')
        const delay = Math.min(15_000, 1000 * 2 ** attempt) + Math.random() * 400
        attempt += 1
        retryTimer = setTimeout(connect, delay)
      }
    }

    connect()
    return () => {
      disposed = true
      clearInterval(pingTimer)
      clearTimeout(retryTimer)
      if (ws && ws.readyState <= 1) ws.close(1000)
    }
  }, [matchId])

  return { status, state, events, players, winHistory, ended, closeCode, error, feedStatus, scorecardAt }
}
