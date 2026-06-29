import { useState, useRef, useEffect } from 'react'
import { useMutation } from '@tanstack/react-query'
import { sendChat } from '../api/client'

const QUICK_PROMPTS = [
  '🎯 Who should be my captain today?',
  '🏆 Best picks for Grand League?',
  '⚡ Who are the top differentials?',
  '📊 Is Virat Kohli a good pick?',
  '🧤 Best wicketkeeper option?',
  '🏏 Death over specialist bowlers?',
]

const WELCOME = {
  role: 'assistant',
  content: "👋 Hi! I'm your XithSense AI assistant, trained on 22,062 cricket matches. Ask me anything about today's match — captain picks, differentials, matchups, or strategy. What would you like to know?",
}

export default function ChatPage() {
  const [messages, setMessages] = useState([WELCOME])
  const [input, setInput] = useState('')
  const [sessionId, setSessionId] = useState(null)
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const chatMutation = useMutation({
    mutationFn: (msg) => sendChat({ message: msg, session_id: sessionId }),
    onSuccess: (data) => {
      setSessionId(data.session_id)
      setMessages(prev => [...prev, { role: 'assistant', content: data.answer }])
    },
    onError: () => {
      setMessages(prev => [...prev, { role: 'assistant', content: '⚠️ Sorry, I encountered an error. Please check if the backend is running.' }])
    },
  })

  const sendMessage = (msg) => {
    const text = msg || input.trim()
    if (!text) return
    setMessages(prev => [...prev, { role: 'user', content: text }])
    setInput('')
    chatMutation.mutate(text)
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div className="page" style={{ padding: 'var(--sp-4) var(--sp-6)' }}>
      <div className="container" style={{ height: 'calc(100vh - 100px)' }}>
        <div className="chat-container">
          <div className="chat-header">
            <div className="flex items-center gap-3">
              <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 20 }}>
                🤖
              </div>
              <div>
                <div style={{ fontWeight: 700 }}>XithSense AI</div>
                <div style={{ fontSize: 'var(--text-xs)', color: 'var(--color-success)' }}>● Online · 22,062 matches</div>
              </div>
            </div>
            <span className="badge badge-premium">PRO</span>
          </div>

          <div className="chat-messages">
            {messages.map((msg, i) => (
              <div key={i} className={`chat-message ${msg.role}`}>
                {msg.role === 'assistant' && (
                  <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'linear-gradient(135deg, var(--color-primary), var(--color-secondary))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 14, marginBottom: 6 }}>
                    🤖
                  </div>
                )}
                <div className="chat-bubble">{msg.content}</div>
              </div>
            ))}
            {chatMutation.isPending && (
              <div className="chat-message assistant">
                <div className="chat-bubble" style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <span className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%' }} />
                  <span className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%', animationDelay: '0.2s' }} />
                  <span className="skeleton" style={{ width: 8, height: 8, borderRadius: '50%', animationDelay: '0.4s' }} />
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Quick prompts */}
          {messages.length < 3 && (
            <div style={{ padding: '0 var(--sp-6) var(--sp-3)', display: 'flex', gap: 8, overflowX: 'auto', flexWrap: 'wrap' }}>
              {QUICK_PROMPTS.map(p => (
                <button key={p} onClick={() => sendMessage(p)}
                  className="btn btn-secondary btn-sm"
                  style={{ whiteSpace: 'nowrap', fontSize: 12 }}>
                  {p}
                </button>
              ))}
            </div>
          )}

          <div className="chat-input-area">
            <textarea
              className="input"
              style={{ resize: 'none', minHeight: 44, maxHeight: 120 }}
              placeholder="Ask about captain picks, differentials, matchups..."
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={1}
            />
            <button className="btn btn-primary btn-icon" onClick={() => sendMessage()} disabled={!input.trim() || chatMutation.isPending}>
              <span style={{ fontSize: 18 }}>➤</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
