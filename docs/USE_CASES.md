# Use Cases

## UC-01: Generate Safe Team for a Match

**Actor:** Free or Premium User  
**Precondition:** Match exists and at least 1 innings of feature data is available  
**Trigger:** User calls `POST /api/v1/predict/team` with `mode=safe`

**Main Flow:**
1. System validates match_id and user authentication
2. System loads feature vectors for all available players in the match
3. System runs ensemble engine (ML + Rules + Form)
4. System calls PuLP LP optimizer with safe-mode score modifiers
5. System runs LLM explainer for each selected player
6. System stores prediction in `prediction` and `predicted_player` tables
7. System returns team with explanations, captain recommendation, and confidence scores

**Alternative Flow (Playing XI not confirmed):**
- System uses historical batting order and last-known lineup
- System adds warning: `"playing_xi_confirmed: false"` in response

**Post-condition:** Team logged in DB; user sees 11 players with explanations.

---

## UC-02: Generate Grand League Portfolio

**Actor:** Premium User  
**Precondition:** User has active Premium subscription  
**Trigger:** User calls `POST /api/v1/predict/team/portfolio`

**Main Flow:**
1. System validates Premium subscription
2. System generates Safe, GL, Aggressive, Small League teams in parallel
3. GL team optimizer applies differential bonus for players with ownership < 20%
4. System returns 4 teams with distinct captain/VC choices
5. Each team's players have explanations

**Error:** Free user → `402 PAYMENT_REQUIRED`

---

## UC-03: AI Chat Assistant

**Actor:** Premium User  
**Precondition:** Active Premium subscription; match_id provided  
**Trigger:** User sends message to `POST /api/v1/chat`

**Main Flow:**
1. System validates Premium subscription and chat quota (unlimited for Premium)
2. System retrieves prediction data for the match
3. System builds LLM context: player scores, rules fired, match metadata
4. System sends user message + context to LLM (Claude/GPT/Gemini)
5. LLM generates response grounded in prediction data
6. System stores message and response in `chat_message` table
7. System returns answer

---

## UC-04: Admin Retrain Model

**Actor:** Admin  
**Precondition:** Admin JWT  
**Trigger:** `POST /api/v1/admin/retrain` with `{"format": "T20"}`

**Main Flow:**
1. System validates admin role
2. System queues Celery task `retrain_models`
3. Worker loads latest feature data from DB
4. Worker trains XGBoost, LightGBM, CatBoost
5. Worker backtests new models on 2025 held-out set
6. Worker promotes model if metrics improve
7. New model registered in `model_version` table
8. Admin notified via email on completion
