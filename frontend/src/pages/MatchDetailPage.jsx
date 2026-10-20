import { useEffect, useState } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery } from '@tanstack/react-query'
import {
  ArrowLeft, BrainCircuit, CalendarDays, Coins, Crown, Flame, Layers, Lock, MapPin, Radio, RefreshCw, Shield,
  ShieldCheck, Sparkles, Swords, Target, Trophy, Users, Wand2, Zap,
} from 'lucide-react'
import { apiError, getMatch, predictPortfolio, predictTeam } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useUiStore } from '../store/uiStore'
import {
  Alert, Badge, Button, ButtonLink, Card, Countdown, EmptyState, FormGuide, LiveBadge, Skeleton, Tabs, TeamCrest,
  UnderlineTabs,
} from '../components/ui'
import TeamView from '../components/match/TeamView'
import PlayerDrawer from '../components/match/PlayerDrawer'
import { CaptaincyTab, DifferentialsTab, SquadsTab, VenueTab } from '../components/match/MatchTabs'
import { MODES, fmtDate, fmtTime, matchStart, registerMatches, scoreLine, shortVenue, team } from '../lib/format'
import './match.css'

const MODE_CARDS = [
  { id: 'safe', icon: Shield, color: 'var(--success)', desc: 'High-floor, consistent picks for head-to-heads.' },
  { id: 'grand_league', icon: Trophy, color: 'var(--captain)', desc: 'Ceiling + differentials to climb mega contests.' },
  { id: 'aggressive', icon: Flame, color: 'var(--danger)', desc: 'Maximum ceiling, high variance, bold captaincy.' },
  { id: 'small_league', icon: Target, color: 'var(--primary-light)', desc: 'Balanced XI for 3–20 team contests.' },
]
const COUNTS = [1, 3, 5, 10, 20]
const MODE_PARAM = { gl: 'grand_league', safe: 'safe', aggressive: 'aggressive', sl: 'small_league' }

function HeroSide({ name, form, right }) {
  return (
    <div className={`side ${right ? 'right' : ''}`}>
      <TeamCrest name={name} size="xl" />
      <div style={{ minWidth: 0 }}>
        <div className="team-big">{name}</div>
        <div className="mt-8" style={{ display: 'flex', justifyContent: right ? 'flex-end' : 'flex-start' }}><FormGuide results={form || []} /></div>
      </div>
    </div>
  )
}

function Hero({ m }) {
  const start = matchStart(m)
  const style = { '--team-a': team(m.team_a).color, '--team-b': team(m.team_b).color }
  return (
    <div className="hero-match fade-in" style={style}>
      <div className="row between wrap mb-24">
        <div className="row wrap gap-6">
          <Badge>{m.match_type}</Badge>
          {m.gender === 'female' && <Badge tone="warning">Women</Badge>}
          {m.event_name && <Badge tone="primary"><Trophy size={11} />{m.event_name}{m.event_stage ? ` · ${m.event_stage}` : m.match_number ? ` · Match ${m.match_number}` : ''}</Badge>}
          {m.is_live && <LiveBadge />}
          {m.playing_xi_confirmed && <Badge tone="success"><ShieldCheck size={11} />XI confirmed</Badge>}
          {!m.playing_xi_confirmed && m.squad_source === 'official' && <Badge tone="success"><ShieldCheck size={11} />Official squad</Badge>}
          {!m.playing_xi_confirmed && m.squad_source === 'probable' && <Badge tone="gray"><Users size={11} />Probable XI</Badge>}
        </div>
        {m.status === 'live' && <ButtonLink to={`/matches/${m.id}/live`} variant="danger" size="sm" icon={Radio}>Live centre</ButtonLink>}
      </div>
      <div className="teams">
        <HeroSide name={m.team_a} form={m.team_form?.[m.team_a]} />
        <div className="hero-mid">
          <span className="vs">VS</span>
          {m.status === 'upcoming' && start && <Countdown to={start} />}
          {m.is_live && <span className="badge badge-live badge-lg"><span className="dot" />In progress</span>}
          {m.status === 'complete' && m.match_winner && <Badge tone="success" size="lg">{team(m.match_winner).short} won</Badge>}
        </div>
        <HeroSide name={m.team_b} form={m.team_form?.[m.team_b]} right />
      </div>
      <div className="hero-info">
        <span><MapPin size={14} />{shortVenue(m.venue_name)}{m.city ? `, ${m.city}` : ''}</span>
        <span><CalendarDays size={14} />{fmtDate(start, { weekday: 'short', day: 'numeric', month: 'short' })} · {fmtTime(start)}</span>
        <span><Coins size={14} />{m.toss_winner ? `${m.toss_winner} won the toss, chose to ${m.toss_decision}` : 'Toss pending'}</span>
      </div>
      {(scoreLine(m) || (m.status !== 'upcoming' && m.status_text)) && (
        <div className="hero-status">
          {scoreLine(m) && <span className="mono bold">{scoreLine(m)}</span>}
          {m.status_text && <span className="secondary">{m.status_text}</span>}
        </div>
      )}
    </div>
  )
}

