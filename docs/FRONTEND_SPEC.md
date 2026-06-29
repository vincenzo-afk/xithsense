# Frontend Specification

**Framework:** React 18 + Vite 5  
**Styling:** Tailwind CSS 3  
**State:** Zustand + React Query (TanStack Query v5)  
**Router:** React Router v6  
**UI Components:** Radix UI primitives + custom design system  
**Charts:** Recharts  
**WebSocket:** native browser WebSocket API

---

## Pages

| Route | Page | Auth Required | Plan |
|-------|------|--------------|------|
| `/` | Landing page | No | — |
| `/login` | Login | No | — |
| `/register` | Register | No | — |
| `/matches` | Match list | Yes | Free+ |
| `/matches/:id` | Match detail + prediction | Yes | Free+ |
| `/matches/:id/team` | Team builder | Yes | Free+ |
| `/matches/:id/live` | Live intelligence | Yes | Premium |
| `/players/:id` | Player profile | Yes | Free+ |
| `/chat` | AI chat assistant | Yes | Premium |
| `/account` | Account + subscription | Yes | Free+ |
| `/subscribe` | Upgrade to Premium | Yes | Free+ |
| `/admin` | Admin dashboard | Yes | Admin |

---

## Core Screens

### Match Detail + Prediction (`/matches/:id`)

**Sections:**
1. Match header — teams, venue, date, toss result, event stage
2. Prediction tabs — Safe | Grand League | Aggressive | Small League
3. Team card — 11 players with role, credits, predicted FP, confidence badge
4. Captain section — Best Captain / Safe Captain / Risk Captain cards
5. Differentials section — 3–5 low-ownership high-ceiling picks
6. Explanation panel — click any player to see plain-English rationale
7. Refresh trigger — re-generate after toss confirmation

### AI Chat (`/chat`)

- Persistent chat interface with message history
- Match context selector at top
- Markdown-rendered responses
- Player name highlights link to player profile
- 5-message limit indicator for free users

### Player Profile (`/players/:id`)

- Form graph: FP last 10 matches (Recharts line chart)
- Role-appropriate stats table (batting/bowling/all-round)
- Venue breakdown: top 5 venues by FP average
- Matchup radar: performance vs bowler types

---

## Responsive Breakpoints

| Breakpoint | Width | Layout |
|-----------|-------|--------|
| `mobile` | < 640px | Single column, bottom nav |
| `tablet` | 640–1024px | Two columns, sidebar hidden |
| `desktop` | > 1024px | Three columns, full sidebar |

---

## Performance Requirements

- First Contentful Paint < 1.5s
- Prediction page interactive < 3s
- Lazy-load all chart components
- API responses cached via React Query (staleTime: 5 min for predictions)
