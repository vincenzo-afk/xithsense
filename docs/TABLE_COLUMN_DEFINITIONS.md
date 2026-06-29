# Table Column Definitions

Complete column-level reference for every table in the XithSense database.

---

## `user`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `email` | VARCHAR(320) | No | — | Unique email address |
| `password_hash` | VARCHAR(128) | Yes | NULL | bcrypt hash; NULL for OAuth users |
| `full_name` | VARCHAR(200) | Yes | NULL | Display name |
| `phone` | VARCHAR(20) | Yes | NULL | Optional phone number |
| `role` | VARCHAR(20) | No | `'free'` | `free` \| `premium` \| `admin` |
| `is_active` | BOOLEAN | No | TRUE | False = soft-deleted or banned |
| `is_verified` | BOOLEAN | No | FALSE | Email verification status |
| `google_id` | VARCHAR(128) | Yes | NULL | Google OAuth sub claim |
| `last_login_at` | TIMESTAMPTZ | Yes | NULL | Last successful login timestamp |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Account creation time |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last profile update |

---

## `subscription`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `user_id` | UUID | No | — | FK → `user.id` |
| `plan` | VARCHAR(30) | No | — | `free` \| `premium_monthly` \| `premium_annual` |
| `status` | VARCHAR(30) | No | — | `active` \| `cancelled` \| `expired` \| `trial` |
| `razorpay_sub_id` | VARCHAR(100) | Yes | NULL | Razorpay subscription ID |
| `razorpay_customer_id` | VARCHAR(100) | Yes | NULL | Razorpay customer ID |
| `current_period_start` | TIMESTAMPTZ | Yes | NULL | Start of current billing period |
| `current_period_end` | TIMESTAMPTZ | Yes | NULL | End of current billing period |
| `cancelled_at` | TIMESTAMPTZ | Yes | NULL | When user cancelled |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Subscription created |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last status change |

---

## `match`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | VARCHAR(20) | No | — | Cricsheet numeric match ID (PK) |
| `match_type` | VARCHAR(20) | No | — | `T20` \| `ODI` \| `Test` \| `IPL` \| `BBL` \| `PSL` \| `CPL` \| `IT20` \| `WPL` \| `NTB` \| `CCH` \| `ODM` \| `MDM` |
| `gender` | VARCHAR(10) | No | — | `male` \| `female` |
| `team_type` | VARCHAR(20) | No | — | `club` \| `international` |
| `venue_id` | UUID | Yes | NULL | FK → `venue.id` (nullable if venue not in master) |
| `venue_name` | VARCHAR(200) | Yes | NULL | Raw venue string from Cricsheet |
| `city` | VARCHAR(100) | Yes | NULL | City from Cricsheet info block |
| `team_a` | VARCHAR(100) | No | — | First team name |
| `team_b` | VARCHAR(100) | No | — | Second team name |
| `toss_winner` | VARCHAR(100) | Yes | NULL | Team that won the toss |
| `toss_decision` | VARCHAR(10) | Yes | NULL | `bat` \| `field` |
| `match_winner` | VARCHAR(100) | Yes | NULL | Winning team; NULL if no result |
| `win_by_runs` | INTEGER | Yes | NULL | Runs margin if batting team won |
| `win_by_wickets` | INTEGER | Yes | NULL | Wickets margin if chasing team won |
| `player_of_match` | VARCHAR(100)[] | Yes | NULL | Array of player keys |
| `season` | VARCHAR(20) | Yes | NULL | Season string e.g. `"2026"` |
| `event_name` | VARCHAR(200) | Yes | NULL | Tournament name |
| `event_stage` | VARCHAR(100) | Yes | NULL | `"Final"` \| `"Qualifier 1"` etc. |
| `match_date` | DATE | No | — | Date of match (first day for Tests) |
| `day_night` | BOOLEAN | No | FALSE | D/N match indicator |
| `balls_per_over` | INTEGER | No | 6 | Usually 6; can be 5 for some formats |
| `data_version` | VARCHAR(10) | Yes | NULL | Cricsheet data_version e.g. `"1.2.0"` |
| `is_complete` | BOOLEAN | No | TRUE | FALSE if abandoned/no result |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Ingestion timestamp |

---

## `player`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `full_name` | VARCHAR(200) | No | — | Full player name as in Cricsheet |
| `cricsheet_key` | VARCHAR(200) | No | — | Unique Cricsheet registry key e.g. `"Kohli, V"` |
| `short_name` | VARCHAR(50) | Yes | NULL | Display short name e.g. `"V Kohli"` |
| `nationality` | VARCHAR(100) | Yes | NULL | Country of origin |
| `batting_style` | VARCHAR(30) | Yes | NULL | `"Right-hand bat"` \| `"Left-hand bat"` |
| `bowling_style` | VARCHAR(50) | Yes | NULL | Full Cricsheet bowling style string |
| `primary_role` | VARCHAR(20) | Yes | NULL | `BAT` \| `BOWL` \| `AR` \| `WK` |
| `dob` | DATE | Yes | NULL | Date of birth (if known) |
| `is_active` | BOOLEAN | No | TRUE | FALSE = retired or not in active squads |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Record creation |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last update |

---

