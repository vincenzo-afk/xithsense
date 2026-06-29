# AI Development Rules

**Scope:** These rules apply to every AI assistant, agent, or automated tool that writes, modifies, reviews, or generates code and documentation for the XithSense project.  
**Enforcement:** Treat these as hard constraints, not guidelines. Violations must be flagged before committing.

---

## SECTION 1 — Integrity Rules

### RULE-DEV-01: Never remove existing functionality
Do not delete, comment out, or disable any working feature, endpoint, function, or configuration unless explicitly instructed to do so with a written reason. Refactors must preserve all existing behaviour.

### RULE-DEV-02: Never hardcode player names
All player references must use `player_key` (Cricsheet registry key) or `player_id` (UUID from the database). Never embed player name strings like `"Virat Kohli"` in prediction logic, model code, or optimizer constraints. Player names belong only in UI display and human rules JSON (as `player_key`).

### RULE-DEV-03: Never use mock data in production
Mock data, seed data, and fixtures are strictly for the test environment (`ENV=test`). Production and staging environments must always connect to live data sources. Never add `if ENV == "production": return mock_response`.

### RULE-DEV-04: Never deploy without passing all tests
Every deployment — including hotfixes — must pass the full test suite (`make test`). CI must be green before any merge to `main`. Do not bypass CI checks with `--no-verify` or force-push.

### RULE-DEV-05: Never skip validation
Every API input must be validated through Pydantic models before processing. Never access `request.body` or raw dict keys without schema validation. Every prediction input must be range-checked before feeding models.

### RULE-DEV-06: Never change database schema without migration
All schema changes (new table, new column, index, constraint) must be implemented as an Alembic migration file. Never run `ALTER TABLE` or `CREATE TABLE` directly against production. Migration must be reversible (include `downgrade()`).

---

## SECTION 2 — Code Quality Rules

### RULE-DEV-07: Always write tests for new features
Every new function, class, or API endpoint requires:
- At least one unit test covering the happy path
- At least one test for the primary error/edge case
- Integration test if the feature touches the database or external API

### RULE-DEV-08: Always update documentation
When any of the following change, update the corresponding docs file immediately — not later:
- API endpoint added/changed → `docs/API_SPEC.md`
- Database schema changed → `docs/DATABASE_SCHEMA.md`
- Feature added/changed → `docs/FEATURE_ENGINEERING_SPEC.md`
- Model changed → `docs/MODEL_SPECIFICATION.md`
- New environment variable → `.env.example`

### RULE-DEV-09: Follow existing architecture
New code must fit the established module structure. Do not create new top-level modules without discussion. Business logic belongs in `backend/services/`, not in route handlers. Data access belongs in `backend/repositories/`. ML logic belongs in `training/` or `optimizer/`.

### RULE-DEV-10: Use modular and reusable code
Extract repeated logic into shared utilities. No function longer than 80 lines. No file longer than 500 lines. Every function must do exactly one thing. No copy-paste duplication.

### RULE-DEV-11: Complete one task fully before starting another
Do not leave partial implementations. A task is complete only when: code works, tests pass, docs updated, and the feature is accessible via its intended interface (API endpoint, CLI command, etc.).

### RULE-DEV-12: Maintain backward compatibility
Never remove or rename a public API endpoint, response field, or database column without a deprecation notice. If breaking changes are required, version the API (`/api/v2/`) and keep the old endpoint active for ≥ 30 days.

---

## SECTION 3 — ML and Prediction Rules

### RULE-DEV-13: Always provide explanations for predictions
Every prediction response must include an `explanation` field. Never return a bare score without reasoning. The LLM explainability engine must run for every player returned in a team recommendation. Empty explanations are a bug.

### RULE-DEV-14: Every prediction must include a confidence score
Every `predicted_player` record must have a `confidence` integer (0–100). Never return a prediction without a confidence value. A confidence of 0 is valid (uncertain); a missing confidence is not.

### RULE-DEV-15: Every selected player must have selection reasoning
The `rules_fired` and `explanation` fields in `predicted_player` are mandatory. If no rules fire for a player, log `rules_fired: []` and state that in the explanation. Blank explanations must never reach the user.

### RULE-DEV-16: Every model change must be backtested
Before activating a new model version or changing ensemble weights:
1. Run `make backtest` on ≥ 2,000 historical matches
2. Compare captain accuracy and correct-player rate against the current active model
3. Document results in `evaluation/EXPERIMENT_TRACKING.md`
4. Only promote if metrics improve or are statistically equivalent

### RULE-DEV-17: Follow Dream11 constraints strictly
The team optimizer must enforce ALL constraints in `docs/BUSINESS_RULES.md` without exception. Never relax credit limits, role minimums, or team caps "for testing". Any team returned by the API must be a legal Dream11 submission.

---

## SECTION 4 — Security Rules

### RULE-DEV-18: No secrets in code or version control
API keys, database passwords, JWT secrets, and webhook tokens must only exist in `.env` (local) or in the deployment platform's secret manager. Never commit real credentials even in comments, tests, or example files. `.env.example` must use placeholder values only.

### RULE-DEV-19: Validate and sanitise all user inputs
All string inputs (player names in chat, search queries) must be sanitised before use in database queries. Use parameterised queries (SQLAlchemy ORM or `text()` with bound params). Never use string concatenation to build SQL.

### RULE-DEV-20: Rate limit all endpoints
Every public and authenticated endpoint must be covered by the rate limiter. Never bypass rate limiting for a specific user without admin approval. Rate limit headers (`X-RateLimit-Limit`, `X-RateLimit-Remaining`) must be included in all responses.

---

## SECTION 5 — Operational Rules

### RULE-DEV-21: Optimise for maintainability and scalability
Prefer readability over cleverness. Use explicit variable names. Avoid premature optimisation. If a feature requires a major architectural change, raise it for discussion before implementing.

### RULE-DEV-22: Keep code production-ready at all times
`main` branch must always be deployable. Never merge code that breaks existing tests. Feature flags are acceptable for incomplete features, but broken code is not.

### RULE-DEV-23: Ask before making breaking changes
If a task requires changing a public API contract, the database schema, or an ML feature that affects prediction output, pause and confirm with the team before proceeding. Document the proposed change in a GitHub issue first.

### RULE-DEV-24: Log all prediction inputs and outputs
Every call to `predict_team()` or `predict_fantasy_points()` must emit a structured log entry including: match_id, model_version_id, ensemble_weights, player_id, input_feature_hash, output_score. This enables audit and debugging.

### RULE-DEV-25: Treat data as the most critical asset
Never drop, truncate, or overwrite production data without a verified backup. All bulk data operations must be wrapped in a transaction with a rollback plan. Ingestion pipelines must be idempotent.

---

## Violation Protocol

If an AI tool or contributor identifies a potential violation of these rules:

1. **Stop** — Do not proceed with the violating change
2. **Flag** — Open a GitHub issue tagged `rule-violation` with the specific rule ID
3. **Propose** — Suggest a compliant alternative
4. **Wait** — Do not merge until a maintainer approves the resolution
