import { useEffect, useRef, useState } from 'react'
import { Link, NavLink, Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import {
  Bell, Crown, LayoutDashboard, LogOut, MessageSquareText, Moon, Radio, Settings,
  ShieldCheck, Sun, Trophy, User,
} from 'lucide-react'
import { getNotifications, getUpcomingMatches, logoutApi, markNotificationsRead } from '../api/client'
import { useAuthStore } from '../store/authStore'
import { useUiStore } from '../store/uiStore'
import { timeAgo } from '../lib/format'
import { ProBadge } from './ui'

export function Logo({ size = 34, withText = true }) {
  return (
    <span className="brand" style={{ padding: 0 }}>
      <span className="brand-mark" style={{ width: size, height: size, borderRadius: size * 0.3 }}>
        <svg width={size * 0.56} height={size * 0.56} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round">
          <path d="M5 4l14 16M19 4L5 20" />
          <circle cx="12" cy="12" r="2.2" fill="currentColor" stroke="none" />
        </svg>
      </span>
      {withText && <span>Xith<span className="gradient-text">Sense</span></span>}
    </span>
  )
}

const TITLES = [
  [/^\/matches\/[^/]+\/live/, 'Live intelligence'],
  [/^\/matches\/[^/]+/, 'Match centre'],
  [/^\/matches/, 'Matches'],
  [/^\/players/, 'Player profile'],
  [/^\/chat/, 'AI assistant'],
  [/^\/account/, 'Account'],
  [/^\/subscribe/, 'Premium'],
  [/^\/admin/, 'Admin console'],
]

function Notifications() {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const qc = useQueryClient()
  const { data } = useQuery({ queryKey: ['notifications'], queryFn: getNotifications, refetchInterval: 60_000 })
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const unread = data?.unread || 0
  const toggle = async () => {
    setOpen((o) => !o)
    if (!open && unread) {
      await markNotificationsRead()
      qc.invalidateQueries({ queryKey: ['notifications'] })
    }
  }
  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button className="btn btn-ghost btn-icon" onClick={toggle} aria-label="Notifications">
        <Bell size={18} />
        {unread > 0 && <span style={{ position: 'absolute', top: 7, right: 8, width: 8, height: 8, borderRadius: 9, background: 'var(--danger)', boxShadow: '0 0 0 2px var(--bg)' }} />}
      </button>
      {open && (
        <div className="dropdown" style={{ width: 340 }}>
          <div className="row between" style={{ padding: '8px 10px' }}><b>Notifications</b><span className="muted xs">{data?.notifications?.length || 0}</span></div>
          {(data?.notifications || []).length === 0 && <div className="muted small" style={{ padding: '18px 10px' }}>You're all caught up. Toss and playing-XI alerts will appear here.</div>}
          <div style={{ maxHeight: 360, overflowY: 'auto' }}>
            {(data?.notifications || []).map((n) => (
              <Link key={n.id} to={n.match_id ? `/matches/${n.match_id}` : '#'} className="dropdown-item" style={{ alignItems: 'flex-start' }} onClick={() => setOpen(false)}>
                <span className="status-dot" style={{ background: n.is_read ? 'var(--border-strong)' : 'var(--primary)', marginTop: 6 }} />
                <span className="grow"><span className="bold" style={{ color: 'var(--text)' }}>{n.title}</span><br /><span className="small">{n.message_preview}</span><br /><span className="xs muted">{timeAgo(n.created_at)}</span></span>
              </Link>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function UserMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef(null)
  const navigate = useNavigate()
  const { user, logout, refreshToken, isPremium } = useAuthStore()
  const qc = useQueryClient()
  useEffect(() => {
    const h = (e) => ref.current && !ref.current.contains(e.target) && setOpen(false)
    document.addEventListener('mousedown', h)
    return () => document.removeEventListener('mousedown', h)
  }, [])
  const signOut = async () => {
    await logoutApi(refreshToken)
    logout()
    qc.clear()
    window.location.assign('/')
  }
  return (
    <div style={{ position: 'relative' }} ref={ref}>
      <button className="row gap-8" onClick={() => setOpen((o) => !o)} aria-label="Account menu">
        <span className="avatar">{(user?.full_name || user?.email || '?')[0].toUpperCase()}</span>
      </button>
      {open && (
        <div className="dropdown">
          <div style={{ padding: '10px 10px 12px' }}>
            <div className="bold truncate">{user?.full_name || 'Fantasy player'}</div>
            <div className="muted small truncate">{user?.email}</div>
            <div className="mt-8">{isPremium() ? <ProBadge /> : <span className="badge">Free plan</span>}</div>
          </div>
          <div className="divider" style={{ margin: '0 0 6px' }} />
          <Link to="/account" className="dropdown-item" onClick={() => setOpen(false)}><Settings size={16} />Account & settings</Link>
          {!isPremium() && <Link to="/subscribe" className="dropdown-item" onClick={() => setOpen(false)}><Crown size={16} className="text-captain" />Upgrade to Premium</Link>}
          <button className="dropdown-item" onClick={signOut}><LogOut size={16} />Sign out</button>
        </div>
      )}
    </div>
  )
}

export default function Layout() {
  const { pathname } = useLocation()
  const { user, isPremium, isAdmin } = useAuthStore()
  const { theme, toggleTheme } = useUiStore()
  const { data: upcoming } = useQuery({ queryKey: ['matches', 'upcoming', 'All'], queryFn: () => getUpcomingMatches({ limit: 20 }), staleTime: 60_000 })
  const live = upcoming?.matches?.find((m) => m.is_live)
  const title = TITLES.find(([re]) => re.test(pathname))?.[1] || 'XithSense'
  useEffect(() => { window.scrollTo(0, 0) }, [pathname])

  const nav = [
    { to: '/matches', label: 'Matches', icon: Trophy },
    live && { to: `/matches/${live.id}/live`, label: 'Live now', icon: Radio, pill: <span className="badge badge-live"><span className="dot" />LIVE</span> },
    { to: '/chat', label: 'AI Assistant', icon: MessageSquareText, pill: !isPremium() && <ProBadge /> },
    { to: '/account', label: 'Account', icon: User },
  ].filter(Boolean)

  return (
    <div className="shell">
      <aside className="sidebar">
        <Link to="/matches" className="brand"><Logo /></Link>
        <div className="nav-section">
          <div className="nav-label">Play</div>
          {nav.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.to === '/matches'} className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}>
              <n.icon size={18} />{n.label}{n.pill && <span className="pill">{n.pill}</span>}
            </NavLink>
          ))}
        </div>
        {isAdmin() && (
          <div className="nav-section">
            <div className="nav-label">Operate</div>
            <NavLink to="/admin" className={({ isActive }) => `nav-item${isActive ? ' active' : ''}`}><ShieldCheck size={18} />Admin console</NavLink>
          </div>
        )}
        <div className="sidebar-foot">
          {!isPremium() && (
            <div className="upgrade-card">
              <div className="row gap-8 bold"><Crown size={16} className="text-captain" />Go Premium</div>
              <p className="small mt-4">All 4 team modes, differentials, AI chat and the live feed.</p>
              <Link to="/subscribe" className="btn btn-gold btn-sm btn-block mt-12">Upgrade · ₹299/mo</Link>
            </div>
          )}
          <div className="row" style={{ padding: '10px 8px 2px' }}>
            <span className="avatar">{(user?.full_name || user?.email || '?')[0].toUpperCase()}</span>
            <div className="grow">
              <div className="bold small truncate">{user?.full_name || user?.email}</div>
              <div className="xs muted" style={{ textTransform: 'capitalize' }}>{user?.role} plan</div>
            </div>
          </div>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <Link to="/matches" className="show-mobile"><Logo size={30} withText={false} /></Link>
          <div className="topbar-title grow">{title}</div>
          {live && !pathname.includes('/live') && (
            <Link to={`/matches/${live.id}/live`} className="badge badge-live badge-lg hide-mobile"><span className="dot" />{live.team_a.split(' ').pop()} v {live.team_b.split(' ').pop()} · live</Link>
          )}
          <button className="btn btn-ghost btn-icon" onClick={toggleTheme} aria-label="Toggle theme">{theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}</button>
          <Notifications />
          <UserMenu />
        </header>
        <main className="content"><Outlet /></main>
      </div>

      <nav className="bottom-nav">
        <NavLink to="/matches" end><Trophy size={20} />Matches</NavLink>
        {live ? <NavLink to={`/matches/${live.id}/live`}><Radio size={20} />Live</NavLink> : null}
        <NavLink to="/chat"><MessageSquareText size={20} />AI Chat</NavLink>
        {isAdmin() && <NavLink to="/admin"><LayoutDashboard size={20} />Admin</NavLink>}
        <NavLink to="/account"><User size={20} />Account</NavLink>
      </nav>
    </div>
  )
}