function HeroSkeleton() {
  return (
    <div className="hero-match">
      <Skeleton h={22} w="35%" />
      <div className="row between mt-24"><Skeleton h={88} w={260} r={20} /><Skeleton h={50} w={120} /><Skeleton h={88} w={260} r={20} /></div>
      <Skeleton h={16} w="60%" style={{ margin: '24px auto 0' }} />
    </div>
  )
}

function TeamSkeleton() {
  return (
    <div>
      <div className="stat-row">{[1, 2, 3, 4, 5].map((i) => <Skeleton key={i} h={84} r={14} />)}</div>
      <div className="team-layout"><Skeleton h={520} r={24} /><div className="col"><Skeleton h={160} r={14} /><Skeleton h={120} r={14} /></div></div>
    </div>
  )
}

function AiTeamTab({ match, premium, onPlayer }) {
  const [params, setParams] = useSearchParams()
  const showUpgrade = useUiStore((s) => s.showUpgrade)
  const [mode, setMode] = useState(() => (premium ? MODE_PARAM[params.get('mode')] : null) || 'safe')
  const [count, setCount] = useState(1)
  const [teamIdx, setTeamIdx] = useState(0)
  const [result, setResult] = useState(null) // { kind: 'single'|'portfolio', data }

  const onErr = (err) => {
    const e = apiError(err)
    if (e.status === 402) showUpgrade({ feature: 'Premium teams', message: e.message })
  }
  const single = useMutation({
    mutationFn: () => predictTeam({ match_id: match.id, mode, count: premium ? count : 1 }),
    onSuccess: (data) => { setResult({ kind: 'single', data }); setTeamIdx(0) },
    onError: onErr,
  })
  const portfolio = useMutation({
    mutationFn: () => predictPortfolio(match.id),
    onSuccess: (data) => { setResult({ kind: 'portfolio', data }); setTeamIdx(0) },
    onError: onErr,
  })
  const pending = single.isPending || portfolio.isPending
  const error = single.error || portfolio.error

  // Auto-generate the default team on first load so the screen is never empty
  useEffect(() => { if (match.status !== 'complete') single.mutate() }, [match.id]) // eslint-disable-line react-hooks/exhaustive-deps

  const pickMode = (id) => {
    if (!premium && id !== 'safe') {
      showUpgrade({ feature: `${MODES[id].label} teams`, message: `${MODES[id].label} mode is part of XithSense Premium.` })
      return
    }
    setMode(id)
    const short = Object.entries(MODE_PARAM).find(([, v]) => v === id)?.[0]
    setParams(short && id !== 'safe' ? { mode: short } : {}, { replace: true })
  }

  let teams = [], label = (i) => `Team ${i + 1}`, weights, phase, teamMode = mode, xiConfirmed = match.playing_xi_confirmed
  if (result?.kind === 'single') {
    teams = result.data.teams
    weights = result.data.ensemble_weights
    phase = result.data.match_phase
    teamMode = result.data.mode
    xiConfirmed = result.data.playing_xi_confirmed
  } else if (result?.kind === 'portfolio') {
    const keys = Object.keys(result.data.teams)
    teams = keys.map((k) => result.data.teams[k])
    label = (i) => MODES[keys[i]].label
    weights = result.data.ensemble_weights
    phase = result.data.match_phase
    teamMode = keys[teamIdx]
  }
  const t = teams[teamIdx]

  return (
    <div>
      <div className="modes">
        {MODE_CARDS.map((c) => {
          const locked = !premium && c.id !== 'safe'
          return (
            <button key={c.id} className={`mode ${mode === c.id ? 'active' : ''} ${locked ? 'locked' : ''}`} onClick={() => pickMode(c.id)}>
              <span className="mode-icon" style={{ background: `color-mix(in srgb, ${c.color} 15%, transparent)`, color: c.color }}><c.icon size={17} /></span>
              <div className="mode-name">{MODES[c.id].label}</div>
              <div className="mode-desc">{c.desc}</div>
              {locked && <span className="lock badge badge-pro"><Lock size={10} />PRO</span>}
            </button>
          )
        })}
      </div>

      <div className="gen-bar">
        <div className="row wrap gap-16">
          <div className="row gap-8">
            <span className="small secondary">Teams</span>
            <div className="count-pick">
              {COUNTS.map((n) => (
                <button key={n} className={count === n ? 'active' : ''} disabled={!premium && n > 1}
                  onClick={() => setCount(n)} title={!premium && n > 1 ? 'Premium' : undefined}>{n}</button>
              ))}
            </div>
            {!premium && <Lock size={13} className="muted" />}
          </div>
          <span className="xs muted hide-mobile">Mode: <b style={{ color: 'var(--text)' }}>{MODES[mode].label}</b></span>
        </div>
        <div className="row gap-8">
          <Button variant="secondary" icon={Layers} loading={portfolio.isPending} disabled={pending}
            onClick={() => (premium ? portfolio.mutate() : showUpgrade({ feature: 'Portfolio generation', message: 'Generate Safe, GL, Aggressive and Small League teams in one click.' }))}>
            <span className="hide-mobile">Portfolio</span>{!premium && <Lock size={12} />}
          </Button>
          <Button icon={result ? RefreshCw : Wand2} loading={single.isPending} disabled={pending} onClick={() => single.mutate()}>
            {result ? 'Regenerate' : 'Generate AI team'}
          </Button>
        </div>
      </div>

      {!xiConfirmed && match.squad_source === 'probable' && (
        <div className="mb-16">
          <Alert tone="info" title="Probable XIs">Squads are probable XIs built from each team's recent line-ups in real match data. Official squads replace them when announced.</Alert>
        </div>
      )}
      {!xiConfirmed && match.squad_source !== 'probable' && (
        <div className="mb-16">
          <Alert tone="info" title="Playing XI not announced">Predictions use the full squad; regenerate after the toss once line-ups are confirmed.</Alert>
        </div>
      )}
      {error && apiError(error).status !== 402 && <div className="mb-16"><Alert tone="danger" title="Couldn't generate a team">{apiError(error).message}</Alert></div>}

      {pending && <TeamSkeleton />}

      {!pending && t && (
        <>
          {teams.length > 1 && (
            <div className="mb-16">
              <Tabs tabs={teams.map((x, i) => ({ value: i, label: label(i), count: Math.round(x.predicted_total_fp) }))} value={teamIdx} onChange={setTeamIdx} />
            </div>
          )}
          <TeamView key={`${result.kind}-${teamIdx}`} match={match} mode={teamMode} t={t} weights={weights} phase={phase} onPlayer={onPlayer} />
        </>
      )}

      {!pending && !t && !error && (
        <Card><EmptyState icon={BrainCircuit} title="Generate your first AI team" action={<Button icon={Wand2} onClick={() => single.mutate()}>Generate</Button>}>
          The optimizer will pick a Dream11-valid XI within 100 credits, plus captain and vice-captain.
        </EmptyState></Card>
      )}
    </div>
  )
}

