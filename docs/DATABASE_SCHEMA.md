# Database Schema

**Database:** PostgreSQL 15 (via Supabase)  
**ORM:** SQLAlchemy 2.0 with Alembic migrations  
**Naming convention:** snake_case tables and columns, singular table names

---

## Table Overview

| Table | Purpose |
|-------|---------|
| `user` | User accounts |
| `subscription` | Subscription plans and billing status |
| `match` | Match metadata (Cricsheet info block) |
| `venue` | Venue master data |
| `player` | Player master data |
| `player_team_match` | Players per team per match |
| `innings` | Innings per match |
| `delivery` | Ball-by-ball delivery records |
| `player_match_performance` | Aggregated per-match stats per player |
| `rolling_feature` | Pre-computed rolling window features |
| `venue_stat` | Venue-level aggregated stats |
| `matchup_stat` | Batter vs. bowler-type matchup stats |
| `human_rule` | Analyst-encoded human intelligence rules |
| `rule_trigger` | Audit log of rule firings per prediction |
| `prediction` | Match-level prediction run records |
| `predicted_player` | Player scores within a prediction |
| `recommended_team` | Generated team configurations |
| `team_player` | Players within a recommended team |
| `fantasy_point_history` | Historical fantasy points per player per match |
| `notification` | Notification delivery records |
| `chat_session` | AI chat sessions per user |
| `chat_message` | Individual messages within a chat session |
| `backtest_run` | Backtesting run metadata |
| `backtest_result` | Per-match results within a backtest run |
| `model_version` | Model artifact registry |
| `admin_action` | Admin activity audit log |

---

## Table Definitions

### `user`

```sql
CREATE TABLE "user" (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           VARCHAR(320) UNIQUE NOT NULL,
    password_hash   VARCHAR(128),              -- NULL for OAuth users
    full_name       VARCHAR(200),
    phone           VARCHAR(20),
    role            VARCHAR(20) NOT NULL DEFAULT 'free',  -- free | premium | admin
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    is_verified     BOOLEAN NOT NULL DEFAULT FALSE,
    google_id       VARCHAR(128) UNIQUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_user_email ON "user"(email);
CREATE INDEX idx_user_role ON "user"(role);
```

### `subscription`

```sql
CREATE TABLE subscription (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id             UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    plan                VARCHAR(30) NOT NULL,   -- free | premium_monthly | premium_annual
    status              VARCHAR(30) NOT NULL,   -- active | cancelled | expired | trial
    razorpay_sub_id     VARCHAR(100) UNIQUE,
    razorpay_customer_id VARCHAR(100),
    current_period_start TIMESTAMPTZ,
    current_period_end   TIMESTAMPTZ,
    cancelled_at        TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_subscription_user ON subscription(user_id);
CREATE INDEX idx_subscription_status ON subscription(status);
```

### `venue`

```sql
CREATE TABLE venue (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200) NOT NULL,
    city            VARCHAR(100),
    country         VARCHAR(100),
    capacity        INTEGER,
    pitch_type      VARCHAR(50),   -- batting | bowling | balanced | spin | pace
    avg_first_innings_score INTEGER,
    boundary_short_m DECIMAL(5,2),  -- average short boundary in metres
    boundary_long_m  DECIMAL(5,2),  -- average long boundary in metres
    dew_factor      BOOLEAN DEFAULT FALSE,
    altitude_m      INTEGER,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_venue_name ON venue(LOWER(name));
```

### `match`

```sql
CREATE TABLE match (
    id              VARCHAR(20) PRIMARY KEY,   -- Cricsheet numeric match ID
    match_type      VARCHAR(20) NOT NULL,      -- T20 | ODI | Test | IT20 | IPL | BBL | ...
    gender          VARCHAR(10) NOT NULL,      -- male | female
    team_type       VARCHAR(20) NOT NULL,      -- club | international
    venue_id        UUID REFERENCES venue(id),
    venue_name      VARCHAR(200),              -- raw string from Cricsheet
    city            VARCHAR(100),
    team_a          VARCHAR(100) NOT NULL,
    team_b          VARCHAR(100) NOT NULL,
    toss_winner     VARCHAR(100),
    toss_decision   VARCHAR(10),               -- bat | field
    match_winner    VARCHAR(100),
    win_by_runs     INTEGER,
    win_by_wickets  INTEGER,
    player_of_match VARCHAR(100)[],
    season          VARCHAR(20),
    event_name      VARCHAR(200),
    event_stage     VARCHAR(100),
    match_date      DATE NOT NULL,
    day_night       BOOLEAN DEFAULT FALSE,
    balls_per_over  INTEGER DEFAULT 6,
    data_version    VARCHAR(10),
    is_complete     BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_match_type ON match(match_type);
CREATE INDEX idx_match_date ON match(match_date);
CREATE INDEX idx_match_season ON match(season);
CREATE INDEX idx_match_team_a ON match(team_a);
CREATE INDEX idx_match_team_b ON match(team_b);
CREATE INDEX idx_match_venue ON match(venue_id);
```

