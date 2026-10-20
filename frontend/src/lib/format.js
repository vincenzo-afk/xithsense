/** Team identity, number/date formatting and confidence helpers shared across pages. */

export const TEAMS = {
  'Mumbai Indians': { short: 'MI', color: '#0b5cc4' },
  'Royal Challengers Bengaluru': { short: 'RCB', color: '#d1171b' },
  'Chennai Super Kings': { short: 'CSK', color: '#e5b80b' },
  'Kolkata Knight Riders': { short: 'KKR', color: '#5b2d90' },
  'Gujarat Titans': { short: 'GT', color: '#1c3f7a' },
  'Rajasthan Royals': { short: 'RR', color: '#e7348f' },
  'Sunrisers Hyderabad': { short: 'SRH', color: '#f26522' },
  'Delhi Capitals': { short: 'DC', color: '#1f5bd1' },
  'Punjab Kings': { short: 'PBKS', color: '#d71920' },
  'Lucknow Super Giants': { short: 'LSG', color: '#00a6e0' },
}

const PALETTE = ['#6366f1', '#0ea5e9', '#10b981', '#f59e0b', '#ef4444', '#a855f7', '#14b8a6', '#f97316']

/** Provider team metadata (short code + logo) registered from match payloads. */
const REGISTRY = {}

export function registerTeams(teamInfo) {
  if (!teamInfo) return
  for (const [name, info] of Object.entries(teamInfo)) {
    if (!name || !info) continue
    REGISTRY[name] = { ...(REGISTRY[name] || {}), ...(info.short ? { short: info.short } : {}), ...(info.img ? { img: info.img } : {}) }
  }
}

/** Register team_info from a list of matches (or a single match). */
export function registerMatches(matches) {
  for (const m of Array.isArray(matches) ? matches : [matches]) if (m?.team_info) registerTeams(m.team_info)
}

export function team(name = '') {
  const base = (name || '').replace(/\s+Women$/i, '').trim()
  const known = TEAMS[name] || TEAMS[base]
  const reg = REGISTRY[name] || {}
  let h = 0
  for (const c of base) h = (h * 31 + c.charCodeAt(0)) >>> 0
  const words = base.split(/\s+/).filter(Boolean)
  const derived = words.length > 1 ? words.map((w) => w[0]).join('').slice(0, 3).toUpperCase() : base.slice(0, 3).toUpperCase()
  return {
    name,
    short: reg.short || known?.short || derived,
    color: known?.color || PALETTE[h % PALETTE.length],
    img: reg.img || null,
  }
}

export const initials = (name = '') =>
  name.split(/\s+/).filter(Boolean).map((w) => w[0]).join('').slice(0, 2).toUpperCase() || '?'

export const shortVenue = (v = '') => (v || 'Venue TBC').split(',')[0]

export function confidenceLevel(c = 0) {
  if (c >= 80) return { label: 'High', cls: 'c-high', color: 'var(--success)', badge: 'badge-success' }
  if (c >= 60) return { label: 'Medium', cls: 'c-medium', color: 'var(--warning)', badge: 'badge-warning' }
  if (c >= 40) return { label: 'Low', cls: 'c-low', color: 'var(--danger)', badge: 'badge-danger' }
  return { label: 'Very Low', cls: 'c-vlow', color: 'var(--gray)', badge: 'badge-gray' }
}

export const ROLE_ORDER = ['WK', 'BAT', 'AR', 'BOWL']
export const ROLE_NAMES = { WK: 'Wicket-keepers', BAT: 'Batters', AR: 'All-rounders', BOWL: 'Bowlers' }
export const ROLE_COLORS = { WK: 'var(--wk)', BAT: 'var(--bat)', AR: 'var(--ar)', BOWL: 'var(--bowl)' }

export const BOWLER_TYPES = {
  pace_right: 'Right-arm pace',
  pace_left: 'Left-arm pace',
  spin_off: 'Off-spin',
  spin_left: 'Left-arm orthodox',
  spin_wrist: 'Wrist spin',
}