export default function MatchDetailPage() {
  const { matchId } = useParams()
  const premium = useAuthStore((s) => ['premium', 'admin'].includes(s.user?.role))
  const [tab, setTab] = useState('team')
  const [drawer, setDrawer] = useState(null)
  const { data: match, isLoading, error } = useQuery({ queryKey: ['match', matchId], queryFn: () => getMatch(matchId) })
  if (match) registerMatches(match)

  if (error) {
    const e = apiError(error)
    return (
      <Card>
        <EmptyState icon={Swords} title={e.status === 404 ? 'Match not found' : 'Couldn\'t load match'}
          action={<ButtonLink to="/matches" variant="secondary" icon={ArrowLeft}>Upcoming matches</ButtonLink>}>
          {e.status === 404 ? 'This fixture may have been removed or the link is wrong.' : e.message}
        </EmptyState>
      </Card>
    )
  }

  const tabs = [
    { value: 'team', label: 'AI Team', icon: Sparkles },
    { value: 'captain', label: 'Captaincy', icon: Crown },
    { value: 'diff', label: 'Differentials', icon: Zap, locked: !premium },
    { value: 'squads', label: 'Squads', icon: Users },
    { value: 'venue', label: 'Venue & H2H', icon: MapPin },
  ]

  return (
    <div>
      <Link to="/matches" className="back-link"><ArrowLeft size={15} />All matches</Link>
      {isLoading || !match ? <HeroSkeleton /> : <Hero m={match} />}
      <div className="mt-24" />
      <UnderlineTabs tabs={tabs} value={tab} onChange={setTab} />
      {match && (
        <>
          <div style={{ display: tab === 'team' ? 'block' : 'none' }}><AiTeamTab match={match} premium={premium} onPlayer={setDrawer} /></div>
          {tab === 'captain' && <CaptaincyTab matchId={match.id} premium={premium} onPlayer={setDrawer} />}
          {tab === 'diff' && <DifferentialsTab matchId={match.id} premium={premium} onPlayer={setDrawer} />}
          {tab === 'squads' && <SquadsTab match={match} />}
          {tab === 'venue' && <VenueTab match={match} />}
        </>
      )}
      <PlayerDrawer matchId={matchId} player={drawer} onClose={() => setDrawer(null)} />
    </div>
  )
}
