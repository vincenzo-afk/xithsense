# Feature Gating Rules

Feature gates control which features are available to which users. Enforced at both API layer and frontend.

---

## Gate Definitions

```python
# backend/feature_gates.py

class FeatureGate:
    """Centralized feature gate definitions."""

    @staticmethod
    def can_generate_team(user: User, count: int, mode: str) -> GateResult:
        if count > 1 and user.role == "free":
            return GateResult(False, "PREMIUM_REQUIRED", "Multiple teams require Premium")
        if mode in ("grand_league", "aggressive", "small_league") and user.role == "free":
            return GateResult(False, "PREMIUM_REQUIRED", f"{mode} mode requires Premium")
        return GateResult(True)

    @staticmethod
    def can_use_chat(user: User, messages_used: int) -> GateResult:
        if user.role == "free":
            return GateResult(False, "PREMIUM_REQUIRED", "AI chat requires Premium")
        return GateResult(True)

    @staticmethod
    def can_view_differentials(user: User) -> GateResult:
        if user.role == "free":
            return GateResult(False, "PREMIUM_REQUIRED", "Differential picks require Premium")
        return GateResult(True)

    @staticmethod
    def can_access_live(user: User) -> GateResult:
        if user.role == "free":
            return GateResult(False, "PREMIUM_REQUIRED", "Live intelligence requires Premium")
        return GateResult(True)

    @staticmethod
    def explanation_depth(user: User) -> str:
        return "full" if user.role in ("premium", "admin") else "basic"
```

---

## Feature Gate Matrix

| Feature | Gate | Free | Premium | Admin |
|---------|------|------|---------|-------|
| Safe team (1) | `can_generate_team(count=1, mode=safe)` | ✅ | ✅ | ✅ |
| GL/Aggressive/SL team | `mode != safe` | ❌ | ✅ | ✅ |
| Multiple teams (>1) | `count > 1` | ❌ | ✅ | ✅ |
| Portfolio (4 modes) | `can_generate_portfolio` | ❌ | ✅ | ✅ |
| AI chat | `can_use_chat` | ❌ | ✅ | ✅ |
| Differentials | `can_view_differentials` | ❌ | ✅ | ✅ |
| Live intelligence | `can_access_live` | ❌ | ✅ | ✅ |
| Full explanation | `explanation_depth == full` | Basic | ✅ | ✅ |
| Telegram notifications | `notifications.telegram` | ❌ | ✅ | ✅ |
| API access (external) | `has_api_access` | ❌ | ✅ | ✅ |

---

## Frontend Gate Enforcement

```jsx
// frontend/src/hooks/useFeatureGate.js
export function useFeatureGate(feature) {
  const { user } = useAuth();

  const gates = {
    gl_team: user?.role === "premium" || user?.role === "admin",
    ai_chat: user?.role === "premium" || user?.role === "admin",
    differentials: user?.role === "premium" || user?.role === "admin",
    live_intelligence: user?.role === "premium" || user?.role === "admin",
  };

  return {
    allowed: gates[feature] ?? false,
    upgrade_url: "/subscribe",
  };
}

// Usage in component
const { allowed, upgrade_url } = useFeatureGate("gl_team");
if (!allowed) return <UpgradePrompt href={upgrade_url} feature="Grand League teams" />;
```

---

## Gate Bypass for Testing

In `ENV=test` or `ENV=development`:
```python
BYPASS_FEATURE_GATES = os.getenv("BYPASS_FEATURE_GATES", "false").lower() == "true"
```

Set `BYPASS_FEATURE_GATES=true` in local `.env` to test premium features without a subscription.  
**Never set in production.**