export const MODES = {
  safe: { label: 'Safe', short: 'Safe' },
  grand_league: { label: 'Grand League', short: 'GL' },
  aggressive: { label: 'Aggressive', short: 'AGG' },
  small_league: { label: 'Small League', short: 'SL' },
}

export const fmt = (n, d = 1) => (n == null || Number.isNaN(n) ? '—' : Number(n).toFixed(d))
export const fmtInt = (n) => (n == null ? '—' : Number(n).toLocaleString('en-IN'))
export const pct = (n, d = 0) => (n == null ? '—' : `${(n * 100).toFixed(d)}%`)

export function matchStart(m) {
  if (m?.start_time) return new Date(m.start_time)
  if (m?.match_date) return new Date(`${m.match_date}T19:30:00+05:30`)
  return null
}

export function fmtDate(d, opts = { day: 'numeric', month: 'short' }) {
  if (!d) return '—'
  return new Date(d).toLocaleDateString('en-IN', opts)
}

export function fmtTime(d) {
  if (!d) return ''
  return new Date(d).toLocaleTimeString('en-IN', { hour: 'numeric', minute: '2-digit' })
}

export function relativeDay(d) {
  if (!d) return ''
  const date = new Date(d)
  const today = new Date()
  const diff = Math.round((new Date(date.toDateString()) - new Date(today.toDateString())) / 86400000)
  if (diff === 0) return 'Today'
  if (diff === 1) return 'Tomorrow'
  if (diff === -1) return 'Yesterday'
  return date.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })
}

export function timeAgo(d) {
  const s = Math.max(0, (Date.now() - new Date(d).getTime()) / 1000)
  if (s < 60) return 'just now'
  if (s < 3600) return `${Math.floor(s / 60)}m ago`
  if (s < 86400) return `${Math.floor(s / 3600)}h ago`
  return `${Math.floor(s / 86400)}d ago`
}

export function countdownParts(target) {
  const ms = Math.max(0, new Date(target).getTime() - Date.now())
  return {
    done: ms === 0,
    d: Math.floor(ms / 86400000),
    h: Math.floor((ms % 86400000) / 3600000),
    m: Math.floor((ms % 3600000) / 60000),
    s: Math.floor((ms % 60000) / 1000),
  }
}

/** Plain-text Dream11-style team summary for the clipboard. */
export function teamToText(match, mode, t) {
  const by = (r) => t.players.filter((p) => p.role === r).map((p) => {
    const tag = p.player_id === t.captain.player_id ? ' (C)' : p.player_id === t.vice_captain.player_id ? ' (VC)' : ''
    return `${p.full_name}${tag}`
  })
  return [
    `XithSense ${MODES[mode]?.label || mode} XI — ${match?.team_a} vs ${match?.team_b}`,
    ...ROLE_ORDER.map((r) => `${r}: ${by(r).join(', ')}`),
    `Credits ${t.total_credits} · Projected ${Math.round(t.predicted_total_fp)} pts`,
  ].join('\n')
}

/** Innings from a provider score list, attributing each to a team (labels can name both sides). */
export function scoreInnings(m) {
  const score = m?.live_state?.score || []
  const teams = [m?.team_a, m?.team_b].filter(Boolean)
  const out = []
  score.forEach((s, i) => {
    const label = (s.inning || '').toLowerCase()
    const hits = teams.filter((t) => label.includes(t.toLowerCase().replace(/\s+women$/, '')))
    const bat = hits.length === 1 ? hits[0] : out.length ? (out[out.length - 1].team === teams[0] ? teams[1] : teams[0]) : teams[0]
    out.push({ number: i + 1, team: bat, runs: s.r ?? 0, wickets: s.w ?? 0, overs: s.o ?? 0 })
  })
  return out
}

/** "IND-W 216/7 (20) · ZIM-W 73/2 (12.2)" */
export function scoreLine(m) {
  return scoreInnings(m).map((i) => `${team(i.team).short} ${i.runs}/${i.wickets} (${i.overs})`).join(' · ')
}
