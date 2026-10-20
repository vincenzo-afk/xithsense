import { useEffect, useMemo, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import {
  Activity, ArrowLeft, CheckCircle2, CircleDot, Clock, Crown, Flag, Gauge, Info, Loader2, Radio, Target, Trophy,
  Wifi, WifiOff, XCircle,
} from 'lucide-react'
import { getMatch } from '../api/client'
import useLiveFeed from '../components/live/useLiveFeed'
import {
  Alert, Badge, ButtonLink, Card, ChartTip, EmptyState, LiveBadge, Meter, RoleBadge, Skeleton, TeamCrest,
} from '../components/ui'
import { fmt, registerMatches, shortVenue, team, timeAgo } from '../lib/format'
import './ops.css'

const EVENT_STYLE = {
  wicket: { icon: XCircle, color: 'var(--danger)', label: 'Wicket' },
  status: { icon: CircleDot, color: 'var(--primary-light)', label: 'Update' },
  toss: { icon: CircleDot, color: 'var(--primary-light)', label: 'Toss' },
  result: { icon: Trophy, color: 'var(--captain)', label: 'Result' },
  innings: { icon: Flag, color: 'var(--warning)', label: 'Innings' },
}

function ConnStatus({ status }) {
  if (status === 'live') return <Badge tone="success"><Wifi size={11} />Connected</Badge>
  if (status === 'reconnecting') return <Badge tone="warning"><Loader2 size={11} className="spin" />Reconnecting</Badge>
  if (status === 'connecting') return <Badge tone="primary"><Loader2 size={11} className="spin" />Connecting</Badge>
  if (status === 'ended') return <Badge tone="gray"><CheckCircle2 size={11} />Final</Badge>
  return <Badge tone="danger"><WifiOff size={11} />Offline</Badge>
}

/** Re-render every 15s so "updated Xs ago" stays fresh. */
function useTick(ms = 15_000) {
  const [, set] = useState(0)
  useEffect(() => { const t = setInterval(() => set((x) => x + 1), ms); return () => clearInterval(t) }, [ms])
}

export default function LivePage() {
  const { matchId } = useParams()
  const navigate = useNavigate()
  const { data: match } = useQuery({ queryKey: ['match', matchId], queryFn: () => getMatch(matchId) })
  if (match) registerMatches(match)
  const feed = useLiveFeed(matchId)
  const { status, state, events, players, winHistory, ended, closeCode, feedStatus, scorecardAt } = feed
  useTick()

  useEffect(() => { if (closeCode === 4402) navigate('/subscribe', { replace: true }) }, [closeCode, navigate])

  const teamA = match?.team_a || state?.teams?.[0]
  const teamB = match?.team_b || state?.teams?.[1]
  const tA = team(teamA || '')
  const tB = team(teamB || '')
  const inn = state?.innings
  const inningsList = state?.innings_list || []

  const wp = state?.win_probability
  const pA = wp && teamA && wp[teamA] != null ? wp[teamA] : null
  const chart = winHistory.map((h) => ({ i: h.i, label: h.label, pA: Math.round((h.wp[teamA] ?? 0.5) * 1000) / 10 }))

  const leaderboard = useMemo(() => Object.values(players)
    .filter((p) => p.full_name)
    .sort((a, b) => (b.live_fp ?? 0) - (a.live_fp ?? 0)), [players])
  const hasLiveFp = leaderboard.some((p) => (p.live_fp || 0) > 0)
  const topFp = leaderboard[0]?.live_fp || 0
  const maxScale = Math.max(40, ...leaderboard.map((p) => Math.max(p.live_fp || 0, p.predicted_fp || 0)))
  const isLimited = ['T20', 'IT20', 'IPL', 'BBL', 'PSL', 'CPL', 'WPL', 'ODI', 'ODM'].includes(match?.match_type)
  const maxBalls = ['ODI', 'ODM'].includes(match?.match_type) ? 300 : 120
  const ballsDone = inn ? Number(String(inn.overs).split('.')[0]) * 6 + Number(String(inn.overs).split('.')[1] || 0) : 0
  const progress = isLimited && inn ? ((inn.number - 1) * maxBalls + ballsDone) / (2 * maxBalls) : 0

  if (closeCode === 4404 || feed.error?.code === 'MATCH_NOT_LIVE') {
    return (
      <div className="card"><EmptyState icon={Radio} title="This match isn't live" action={<ButtonLink to={`/matches/${matchId}`} variant="secondary" icon={ArrowLeft}>Back to match centre</ButtonLink>}>
        Live intelligence switches on automatically once the match starts and the score feed reports it in progress.
      </EmptyState></div>
    )
  }
  if (status === 'error') {
    return (
      <div className="card"><EmptyState icon={WifiOff} title="Couldn't connect to the live feed" action={<ButtonLink to={`/matches/${matchId}`} variant="secondary" icon={ArrowLeft}>Back to match centre</ButtonLink>}>
        {closeCode === 4429 ? 'You have too many live tabs open — close one and retry.' : 'The live service may be unavailable. Try refreshing in a moment.'}
      </EmptyState></div>
    )
  }

  return (
    <div className="fade-in">
      <Link to={`/matches/${matchId}`} className="back-link"><ArrowLeft size={14} />Match centre</Link>
      <div className="page-head" style={{ marginBottom: 18 }}>
        <div>
          <div className="row gap-8 mb-8 wrap">
            <LiveBadge label={status === 'ended' ? 'FULL TIME' : 'LIVE'} /><ConnStatus status={status} />
            {match?.gender === 'female' && <Badge tone="warning">Women</Badge>}
            {match?.match_type && <Badge>{match.match_type}</Badge>}
          </div>
          <h1>{teamA ? `${teamA} vs ${teamB}` : <Skeleton h={30} w={360} />}</h1>
          {match && <p>{shortVenue(match.venue_name)}{match.event_name ? ` · ${match.event_name}` : ''}{state?.toss_winner ? ` · ${state.toss_winner} chose to ${state.toss_decision}` : ''}</p>}
        </div>
        <ButtonLink to={`/matches/${matchId}`} variant="secondary" icon={Target}>View predictions</ButtonLink>
      </div>

      {ended && (
        <div className="card live-result mb-16">
          <div className="row wrap gap-16">
            <div style={{ background: 'var(--secondary-soft)', color: 'var(--captain)', width: 48, height: 48, borderRadius: 14, display: 'grid', placeItems: 'center' }}><Trophy size={22} /></div>
            <div className="grow">
              <div className="upper muted">Result</div>
              <h2 className="mt-4">{ended.result || state?.status_text || 'Match complete'}</h2>
              {ended.top_fantasy_scorer && (
                <p className="mt-4">Top fantasy scorer: <b style={{ color: 'var(--text)' }}>{ended.top_fantasy_scorer.full_name}</b> · <span className="mono">{fmt(ended.top_fantasy_scorer.fantasy_points, 0)} FP</span></p>
              )}
            </div>
            {ended.captain_accuracy && (
              <div className={`card-elevated ${ended.captain_accuracy.correct ? 'ok' : ''}`} style={{ minWidth: 240 }}>
                <div className="upper muted">Predicted captain</div>
                <div className="row gap-8 mt-8">
                  {ended.captain_accuracy.correct ? <CheckCircle2 size={18} className="text-success" /> : <XCircle size={18} className="text-danger" />}
                  <b>{ended.captain_accuracy.predicted_captain}</b>
                </div>
                <div className="small muted mt-4">{ended.captain_accuracy.correct ? 'Called it — top scorer' : `Top scorer was ${ended.captain_accuracy.actual_top_scorer}`}</div>
              </div>
            )}
          </div>
        </div>
      )}

      <div className="split">
        <div className="col" style={{ gap: 16 }}>
          {/* Scoreboard */}
          <div className="scoreboard">
            {!state ? (
              <div className="col"><Skeleton h={22} w={180} /><Skeleton h={50} w={220} /><Skeleton h={16} w="60%" /></div>
            ) : !inn ? (
              <div className="empty" style={{ padding: 24 }}>
                <Clock size={22} className="muted" />
                <h3>Waiting for the first score</h3>
                <p className="small">{state.status_text || 'The score feed will update once play begins.'}</p>
              </div>
            ) : (
              <>
                <div className="row between wrap gap-16">
                  <div className="row gap-16">
                    <TeamCrest name={inn.batting_team} size="lg" />
                    <div>
                      <div className="upper muted">Innings {inn.number} · batting</div>
                      <div className="bold mt-4" style={{ fontSize: 16 }}>{inn.batting_team}</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="score-big">{inn.runs}<span className="muted">/{inn.wickets}</span></div>
                    <div className="mono secondary mt-4">{inn.overs} ov · CRR {fmt(inn.current_run_rate, 2)}</div>
                  </div>
                </div>

                {state.status_text && <div className="live-status mt-16">{state.status_text}</div>}

                <div className="live-meta mt-16">
                  {inn.target && state.required ? (
                    <>
                      <div><span className="muted xs upper">Target</span><b className="mono">{inn.target}</b></div>
                      <div><span className="muted xs upper">Need</span><b className="mono">{state.required.runs} off {state.required.balls}</b></div>
                      <div><span className="muted xs upper">Req. RR</span><b className="mono">{state.required.run_rate != null ? fmt(state.required.run_rate, 2) : '—'}</b></div>
                    </>
                  ) : inn.projected_total ? (
                    <div><span className="muted xs upper">Projected</span><b className="mono">{inn.projected_total}</b></div>
                  ) : null}
                  <div><span className="muted xs upper">Bowling</span><b>{team(inn.bowling_team).short}</b></div>
                </div>

                {inningsList.length > 1 && (
                  <>
                    <div className="divider" />
                    <div className="innings-list">
                      {inningsList.map((i) => (
                        <div key={i.number} className={`innings-chip ${i.number === inn.number ? 'current' : ''}`}>
                          <TeamCrest name={i.team} size="sm" />
                          <div>
                            <div className="xs muted">Innings {i.number}</div>
                            <div className="mono bold">{i.runs}/{i.wickets} <span className="muted small">({i.overs})</span></div>
                          </div>
                        </div>
                      ))}
                    </div>
                  </>
                )}

                {isLimited && <div className="mt-16"><Meter value={progress * 100} color="linear-gradient(90deg, var(--primary), var(--violet))" height={4} /></div>}
                <div className="xs muted mt-12 row gap-6"><Clock size={12} />
                  {state.score_updated_at ? `Score updated ${timeAgo(state.score_updated_at)}` : 'Awaiting score'} · refreshes about every {Math.round((feedStatus?.nextPoll || 240) / 60)} min
                </div>
              </>
            )}
          </div>

          {/* Win probability */}
          {isLimited && (
            <Card title="Win probability" icon={Activity} subtitle="Estimated from score, wickets and resources left at each update">
              {pA == null ? (
                <p className="small muted">Win probability appears once both sides' scores are in play.</p>
              ) : (
                <>
                  <div className="row between mb-8">
                    <div className="row gap-8"><TeamCrest name={teamA} size="sm" /><b className="mono" style={{ fontSize: 20 }}>{fmt(pA * 100, 0)}%</b></div>
                    <div className="row gap-8"><b className="mono" style={{ fontSize: 20 }}>{fmt((1 - pA) * 100, 0)}%</b><TeamCrest name={teamB} size="sm" /></div>
                  </div>
                  <div className="winbar">
                    <span style={{ width: `${pA * 100}%`, background: tA.color }} />
                    <span style={{ width: `${(1 - pA) * 100}%`, background: tB.color }} />
                  </div>
                  <div style={{ height: 190, marginTop: 18 }}>
                    {chart.length > 1 ? (
                      <ResponsiveContainer>
                        <AreaChart data={chart} margin={{ top: 6, right: 6, bottom: 0, left: -18 }}>
                          <defs>
                            <linearGradient id="wpA" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="0%" stopColor={tA.color} stopOpacity={0.55} />
                              <stop offset="100%" stopColor={tA.color} stopOpacity={0.04} />
                            </linearGradient>
                          </defs>
                          <XAxis dataKey="label" tickLine={false} axisLine={false} interval="preserveStartEnd" minTickGap={60} />
                          <YAxis domain={[0, 100]} ticks={[0, 50, 100]} tickLine={false} axisLine={false} />
                          <ReferenceLine y={50} stroke="var(--border-strong)" strokeDasharray="4 4" />
                          <Tooltip content={<ChartTip render={(d) => <><div className="t">{d.label}</div><div>{tA.short} <b className="mono">{d.pA}%</b> · {tB.short} <b className="mono">{fmt(100 - d.pA, 1)}%</b></div></>} />} />
                          <Area type="monotone" dataKey="pA" stroke={tA.color} strokeWidth={2} fill="url(#wpA)" isAnimationActive={false} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : <div className="empty" style={{ padding: 30 }}><p className="small">The trend builds with each score update while you watch.</p></div>}
                  </div>
                </>
              )}
            </Card>
          )}

          {/* Live FP leaderboard */}
          <Card title="Live fantasy points" icon={Trophy}
            subtitle={scorecardAt ? `From the live scorecard · updated ${timeAgo(scorecardAt)}` : 'Actual points vs our pre-match projection'}
            actions={<span className="legend" style={{ marginTop: 0 }}><span><i style={{ background: 'var(--primary)' }} />Live</span><span><i style={{ background: 'var(--border-strong)' }} />Projected</span></span>}>
            <div className="xs muted mb-12 row gap-6"><Info size={12} />Fantasy points refresh every ~45 min to stay within the API quota.</div>
            {feedStatus?.note && <div className="mb-12"><Alert tone="warning">{feedStatus.note}</Alert></div>}
            {!leaderboard.length ? (
              <div className="col">{[1, 2, 3, 4].map((i) => <Skeleton key={i} h={44} />)}</div>
            ) : (
              <div className="lb">
                {leaderboard.slice(0, 22).map((p, i) => {
                  const live = p.live_fp || 0
                  const pred = p.predicted_fp
                  const isTop = i === 0 && topFp > 0
                  return (
                    <Link to={p.player_id ? `/players/${p.player_id}` : '#'} key={p.player_id || p.full_name} className={`lb-row${isTop ? ' top' : ''}`}>
                      <span className="lb-rank mono">{i + 1}</span>
                      <TeamCrest name={p.team} size="sm" />
                      <div className="grow">
                        <div className="row gap-8">
                          <span className="bold truncate">{p.full_name}</span>
                          {p.role && <RoleBadge role={p.role} />}
                          {isTop && <span className="badge badge-warning"><Crown size={10} />Top scorer</span>}
                        </div>
                        <div className="lb-bars mt-4">
                          <div className="lb-pred" style={{ width: `${pred != null ? (pred / maxScale) * 100 : 0}%` }} />
                          <div className="lb-live" style={{ width: `${(live / maxScale) * 100}%`, background: isTop ? 'linear-gradient(90deg,#fcd34d,#f59e0b)' : undefined }} />
                        </div>
                        <div className="xs muted mt-4">
                          {p.batting ? `${p.batting.runs}(${p.batting.balls})${p.batting.dismissed ? '' : '*'}` : ''}
                          {p.batting && p.bowling ? ' · ' : ''}
                          {p.bowling ? `${p.bowling.wickets}/${p.bowling.runs} (${p.bowling.overs})` : ''}
                          {p.fielding && (p.fielding.catches || p.fielding.stumpings || p.fielding.run_outs)
                            ? `${p.batting || p.bowling ? ' · ' : ''}${p.fielding.catches ? `${p.fielding.catches}ct ` : ''}${p.fielding.stumpings ? `${p.fielding.stumpings}st ` : ''}${p.fielding.run_outs ? `${p.fielding.run_outs}ro` : ''}` : ''}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="mono bold" style={{ fontSize: 16 }}>{hasLiveFp ? fmt(live, 0) : '—'}</div>
                        <div className="xs muted mono">{pred != null ? `proj ${fmt(pred, 0)}` : '—'}</div>
                      </div>
                    </Link>
                  )
                })}
              </div>
            )}
          </Card>
        </div>

        {/* Feed */}
        <div className="col" style={{ gap: 16, position: 'sticky', top: 80 }}>
          <Card title="Match feed" icon={Radio} pad="sm">
            <div className="feed">
              {!events.length && <p className="small muted" style={{ padding: '6px 4px' }}>Wickets and match status changes appear here as the score feed updates.</p>}
              {events.map((e) => {
                const s = EVENT_STYLE[e.kind] || EVENT_STYLE.status
                return (
                  <div key={e.id} className={`feed-item feed-${e.kind}`}>
                    <span className="feed-icon" style={{ color: s.color, background: `color-mix(in srgb, ${s.color} 14%, transparent)` }}><s.icon size={14} /></span>
                    <div className="grow">
                      <div className="small" style={{ color: 'var(--text)' }}>{e.text}</div>
                      <div className="xs muted mono">{e.over ? `${e.over} ov · ` : ''}{s.label} · {timeAgo(e.ts)}</div>
                    </div>
                  </div>
                )
              })}
            </div>
          </Card>
          {feedStatus?.usage?.configured !== false && feedStatus?.usage && (
            <Card pad="sm">
              <div className="row between mb-8"><span className="muted xs upper row gap-6"><Gauge size={12} />Live data quota today</span>
                <span className="mono xs">{feedStatus.usage.hits}/{feedStatus.usage.limit}</span></div>
              <Meter value={feedStatus.usage.hits} max={feedStatus.usage.limit || 100}
                color={feedStatus.usage.remaining < 20 ? 'var(--warning)' : 'var(--primary)'} height={5} />
              <p className="xs muted mt-8">Shared across all viewers. Score polls cost 1 hit, scorecards 10.</p>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
