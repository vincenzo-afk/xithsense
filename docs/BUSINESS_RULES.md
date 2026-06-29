# Business Rules

## Dream11 Team Composition Rules

| Rule | Value |
|------|-------|
| Total players per team | 11 |
| Total credit budget | 100.0 |
| Max players from one real team | 7 |
| Min players from one real team | Implicit (need both teams represented) |
| Wicketkeeper slots | Min 1, Max 4 |
| Batter slots | Min 3, Max 6 |
| All-rounder slots | Min 1, Max 4 |
| Bowler slots | Min 3, Max 6 |
| Captain multiplier | 2× fantasy points |
| Vice-Captain multiplier | 1.5× fantasy points |
| Captain ≠ Vice-Captain | Always enforced |

## Subscription Rules

| Feature | Free | Premium Monthly | Premium Annual |
|---------|------|----------------|----------------|
| Price | ₹0 | ₹299/month | ₹2,499/year |
| Teams per match | 1 | 20 | 20 |
| AI chat messages per match | 0 | Unlimited | Unlimited |
| Insights depth | Basic | Full | Full |
| Grand league teams | No | Yes | Yes |
| Live alerts | No | Yes | Yes |
| Differential picks | No | Yes | Yes |
| Notifications | None | Telegram | All channels |

## Player Credit Ranges (Dream11 approximations)

| Credit Range | Player Tier |
|---|---|
| 10.0 – 10.5 | Elite (Kohli, Bumrah tier) |
| 9.0 – 9.5 | Star players |
| 8.0 – 8.5 | Good performers |
| 7.0 – 7.5 | Decent picks |
| 6.0 – 6.5 | Differential/budget picks |
| 5.0 – 5.5 | Value/tail picks |

## Data Freshness Rules

| Data Type | Max Staleness |
|-----------|--------------|
| Playing XI | 30 minutes before match |
| Feature vectors | 6 hours (Redis TTL) |
| Predictions | Regenerate after toss |
| Live scores | Every over |

## Prediction Confidence Thresholds

| Confidence | Label | Recommendation |
|---|---|---|
| 80–100 | High | Strong pick — include in all modes |
| 60–79 | Medium | Good pick — include in safe, consider in GL |
| 40–59 | Low | Risky — GL differential or avoid |
| 0–39 | Very Low | Avoid unless specific GL strategy |
