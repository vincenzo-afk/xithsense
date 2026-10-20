import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Pencil, Plus, ScrollText, Search, Trash2 } from 'lucide-react'
import { apiError, createRule, deleteRule, getRules, updateRule } from '../../api/client'
import { Alert, Badge, Button, EmptyState, Modal, Skeleton, Switch, Tabs } from '../ui'
import { fmt } from '../../lib/format'
import { toast } from '../../store/uiStore'

const TYPES = ['player', 'venue', 'matchup', 'context']
const TYPE_TONE = { player: 'primary', venue: 'success', matchup: 'warning', context: 'gray' }
const EMPTY = { rule_type: 'player', player_key: '', condition: '{\n  "is_chasing": true\n}', match_types: 'T20, IPL', impact_score: 10, confidence: 0.7, description: '', source: '' }

function condChips(cond) {
  return Object.entries(cond || {}).map(([k, v]) => (
    <span key={k} className="cond-chip">{k}={Array.isArray(v) ? v.join('|') : typeof v === 'object' ? JSON.stringify(v) : String(v)}</span>
  ))
}

function RuleForm({ initial, onClose }) {
  const qc = useQueryClient()
  const editing = !!initial?.id
  const [f, setF] = useState(() => editing ? {
    ...initial, player_key: initial.player_key || '', condition: JSON.stringify(initial.condition, null, 2),
    match_types: (initial.match_types || []).join(', '), description: initial.description || '', source: initial.source || '',
  } : EMPTY)
  const [err, setErr] = useState(null)
  const set = (k) => (e) => setF((s) => ({ ...s, [k]: e?.target ? e.target.value : e }))

  const parsed = useMemo(() => { try { const c = JSON.parse(f.condition); return typeof c === 'object' && c && !Array.isArray(c) ? c : null } catch { return null } }, [f.condition])

  const save = useMutation({
    mutationFn: () => {
      const body = {
        player_key: f.player_key.trim() || null, condition: parsed,
        match_types: f.match_types.split(',').map((s) => s.trim()).filter(Boolean),
        impact_score: Number(f.impact_score), confidence: Number(f.confidence),
        description: f.description.trim() || null, source: f.source.trim() || null,
      }
      if (!body.match_types.length) body.match_types = null
      return editing ? updateRule(initial.id, body) : createRule({ ...body, rule_type: f.rule_type, is_active: true })
    },
    onSuccess: (r) => { toast.success(editing ? 'Rule updated' : `Rule ${r.id} created`, 'Predictions refresh on next request.'); qc.invalidateQueries({ queryKey: ['admin-rules'] }); onClose() },
    onError: (e) => setErr(apiError(e).message),
  })

  const effective = Number(f.impact_score) * Number(f.confidence)
  return (
    <Modal open onClose={onClose} title={editing ? `Edit ${initial.id}` : 'New analyst rule'} width={620}
      footer={<><Button variant="ghost" onClick={onClose}>Cancel</Button><Button loading={save.isPending} disabled={!parsed || !Object.keys(parsed || {}).length} onClick={() => { setErr(null); save.mutate() }}>{editing ? 'Save changes' : 'Create rule'}</Button></>}>
      <div className="col" style={{ gap: 14 }}>
        {err && <Alert tone="danger">{err}</Alert>}
        <div className="grid-2">
          <div className="field">
            <label className="label">Rule type</label>
            <select className="select" value={f.rule_type} onChange={set('rule_type')} disabled={editing}>{TYPES.map((t) => <option key={t} value={t}>{t}</option>)}</select>
          </div>
          <div className="field">
            <label className="label">Player key <span className="muted">(blank = all players)</span></label>
            <input className="input" placeholder="Kohli, V" value={f.player_key} onChange={set('player_key')} />
          </div>
        </div>
        <div className="field">
          <label className="label">Condition (JSON)</label>
          <textarea className="textarea mono" rows={5} value={f.condition} onChange={set('condition')} style={{ fontSize: 12.5 }} />
          <span className="hint" style={{ color: parsed ? undefined : 'var(--danger)' }}>
            {parsed ? 'Keys: venue, pitch_type, is_chasing, toss_decision, phase, batting_position, opposition_bowling_type, is_final_or_knockout, home_match, rest_days {min,max}, batting_style, primary_role, bowling_style_contains' : 'Invalid JSON object'}
          </span>
        </div>
        <div className="field"><label className="label">Match types</label><input className="input" value={f.match_types} onChange={set('match_types')} placeholder="T20, IPL" /></div>
        <div className="grid-2">
          <div className="field">
            <label className="label row between"><span>Impact score</span><b className={`mono ${f.impact_score >= 0 ? 'impact-pos' : 'impact-neg'}`}>{f.impact_score > 0 ? '+' : ''}{f.impact_score}</b></label>
            <input type="range" min={-100} max={100} value={f.impact_score} onChange={set('impact_score')} />
          </div>
          <div className="field">
            <label className="label row between"><span>Confidence</span><b className="mono">{Number(f.confidence).toFixed(2)}</b></label>
            <input type="range" min={0} max={1} step={0.01} value={f.confidence} onChange={set('confidence')} />
          </div>
        </div>
        <div className="small muted">Effective impact per player: <b className={effective >= 0 ? 'impact-pos' : 'impact-neg'}>{effective >= 0 ? '+' : ''}{fmt(effective, 2)}</b></div>
        <div className="field"><label className="label">Description</label><input className="input" value={f.description} onChange={set('description')} placeholder="Shown to users in explanations" /></div>
        <div className="field"><label className="label">Source / evidence</label><input className="input" value={f.source} onChange={set('source')} placeholder="e.g. Cricsheet 2019–2026: chasing avg 54 vs 34 (n=62)" /></div>
      </div>
    </Modal>
  )
}

