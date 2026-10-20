import { Link } from 'react-router-dom'
import { BrainCircuit, ShieldCheck } from 'lucide-react'
import { Logo } from '../components/Layout'
import { Badge, ConfidenceBar } from '../components/ui'
import { team } from '../lib/format'

/** Right-hand brand panel shared by the login and register pages. */
export default function AuthArt({ quote }) {
  return (
    <aside className="auth-art">
      <Link to="/"><Logo /></Link>
      <div className="col gap-24">
        <blockquote>{quote}</blockquote>
        <div className="insight fade-in">
          <div className="row between">
            <span className="row gap-8 upper muted"><BrainCircuit size={14} className="text-primary" />Pick insight</span>
            <Badge tone="success">High · 84%</Badge>
          </div>
          <div className="row mt-16">
            <div className="crest" style={{ '--team': team('Royal Challengers Bengaluru').color }}>VK</div>
            <div className="grow">
              <div className="bold">V Kohli <span className="cvc cvc-c" style={{ marginLeft: 6, verticalAlign: 1 }}>C</span></div>
              <div className="small muted">Projects 61 pts · ceiling 112</div>
            </div>
          </div>
          <div className="col gap-8 mt-16 small">
            <div className="row between"><span className="secondary">Recent form</span><span className="mono">52.4 avg FP</span></div>
            <div className="row between"><span className="secondary">Venue record</span><span className="mono">58.1 at Chinnaswamy</span></div>
            <div className="row between"><span className="secondary">Matchup vs attack</span><span className="mono">SR 151</span></div>
          </div>
          <div className="mt-16"><ConfidenceBar value={84} /></div>
          <p className="xs mt-12">Chasing tonight — the analyst rule for chasing specialists fires (+19 pts).</p>
        </div>
      </div>
      <div className="row gap-8 small muted"><ShieldCheck size={14} />Built on Cricsheet ball-by-ball data</div>
    </aside>
  )
}
