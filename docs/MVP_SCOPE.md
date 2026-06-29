# MVP Scope

**Target Launch:** Q4 2026  
**MVP Philosophy:** Deliver a complete prediction → explanation → team loop for T20 and IPL matches only. Prove accuracy before expanding formats.

---

## In Scope (MVP)

### Data
- [x] Cricsheet JSON ingestion (all 22,062 matches)
- [x] Ball-by-ball relational schema (deliveries, innings, matches)
- [x] Feature engineering: rolling form, venue stats, matchup stats
- [x] Incremental ingestion pipeline

### ML
- [x] Fantasy points prediction model (XGBoost primary)
- [x] Human rules engine (PLAYER_RULES, VENUE_RULES, MATCHUP_RULES, CONTEXT_RULES)
- [x] Ensemble: ML 40% + Human Rules 30% + Form 20% + Live 10%
- [x] Backtesting harness (10,000 historical matches)

### Team Generation
- [x] 4 team modes: Safe, Grand League, Aggressive, Small League
- [x] Dream11 constraint compliance (credits, role limits, team cap)
- [x] Captain + Vice-Captain recommendation
- [x] Differential pick identification

### Explainability
- [x] LLM-generated plain-English rationale per player
- [x] Confidence score per player and team
- [x] Rule trigger audit log

### API
- [x] `POST /api/v1/predict/team`
- [x] `POST /api/v1/predict/captain`
- [x] `GET /api/v1/players/{id}`
- [x] `GET /api/v1/matches/{id}`
- [x] `POST /api/v1/chat`
- [x] `GET /api/v1/explain/{match_id}/{player_id}`
- [x] JWT authentication
- [x] Rate limiting

### Users
- [x] Email registration + login
- [x] Free tier: 1 team per match, basic insights
- [x] Premium tier: unlimited teams, AI chat, detailed insights
- [x] Razorpay payment integration

### Notifications
- [x] Telegram alerts: Playing XI, Toss, Injury

### Admin
- [x] Model retraining trigger
- [x] Prediction metrics dashboard (API only — no UI in MVP)
- [x] Human rules CRUD

---

## Out of Scope (MVP — Post-Launch Roadmap)

| Feature | Target Phase |
|---------|-------------|
| React SPA frontend | Phase 2 |
| Live match WebSocket feed | Phase 2 |
| ODI and Test match predictions | Phase 2 |
| WhatsApp and Push notifications | Phase 2 |
| Google OAuth | Phase 2 |
| Multi-language support (Hindi) | Phase 3 |
| Player injury feed integration | Phase 3 |
| Odds movement tracking | Phase 3 |
| Contest ROI analytics per user | Phase 3 |
| Mobile app (iOS / Android) | Phase 4 |
| Automated lineup detection from Twitter/X | Phase 4 |

---

## MVP Launch Criteria (Definition of Done)

All of the following must be true before launch:

- [ ] Backtesting captain accuracy ≥ 38% on held-out 2024–2025 IPL matches
- [ ] Backtesting correct-player rate ≥ 60% (at least 7 correct players in predicted XI)
- [ ] API p95 response time < 500ms under 100 concurrent users
- [ ] All critical tests passing (coverage ≥ 75%)
- [ ] Zero High/Critical severity security findings in OWASP ZAP scan
- [ ] Razorpay webhook handling tested with sandbox
- [ ] At least 50 human rules loaded and validated
- [ ] Deployment automated via Docker Compose on Railway/Render
- [ ] Monitoring (Sentry error tracking, uptime check) active
- [ ] Admin can retrain model without engineer intervention