export default function Rules() {
  const qc = useQueryClient()
  const [type, setType] = useState('all')
  const [q, setQ] = useState('')
  const [editing, setEditing] = useState(null)
  const { data: rules = [], isLoading } = useQuery({ queryKey: ['admin-rules'], queryFn: () => getRules() })

  const toggle = useMutation({
    mutationFn: (r) => updateRule(r.id, { is_active: !r.is_active }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-rules'] }),
    onError: (e) => toast.error('Update failed', apiError(e).message),
  })
  const remove = useMutation({
    mutationFn: (r) => deleteRule(r.id),
    onSuccess: (_, r) => { toast.success(`${r.id} deactivated`); qc.invalidateQueries({ queryKey: ['admin-rules'] }) },
    onError: (e) => toast.error('Delete failed', apiError(e).message),
  })

  const counts = TYPES.reduce((acc, t) => ({ ...acc, [t]: rules.filter((r) => r.rule_type === t).length }), {})
  const shown = rules.filter((r) => (type === 'all' || r.rule_type === type)
    && (!q || `${r.id} ${r.player_key || ''} ${r.description || ''} ${JSON.stringify(r.condition)}`.toLowerCase().includes(q.toLowerCase())))

  return (
    <div>
      <div className="toolbar">
        <Tabs value={type} onChange={setType} tabs={[{ value: 'all', label: 'All', count: rules.length }, ...TYPES.map((t) => ({ value: t, label: t[0].toUpperCase() + t.slice(1), count: counts[t] }))]} />
        <div className="row">
          <div className="input-wrap" style={{ width: 240 }}><Search size={15} /><input className="input" style={{ height: 36 }} placeholder="Search rules" value={q} onChange={(e) => setQ(e.target.value)} /></div>
          <Button icon={Plus} onClick={() => setEditing({})}>New rule</Button>
        </div>
      </div>
      {isLoading ? <Skeleton h={300} r={14} /> : !shown.length ? <div className="card"><EmptyState icon={ScrollText} title="No rules match">Adjust the filter or add a new rule.</EmptyState></div> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>Rule</th><th>Applies to</th><th>Condition</th><th className="num">Impact</th><th className="num">Conf.</th><th className="num">Effective</th><th>Active</th><th /></tr></thead>
            <tbody>
              {shown.map((r) => (
                <tr key={r.id} style={{ opacity: r.is_active ? 1 : 0.55 }}>
                  <td style={{ maxWidth: 300 }}>
                    <div className="row gap-8"><span className="mono bold">{r.id}</span><Badge tone={TYPE_TONE[r.rule_type]}>{r.rule_type}</Badge></div>
                    <div className="xs muted mt-4" style={{ whiteSpace: 'normal' }}>{r.description}</div>
                  </td>
                  <td className="small">{r.player_key || <span className="muted">All players</span>}</td>
                  <td><div className="row gap-4 wrap" style={{ maxWidth: 280 }}>{condChips(r.condition)}</div></td>
                  <td className={`num ${r.impact_score >= 0 ? 'impact-pos' : 'impact-neg'}`}>{r.impact_score > 0 ? '+' : ''}{r.impact_score}</td>
                  <td className="num mono">{fmt(r.confidence, 2)}</td>
                  <td className={`num ${r.effective_impact >= 0 ? 'impact-pos' : 'impact-neg'}`}>{r.effective_impact > 0 ? '+' : ''}{fmt(r.effective_impact, 1)}</td>
                  <td><Switch checked={r.is_active} onChange={() => toggle.mutate(r)} label={`Toggle ${r.id}`} /></td>
                  <td>
                    <div className="row gap-4">
                      <Button size="sm" variant="ghost" icon={Pencil} onClick={() => setEditing(r)} aria-label="Edit" />
                      <Button size="sm" variant="ghost" icon={Trash2} disabled={!r.is_active} onClick={() => remove.mutate(r)} aria-label="Deactivate" />
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      {editing && <RuleForm initial={editing.id ? editing : null} onClose={() => setEditing(null)} />}
    </div>
  )
}
