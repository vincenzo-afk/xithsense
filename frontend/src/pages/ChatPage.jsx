import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  Bot, Crown, FileText, Globe, History, Link as LinkIcon, MapPin, MessageSquareText, Plus, RefreshCw, Send, Shield, Sparkles,
  Swords, Target, Trash2, User,
} from 'lucide-react'
import {
  apiError, deleteChatSession, getChatMessages, getChatSessions, getMatch, getUpcomingMatches, sendChat,
} from '../api/client'
import { Badge, Button, Spinner } from '../components/ui'
import { fmtDate, registerMatches, relativeDay, timeAgo } from '../lib/format'
import { toast } from '../store/uiStore'
import './ops.css'

const INTENT_LABEL = {
  CAPTAIN_PICK: 'Captaincy', DIFFERENTIAL: 'Differentials', TEAM_PICK: 'Team', MATCHUP_QUERY: 'Matchup',
  VENUE_QUERY: 'Venue', PLAYER_EXPLAIN: 'Player', GENERAL_STRATEGY: 'Strategy', OUT_OF_SCOPE: 'Out of scope',
  NEWS_QUERY: 'News',
}
const TOOL_ICON = {
  web_search: Globe, fetch_page: FileText, predict_players: Target, build_team: Shield, captain_options: Crown,
  differentials: Sparkles, player_profile: User, get_match_context: MapPin, list_upcoming_matches: History,
}