### `player`

```sql
CREATE TABLE player (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    full_name       VARCHAR(200) NOT NULL,
    cricsheet_key   VARCHAR(200) UNIQUE NOT NULL,  -- registry key from Cricsheet
    short_name      VARCHAR(50),
    nationality     VARCHAR(100),
    batting_style   VARCHAR(30),   -- Right-hand bat | Left-hand bat
    bowling_style   VARCHAR(50),   -- Right-arm fast | Right-arm off-break | Left-arm orthodox | ...
    primary_role    VARCHAR(20),   -- BAT | BOWL | AR | WK
    dob             DATE,
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_player_name ON player(LOWER(full_name));
CREATE INDEX idx_player_role ON player(primary_role);
```

### `player_team_match`

```sql
CREATE TABLE player_team_match (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id    VARCHAR(20) NOT NULL REFERENCES match(id),
    player_id   UUID NOT NULL REFERENCES player(id),
    team        VARCHAR(100) NOT NULL,
    batting_order INTEGER,
    is_captain  BOOLEAN DEFAULT FALSE,
    is_keeper   BOOLEAN DEFAULT FALSE,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(match_id, player_id)
);

CREATE INDEX idx_ptm_match ON player_team_match(match_id);
CREATE INDEX idx_ptm_player ON player_team_match(player_id);
```

### `innings`

```sql
CREATE TABLE innings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        VARCHAR(20) NOT NULL REFERENCES match(id),
    innings_number  SMALLINT NOT NULL,   -- 1 | 2 | 3 | 4
    batting_team    VARCHAR(100) NOT NULL,
    bowling_team    VARCHAR(100) NOT NULL,
    total_runs      INTEGER DEFAULT 0,
    total_wickets   INTEGER DEFAULT 0,
    total_overs     DECIMAL(5,1) DEFAULT 0,
    is_complete     BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(match_id, innings_number)
);

CREATE INDEX idx_innings_match ON innings(match_id);
```

### `delivery`

```sql
CREATE TABLE delivery (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    innings_id      UUID NOT NULL REFERENCES innings(id),
    match_id        VARCHAR(20) NOT NULL,
    over_number     SMALLINT NOT NULL,
    ball_number     DECIMAL(4,1) NOT NULL,    -- actual_delivery: "2.3" stored as 2.3
    batter          VARCHAR(200) NOT NULL,
    bowler          VARCHAR(200) NOT NULL,
    non_striker     VARCHAR(200),
    runs_batter     SMALLINT NOT NULL DEFAULT 0,
    runs_extras     SMALLINT NOT NULL DEFAULT 0,
    runs_total      SMALLINT NOT NULL DEFAULT 0,
    is_wide         BOOLEAN DEFAULT FALSE,
    is_no_ball      BOOLEAN DEFAULT FALSE,
    is_bye          BOOLEAN DEFAULT FALSE,
    is_leg_bye      BOOLEAN DEFAULT FALSE,
    extra_wides     SMALLINT DEFAULT 0,
    extra_no_balls  SMALLINT DEFAULT 0,
    extra_byes      SMALLINT DEFAULT 0,
    extra_leg_byes  SMALLINT DEFAULT 0,
    is_wicket       BOOLEAN DEFAULT FALSE,
    wicket_player_out VARCHAR(200),
    wicket_kind     VARCHAR(50),   -- caught | bowled | lbw | run out | stumped | ...
    wicket_fielder  VARCHAR(200),
    is_powerplay    BOOLEAN DEFAULT FALSE,
    phase           VARCHAR(20),   -- powerplay | middle | death
    review_by       VARCHAR(100),
    review_decision VARCHAR(20),   -- upheld | struck_out
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_delivery_innings ON delivery(innings_id);
CREATE INDEX idx_delivery_match ON delivery(match_id);
CREATE INDEX idx_delivery_batter ON delivery(batter);
CREATE INDEX idx_delivery_bowler ON delivery(bowler);
CREATE INDEX idx_delivery_wicket ON delivery(is_wicket) WHERE is_wicket = TRUE;
```

### `player_match_performance`

