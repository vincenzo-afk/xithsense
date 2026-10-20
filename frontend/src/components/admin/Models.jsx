import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { BrainCircuit, CheckCircle2, FlaskConical, Rocket } from 'lucide-react'
import { activateModel, apiError, getBacktests, getModels } from '../../api/client'
import { Badge, Button, Card, ChartTip, EmptyState, Skeleton } from '../ui'
import { fmt, fmtDate, fmtInt, pct } from '../../lib/format'
import { toast } from '../../store/uiStore'

export default function Models() {
  const qc = useQueryClient()
  const { data, isLoading } = useQuery({ queryKey: ['admin-models'], queryFn: getModels })
  const { data: bts } = useQuery({ queryKey: ['admin-backtests'], queryFn: getBacktests })
  const models = data?.models || []
  const active = models.find((m) => m.is_active)
  const importance = Object.entries(active?.feature_importance || {})
    .map(([feature, value]) => ({ feature: feature.replace(/_/g, ' '), value: Math.round(value * 1000) / 10 }))
    .sort((a, b) => b.value - a.value)

  const activate = useMutation({
    mutationFn: activateModel,
    onSuccess: () => { toast.success('Model promoted', 'New predictions now use this artifact.'); qc.invalidateQueries({ queryKey: ['admin-models'] }); qc.invalidateQueries({ queryKey: ['admin-metrics'] }) },
    onError: (e) => toast.error('Activation failed', apiError(e).message),
  })

  if (isLoading) return <Skeleton h={300} r={14} />

  return (
    <div className="col" style={{ gap: 20 }}>
      <Card title="Model registry" icon={BrainCircuit} subtitle="Holdout metrics from a strict time split" pad="sm">
        {!models.length ? <EmptyState icon={BrainCircuit} title="No models trained">Use Jobs → Retrain model.</EmptyState> : (
          <div className="table-wrap" style={{ border: 0 }}>
            <table className="table">
              <thead><tr><th>Model</th><th>Format</th><th>Type</th><th className="num">Rows</th><th className="num">Val MAE</th><th className="num">Baseline</th><th className="num">ρ</th><th>Trained on</th><th /></tr></thead>
              <tbody>
                {models.map((m) => (
                  <tr key={m.id}>
                    <td><div className="bold">{m.name}</div><div className="xs muted">{fmtDate(m.created_at, { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}</div></td>
                    <td><span className="badge">{m.match_type || 'T20'}</span></td>
                    <td><span className="xs mono secondary">{m.model_type}</span></td>
                    <td className="num mono">{fmtInt(m.train_rows)}</td>
                    <td className="num mono bold">{fmt(m.val_mae, 2)}</td>
                    <td className="num mono muted">{fmt(m.baseline_mae, 2)}</td>
                    <td className="num mono">{fmt(m.val_spearman, 3)}</td>
                    <td className="small muted">{fmtDate(m.train_from)} → {fmtDate(m.train_to, { day: 'numeric', month: 'short', year: '2-digit' })}</td>
                    <td className="text-right">
                      {m.is_active ? <Badge tone="success"><CheckCircle2 size={11} />Active</Badge>
                        : <Button size="sm" variant="secondary" icon={Rocket} loading={activate.isPending && activate.variables === m.id} onClick={() => activate.mutate(m.id)}>Activate</Button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid-2">
        <Card title="Feature importance" icon={BrainCircuit} subtitle={active ? active.name : 'No active model'}>
          {importance.length ? (
            <div style={{ height: Math.max(220, importance.length * 24) }}>
              <ResponsiveContainer>
                <BarChart data={importance} layout="vertical" margin={{ top: 0, right: 16, left: 40, bottom: 0 }}>
                  <XAxis type="number" tickLine={false} axisLine={false} unit="%" />
                  <YAxis type="category" dataKey="feature" width={130} tickLine={false} axisLine={false} />
                  <Tooltip cursor={{ fill: 'var(--bg-hover)' }} content={<ChartTip render={(d) => <><div className="t">{d.feature}</div><b className="mono">{d.value}%</b> of importance</>} />} />
                  <Bar dataKey="value" fill="var(--violet)" radius={[0, 6, 6, 0]} barSize={14} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="small">Importance is recorded when a model is trained.</p>}
        </Card>

        <Card title="Backtest runs" icon={FlaskConical} pad="sm">
          {!(bts?.backtests || []).length ? <EmptyState icon={FlaskConical} title="No backtests">Run one from the Jobs tab.</EmptyState> : (
            <div className="table-wrap" style={{ border: 0 }}>
              <table className="table">
                <thead><tr><th>Run</th><th className="num">N</th><th className="num">Capt.</th><th className="num">Top-3</th><th className="num">CPR</th><th className="num">ROI</th></tr></thead>
                <tbody>
                  {bts.backtests.map((b) => (
                    <tr key={b.id}>
                      <td><div className="bold small">{b.name}</div><div className="xs muted">{fmtDate(b.run_at)}</div></td>
                      <td className="num mono">{b.total_matches}</td>
                      <td className="num mono">{pct(b.captain_accuracy, 1)}</td>
                      <td className="num mono">{pct(b.top3_captain_rate, 0)}</td>
                      <td className="num mono">{pct(b.correct_player_rate, 0)}</td>
                      <td className={`num mono ${b.simulated_roi >= 0 ? 'text-success' : 'text-danger'}`}>{pct(b.simulated_roi, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>
      </div>
    </div>
  )
}
