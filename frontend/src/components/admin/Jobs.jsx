import { Fragment, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  BrainCircuit, CalendarClock, CheckCircle2, ChevronDown, ChevronRight, Clock, Database, FlaskConical, Loader2, Play, RefreshCw, XCircle,
} from 'lucide-react'
import {
  apiError, getJobs, triggerBacktest, triggerFeatures, triggerIngest, triggerRetrain,
} from '../../api/client'
import { Badge, Button, Card, EmptyState, Switch } from '../ui'
import { timeAgo } from '../../lib/format'
import { toast } from '../../store/uiStore'

const KIND = {
  ingest: { label: 'Ingest data', icon: Database, color: 'var(--bat)' },
  features: { label: 'Rebuild features', icon: RefreshCw, color: 'var(--wk)' },
  retrain: { label: 'Retrain models', icon: BrainCircuit, color: 'var(--primary-light)' },
  fixtures: { label: 'Sync fixtures', icon: CalendarClock, color: 'var(--cyan)' },
  backtest: { label: 'Backtest', icon: FlaskConical, color: 'var(--captain)' },
}

export function JobStatus({ status }) {
  if (status === 'running') return <Badge tone="primary"><Loader2 size={11} className="spin" />Running</Badge>
  if (status === 'queued') return <Badge tone="gray"><Clock size={11} />Queued</Badge>
  if (status === 'succeeded') return <Badge tone="success"><CheckCircle2 size={11} />Succeeded</Badge>
  return <Badge tone="danger"><XCircle size={11} />Failed</Badge>
}

function duration(j) {
  if (!j.started_at) return '—'
  const end = j.finished_at ? new Date(j.finished_at) : new Date()
  const s = (end - new Date(j.started_at)) / 1000
  return s < 60 ? `${s.toFixed(1)}s` : `${Math.floor(s / 60)}m ${Math.round(s % 60)}s`
}

function JobCard({ kind, desc, children, onRun, busy }) {
  const k = KIND[kind]
  return (
    <div className="card job-card">
      <div className="row">
        <span className="job-icon" style={{ color: k.color, background: `color-mix(in srgb, ${k.color} 14%, transparent)` }}><k.icon size={18} /></span>
        <div className="grow"><h4>{k.label}</h4><div className="xs muted">{desc}</div></div>
      </div>
      {children}
      <Button variant="secondary" icon={Play} loading={busy} onClick={onRun} style={{ marginTop: 'auto' }}>Run</Button>
    </div>
  )
}

export default function Jobs() {
  const qc = useQueryClient()
  const [source, setSource] = useState('data/raw/all_json.zip')
  const [incremental, setIncremental] = useState(true)
  const [n, setN] = useState(60)
  const [open, setOpen] = useState(null)

  const { data, isLoading } = useQuery({
    queryKey: ['admin-jobs'],
    queryFn: getJobs,
    refetchInterval: (q) => (q.state.data?.jobs || []).some((j) => ['queued', 'running'].includes(j.status)) ? 2000 : 10_000,
  })
  const jobs = data?.jobs || []

  const run = useMutation({
    mutationFn: ({ kind }) => ({
      ingest: () => triggerIngest({ source, incremental }),
      features: () => triggerFeatures(),
      retrain: () => triggerRetrain({ format: 'all' }),
      backtest: () => triggerBacktest({ n: Number(n) || 60 }),
    })[kind](),
    onSuccess: (_, { kind }) => {
      toast.success(`${KIND[kind].label} queued`, 'Progress updates below.')
      qc.invalidateQueries({ queryKey: ['admin-jobs'] })
      if (kind === 'retrain' || kind === 'backtest') {
        setTimeout(() => qc.invalidateQueries({ queryKey: ['admin-models'] }), 4000)
      }
    },
    onError: (err) => toast.error('Could not queue job', apiError(err).message),
  })
  const busy = (kind) => run.isPending && run.variables?.kind === kind

  return (
    <div className="col" style={{ gap: 20 }}>
      <div className="grid-4">
        <JobCard kind="ingest" desc="Cricsheet JSON zip or folder → matches, deliveries, performances" busy={busy('ingest')} onRun={() => run.mutate({ kind: 'ingest' })}>
          <div className="field"><label className="label">Source path</label><input className="input" value={source} onChange={(e) => setSource(e.target.value)} /></div>
          <label className="row between small"><span className="secondary">Incremental (skip existing)</span><Switch checked={incremental} onChange={setIncremental} label="Incremental" /></label>
        </JobCard>
        <JobCard kind="features" desc="Rolling form, venue & matchup stats; infers roles and pace/spin styles" busy={busy('features')} onRun={() => run.mutate({ kind: 'features' })} />
        <JobCard kind="retrain" desc="Trains T20, ODI and Test ensembles (time-split validation), then promotes them" busy={busy('retrain')} onRun={() => run.mutate({ kind: 'retrain' })} />
        <JobCard kind="backtest" desc="Replay held-out matches through the full pipeline" busy={busy('backtest')} onRun={() => run.mutate({ kind: 'backtest' })}>
          <div className="field"><label className="label">Matches</label><input className="input" type="number" min={5} max={10000} value={n} onChange={(e) => setN(e.target.value)} /></div>
        </JobCard>
      </div>

      <Card title="Job history" icon={Clock} subtitle="Last 50 jobs in this API process" pad="sm">
        {!isLoading && !jobs.length ? <EmptyState icon={Clock} title="No jobs yet">Run an operation above to see its progress here.</EmptyState> : (
          <div className="table-wrap" style={{ border: 0 }}>
            <table className="table">
              <thead><tr><th /><th>Job</th><th>Status</th><th>Created</th><th className="num">Duration</th></tr></thead>
              <tbody>
                {jobs.map((j) => {
                  const k = KIND[j.kind] || { label: j.kind, icon: Play, color: 'var(--text-muted)' }
                  const isOpen = open === j.id
                  return (
                    <Fragment key={j.id}>
                      <tr onClick={() => setOpen(isOpen ? null : j.id)} style={{ cursor: 'pointer' }}>
                        <td style={{ width: 28 }}>{isOpen ? <ChevronDown size={14} /> : <ChevronRight size={14} />}</td>
                        <td><span className="row gap-8"><k.icon size={15} style={{ color: k.color }} /><b>{k.label}</b><span className="xs muted mono">{j.id.slice(0, 8)}</span></span></td>
                        <td><JobStatus status={j.status} /></td>
                        <td className="muted">{timeAgo(j.created_at)}</td>
                        <td className="num mono">{duration(j)}</td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={5} style={{ background: 'var(--bg-base)' }}>
                            {Object.keys(j.params || {}).length > 0 && <div className="xs muted mb-8">Params: <span className="mono">{JSON.stringify(j.params)}</span></div>}
                            <pre className="code" style={{ maxHeight: 320, overflow: 'auto' }}>
                              {j.error || (j.result ? JSON.stringify(j.result, null, 2) : j.status === 'succeeded' ? 'Done' : 'Waiting for result…')}
                            </pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