```sql
CREATE TABLE player_match_performance (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        VARCHAR(20) NOT NULL REFERENCES match(id),
    player_id       UUID NOT NULL REFERENCES player(id),
    team            VARCHAR(100) NOT NULL,
    -- Batting
    runs_scored     INTEGER DEFAULT 0,
    balls_faced     INTEGER DEFAULT 0,
    fours           INTEGER DEFAULT 0,
    sixes           INTEGER DEFAULT 0,
    strike_rate     DECIMAL(7,2),
    is_dismissed    BOOLEAN DEFAULT FALSE,
    dismissal_type  VARCHAR(50),
    batting_position SMALLINT,
    -- Bowling
    overs_bowled    DECIMAL(4,1) DEFAULT 0,
    balls_bowled    INTEGER DEFAULT 0,
    runs_conceded   INTEGER DEFAULT 0,
    wickets_taken   INTEGER DEFAULT 0,
    maidens         INTEGER DEFAULT 0,
    economy         DECIMAL(6,2),
    dot_balls       INTEGER DEFAULT 0,
    -- Fielding
    catches         INTEGER DEFAULT 0,
    run_outs        INTEGER DEFAULT 0,
    stumpings       INTEGER DEFAULT 0,
    -- Fantasy
    fantasy_points  DECIMAL(8,2),
    fantasy_platform VARCHAR(30) DEFAULT 'dream11',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(match_id, player_id, fantasy_platform)
);

CREATE INDEX idx_pmp_match ON player_match_performance(match_id);
CREATE INDEX idx_pmp_player ON player_match_performance(player_id);
CREATE INDEX idx_pmp_fantasy ON player_match_performance(fantasy_points);
```

### `rolling_feature`

```sql
CREATE TABLE rolling_feature (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id           UUID NOT NULL REFERENCES player(id),
    match_type          VARCHAR(20) NOT NULL,
    as_of_date          DATE NOT NULL,
    window_matches      SMALLINT NOT NULL,    -- 3 | 5 | 10
    -- Batting
    avg_runs            DECIMAL(7,2),
    avg_balls           DECIMAL(7,2),
    avg_sr              DECIMAL(7,2),
    avg_fours           DECIMAL(5,2),
    avg_sixes           DECIMAL(5,2),
    -- Bowling
    avg_wickets         DECIMAL(5,2),
    avg_economy         DECIMAL(5,2),
    avg_overs           DECIMAL(5,2),
    -- Fantasy
    fp_avg              DECIMAL(7,2),
    fp_ceiling          DECIMAL(7,2),   -- 90th pctile
    fp_floor            DECIMAL(7,2),   -- 10th pctile
    fp_consistency      DECIMAL(5,3),   -- std dev / mean (lower = more consistent)
    fp_last_3           DECIMAL(7,2),   -- simple 3-match avg
    -- Metadata
    matches_included    INTEGER,
    last_match_id       VARCHAR(20),
    created_at          TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(player_id, match_type, as_of_date, window_matches)
);

CREATE INDEX idx_rf_player_type ON rolling_feature(player_id, match_type);
CREATE INDEX idx_rf_date ON rolling_feature(as_of_date);
```

### `venue_stat`

```sql
CREATE TABLE venue_stat (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    venue_id        UUID NOT NULL REFERENCES venue(id),
    match_type      VARCHAR(20) NOT NULL,
    -- Batting
    avg_runs_per_innings DECIMAL(7,2),
    avg_first_innings    DECIMAL(7,2),
    avg_second_innings   DECIMAL(7,2),
    avg_wickets_per_match DECIMAL(5,2),
    -- Surface assistance
    spin_wicket_pct  DECIMAL(5,2),    -- % of wickets taken by spinners
    pace_wicket_pct  DECIMAL(5,2),
    -- Context
    chasing_win_pct  DECIMAL(5,2),
    toss_advantage   VARCHAR(10),     -- bat | field | neutral
    dew_impact       DECIMAL(5,2),    -- average score differential 2nd innings with dew
    total_matches    INTEGER,
    last_updated     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(venue_id, match_type)
);
```

### `matchup_stat`

```sql
CREATE TABLE matchup_stat (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id       UUID NOT NULL REFERENCES player(id),
    match_type      VARCHAR(20) NOT NULL,
    bowler_type     VARCHAR(50) NOT NULL,  -- pace_right | pace_left | spin_off | spin_left | spin_wrist
    -- Stats
    balls_faced     INTEGER DEFAULT 0,
    runs_scored     INTEGER DEFAULT 0,
    dismissals      INTEGER DEFAULT 0,
    strike_rate     DECIMAL(7,2),
    avg_runs        DECIMAL(7,2),
    dot_ball_pct    DECIMAL(5,2),
    boundary_pct    DECIMAL(5,2),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(player_id, match_type, bowler_type)
);

CREATE INDEX idx_matchup_player ON matchup_stat(player_id);
```

