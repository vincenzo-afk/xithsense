# Screen Flows

## Flow 1: New User Onboarding

```
Landing Page
    │
    ▼
Register Page ──(already have account?)──► Login Page
    │
    ▼
Email Verification (link in email)
    │
    ▼
Match List Page  ◄── (home screen after login)
```

## Flow 2: Generate Team (Free User)

```
Match List
    │ click match
    ▼
Match Detail
    │ click "Generate Team" → mode=safe (only available)
    ▼
[Loading skeleton 1-3s]
    │
    ▼
Team Display (Safe mode)
    │ click player
    ▼
Player Explanation Panel (slide-up drawer)
    │ click "Captain"
    ▼
Captain Picker (modal)
    │ confirm
    ▼
Team locked / copy to clipboard
```

## Flow 3: Generate Portfolio (Premium User)

```
Match Detail
    │ click "Generate Portfolio"
    ▼
[Loading 2-3s — 4 teams generated in parallel]
    │
    ▼
Team Tabs: Safe | Grand League | Aggressive | Small League
    │ switch tabs
    ▼
Each tab shows its team + captain recommendation
    │ click "Differentials" tab
    ▼
Differential Picks panel with ownership % and reasoning
```

## Flow 4: Upgrade to Premium

```
Free user hits premium feature
    │
    ▼
Upgrade prompt modal
    │ click "View Plans"
    ▼
Subscribe Page (plan comparison)
    │ click "Get Premium Monthly"
    ▼
Razorpay Checkout (modal overlay)
    │ payment success
    ▼
Success screen: "You're Premium!"
    │ auto-redirect after 3s
    ▼
Match List (with Premium badge)
```

## Flow 5: Live Match

```
Match List (match in progress)
    │ click live match
    ▼
Live Intelligence Page
    │ WebSocket connected
    ▼
Real-time score + win probability bar
    │ scroll down
    ▼
Live player FP tracker
    │ captain indicator (actual vs predicted)
    ▼
Auto-updates every over without page refresh
```

## Navigation Guards

- Unauthenticated → any protected page → redirect `/login`
- Free user → Chat page → redirect `/subscribe`
- Free user → Live page → redirect `/subscribe`
- Admin user → `/admin` → Admin dashboard
