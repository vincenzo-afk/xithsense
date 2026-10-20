import { useSearchParams } from 'react-router-dom'
import { Activity, BrainCircuit, Play, Radio, ScrollText, ShieldCheck, Trophy, Users } from 'lucide-react'
import { PageHead, UnderlineTabs } from '../components/ui'
import Overview from '../components/admin/Overview'
import Jobs from '../components/admin/Jobs'
import Models from '../components/admin/Models'
import Rules from '../components/admin/Rules'
import LiveData from '../components/admin/LiveData'
import { AuditTab, MatchesTab, UsersTab } from '../components/admin/People'
import './ops.css'

const TABS = [
  { value: 'overview', label: 'Overview', icon: Activity },
  { value: 'live', label: 'Live data', icon: Radio },
  { value: 'jobs', label: 'Jobs', icon: Play },
  { value: 'models', label: 'Models', icon: BrainCircuit },
  { value: 'rules', label: 'Rules', icon: ScrollText },
  { value: 'users', label: 'Users', icon: Users },
  { value: 'matches', label: 'Matches', icon: Trophy },
  { value: 'audit', label: 'Audit', icon: ShieldCheck },
]

export default function AdminPage() {
  const [params, setParams] = useSearchParams()
  const tab = TABS.some((t) => t.value === params.get('tab')) ? params.get('tab') : 'overview'
  const setTab = (t) => setParams(t === 'overview' ? {} : { tab: t }, { replace: true })

  return (
    <div className="fade-in">
      <PageHead eyebrow={<><ShieldCheck size={13} />Operator console</>} title="Admin" subtitle="Live data feed, pipeline jobs, models, analyst rules, users and fixtures." />
      <UnderlineTabs tabs={TABS} value={tab} onChange={setTab} />
      {tab === 'overview' && <Overview />}
      {tab === 'live' && <LiveData />}
      {tab === 'jobs' && <Jobs />}
      {tab === 'models' && <Models />}
      {tab === 'rules' && <Rules />}
      {tab === 'users' && <UsersTab />}
      {tab === 'matches' && <MatchesTab />}
      {tab === 'audit' && <AuditTab />}
    </div>
  )
}
