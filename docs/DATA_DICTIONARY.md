# Data Dictionary

## Key Field Definitions

| Field | Table | Type | Description |
|-------|-------|------|-------------|
| `match_type` | `match` | VARCHAR | Cricket format: T20, ODI, Test, IT20, IPL, BBL, PSL, CPL, WPL, NTB, CCH, MDM, WOD, WTB, IPT, ODM |
| `gender` | `match` | VARCHAR | `male` or `female` |
| `team_type` | `match` | VARCHAR | `club` (franchise leagues) or `international` |
| `toss_decision` | `match` | VARCHAR | `bat` = elected to bat first; `field` = elected to field first |
| `actual_delivery` | `delivery` | DECIMAL | Cricsheet notation: over.ball e.g. 2.3 = over 2, ball 3 |
| `phase` | `delivery` | VARCHAR | `powerplay` = overs 1–6 (T20); `middle` = 7–15; `death` = 16–20 |
| `fp_ceiling` | `rolling_feature` | DECIMAL | 90th percentile of fantasy points over last 10 matches |
| `fp_floor` | `rolling_feature` | DECIMAL | 10th percentile of fantasy points over last 10 matches |
| `fp_consistency` | `rolling_feature` | DECIMAL | Coefficient of variation (stddev/mean). 0 = perfectly consistent. Higher = volatile |
| `impact_score` | `human_rule` | INT | -100 to +100. Positive = boost player. Negative = penalise |
| `confidence` | `human_rule` | DECIMAL | 0.0–1.0. Multiplied by impact_score for effective adjustment |
| `ensemble_score` | `predicted_player` | DECIMAL | Final weighted score combining ML + rules + form + live |
| `mode` | `recommended_team` | VARCHAR | `safe` / `grand_league` / `aggressive` / `small_league` |
| `plan` | `subscription` | VARCHAR | `free` / `premium_monthly` / `premium_annual` |
| `status` | `subscription` | VARCHAR | `active` / `cancelled` / `expired` / `trial` |
| `bowler_type` | `matchup_stat` | VARCHAR | `pace_right` / `pace_left` / `spin_off` / `spin_left` / `spin_wrist` |
| `spin_wicket_pct` | `venue_stat` | DECIMAL | Fraction of wickets at venue taken by spinners (0.0–1.0) |
| `chasing_win_pct` | `venue_stat` | DECIMAL | Fraction of matches won by team batting second (0.0–1.0) |
| `batting_style` | `player` | VARCHAR | `Right-hand bat` or `Left-hand bat` |
| `bowling_style` | `player` | VARCHAR | Full Cricsheet bowling style string |
| `primary_role` | `player` | VARCHAR | `BAT` / `BOWL` / `AR` (all-rounder) / `WK` (wicketkeeper) |