function Message({ m, onRetry }) {
  if (m.role === 'user') {
    return (
      <div className="msg user">
        <div className="user-avatar-sm"><User size={15} /></div>
        <div className="bubble">{m.content}</div>
      </div>
    )
  }
  return (
    <div className="msg assistant fade-in">
      <div className="bot-avatar"><Bot size={17} /></div>
      <div className="grow" style={{ minWidth: 0 }}>
        <div className={`bubble${m.error ? ' error' : ''}`}>
          {m.error ? (
            <div className="row gap-8 wrap">
              <span>{m.content}</span>
              {onRetry && <Button size="sm" variant="secondary" icon={RefreshCw} onClick={onRetry}>Retry</Button>}
            </div>
          ) : (
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
          )}
        </div>
        {m.tools?.length > 0 && !m.error && (
          <div className="msg-tools">
            {m.tools.map((t, i) => { const I = TOOL_ICON[t.name] || Sparkles; return <span key={i} className="tool-chip" title={t.name}><I size={12} />{t.summary}</span> })}
          </div>
        )}
        {m.sources?.length > 0 && !m.error && (
          <div className="msg-sources">
            <span className="xs muted upper">Sources</span>
            {m.sources.map((s, i) => <a key={i} href={s.url} target="_blank" rel="noopener noreferrer" className="source-link"><LinkIcon size={11} />{s.title || s.url}</a>)}
          </div>
        )}
        {(m.related?.length > 0 || m.intent) && !m.error && (
          <div className="msg-meta">
            {m.intent && <Badge tone="gray">{INTENT_LABEL[m.intent] || m.intent}</Badge>}
            {m.related?.map((p) => (
              <Link key={p.player_id} to={`/players/${p.player_id}`} className="chip" style={{ height: 26, fontSize: 12 }}>{p.full_name}</Link>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default function ChatPage() {
  const qc = useQueryClient()
  const [params, setParams] = useSearchParams()
  const [matchId, setMatchId] = useState(params.get('match') || '')
  const [sessionId, setSessionId] = useState(null)
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loadingSession, setLoadingSession] = useState(false)
  const scrollRef = useRef(null)
  const taRef = useRef(null)

  const { data: upcoming } = useQuery({ queryKey: ['matches', 'upcoming', 'All'], queryFn: () => getUpcomingMatches({ limit: 20 }) })
  const matches = upcoming?.matches || []
  registerMatches(matches)
  useEffect(() => { if (!matchId && matches.length) setMatchId(matches[0].id) }, [matches, matchId])
  const match = matches.find((m) => m.id === matchId)
  const { data: detail } = useQuery({ queryKey: ['match', matchId], queryFn: () => getMatch(matchId), enabled: !!matchId })
  const { data: sessions = [], isLoading: sessionsLoading } = useQuery({ queryKey: ['chat-sessions'], queryFn: getChatSessions })

  useEffect(() => { scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' }) }, [messages])

  const suggestions = useMemo(() => {
    const squadA = detail?.squads?.[detail?.team_a] || []
    const squadB = detail?.squads?.[detail?.team_b] || []
    const star = [...squadA, ...squadB].sort((a, b) => (b.credits || 0) - (a.credits || 0))[0]
    const batter = [...squadA, ...squadB].find((p) => p.role === 'BAT' && p.player_id !== star?.player_id)
    return [
      { icon: Crown, text: 'Who should be my captain today?' },
      { icon: Sparkles, text: 'Best differentials for a grand league?' },
      { icon: Shield, text: 'Suggest a safe XI for this match' },
      { icon: MapPin, text: 'How does the pitch play here?' },
      { icon: Globe, text: 'Any injury or playing XI news for this match?' },
      star && { icon: Target, text: `Is ${star.full_name} a good pick?` },
      batter && { icon: Swords, text: `How does ${batter.full_name} fare against spin and pace?` },
    ].filter(Boolean)
  }, [detail])

  const chat = useMutation({
    mutationFn: (text) => sendChat({ message: text, match_id: matchId || undefined, session_id: sessionId || undefined }),
    onSuccess: (data) => {
      const isNew = !sessionId
      setSessionId(data.session_id)
      setMessages((prev) => [...prev, { role: 'assistant', content: data.answer, intent: data.intent, related: data.related_players, tools: data.tools_used, sources: data.sources }])
      if (isNew) qc.invalidateQueries({ queryKey: ['chat-sessions'] })
    },
    onError: (err, text) => {
      const e = apiError(err)
      setMessages((prev) => [...prev, { role: 'assistant', error: true, content: e.message, retryText: text }])
    },
  })

  const send = (text) => {
    const msg = (text ?? input).trim()
    if (!msg || chat.isPending) return
    setMessages((prev) => [...prev, { role: 'user', content: msg }])
    setInput('')
    if (taRef.current) taRef.current.style.height = 'auto'
    chat.mutate(msg)
  }

  const retry = (idx) => {
    const m = messages[idx]
    setMessages((prev) => prev.filter((_, i) => i !== idx))
    chat.mutate(m.retryText)
  }

  const newChat = () => { setSessionId(null); setMessages([]); taRef.current?.focus() }

  const openSession = async (s) => {
    if (s.id === sessionId) return
    setLoadingSession(true)
    try {
      const msgs = await getChatMessages(s.id)
      setSessionId(s.id)
      if (s.match_id) setMatchId(s.match_id)
      setMessages(msgs.map((m) => ({ role: m.role, content: m.content })))
    } catch (err) {
      toast.error('Could not load conversation', apiError(err).message)
    } finally {
      setLoadingSession(false)
    }
  }

  const removeSession = async (e, s) => {
    e.stopPropagation()
    try {
      await deleteChatSession(s.id)
      if (s.id === sessionId) newChat()
      qc.invalidateQueries({ queryKey: ['chat-sessions'] })
    } catch (err) {
      toast.error('Delete failed', apiError(err).message)
    }
  }

  const changeMatch = (id) => {
    setMatchId(id)
    setParams(id ? { match: id } : {}, { replace: true })
    newChat()
  }

  const onKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }
  const autoGrow = (e) => {
    setInput(e.target.value)
    e.target.style.height = 'auto'
    e.target.style.height = `${Math.min(140, e.target.scrollHeight)}px`
  }

  return (
    <div className="chat-layout fade-in">
      <aside className="chat-sessions">
        <div style={{ padding: 12 }}><Button block icon={Plus} onClick={newChat}>New chat</Button></div>
        <div className="nav-label" style={{ display: 'flex', alignItems: 'center', gap: 6 }}><History size={12} />Recent</div>
        <div className="list">
          {sessionsLoading && <div style={{ padding: 16 }}><Spinner size={16} /></div>}
          {!sessionsLoading && !sessions.length && <p className="small muted" style={{ padding: '8px 10px' }}>Your conversations will be saved here.</p>}
          {sessions.map((s) => (
            <button key={s.id} className={`session-item${s.id === sessionId ? ' active' : ''}`} onClick={() => openSession(s)}>
              <MessageSquareText size={15} style={{ flexShrink: 0 }} />
              <span className="grow">
                <span className="truncate" style={{ display: 'block', fontWeight: 550 }}>{s.title || 'Conversation'}</span>
                <span className="xs muted">{timeAgo(s.created_at)} · {s.message_count} msg</span>
              </span>
              <span className="del btn btn-ghost btn-icon btn-sm" role="button" aria-label="Delete conversation" onClick={(e) => removeSession(e, s)}><Trash2 size={13} /></span>
            </button>
          ))}
        </div>
      </aside>

      <section className="chat-panel">
        <div className="chat-head">
          <div className="bot-avatar"><Bot size={17} /></div>
          <div className="grow">
            <div className="bold">XithSense AI</div>
            <div className="xs muted">Grounded in live projections, venue and matchup data</div>
          </div>
          <select className="select select-sm" style={{ maxWidth: 320 }} value={matchId} onChange={(e) => changeMatch(e.target.value)} aria-label="Match context">
            {matches.map((m) => (
              <option key={m.id} value={m.id}>{m.is_live ? '● ' : ''}{m.team_a} vs {m.team_b}{m.gender === 'female' ? ' (W)' : ''} · {m.match_type} · {relativeDay(m.start_time || m.match_date)}</option>
            ))}
          </select>
        </div>

        <div className="chat-scroll" ref={scrollRef}>
          {loadingSession ? (
            <div className="page-loader" style={{ minHeight: 200 }}><Spinner /></div>
          ) : messages.length === 0 ? (
            <div className="welcome">
              <div className="bot-avatar" style={{ width: 54, height: 54, borderRadius: 16 }}><Sparkles size={24} /></div>
              <h2>Ask anything about {match ? `${match.team_a.split(' ').pop()} vs ${match.team_b.split(' ').pop()}` : 'today\'s match'}</h2>
              <p>Captaincy calls, differentials, matchups and venue trends — every answer is built from the same numbers that power your AI teams.{match ? ` ${fmtDate(match.match_date, { weekday: 'short', day: 'numeric', month: 'short' })}.` : ''}</p>
              <div className="chips">
                {suggestions.map((s) => <button key={s.text} className="chip" onClick={() => send(s.text)}><s.icon size={14} />{s.text}</button>)}
              </div>
            </div>
          ) : (
            messages.map((m, i) => <Message key={i} m={m} onRetry={m.error && m.retryText ? () => retry(i) : null} />)
          )}
          {chat.isPending && (
            <div className="msg assistant">
              <div className="bot-avatar"><Bot size={17} /></div>
              <div className="bubble typing"><span /><span /><span /></div>
            </div>
          )}
        </div>

        <div className="chat-input">
          <div className="box">
            <textarea ref={taRef} rows={1} value={input} onChange={autoGrow} onKeyDown={onKey} maxLength={1000}
              placeholder="Ask about captains, differentials, a player, the pitch…" aria-label="Message" />
            <Button icon={Send} onClick={() => send()} disabled={!input.trim() || chat.isPending} aria-label="Send" />
          </div>
          <div className="xs muted mt-8 row between"><span><kbd>Enter</kbd> to send · <kbd>Shift</kbd>+<kbd>Enter</kbd> new line</span><span className="mono">{input.length}/1000</span></div>
        </div>
      </section>
    </div>
  )
}
