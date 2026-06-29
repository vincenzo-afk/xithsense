# Project Vision

## Mission

Build the world's best Human + AI Cricket Intelligence Platform that consistently generates high-quality fantasy cricket recommendations by fusing 22,062+ matches of ball-by-ball data with expert human knowledge.

---

## Problem Statement

Fantasy cricket players on Dream11, MyTeam11, and similar platforms lose consistently because:

1. **Information overload** — Analysing pitch reports, toss, weather, player form, venue history, and matchups before a contest deadline is impossible manually.
2. **Emotion-driven picks** — Users pick star players based on reputation, not situational data.
3. **No differentiation** — Grand league winners require differential picks that most tools never surface.
4. **No explainability** — Existing apps give recommendations without reasoning; users cannot evaluate or trust them.
5. **Static models** — Most tools do not update predictions after the toss, weather change, or playing XI announcement.

---

## Solution

XithSense is a decision-support platform — not a black box — that:

- Explains every recommendation in plain English
- Quantifies confidence so users can decide how much to trust a pick
- Separates safe-team picks from grand-league differential picks
- Updates dynamically when the toss, weather, or lineup changes
- Combines machine learning with analyst-encoded domain knowledge via a human rules engine

---

## Target Audience

### Primary Users

| Persona | Description | Goal |
|---------|-------------|------|
| Casual Player | Plays 1–5 contests per match, limited time | Quick trustworthy team in under 5 minutes |
| Serious Grinder | Plays 10–50 contests including grand leagues | GL edge: differential picks, ownership data, risk management |
| Fantasy Expert | Runs tipster channels, provides paid picks | Scalable tooling to produce picks at volume |

### Secondary Users

| Persona | Description |
|---------|-------------|
| Cricket Analyst | Data exploration and matchup research |
| Developer | Integrates XithSense predictions via API |

---

## Core Product Goals

1. **Accuracy** — Predict correct 11 players (top-3 fantasy-point-scorer bracket) for ≥ 65% of T20 matches on held-out backtest data.
2. **Captain accuracy** — Select the actual highest-scoring player as captain in ≥ 40% of matches.
3. **Explainability** — Every player selection includes ≥ 3 data-backed reasons with a confidence score.
4. **Speed** — Generate a 4-team portfolio (Safe + GL + Aggressive + Small League) in under 3 seconds.
5. **Reliability** — API uptime ≥ 99.5% during match windows (6 AM – midnight IST).

---

## Non-Goals (v1.0)

- Live ball-by-ball score prediction during an ongoing match
- Automated contest entry (violates platform ToS)
- Being a fantasy platform itself (intelligence layer only)
- Non-cricket sports
- Afghanistan men's matches (excluded from Cricsheet per policy)

---

## Strategic Differentiators

| Differentiator | Typical Competitors | XithSense |
|---|---|---|
| Training data granularity | Seasonal aggregates | 22,062 matches, every delivery |
| Human knowledge | Pure ML | Expert rules override ML where data is thin |
| Explainability | Score only | Plain-English rationale per player |
| Live adaptation | Static at toss | Updates on toss/weather/XI changes |
| Team variety | Single team | Safe / GL / Aggressive / Small League |

---

## 12-Month Success Criteria

- 10,000 active users (free + premium combined)
- 2,000+ paying subscribers
- Captain accuracy ≥ 40% on live match predictions
- MRR ≥ ₹10,00,000
- Net Promoter Score ≥ 50
- Zero data breach or security incidents
