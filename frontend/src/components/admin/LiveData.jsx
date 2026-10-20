import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  CalendarClock, CheckCircle2, Gauge, ListChecks, Loader2, Pin, PinOff, Plus, Radio, RefreshCw, Search, ShieldCheck,
  Users, Wifi, WifiOff,
} from 'lucide-react'
import {
  apiError, createFixture, getJobs, getLiveData, getSeries, rebuildSquad, setPinnedSeries, syncFixtures,
} from '../../api/client'
import { Alert, Badge, Button, Card, EmptyState, Meter, Modal, Skeleton } from '../ui'
import { fmtDate, fmtTime, timeAgo } from '../../lib/format'
import { toast } from '../../store/uiStore'
import { JobStatus } from './Jobs'

function SquadSource({ source }) {
  if (source === 'official') return <Badge tone="success"><ShieldCheck size={11} />Official</Badge>
  if (source === 'probable') return <Badge tone="gray"><Users size={11} />Probable</Badge>
  if (source === 'manual') return <Badge tone="gray">Manual</Badge>
  return <Badge tone="warning">No squad</Badge>
}

function StatusBadge({ status }) {
  if (status === 'live') return <span className="badge badge-live"><span className="dot" />Live</span>
  if (status === 'complete') return <Badge tone="gray">Complete</Badge>
  return <Badge tone="primary">Upcoming</Badge>
}

const EMPTY_FIXTURE = { team_a: '', team_b: '', match_type: 'T20', gender: 'male', start_time: '', venue: '', event_name: '' }

function FixtureModal({ open, onClose }) {
  const qc = useQueryClient()
  const [f, setF] = useState(EMPTY_FIXTURE)
  const set = (k) => (e) => setF((x) => ({ ...x, [k]: e.target.value }))
  const create = useMutation({
    mutationFn: () => createFixture({ ...f, start_time: new Date(f.start_time).toISOString() }),
    onSuccess: (r) => {
      toast.success('Fixture added', `${r.team_a} vs ${r.team_b} · ${r.squad_players} squad players (${r.squad_source})`)
      qc.invalidateQueries({ queryKey: ['admin-live-data'] })
      qc.invalidateQueries({ queryKey: ['matches'] })
      setF(EMPTY_FIXTURE)
      onClose()
    },
    onError: (err) => toast.error('Could not add fixture', apiError(err).message),
  })
  const valid = f.team_a.trim() && f.team_b.trim() && f.start_time
  return (
    <Modal open={open} onClose={onClose} title="Add fixture manually" width={560}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button icon={Plus} loading={create.isPending} disabled={!valid} onClick={() => create.mutate()}>Add fixture</Button></>}>
      <p className="small mb-16">Team and venue names are matched to Cricsheet history, so the probable squad is built from each team's recent real line-ups. Use the names as they appear in match data (e.g. "India", "Mumbai Indians").</p>
      <div className="grid-2">
        <div className="field"><label className="label">Team A</label><input className="input" value={f.team_a} onChange={set('team_a')} placeholder="India" /></div>
        <div className="field"><label className="label">Team B</label><input className="input" value={f.team_b} onChange={set('team_b')} placeholder="Australia" /></div>
        <div className="field"><label className="label">Format</label>
          <select className="select" value={f.match_type} onChange={set('match_type')}>{['T20', 'IPL', 'IT20', 'ODI', 'Test', 'BBL', 'PSL', 'CPL', 'WPL'].map((x) => <option key={x}>{x}</option>)}</select></div>
        <div className="field"><label className="label">Gender</label>
          <select className="select" value={f.gender} onChange={set('gender')}><option value="male">Men</option><option value="female">Women</option></select></div>
        <div className="field"><label className="label">Start (local time)</label><input className="input" type="datetime-local" value={f.start_time} onChange={set('start_time')} /></div>
        <div className="field"><label className="label">Venue</label><input className="input" value={f.venue} onChange={set('venue')} placeholder="Wankhede Stadium, Mumbai" /></div>
      </div>
      <div className="field mt-12"><label className="label">Series / event (optional)</label><input className="input" value={f.event_name} onChange={set('event_name')} placeholder="Australia tour of India" /></div>
    </Modal>
  )
}

