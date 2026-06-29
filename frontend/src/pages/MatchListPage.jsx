import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getUpcomingMatches } from '../api/client'
import MatchCard from '../components/MatchCard'

// Demo matches for when API is not connected
const DEMO_MATCHES = [
  { id: 'demo-001', match_type: 'IPL', team_a: 'Mumbai Indians', team_b: 'Royal Challengers Bengaluru', venue_name: 'Wankhede Stadium', match_date: '2026-04-15', event_name: 'Indian Premier League', event_stage: 'League Stage', prediction_ready: true, is_live: false },
  { id: 'demo-002', match_type: 'IPL', team_a: 'Chennai Super Kings', team_b: 'Kolkata Knight Riders', venue_name: 'MA Chidambaram Stadium', match_date: '2026-04-16', event_name: 'Indian Premier League', event_stage: 'League Stage', prediction_ready: true, is_live: false },
  { id: 'demo-003', match_type: 'T20', team_a: 'India', team_b: 'Australia', venue_name: 'Eden Gardens', match_date: '2026-04-18', event_name: 'T20 Bilateral Series', event_stage: '1st T20I', prediction_ready: true, is_live: false },
  { id: 'demo-004', match_type: 'IPL', team_a: 'Gujarat Titans', team_b: 'Rajasthan Royals', venue_name: 'Narendra Modi Stadium', match_date: '2026-04-19', event_name: 'Indian Premier League', event_stage: 'League Stage', prediction_ready: true, is_live: true },
  { id: 'demo-005', match_type: 'ODI', team_a: 'India', team_b: 'England', venue_name: 'Narendra Modi Stadium', match_date: '2026-04-22', event_name: 'ODI Series', event_stage: '1st ODI', prediction_ready: false, is_live: false },
]

const FORMAT_TABS = ['All', 'IPL', 'T20', 'ODI', 'Test']

export default function MatchListPage() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState('All')
  const [search, setSearch] = useState('')

  const { data, isLoading, error } = useQuery({
    queryKey: ['matches', activeTab],
    queryFn: () => getUpcomingMatches({ format: activeTab === 'All' ? undefined : activeTab }),
    retry: false,
  })

  const matches = data?.matches || DEMO_MATCHES
  const filtered = matches.filter(m => {
    const matchesFormat = activeTab === 'All' || m.match_type === activeTab
    const matchesSearch = !search || m.team_a.toLowerCase().includes(search.toLowerCase()) ||
      m.team_b.toLowerCase().includes(search.toLowerCase())
    return matchesFormat && matchesSearch
  })

  return (
    <div className="page">
      <div className="container">
        <div className="page-header">
          <div className="flex justify-between items-center" style={{ flexWrap: 'wrap', gap: 'var(--sp-4)' }}>
            <div>
              <h1 className="page-title">Upcoming Matches</h1>
              <p>Select a match to generate your AI-powered Dream11 team</p>
            </div>
            {!data && !isLoading && (
              <span className="badge" style={{ background: 'rgba(245,158,11,0.1)', color: 'var(--color-secondary)', border: '1px solid rgba(245,158,11,0.2)', fontSize: 11 }}>
                📋 Demo Mode — Connect backend for live data
              </span>
            )}
          </div>
        </div>

        {/* Filters */}
        <div className="flex gap-3 mb-6" style={{ flexWrap: 'wrap' }}>
          <div className="tabs" style={{ flex: 'none' }}>
            {FORMAT_TABS.map(tab => (
              <button key={tab} className={`tab${activeTab === tab ? ' active' : ''}`} onClick={() => setActiveTab(tab)}>
                {tab}
              </button>
            ))}
          </div>
          <input
            className="input"
            style={{ maxWidth: 280, flex: 1 }}
            placeholder="🔍 Search teams..."
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>

        {isLoading ? (
          <div className="grid-2" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))' }}>
            {[1,2,3,4].map(i => <div key={i} className="skeleton" style={{ height: 160 }} />)}
          </div>
        ) : (
          <>
            {filtered.length === 0 ? (
              <div className="card text-center" style={{ padding: 'var(--sp-16)' }}>
                <div style={{ fontSize: 48, marginBottom: 'var(--sp-4)' }}>🏏</div>
                <h3>No matches found</h3>
                <p style={{ marginTop: 'var(--sp-2)' }}>Try a different format or search term</p>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: 'var(--sp-4)' }}>
                {filtered.map(match => (
                  <MatchCard key={match.id} match={match} onClick={() => navigate(`/matches/${match.id}`)} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}
