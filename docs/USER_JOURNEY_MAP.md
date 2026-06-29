# User Journey Map

---

## Journey 1: First-Time Free User → Team Selection

| Stage | Action | Touchpoint | Emotion | Pain Point | Opportunity |
|-------|--------|-----------|---------|------------|-------------|
| Discovery | Sees XithSense link in fantasy cricket Telegram group | Social referral | Curious | Doesn't know if it's trustworthy | Show accuracy stats on landing page |
| Registration | Signs up with email | Register page | Hopeful | Wants to skip registration | Add Google OAuth (Phase 2) |
| Exploration | Browses match list | Match List page | Interested | Can't tell which matches are ready | Add "Prediction Ready" badge |
| First prediction | Clicks match → generates safe team | Match Detail page | Engaged | Team appears but doesn't know why players selected | Highlight top 3 reasons per player prominently |
| Captain confusion | Unsure who to captain | Captain section | Uncertain | Three options feels like too many choices | Add "Best Captain" with bold highlight |
| Lock team | Copies team to Dream11 | External | Hopeful | No way to verify credits match Dream11 exactly | Add credit validation against Dream11 format |
| Result | Wins small prize | Dream11 app | Happy | — | In-app follow-up: "How did your team do?" |
| Upgrade consideration | Wants GL team for big match | Paywall | Frustrated then accepting | ₹299 feels risky for unknown value | Offer 3-day free trial |

---

## Journey 2: Premium User — IPL Match Day

| Time | Action | Platform | Notes |
|------|--------|---------|-------|
| 3:00 PM | Telegram alert: "Playing XI confirmed — GT vs RCB" | Telegram | EVT-01 notification received |
| 3:05 PM | Opens XithSense, generates 4-mode portfolio | Web app | All 4 teams ready in 2.8s |
| 3:10 PM | Reads differential picks — spots Noor Ahmad at 4% ownership | Differentials tab | Adds to GL team |
| 3:30 PM | Toss notification: "RCB elected to field" | Telegram | EVT-02 |
| 3:32 PM | Opens app — sees updated captain recommendation (Kohli moved up) | Match page | Refreshes team |
| 4:00 PM | Asks AI chat: "Should I use Maxwell in GL?" | Chat page | Gets data-backed No with SR vs spin stats |
| 4:15 PM | Locks 8 teams in Dream11 | Dream11 | Satisfied with research |
| 9:30 PM | Match ends — Kohli scores 77, Noor takes 3 wickets | Dream11 | GL team ranked top 10% |

---

## Journey 3: Expert Tipster — Bulk Prediction

| Stage | Action | Need |
|-------|--------|------|
| Pre-match research | Generates 20 unique GL teams via API | Sees top differentials across all teams |
| Content creation | Extracts player explanations via `GET /explain/:match/:player` | Copy-pastes reasons into Telegram posts |
| Audience posting | Posts 3 picks with confidence % to 10,000 followers | Shares XithSense link for credibility |
| Backtesting | Reviews `GET /admin/metrics` for last 30 days captain accuracy | Validates claims to audience |

---

## Drop-Off Points and Recovery

| Drop-Off | Cause | Recovery Strategy |
|----------|-------|------------------|
| After registration, before first prediction | Doesn't know how to start | Guided onboarding tooltip on Match List |
| After first prediction, before upgrade | Free team is enough for casual play | Push notification when GL team would have won |
| After upgrade, low engagement | Doesn't use AI chat feature | In-app nudge: "Ask me anything about your team" |
| Subscription cancellation | Price sensitivity | Offer 1-month pause instead of cancel |
