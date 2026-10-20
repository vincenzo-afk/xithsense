import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Radio, ScrollText, Search, Trophy, Users } from 'lucide-react'
import {
  apiError, getAuditLog, getUpcomingMatches, getUsers, setUserRole, updateMatchAdmin,
} from '../../api/client'
import { Badge, Button, EmptyState, LiveBadge, Skeleton, TeamCrest } from '../ui'
import { fmtDate, relativeDay, timeAgo, fmtTime, matchStart, shortVenue } from '../../lib/format'
import { useAuthStore } from '../../store/authStore'
import { toast } from '../../store/uiStore'

export function UsersTab() {
  const qc = useQueryClient()
  const me = useAuthStore((s) => s.user)
  const [q, setQ] = useState('')
  const { data, isLoading } = useQuery({ queryKey: ['admin-users', q], queryFn: () => getUsers({ q: q || undefined }) })
  const role = useMutation({
    mutationFn: ({ id, role }) => setUserRole(id, role),
    onSuccess: (r) => { toast.success('Role updated', `User is now ${r.role}.`); qc.invalidateQueries({ queryKey: ['admin-users'] }); qc.invalidateQueries({ queryKey: ['admin-metrics'] }) },
    onError: (e) => toast.error('Could not change role', apiError(e).message),
  })
  const users = data?.users || []
  return (
    <div>
      <div className="toolbar">
        <div className="input-wrap" style={{ width: 300 }}><Search size={15} /><input className="input" style={{ height: 36 }} placeholder="Search by name or email" value={q} onChange={(e) => setQ(e.target.value)} /></div>
        <span className="small muted">{users.length} users</span>
      </div>
      {isLoading ? <Skeleton h={240} r={14} /> : !users.length ? <div className="card"><EmptyState icon={Users} title="No users found" /></div> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>User</th><th>Role</th><th className="num">Predictions</th><th>Joined</th><th>Last login</th></tr></thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td>
                    <div className="row">
                      <span className="avatar">{(u.full_name || u.email)[0].toUpperCase()}</span>
                      <div className="grow"><div className="bold truncate">{u.full_name || '—'}</div><div className="xs muted truncate">{u.email}</div></div>
                    </div>
                  </td>
                  <td>
                    <select className="select select-sm" value={u.role} disabled={u.id === me?.id || role.isPending}
                      onChange={(e) => role.mutate({ id: u.id, role: e.target.value })} aria-label={`Role for ${u.email}`}>
                      <option value="free">Free</option><option value="premium">Premium</option><option value="admin">Admin</option>
                    </select>
                  </td>
                  <td className="num mono">{u.predictions}</td>
                  <td className="small muted">{fmtDate(u.created_at, { day: 'numeric', month: 'short', year: 'numeric' })}</td>
                  <td className="small muted">{u.last_login_at ? timeAgo(u.last_login_at) : 'Never'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function MatchControl({ m }) {
  const qc = useQueryClient()
  const [winner, setWinner] = useState(m.toss_winner || m.team_a)
  const [decision, setDecision] = useState(m.toss_decision || 'field')
  const mut = useMutation({
    mutationFn: (body) => updateMatchAdmin(m.id, body),
    onSuccess: (r) => {
      toast.success('Match updated', r.notifications ? `${r.notifications} notification event${r.notifications > 1 ? 's' : ''} sent to users.` : 'Predictions will refresh.')
      qc.invalidateQueries({ queryKey: ['matches'] })
      qc.invalidateQueries({ queryKey: ['match', m.id] })
      qc.invalidateQueries({ queryKey: ['notifications'] })
    },
    onError: (e) => toast.error('Update failed', apiError(e).message),
  })
  const start = matchStart(m)
  return (
    <div className="match-ctrl">
      <div className="row">
        <TeamCrest name={m.team_a} size="sm" /><TeamCrest name={m.team_b} size="sm" />
        <div className="grow">
          <div className="bold truncate">{m.team_a} vs {m.team_b}</div>
          <div className="xs muted">{m.id} · {relativeDay(start)} {fmtTime(start)} · {shortVenue(m.venue_name)}</div>
        </div>
        {m.is_live ? <LiveBadge /> : m.toss_winner ? <Badge tone="primary">Toss done</Badge> : <Badge>Pre-toss</Badge>}
      </div>
      <div className="row gap-8 wrap">
        <select className="select select-sm" value={winner} onChange={(e) => setWinner(e.target.value)} aria-label="Toss winner">
          <option value={m.team_a}>{m.team_a}</option><option value={m.team_b}>{m.team_b}</option>
        </select>
        <select className="select select-sm" value={decision} onChange={(e) => setDecision(e.target.value)} aria-label="Toss decision">
          <option value="bat">chose to bat</option><option value="field">chose to field</option>
        </select>
        <Button size="sm" variant="secondary" loading={mut.isPending && !!mut.variables?.toss_winner} onClick={() => mut.mutate({ toss_winner: winner, toss_decision: decision })}>Set toss</Button>
      </div>
      <div className="row gap-8">
        <select className="select select-sm" value={m.status} disabled={mut.isPending} onChange={(e) => mut.mutate({ status: e.target.value })} aria-label="Match status">
          <option value="upcoming">Upcoming</option><option value="live">Live</option><option value="complete">Complete</option>
        </select>
      </div>
    </div>
  )
}

export function MatchesTab() {
  const { data, isLoading } = useQuery({ queryKey: ['matches', 'upcoming', 'admin'], queryFn: () => getUpcomingMatches({ limit: 50 }) })
  const matches = data?.matches || []
  return (
    <div className="card pad-0">
      <div className="card-head" style={{ padding: '16px 16px 0' }}>
        <div><h3><Trophy size={17} className="text-primary" />Fixture control</h3><div className="sub">Setting the toss refreshes predictions and notifies users (EVT-02). Setting a match live starts the live feed.</div></div>
        <Badge><Radio size={11} />{matches.filter((m) => m.is_live).length} live</Badge>
      </div>
      {isLoading ? <div style={{ padding: 16 }}><Skeleton h={200} /></div> : !matches.length ? <EmptyState icon={Trophy} title="No upcoming fixtures" /> : matches.map((m) => <MatchControl key={m.id} m={m} />)}
    </div>
  )
}

export function AuditTab() {
  const [action, setAction] = useState('')
  const { data, isLoading } = useQuery({ queryKey: ['admin-audit', action], queryFn: () => getAuditLog({ action: action || undefined, limit: 100 }) })
  const entries = data?.entries || []
  const tone = (a) => a.startsWith('rule') ? 'warning' : a.startsWith('model') ? 'primary' : a.startsWith('user') ? 'danger' : 'gray'
  return (
    <div>
      <div className="toolbar">
        <select className="select" style={{ width: 220, height: 36 }} value={action} onChange={(e) => setAction(e.target.value)} aria-label="Filter actions">
          <option value="">All actions</option>
          {['rule', 'model', 'data', 'features', 'backtest', 'user', 'match'].map((a) => <option key={a} value={a}>{a}.*</option>)}
        </select>
        <span className="small muted">{entries.length} entries</span>
      </div>
      {isLoading ? <Skeleton h={240} r={14} /> : !entries.length ? <div className="card"><EmptyState icon={ScrollText} title="No audit entries yet">Admin actions are recorded here permanently.</EmptyState></div> : (
        <div className="table-wrap">
          <table className="table">
            <thead><tr><th>When</th><th>Admin</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
            <tbody>
              {entries.map((e) => (
                <tr key={e.id}>
                  <td className="small muted" style={{ whiteSpace: 'nowrap' }}>{timeAgo(e.created_at)}</td>
                  <td className="small">{e.admin}</td>
                  <td><Badge tone={tone(e.action)}>{e.action}</Badge></td>
                  <td className="small mono">{e.target_type ? `${e.target_type}:${(e.target_id || '').slice(0, 12)}` : '—'}</td>
                  <td><span className="xs mono muted truncate" style={{ display: 'block', maxWidth: 360 }}>{e.payload ? JSON.stringify(e.payload) : '—'}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
