import { useMemo, useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { ChevronRight, Clock, Coins, MapPin, Radio, RefreshCw, Search, ShieldCheck, Sparkles, Trophy, Users } from 'lucide-react'
import { apiError, getRecentMatches, getUpcomingMatches } from '../api/client'
import {
  Alert, Badge, Card, Countdown, EmptyState, LiveBadge, PageHead, Skeleton, Tabs, TeamCrest,
} from '../components/ui'
import { useAuthStore } from '../store/authStore'
import { fmtDate, fmtTime, matchStart, registerMatches, relativeDay, scoreLine, shortVenue, team } from '../lib/format'
import './match.css'

const FORMATS = ['All', 'IPL', 'T20', 'ODI', 'Test']

function teamVars(m) {
  return { '--team-a': team(m.team_a).color, '--team-b': team(m.team_b).color }
}

function TossLine({ m }) {
  if (!m.toss_winner) return null
  return <Badge tone="primary"><Coins size={11} />{team(m.toss_winner).short} chose to {m.toss_decision}</Badge>
}

export function SquadBadge({ source }) {
  if (source === 'official') return <Badge tone="success"><ShieldCheck size={11} />Official squad</Badge>
  if (source === 'probable') return <Badge tone="gray"><Users size={11} />Probable XI</Badge>
  if (source === 'manual') return <Badge tone="gray">Manual squad</Badge>
  return null
}

function MatchCard({ m }) {
  const navigate = useNavigate()
  const start = matchStart(m)
  const score = scoreLine(m)
  return (
    <div className="card hover match-card" style={teamVars(m)} onClick={() => navigate(`/matches/${m.id}`)}
      role="link" tabIndex={0} onKeyDown={(e) => e.key === 'Enter' && navigate(`/matches/${m.id}`)}>
      <div className="stripe" />
      <div className="row between">
        <div className="status-row">
          <Badge>{m.match_type}</Badge>
          {m.gender === 'female' && <Badge tone="warning">Women</Badge>}
          {m.is_live && <LiveBadge />}
          {m.playing_xi_confirmed ? <Badge tone="success"><ShieldCheck size={11} />XI confirmed</Badge> : <SquadBadge source={m.squad_source} />}
        </div>
        <span className="muted small truncate" style={{ maxWidth: 130 }}>{m.event_stage || (m.match_number ? `Match ${m.match_number}` : '')}</span>
      </div>
      {m.event_name && (
        <div className="xs muted row gap-4 truncate" style={{ marginTop: -8 }} title={m.event_name}>
          <Trophy size={11} /><span className="truncate">{m.event_name}</span>
        </div>
      )}
      <div className="teams">
        <div className="team"><TeamCrest name={m.team_a} size="lg" /><span className="team-name">{m.team_a}</span></div>
        <span className="vs">VS</span>
        <div className="team"><TeamCrest name={m.team_b} size="lg" /><span className="team-name">{m.team_b}</span></div>
      </div>
      <div className="col" style={{ minHeight: 22, gap: 6, alignItems: 'center', textAlign: 'center' }}>
        {score ? <span className="mono small bold">{score}</span> : <TossLine m={m} />}
        {m.is_live && m.status_text && <span className="xs secondary">{m.status_text}</span>}
      </div>
      <div className="match-meta">
        <span className="row gap-6 truncate"><MapPin size={13} /><span className="truncate">{shortVenue(m.venue_name)}</span></span>
        {m.is_live
          ? <span className="row gap-6 text-danger bold"><Radio size={13} />In progress</span>
          : <span className="row gap-6"><Clock size={13} />{fmtTime(start)} · <Countdown to={start} compact /></span>}
      </div>
    </div>
  )
}

function LiveBanner({ m }) {
  const score = scoreLine(m)
  return (
    <Link to={`/matches/${m.id}/live`} className="live-banner fade-in" style={teamVars(m)}>
      <div className="lb-teams">
        <TeamCrest name={m.team_a} size="lg" />
        <TeamCrest name={m.team_b} size="lg" />
      </div>
      <div className="grow">
        <div className="row gap-8 mb-8"><LiveBadge label="LIVE NOW" /><span className="muted small truncate">{m.event_name}</span></div>
        <h3 className="truncate">{m.team_a} vs {m.team_b}</h3>
        <div className="secondary small mt-4 row gap-6 wrap">
          <MapPin size={13} />{shortVenue(m.venue_name)}{score && <span className="mono bold">· {score}</span>}
        </div>
        {m.status_text && <div className="xs muted mt-4">{m.status_text}</div>}
      </div>
      <span className="btn btn-danger">Open live centre <ChevronRight size={16} /></span>
    </Link>
  )
}

function CardSkeleton() {
  return (
    <div className="card col" style={{ gap: 18 }}>
      <Skeleton h={20} w="45%" />
      <div className="row between"><Skeleton h={68} w={68} r={20} /><Skeleton h={24} w={40} /><Skeleton h={68} w={68} r={20} /></div>
      <Skeleton h={14} w="70%" style={{ alignSelf: 'center' }} />
      <Skeleton h={16} />
    </div>
  )
}

function RecentResults() {
  const { data, isLoading } = useQuery({ queryKey: ['matches', 'recent'], queryFn: () => getRecentMatches({ limit: 6 }) })
  const matches = data?.matches || []
  registerMatches(matches)
  return (
    <Card title="Recent results" icon={Trophy} subtitle="Latest completed matches in the database" pad="sm" className="mt-32">
      {isLoading && <div className="col">{[1, 2, 3].map((i) => <Skeleton key={i} h={44} />)}</div>}
      {!isLoading && matches.length === 0 && <p className="muted small" style={{ padding: 12 }}>No completed matches yet.</p>}
      {matches.map((m) => {
        const margin = m.win_by_runs ? `${m.win_by_runs} runs` : m.win_by_wickets ? `${m.win_by_wickets} wickets` : null
        return (
          <Link to={`/matches/${m.id}`} key={m.id} className="result-row">
            <div className="row" style={{ minWidth: 0 }}>
              <TeamCrest name={m.match_winner || m.team_a} size="sm" />
              <div className="grow">
                <div className="bold small truncate">{m.team_a} vs {m.team_b}</div>
                <div className="xs muted truncate">
                  {fmtDate(m.match_date, { day: 'numeric', month: 'short', year: 'numeric' })} · {m.event_name || shortVenue(m.venue_name)}
                  {m.gender === 'female' ? ' · Women' : ''}
                </div>
              </div>
            </div>
            <div className="text-right">
              {m.match_winner
                ? <><div className="small bold">{team(m.match_winner).short} won</div><div className="xs muted">{margin ? `by ${margin}` : ''}</div></>
                : m.status_text
                  ? <div className="xs secondary" style={{ maxWidth: 200 }}>{m.status_text}</div>
                  : <span className="badge">No result</span>}
            </div>
          </Link>
        )
      })}
    </Card>
  )
}

export default function MatchListPage() {
  const [format, setFormat] = useState('All')
  const [q, setQ] = useState('')
  const isAdmin = useAuthStore((st) => st.user?.role === 'admin')
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['matches', 'upcoming', format],
    queryFn: () => getUpcomingMatches({ format: format === 'All' ? undefined : format, limit: 50 }),
    staleTime: 60_000,
  })
  const matches = data?.matches || []
  registerMatches(matches)
  const live = matches.filter((m) => m.is_live)

  const groups = useMemo(() => {
    const term = q.trim().toLowerCase()
    const list = matches.filter((m) => !term || `${m.team_a} ${m.team_b} ${m.venue_name} ${m.event_name}`.toLowerCase().includes(term))
    const out = []
    for (const m of list) {
      const key = m.is_live ? 'Live now' : relativeDay(matchStart(m))
      let g = out.find((x) => x.key === key)
      if (!g) out.push((g = { key, items: [] }))
      g.items.push(m)
    }
    return out
  }, [matches, q])

  return (
    <div className="fade-in">
      <PageHead
        eyebrow={<><Sparkles size={13} />Live fixtures · CricketData</>}
        title="Upcoming matches"
        subtitle="Real fixtures with probable squads from recent line-ups, scored by models trained on 23,000+ Cricsheet matches."
        actions={data && <Badge size="lg"><Users size={12} />{data.total} fixtures</Badge>}
      />

      {live.slice(0, 2).map((m) => <LiveBanner key={m.id} m={m} />)}

      <div className="filters">
        <Tabs tabs={FORMATS.map((f) => ({ value: f, label: f }))} value={format} onChange={setFormat} />
        <div className="input-wrap">
          <Search size={16} />
          <input className="input" placeholder="Search teams, venues or series" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
      </div>

      {error && (
        <Alert tone="danger" title="Couldn't load matches" action={<button className="btn btn-secondary btn-sm" onClick={() => refetch()}>Retry</button>}>
          {apiError(error).message}
        </Alert>
      )}

      {isLoading && <div className="grid-auto">{[1, 2, 3, 4, 5, 6].map((i) => <CardSkeleton key={i} />)}</div>}

      {!isLoading && !error && groups.length === 0 && (
        <Card>
          {q ? <EmptyState icon={Search} title="No matches found">Try a different team, venue or series.</EmptyState> : (
            <EmptyState icon={RefreshCw} title="No upcoming fixtures yet"
              action={isAdmin && <Link to="/admin?tab=live" className="btn btn-primary btn-sm"><RefreshCw size={14} />Open Admin → Live data</Link>}>
              Fixtures sync automatically from CricketData every few hours.{' '}
              {isAdmin
                ? 'You can trigger a sync now or add a fixture manually in Admin → Live data.'
                : 'An admin can also trigger a sync or add a fixture manually — check back shortly.'}
            </EmptyState>
          )}
        </Card>
      )}

      {groups.map((g) => (
        <section key={g.key}>
          <div className="day-head">{g.key}<span className="muted xs mono">{g.items.length}</span></div>
          <div className="grid-auto stagger">{g.items.map((m) => <MatchCard key={m.id} m={m} />)}</div>
        </section>
      ))}

      <RecentResults />
    </div>
  )
}
