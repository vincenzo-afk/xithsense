# Pages and Routes

## Route Definitions

```jsx
// frontend/src/router.jsx
const routes = [
  { path: "/",                    element: <LandingPage />,     auth: false },
  { path: "/login",               element: <LoginPage />,       auth: false },
  { path: "/register",            element: <RegisterPage />,    auth: false },
  { path: "/matches",             element: <MatchListPage />,   auth: true,  plan: "free" },
  { path: "/matches/:matchId",    element: <MatchDetailPage />, auth: true,  plan: "free" },
  { path: "/matches/:matchId/live", element: <LivePage />,      auth: true,  plan: "premium" },
  { path: "/players/:playerId",   element: <PlayerPage />,      auth: true,  plan: "free" },
  { path: "/chat",                element: <ChatPage />,        auth: true,  plan: "premium" },
  { path: "/account",             element: <AccountPage />,     auth: true,  plan: "free" },
  { path: "/subscribe",           element: <SubscribePage />,   auth: true,  plan: "free" },
  { path: "/admin",               element: <AdminPage />,       auth: true,  plan: "admin" },
  { path: "*",                    element: <NotFoundPage /> },
];
```

## Navigation Structure

### Top Navigation (Desktop)
`Logo` | `Matches` | `Chat` | `Account` | `Upgrade` (if Free)

### Bottom Navigation (Mobile)
`Home` | `Matches` | `Chat` | `Account`

## Page-Level Data Fetching

| Page | Primary Query | Secondary Queries |
|------|--------------|------------------|
| MatchList | `GET /api/v1/matches/upcoming` | — |
| MatchDetail | `GET /api/v1/matches/:id` | `POST /predict/team` (on load) |
| PlayerPage | `GET /api/v1/players/:id` | `GET /api/v1/players/:id/matchups` |
| ChatPage | Session history from local state | `POST /api/v1/chat` on send |
| AccountPage | `GET /api/v1/auth/me` | Subscription status |
| AdminPage | `GET /api/v1/admin/metrics` | Model versions, backtest results |

## URL Parameter Conventions

| Param | Type | Validation |
|-------|------|-----------|
| `:matchId` | Cricsheet numeric string | `/^\d+$/` |
| `:playerId` | UUID | UUID v4 regex |

## Protected Route Guard

```jsx
function ProtectedRoute({ auth, plan, element }) {
  const { user } = useAuth();
  if (auth && !user) return <Navigate to="/login" />;
  if (plan === "premium" && user?.role !== "premium" && user?.role !== "admin")
    return <Navigate to="/subscribe" />;
  if (plan === "admin" && user?.role !== "admin")
    return <Navigate to="/matches" />;
  return element;
}
```