## `delivery`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `innings_id` | UUID | No | — | FK → `innings.id` |
| `match_id` | VARCHAR(20) | No | — | Denormalised for query performance |
| `over_number` | SMALLINT | No | — | 0-indexed over number |
| `ball_number` | DECIMAL(4,1) | No | — | `actual_delivery` field e.g. `2.3` |
| `batter` | VARCHAR(200) | No | — | Batsman facing the ball |
| `bowler` | VARCHAR(200) | No | — | Bowler delivering the ball |
| `non_striker` | VARCHAR(200) | Yes | NULL | Non-striking batsman |
| `runs_batter` | SMALLINT | No | 0 | Runs scored by batter off this ball |
| `runs_extras` | SMALLINT | No | 0 | Extras on this delivery |
| `runs_total` | SMALLINT | No | 0 | Total runs including extras |
| `is_wide` | BOOLEAN | No | FALSE | Wide delivery |
| `is_no_ball` | BOOLEAN | No | FALSE | No ball |
| `is_bye` | BOOLEAN | No | FALSE | Bye extras |
| `is_leg_bye` | BOOLEAN | No | FALSE | Leg bye extras |
| `extra_wides` | SMALLINT | No | 0 | Wide runs |
| `extra_no_balls` | SMALLINT | No | 0 | No ball runs |
| `extra_byes` | SMALLINT | No | 0 | Bye runs |
| `extra_leg_byes` | SMALLINT | No | 0 | Leg bye runs |
| `is_wicket` | BOOLEAN | No | FALSE | Wicket on this delivery |
| `wicket_player_out` | VARCHAR(200) | Yes | NULL | Player dismissed |
| `wicket_kind` | VARCHAR(50) | Yes | NULL | `caught` \| `bowled` \| `lbw` \| `run out` \| `stumped` \| `hit wicket` \| `obstructing the field` \| `retired hurt` |
| `wicket_fielder` | VARCHAR(200) | Yes | NULL | Fielder involved in dismissal |
| `is_powerplay` | BOOLEAN | No | FALSE | Delivery in powerplay overs |
| `phase` | VARCHAR(20) | Yes | NULL | `powerplay` \| `middle` \| `death` |
| `review_by` | VARCHAR(100) | Yes | NULL | Team requesting DRS review |
| `review_decision` | VARCHAR(20) | Yes | NULL | `upheld` \| `struck_out` |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Ingestion timestamp |

---

## `rolling_feature`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `player_id` | UUID | No | — | FK → `player.id` |
| `match_type` | VARCHAR(20) | No | — | Format for which features computed |
| `as_of_date` | DATE | No | — | Features valid as of this date |
| `window_matches` | SMALLINT | No | — | Window size: `3` \| `5` \| `10` |
| `avg_runs` | DECIMAL(7,2) | Yes | NULL | Rolling batting runs average |
| `avg_balls` | DECIMAL(7,2) | Yes | NULL | Rolling balls faced average |
| `avg_sr` | DECIMAL(7,2) | Yes | NULL | Rolling strike rate |
| `avg_fours` | DECIMAL(5,2) | Yes | NULL | Rolling fours average |
| `avg_sixes` | DECIMAL(5,2) | Yes | NULL | Rolling sixes average |
| `avg_wickets` | DECIMAL(5,2) | Yes | NULL | Rolling wickets average |
| `avg_economy` | DECIMAL(5,2) | Yes | NULL | Rolling economy rate |
| `avg_overs` | DECIMAL(5,2) | Yes | NULL | Rolling overs bowled average |
| `fp_avg` | DECIMAL(7,2) | Yes | NULL | Rolling fantasy points average |
| `fp_ceiling` | DECIMAL(7,2) | Yes | NULL | 90th percentile FP (window 10 only) |
| `fp_floor` | DECIMAL(7,2) | Yes | NULL | 10th percentile FP (window 10 only) |
| `fp_consistency` | DECIMAL(5,3) | Yes | NULL | CV of FP; lower = more consistent |
| `fp_last_3` | DECIMAL(7,2) | Yes | NULL | Simple 3-match FP avg |
| `matches_included` | INTEGER | Yes | NULL | Actual matches in this window |
| `last_match_id` | VARCHAR(20) | Yes | NULL | Most recent match included |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Feature computation timestamp |

---

## `human_rule`

| Column | Type | Nullable | Default | Description |
|--------|------|----------|---------|-------------|
| `id` | UUID | No | `gen_random_uuid()` | Primary key |
| `rule_type` | VARCHAR(20) | No | — | `player` \| `venue` \| `matchup` \| `context` |
| `player_key` | VARCHAR(200) | Yes | NULL | Cricsheet key; NULL = applies to all |
| `condition_json` | JSONB | No | — | Condition key-value pairs |
| `impact_score` | SMALLINT | No | — | -100 to +100 adjustment |
| `confidence` | DECIMAL(4,3) | No | — | 0.0–1.0 reliability weight |
| `source` | VARCHAR(500) | Yes | NULL | Evidence reference |
| `description` | TEXT | Yes | NULL | Human-readable explanation |
| `is_active` | BOOLEAN | No | TRUE | FALSE = disabled without deletion |
| `match_types` | TEXT[] | Yes | NULL | Restrict to formats; NULL = all |
| `valid_from` | DATE | Yes | NULL | Rule activation date |
| `valid_until` | DATE | Yes | NULL | Rule expiry date |
| `created_by` | UUID | Yes | NULL | FK → `user.id` (admin who created) |
| `created_at` | TIMESTAMPTZ | No | `NOW()` | Creation timestamp |
| `updated_at` | TIMESTAMPTZ | No | `NOW()` | Last modification |
