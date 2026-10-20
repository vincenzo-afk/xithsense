import { ArrowLeft, Trophy } from 'lucide-react'
import { Link } from 'react-router-dom'
import { Logo } from '../components/Layout'
import { ButtonLink } from '../components/ui'
import { useAuthStore } from '../store/authStore'
import './public.css'

export default function NotFoundPage() {
  const user = useAuthStore((s) => s.user)
  return (
    <div className="nf">
      <div className="hero-glow" />
      <div className="text-center fade-in" style={{ position: 'relative', zIndex: 1, maxWidth: 460 }}>
        <Link to="/" style={{ display: 'inline-block', marginBottom: 36 }}><Logo /></Link>
        <div className="stumps" aria-hidden>
          <span className="stump s1" /><span className="stump s2" /><span className="stump s3" />
          <span className="bail b1" /><span className="bail b2" />
        </div>
        <div className="code-404 gradient-text">404</div>
        <h1 className="mt-12">Stumped!</h1>
        <p className="mt-12">This page has been bowled out — it doesn’t exist or may have moved. Let’s get you back to the middle.</p>
        <div className="row center wrap mt-24">
          <ButtonLink to={user ? '/matches' : '/'} icon={user ? Trophy : ArrowLeft}>{user ? 'Back to matches' : 'Back to home'}</ButtonLink>
        </div>
      </div>
    </div>
  )
}
