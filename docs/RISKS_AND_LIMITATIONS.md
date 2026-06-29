# Risks and Limitations

## Known Data Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| Cricsheet lag: new matches available 24–48h post-match | Predictions for next-day matches may not include latest form | Schedule daily ingestion at 2 AM IST |
| No official playing XI feed | Must use admin-entered or manually scraped XI | Build XI input API for manual entry; alert users when XI unconfirmed |
| No live ball-by-ball API (MVP) | Live context limited to toss and weather | Use WebSocket stubs; integrate live API in Phase 2 |
| Women's cricket under-represented in rules engine | Rules accuracy lower for women's matches | Tag rules by gender; build separate women's rule set in Phase 2 |
| Test match fantasy scoring differs per platform | Points model trained on Dream11 only | Parameterise scoring system per platform in future |

## Model Limitations

| Limitation | Impact | Mitigation |
|-----------|--------|-----------|
| New players with < 5 matches | Feature values are imputed from team/role averages | Show `low_data` flag in explanation; reduce confidence |
| Player role changes (e.g. moved up batting order) | Historical features may not reflect new role | Human rules can override; flag recent role changes |
| Prediction accuracy degrades on debut venues | Venue feature based on insufficient data | Fall back to global averages; flag low venue data |
| All-rounder role classification varies by source | Incorrect role can violate optimizer constraints | Manual correction available via admin API |

## Technical Risks

| Risk | Severity | Probability | Mitigation |
|------|---------|------------|-----------|
| Supabase outage | High | Low | Redis cache reduces DB dependency during short outages |
| LLM API rate limit or outage | Medium | Medium | Fallback template explanation; switch provider via env var |
| Razorpay webhook delivery failure | High | Low | Idempotent webhook handler; reconcile on schedule |
| Model accuracy degrades with new cricket rules/balls | Medium | Medium | Monthly retraining; alert on accuracy drop |
| Redis memory exhaustion | Medium | Low | `maxmemory-policy allkeys-lru` eviction; alert on > 80% usage |

## Legal and Compliance

- XithSense provides decision support only. It does not place bets or enter contests on behalf of users.
- Fantasy cricket is legal in India under the Public Gambling Act exemption for skill-based games (subject to state law).
- Compliance with Dream11 terms of service: automation of contest entries is prohibited.
- User data handled per India's DPDP Act 2023.
- Cricsheet data used per its open data license (CC BY 4.0).

## Accuracy Disclaimer

XithSense is a prediction tool, not a guarantee. Cricket outcomes involve inherent randomness (weather, injuries, umpiring decisions) that no model can fully account for. Users should not make financial decisions based solely on XithSense recommendations.
