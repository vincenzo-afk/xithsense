import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', flexDirection: 'column', gap: 'var(--sp-6)', textAlign: 'center', padding: 'var(--sp-6)' }}>
      <div style={{ fontSize: 80 }}>🏏</div>
      <h1 style={{ fontSize: 'var(--text-2xl)' }}>404 — Pitch Not Found</h1>
      <p style={{ color: 'var(--text-secondary)', maxWidth: 400 }}>The page you're looking for doesn't exist. Maybe it got run out?</p>
      <Link to="/" className="btn btn-primary btn-lg">← Back to Home</Link>
    </div>
  )
}