export default function LiveData() {
  const qc = useQueryClient()
  const [showFixture, setShowFixture] = useState(false)
  const [seriesOpen, setSeriesOpen] = useState(false)
  const [confirmOfficial, setConfirmOfficial] = useState(null)
  const [syncJob, setSyncJob] = useState(null)
  const [seriesQ, setSeriesQ] = useState('')

  const { data, isLoading, error } = useQuery({ queryKey: ['admin-live-data'], queryFn: getLiveData, refetchInterval: 60_000 })
  const series = useQuery({ queryKey: ['admin-series'], queryFn: getSeries, enabled: seriesOpen, staleTime: 10 * 60_000 })
  const jobs = useQuery({
    queryKey: ['admin-jobs'], queryFn: getJobs, enabled: !!syncJob,
    refetchInterval: (q) => {
      const j = (q.state.data?.jobs || []).find((x) => x.id === syncJob)
      return j && ['queued', 'running'].includes(j.status) ? 2000 : false
    },
  })
  const job = (jobs.data?.jobs || []).find((x) => x.id === syncJob)
  useEffect(() => {
    if (job?.status === 'succeeded') {
      qc.invalidateQueries({ queryKey: ['admin-live-data'] })
      qc.invalidateQueries({ queryKey: ['matches'] })
    }
  }, [job?.status, qc])

  const sync = useMutation({
    mutationFn: (refresh) => syncFixtures(refresh),
    onSuccess: (r) => { setSyncJob(r.task_id); toast.success('Fixture sync queued') },
    onError: (err) => toast.error('Sync failed', apiError(err).message),
  })
  const squad = useMutation({
    mutationFn: ({ id, official }) => rebuildSquad(id, official),
    onSuccess: (r) => {
      toast.success('Squad rebuilt', `Source: ${r.squad_source}`)
      qc.invalidateQueries({ queryKey: ['admin-live-data'] })
      qc.invalidateQueries({ queryKey: ['match', r.match_id] })
      setConfirmOfficial(null)
    },
    onError: (err) => toast.error('Squad rebuild failed', apiError(err).message),
  })
  const pin = useMutation({
    mutationFn: (ids) => setPinnedSeries(ids),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['admin-live-data'] }); qc.invalidateQueries({ queryKey: ['admin-series'] }) },
    onError: (err) => toast.error('Could not update pins', apiError(err).message),
  })

  if (isLoading) return <div className="col"><Skeleton h={140} r={14} /><Skeleton h={260} r={14} /></div>
  if (error) return <Alert tone="danger" title="Couldn't load live-data status">{apiError(error).message}</Alert>

  const u = data.usage || {}
  const pinned = new Set(data.pinned_series || [])
  const togglePin = (id) => {
    const next = new Set(pinned)
    next.has(id) ? next.delete(id) : next.add(id)
    pin.mutate([...next])
  }
  const s = data.settings || {}
  const seriesList = (series.data?.series || []).filter((x) => !seriesQ || x.name.toLowerCase().includes(seriesQ.toLowerCase()))

  return (
    <div className="col" style={{ gap: 20 }}>
      {!data.configured && (
        <Alert tone="warning" title="CricketData API key not configured">
          Set <span className="mono">CRICKETDATA_API_KEY</span> in <span className="mono">.env</span> and restart the API to sync live fixtures and scores. Manual fixtures still work.
        </Alert>
      )}

      <div className="grid-3">
        <Card title="API quota today" icon={Gauge} subtitle={`Resets daily · last ${s.max_series || 8} tracked series`}>
          <div className="row between mb-8">
            <span className="mono" style={{ fontSize: 26, fontWeight: 700 }}>{u.hits ?? 0}<span className="muted" style={{ fontSize: 15 }}> / {u.limit ?? 100}</span></span>
            {data.configured ? <Badge tone="success"><Wifi size={11} />Connected</Badge> : <Badge tone="gray"><WifiOff size={11} />Off</Badge>}
          </div>
          <Meter value={u.hits || 0} max={u.limit || 100} color={(u.remaining ?? 100) - (u.reserve ?? 0) < 20 ? 'var(--warning)' : 'var(--primary)'} height={7} />
          <p className="xs muted mt-12">{u.remaining ?? '—'} hits left · {u.reserve ?? 0} kept in reserve. Lists & live scores cost 1 hit; squads and scorecards cost 10.</p>
        </Card>
        <Card title="Polling settings" icon={Radio} subtitle="From .env (CRICKETDATA_* / LIVE_*)">
          <div className="kv"><span>Fixture sync</span><span className="mono">every {s.sync_hours}h · {s.days_ahead} days ahead</span></div>
          <div className="kv"><span>Live score</span><span className="mono">every {Math.round((s.poll_seconds || 240) / 60)} min (while watched)</span></div>
          <div className="kv"><span>Live scorecard</span><span className="mono">every {s.scorecard_minutes} min</span></div>
          <div className="kv"><span>Last series sync</span><span className="mono">{data.last_series_sync ? timeAgo(data.last_series_sync) : 'never'}</span></div>
        </Card>
        <Card title="Fixtures" icon={CalendarClock} subtitle="Sync from CricketData or add one by hand">
          <div className="col">
            <Button icon={RefreshCw} loading={sync.isPending} disabled={!data.configured} onClick={() => sync.mutate(false)}>Sync fixtures now</Button>
            <Button variant="secondary" icon={RefreshCw} disabled={!data.configured || sync.isPending} onClick={() => sync.mutate(true)}>Force-refresh series schedules</Button>
            <Button variant="secondary" icon={Plus} onClick={() => setShowFixture(true)}>Add fixture manually</Button>
            {job && (
              <div className="row between small mt-4"><span className="muted">Last sync job</span><JobStatus status={job.status} /></div>
            )}
            {job?.status === 'succeeded' && job.result && (
              <div className="xs muted">{job.result.matches_upserted ?? 0} matches from {(job.result.series_tracked || []).length} series</div>
            )}
            {job?.status === 'failed' && <div className="xs text-danger">{String(job.error || '').split('\n')[0]}</div>}
          </div>
        </Card>
      </div>

      <Card title="Tracked fixtures" icon={ListChecks} subtitle="Upcoming and live matches from the provider and manual entries" pad="sm">
        {!data.fixtures?.length ? (
          <EmptyState icon={CalendarClock} title="No tracked fixtures">Run a sync or add a fixture manually.</EmptyState>
        ) : (
          <div className="table-wrap" style={{ border: 0 }}>
            <table className="table">
              <thead><tr><th>Match</th><th>Series</th><th>Status</th><th>Start</th><th>Squad</th><th className="text-right">Actions</th></tr></thead>
              <tbody>
                {data.fixtures.map((m) => (
                  <tr key={m.id}>
                    <td>
                      <Link to={`/matches/${m.id}`} className="bold">{m.name}</Link>
                      <div className="xs muted">{m.match_type}{m.gender === 'female' ? ' · Women' : ''}</div>
                    </td>
                    <td className="small secondary" style={{ maxWidth: 240 }}><span className="truncate" style={{ display: 'block' }}>{m.series || '—'}</span></td>
                    <td><StatusBadge status={m.status} /></td>
                    <td className="small mono">{m.start_time ? `${fmtDate(m.start_time)} · ${fmtTime(m.start_time)}` : '—'}</td>
                    <td><SquadSource source={m.squad_source} /></td>
                    <td className="text-right">
                      <div className="row gap-6" style={{ justifyContent: 'flex-end' }}>
                        <Button size="sm" variant="ghost" icon={Users} loading={squad.isPending && squad.variables?.id === m.id && !squad.variables?.official}
                          onClick={() => squad.mutate({ id: m.id, official: false })}>Rebuild probable</Button>
                        <Button size="sm" variant="secondary" icon={ShieldCheck} disabled={!data.configured}
                          onClick={() => setConfirmOfficial(m)}>Official (10 hits)</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <Card title="Series discovery" icon={Search}
        subtitle="Series overlapping the sync window, ranked by importance. Pinned series are always tracked."
        actions={!seriesOpen
          ? <Button size="sm" variant="secondary" icon={Search} disabled={!data.configured} onClick={() => setSeriesOpen(true)}>Load series (uses API hits)</Button>
          : <Button size="sm" variant="ghost" icon={RefreshCw} onClick={() => series.refetch()} loading={series.isFetching}>Reload</Button>}>
        {!seriesOpen && <p className="small muted">Loading the series list pages through the provider (≈1 hit per page, cached for 24h).</p>}
        {seriesOpen && series.isLoading && <div className="col">{[1, 2, 3].map((i) => <Skeleton key={i} h={40} />)}</div>}
        {seriesOpen && series.error && <Alert tone="danger">{apiError(series.error).message}</Alert>}
        {seriesOpen && series.data && (
          <>
            <div className="input-wrap mb-12" style={{ maxWidth: 320 }}><Search size={16} /><input className="input" placeholder="Filter series" value={seriesQ} onChange={(e) => setSeriesQ(e.target.value)} /></div>
            <div className="table-wrap" style={{ border: 0 }}>
              <table className="table">
                <thead><tr><th>Series</th><th>Dates</th><th className="num">Matches</th><th>Priority</th><th className="text-right">Track</th></tr></thead>
                <tbody>
                  {seriesList.map((x) => (
                    <tr key={x.id}>
                      <td><b>{x.name}</b><div className="xs muted">{[x.t20 && `${x.t20} T20`, x.odi && `${x.odi} ODI`, x.test && `${x.test} Test`].filter(Boolean).join(' · ')}</div></td>
                      <td className="small mono">{fmtDate(x.start)} → {fmtDate(x.end)}</td>
                      <td className="num mono">{x.matches}</td>
                      <td><Badge tone={x.priority >= 4 ? 'success' : x.priority >= 3 ? 'primary' : 'gray'}>{['', 'Low', 'Normal', 'High', 'Top'][x.priority] || x.priority}</Badge></td>
                      <td className="text-right">
                        <Button size="sm" variant={x.pinned ? 'primary' : 'ghost'} icon={x.pinned ? Pin : PinOff} loading={pin.isPending}
                          onClick={() => togglePin(x.id)}>{x.pinned ? 'Pinned' : 'Pin'}</Button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {!seriesList.length && <p className="small muted">No series match.</p>}
          </>
        )}
      </Card>

      <FixtureModal open={showFixture} onClose={() => setShowFixture(false)} />

      <Modal open={!!confirmOfficial} onClose={() => setConfirmOfficial(null)} title="Fetch official squad?" width={460}
        footer={<><Button variant="ghost" onClick={() => setConfirmOfficial(null)}>Cancel</Button>
          <Button icon={squad.isPending ? Loader2 : CheckCircle2} loading={squad.isPending}
            onClick={() => squad.mutate({ id: confirmOfficial.id, official: true })}>Fetch (10 hits)</Button></>}>
        <p>This calls CricketData's <span className="mono">match_squad</span> for <b>{confirmOfficial?.name}</b> and costs 10 of today's {u.limit ?? 100} hits ({u.remaining ?? '—'} left).</p>
        <p className="small mt-8">If the provider hasn't published squads yet, the probable XI from recent line-ups is kept.</p>
      </Modal>
    </div>
  )
}
