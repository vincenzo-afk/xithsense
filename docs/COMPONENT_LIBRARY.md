# Component Library

All components live in `frontend/src/components/`. Primitives use Radix UI; business components are custom.

## Primitive Components

| Component | Source | Usage |
|-----------|--------|-------|
| `Button` | Custom (wraps Radix) | All CTA buttons |
| `Badge` | Custom | Confidence labels, role tags |
| `Card` | Custom | Player cards, team cards |
| `Dialog` | Radix Dialog | Explanation panel, confirm dialogs |
| `Tabs` | Radix Tabs | Safe/GL/Aggressive/SL mode switcher |
| `Tooltip` | Radix Tooltip | Metric explanations |
| `Skeleton` | Custom | Loading placeholders |
| `Alert` | Custom | Error and info messages |
| `Input` | Custom | Chat input, search |
| `Select` | Radix Select | Format filter, match selector |
| `Switch` | Radix Switch | Notification toggles |
| `Progress` | Custom | Confidence bar |

## Business Components

### `<PlayerCard player={} showExplanation={} />`
Displays a single player in a team context. Shows: name, role badge, credits, predicted FP, confidence badge. Click expands explanation panel.

### `<TeamDisplay team={} mode={} />`
Full 11-player team in visual layout (WK / BAT / AR / BOWL rows). Highlights captain (C) and VC.

### `<CaptainPicker recommendations={} onSelect={} />`
Three captain cards: Best / Safe / Risk. Each shows ceiling, confidence, and reasoning.

### `<DifferentialList picks={} />`
Scrollable list of differential picks with ownership estimate and ceiling score.

### `<FormChart playerId={} />`
Recharts LineChart of FP over last 10 matches with 30+ point reference line.

### `<MatchupRadar playerId={} />`
Recharts RadarChart showing SR vs 5 bowler types.

### `<ChatBubble message={} role={} />`
Single message in the chat interface. `role="user"` or `role="assistant"`. Renders markdown.

### `<LiveScoreBar matchId={} />`
Real-time score display fed via WebSocket. Shows runs, wickets, overs, CRR, win probability bars.

### `<ConfidenceBadge confidence={} />`
Pill badge: High (green) / Medium (amber) / Low (red) / Very Low (gray).

### `<ModeTabs onModeChange={} />`
Tabs: Safe | Grand League | Aggressive | Small League. Triggers new prediction API call.
