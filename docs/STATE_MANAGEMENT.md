# State Management

## Architecture

- **Server state:** TanStack Query v5 — all API data, caching, background refetch
- **Client state:** Zustand — auth, UI preferences, active match context
- **URL state:** React Router search params — active mode, selected player

## Zustand Stores

### `useAuthStore`
```js
{ user, token, setUser, logout }
```

### `useMatchStore`
```js
{ activeMatchId, activeMode, setMatch, setMode }
```

### `useChatStore`
```js
{ sessions, activeSessionId, addMessage, setActiveSession }
```

### `useNotificationStore`
```js
{ preferences, updatePreference }
```

## React Query Keys

```js
const queryKeys = {
  matches: { upcoming: ["matches", "upcoming"], detail: (id) => ["matches", id] },
  players: { detail: (id) => ["players", id], matchups: (id) => ["players", id, "matchups"] },
  prediction: { team: (matchId, mode) => ["prediction", matchId, mode] },
  chat: { session: (sessionId) => ["chat", sessionId] },
};
```

## Cache Strategy

| Data | staleTime | cacheTime |
|------|-----------|-----------|
| Upcoming matches | 5 min | 15 min |
| Match detail | 10 min | 30 min |
| Player profile | 30 min | 60 min |
| Team prediction (pre-toss) | 30 min | 60 min |
| Team prediction (post-toss) | 5 min | 15 min |
| Chat history | ∞ (stored in Zustand) | session |

## WebSocket State

Live match data flows directly into Zustand `useLiveMatchStore`:
```js
{ liveScore, playerFP, winProbability, updateFromEvent }
```
