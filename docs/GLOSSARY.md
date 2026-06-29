# Glossary

Definitions of all terms used in XithSense documentation, code, and data.

---

## Cricket Terms

| Term | Definition |
|------|-----------|
| **Ball-by-ball data** | Delivery-level records capturing every ball bowled in a match: batter, bowler, runs, wickets, extras |
| **Chasing** | Batting second (team batting after the opposition has set a target) |
| **Setting** | Batting first (team establishing the target for the opposition to chase) |
| **Powerplay** | Mandatory fielding restriction overs. T20: overs 1–6. ODI: overs 1–10 |
| **Death overs** | Final overs of an innings where batters attack and bowlers defend. T20: overs 16–20. ODI: 41–50 |
| **Economy rate** | Runs conceded per over bowled by a bowler |
| **Strike rate (batting)** | Runs scored per 100 balls faced |
| **Dot ball** | Delivery from which no runs are scored and no wicket falls |
| **Wicket kind** | Type of dismissal: caught, bowled, LBW, run out, stumped, hit wicket, etc. |
| **DRS** | Decision Review System — technology-assisted umpire review |
| **Dew** | Moisture on the outfield and pitch in evening matches; favours batting second at certain venues |
| **Pitch type** | Surface character: `batting` (flat, high scores), `bowling` (seam/swing), `spin` (turn for spinners), `pace` (bounce and pace) |
| **Super Over** | One-over eliminator used to break ties in T20 matches |
| **Player of the Match** | Award given to the best-performing player in a match |
| **Maiden over** | Over in which the bowler concedes zero runs |
| **Boundary** | Ball reaching or crossing the rope: 4 runs (ground) or 6 runs (over the rope in the air) |
| **Wrist spin** | Bowling using wrist action to generate turn: leg-spin, googly, chinaman |
| **Orthodox spin** | Finger spin bowling: right-arm off-break, left-arm orthodox |

---

## Fantasy Cricket Terms

| Term | Definition |
|------|-----------|
| **Fantasy points** | Points awarded based on real player performance per the Dream11 scoring system |
| **FP ceiling** | A player's best-case fantasy performance (90th percentile of historical FP) |
| **FP floor** | A player's worst-case fantasy performance (10th percentile of historical FP) |
| **FP consistency** | Coefficient of variation of FP (std / mean). Lower = more consistent performer |
| **Captain** | Fantasy team captain; earns 2× fantasy points for the match |
| **Vice-Captain (VC)** | Second-in-command; earns 1.5× fantasy points |
| **Differential pick** | Player chosen by fewer than 20% of fantasy teams; provides a competitive edge if they perform |
| **Grand League (GL)** | Large-pool contest (typically thousands of entries) with high prize but low individual win probability |
| **Small League** | Small-pool contest with fewer entries and higher win probability per entry |
| **Ownership percentage** | Proportion of fantasy teams that include a given player in a contest |
| **Credits** | Dream11's in-game currency used to select players; each team has 100 credits |
| **Safe team** | Conservative fantasy team optimised for consistency; minimises downside risk |
| **Aggressive team** | High-ceiling fantasy team; maximises upside at cost of consistency |

---

## XithSense System Terms

| Term | Definition |
|------|-----------|
| **Ensemble score** | Final player score combining ML (40%), human rules (30%), form (20%), live context (10%) |
| **Human rules engine** | Module that applies analyst-encoded conditional rules to adjust ML scores |
| **Rule trigger** | Instance of a human rule firing for a specific player in a specific match context |
| **Rolling feature** | A statistical feature computed over a sliding window of N recent matches (3, 5, or 10) |
| **Matchup stat** | Batter vs. bowler-type performance record (e.g. strike rate vs. left-arm pace) |
| **Venue stat** | Aggregated historical statistics at a specific ground for a specific format |
| **Inference pipeline** | End-to-end flow from match context + player features → ensemble score → team optimization → explanation |
| **Team mode** | Strategy configuration for team generation: `safe`, `grand_league`, `aggressive`, `small_league` |
| **Match phase** | Stage of prediction: `pre_toss` (before toss), `post_toss` (after toss), `live` (in-match) |
| **Feature vector** | 47-dimensional array representing a player's statistical profile for model input |
| **Cricsheet key** | Unique player identifier used by Cricsheet (e.g. `"Kohli, V"`) |
| **Model version** | A specific trained model artifact, identified by `{model_id}-{format}-{date}` |
| **Backtest** | Retrospective evaluation of prediction accuracy on historical matches where outcomes are known |
| **Captain accuracy** | Fraction of matches where the predicted best captain is the actual top fantasy scorer |
| **Correct player rate (CPR)** | Fraction of matches where ≥ 7 of 11 predicted players are in the actual top-11 FP scorers |
| **LP optimizer** | Linear programming team optimizer using PuLP/CBC to find the optimal player combination |
| **DEAP** | Genetic algorithm optimizer (fallback when LP is infeasible) |
| **Feature gate** | Access control check that restricts premium features to Premium/Admin users |
| **Request ID** | UUID attached to every API request for log tracing and support |
| **Admin action** | Privileged operation by an admin user, logged in the `admin_action` audit table |
| **Rule schema** | JSON schema (`human_rules/RULE_SCHEMA.json`) that every human rule must conform to |
| **Bowler type** | Categorisation of a bowler's style: `pace_right`, `pace_left`, `spin_off`, `spin_left`, `spin_wrist` |
| **Dead Letter Queue (DLQ)** | Celery queue holding tasks that exhausted all retries; requires admin attention |
| **Pre-commit hook** | Automated code quality check (lint, format) run before each git commit |
| **Alembic** | Python database migration framework used to manage schema changes |
| **Structlog** | Structured logging library producing JSON logs in production |

---

## Acronyms

| Acronym | Expansion |
|---------|-----------|
| FP | Fantasy Points |
| GL | Grand League |
| WK | Wicketkeeper |
| BAT | Batter |
| AR | All-Rounder |
| BOWL | Bowler |
| LP | Linear Programming |
| LLM | Large Language Model |
| TTL | Time To Live (cache expiry) |
| CPR | Correct Player Rate |
| CA | Captain Accuracy |
| MAE | Mean Absolute Error |
| RMSE | Root Mean Squared Error |
| CV | Coefficient of Variation |
| ORM | Object-Relational Mapper (SQLAlchemy) |
| JWT | JSON Web Token |
| MRR | Monthly Recurring Revenue |
| DAU | Daily Active Users |
| NPS | Net Promoter Score |
| ARPU | Average Revenue Per User |
| RPM | Requests Per Minute |
| DRS | Decision Review System |
| DLQ | Dead Letter Queue |
| CORS | Cross-Origin Resource Sharing |
| HSTS | HTTP Strict Transport Security |
| OWASP | Open Web Application Security Project |
| CDN | Content Delivery Network |
