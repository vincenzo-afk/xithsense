# Navigation Flow

## Primary Navigation Paths

```
Landing Page (/)
    ├── [Register] → /register → [Email Verify] → /matches
    └── [Login]    → /login   → /matches

/matches (Match List)
    ├── Click match card → /matches/:id (Match Detail)
    │       ├── [Generate Team] → team displayed below
    │       │       ├── Click player → Explanation panel (drawer)
    │       │       ├── [Captain tab] → Captain picker modal
    │       │       └── [Differentials tab] → Differential list
    │       ├── [Switch Mode tab] Safe|GL|Agg|SL → new team
    │       └── [Live] → /matches/:id/live (Premium)
    │
    ├── Click player link → /players/:id (Player Profile)
    │       ├── Form chart (last 10 FP)
    │       ├── Matchup radar
    │       └── [Back] → previous page
    │
    └── Top nav: [Chat] → /chat (Premium)
                        └── Message input → AI response

/account
    ├── Profile settings
    ├── Notification preferences
    ├── Subscription status
    └── [Upgrade] → /subscribe → Razorpay checkout → /account (refreshed)

/admin (Admin only)
    ├── Metrics dashboard
    ├── [Retrain Models]
    ├── [Manage Rules]
    ├── [Manage Users]
    └── [Push Notification]
```

## Deep Link Patterns

| Deep Link | Destination | Auth |
|-----------|-------------|------|
| `/matches/1535465` | IPL Final match detail | Required |
| `/matches/1535465?mode=gl` | Match detail, GL tab active | Required |
| `/players/uuid` | Player profile | Required |
| `/chat?match=1535465` | Chat pre-loaded with match | Premium |
| `/subscribe?plan=monthly` | Subscribe page, monthly pre-selected | Required |

## 404 and Error States

- Unknown match ID → 404 page with "Match not found" + link to upcoming matches
- Expired prediction → Show stale warning + "Regenerate" button
- No matches available → Empty state with cricket illustration + "Check back later"
- Auth error mid-session → Toast notification + redirect to `/login`