### `human_rule`

```sql
CREATE TABLE human_rule (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    rule_type       VARCHAR(20) NOT NULL,  -- player | venue | matchup | context
    player_key      VARCHAR(200),          -- NULL for wildcard rules
    condition_json  JSONB NOT NULL,
    impact_score    SMALLINT NOT NULL CHECK (impact_score BETWEEN -100 AND 100),
    confidence      DECIMAL(4,3) NOT NULL CHECK (confidence BETWEEN 0 AND 1),
    source          VARCHAR(500),
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_by      UUID REFERENCES "user"(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rule_type ON human_rule(rule_type);
CREATE INDEX idx_rule_player ON human_rule(player_key);
CREATE INDEX idx_rule_active ON human_rule(is_active);
```

### `prediction`

```sql
CREATE TABLE prediction (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        VARCHAR(20) NOT NULL REFERENCES match(id),
    user_id         UUID REFERENCES "user"(id),    -- NULL for system predictions
    model_version_id UUID,
    ensemble_weights JSONB,       -- {"ml":0.40,"rules":0.30,"form":0.20,"live":0.10}
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    is_live         BOOLEAN DEFAULT FALSE,
    match_phase     VARCHAR(20),  -- pre_toss | post_toss | live
    UNIQUE(match_id, user_id, match_phase)
);

CREATE INDEX idx_prediction_match ON prediction(match_id);
CREATE INDEX idx_prediction_user ON prediction(user_id);
```

### `predicted_player`

```sql
CREATE TABLE predicted_player (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id   UUID NOT NULL REFERENCES prediction(id),
    player_id       UUID NOT NULL REFERENCES player(id),
    ensemble_score  DECIMAL(8,3) NOT NULL,
    ml_score        DECIMAL(8,3),
    rules_score     DECIMAL(8,3),
    form_score      DECIMAL(8,3),
    live_score      DECIMAL(8,3),
    fp_predicted    DECIMAL(7,2),
    fp_ceiling      DECIMAL(7,2),
    fp_floor        DECIMAL(7,2),
    confidence      SMALLINT,         -- 0–100
    rank            SMALLINT,
    rules_fired     JSONB,            -- array of rule IDs that triggered
    explanation     TEXT,             -- LLM-generated explanation
    UNIQUE(prediction_id, player_id)
);

CREATE INDEX idx_pp_prediction ON predicted_player(prediction_id);
CREATE INDEX idx_pp_score ON predicted_player(ensemble_score DESC);
```

### `recommended_team`

```sql
CREATE TABLE recommended_team (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    prediction_id   UUID NOT NULL REFERENCES prediction(id),
    mode            VARCHAR(20) NOT NULL,  -- safe | grand_league | aggressive | small_league
    captain_id      UUID NOT NULL REFERENCES player(id),
    vice_captain_id UUID NOT NULL REFERENCES player(id),
    total_credits   DECIMAL(6,2),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_rt_prediction ON recommended_team(prediction_id);
```

### `team_player`

```sql
CREATE TABLE team_player (
    team_id     UUID NOT NULL REFERENCES recommended_team(id),
    player_id   UUID NOT NULL REFERENCES player(id),
    role        VARCHAR(10) NOT NULL,   -- WK | BAT | AR | BOWL
    credits     DECIMAL(4,1),
    PRIMARY KEY (team_id, player_id)
);
```

### `backtest_run`

```sql
CREATE TABLE backtest_run (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(200),
    match_type      VARCHAR(20),
    from_date       DATE,
    to_date         DATE,
    total_matches   INTEGER,
    correct_player_rate  DECIMAL(5,3),
    captain_accuracy     DECIMAL(5,3),
    avg_fp_error         DECIMAL(7,3),
    simulated_roi        DECIMAL(8,4),
    model_version_id     UUID,
    run_at          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

### `model_version`

```sql
CREATE TABLE model_version (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    model_type      VARCHAR(50) NOT NULL,  -- xgboost | lightgbm | catboost | ensemble
    match_type      VARCHAR(20),
    artifact_path   VARCHAR(500) NOT NULL,
    feature_count   INTEGER,
    train_mae       DECIMAL(8,4),
    val_mae         DECIMAL(8,4),
    train_from      DATE,
    train_to        DATE,
    is_active       BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_mv_active ON model_version(is_active);
CREATE INDEX idx_mv_type ON model_version(model_type, match_type);
```

---

## Migration Strategy

- All migrations managed by Alembic
- Migration files in `alembic/versions/`
- Never edit existing migration files; always create new ones
- Run `make migrate` to apply all pending migrations
- Run `make migrate-create MSG="description"` to generate a new migration
