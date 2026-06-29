# Grand League Strategy Specification

**Module:** `optimizer/gl_strategy.py`

---

## GL vs Safe — Core Difference

| Dimension | Safe Team | Grand League Team |
|-----------|----------|------------------|
| Objective | Maximise expected FP | Maximise ceiling FP |
| Ownership | High-ownership picks | Low-ownership picks (differentials) |
| Risk | Low — consistent performers | High — high variance picks |
| Captain | Consensus favourite | Contrarian or split-captain |
| Win scenario | Small leagues, head-to-head | Large pools (10k+ entries) |

---

## GL Optimizer Score Formula

```python
def gl_player_score(player: PlayerWithFeatures, ownership_pct: float) -> float:
    """
    GL score maximises ceiling while rewarding low ownership.
    """
    ceiling_component = player.fp_ceiling * 0.60
    form_component    = player.fp_avg_5   * 0.25
    diff_bonus        = differential_bonus(ownership_pct) * 0.15

    return ceiling_component + form_component + diff_bonus

def differential_bonus(ownership_pct: float) -> float:
    if   ownership_pct < 3:  return 35.0
    elif ownership_pct < 5:  return 25.0
    elif ownership_pct < 10: return 18.0
    elif ownership_pct < 15: return 10.0
    elif ownership_pct < 20: return  5.0
    else:                    return  0.0
```

---

## GL Team Constraints (Additional vs Base)

| Rule | Safe Mode | GL Mode |
|------|-----------|---------|
| Min differential picks (< 20% ownership) | 0 | ≥ 1 |
| Max consensus picks (> 75% ownership) | No limit | ≤ 7 |
| Captain: must not be top 2 by ownership | No | No (contrarian only in split-captain strategy) |
| Max ownership of team (sum) | No limit | ≤ 500% (spread required) |

---

## GL Captain Strategy

### Strategy A: Contrarian Captain
Pick the highest-ceiling player with ownership < 40%:

```python
def contrarian_captain(players: list[PlayerWithFeatures]) -> PlayerWithFeatures:
    eligible = [p for p in players if p.ownership_pct < 40.0]
    return max(eligible, key=lambda p: p.fp_ceiling)
```

### Strategy B: Split Captain (Multiple Teams)
When generating multiple GL teams, split captain across 2–3 high-ceiling picks:

```python
def split_captain_pool(top_players: list, n_teams: int) -> list[tuple]:
    """
    Distribute captaincy across top ceiling picks.
    Ensures teams are sufficiently different.

    Example with 5 teams:
      Team 1,2: Captain = Virat Kohli (35% ownership, 116 ceiling)
      Team 3,4: Captain = Andre Russell (12% ownership, 98 ceiling)
      Team 5:   Captain = Noor Ahmad (4% ownership, 95 ceiling) — punt
    """
    captains = top_players[:3]   # top 3 by gl_score
    distribution = split_evenly(captains, n_teams)
    return distribution
```

---

## GL Ownership Constraint (LP Additional)

```python
# Additional LP constraint for GL mode

# Ensure at least 1 differential pick
differential_players = [i for i, p in enumerate(players)
                         if p.ownership_pct < 20.0]
optimizer.add_constraint(
    sum(x[i] for i in differential_players) >= 1,
    name="min_one_differential"
)

# Limit super-popular picks
lock_players = [i for i, p in enumerate(players) if p.ownership_pct > 75.0]
optimizer.add_constraint(
    sum(x[i] for i in lock_players) <= 7,
    name="max_lock_players"
)
```

---

## GL Team Diversity (Multi-Team Generation)

When generating N GL teams for a Premium user:

```python
def ensure_gl_diversity(teams: list[GeneratedTeam], min_diff_players: int = 2) -> list[GeneratedTeam]:
    """
    Ensure each pair of GL teams differs by at least min_diff_players.
    Achieved by adding exclusion constraints in LP for each subsequent team.
    """
    for i in range(1, len(teams)):
        for j in range(i):
            shared = {p.player_id for p in teams[i].players} & \
                     {p.player_id for p in teams[j].players}
            if len(shared) > 11 - min_diff_players:
                # Re-generate team i with exclusion constraint
                exclude = list(shared)[:min_diff_players]
                teams[i] = regenerate_with_exclusions(exclude)
    return teams
```

---

## GL Performance Tracking

After each match, track GL team performance:

```python
async def evaluate_gl_performance(match_id: str) -> GLPerformanceReport:
    gl_teams = await get_teams_by_mode(match_id, mode="grand_league")
    actual_scores = await get_actual_fantasy_scores(match_id)

    for team in gl_teams:
        total_fp = compute_team_fp(team, actual_scores)
        rank_percentile = compute_percentile(total_fp, all_contest_scores)
        await save_gl_result(team, total_fp, rank_percentile)

    # Track: what % of GL teams finished in top 10%?
    top10_rate = sum(1 for t in gl_teams if t.rank_percentile >= 0.90) / len(gl_teams)
    return GLPerformanceReport(
        match_id=match_id,
        top10_rate=top10_rate,
        avg_total_fp=avg_fp,
        differential_correct_pct=diff_correct_pct
    )
```

---

## GL Strategy Config

```python
# Tunable via admin API
GL_STRATEGY_CONFIG = {
    "min_differentials": 1,           # Minimum players with < 20% ownership
    "max_lock_players": 7,            # Max players with > 75% ownership
    "ceiling_weight": 0.60,           # Weight on fp_ceiling in GL score
    "form_weight": 0.25,              # Weight on fp_avg_5
    "differential_weight": 0.15,      # Weight on differential bonus
    "contrarian_captain_threshold": 40.0,  # Max ownership for contrarian captain
    "split_captain_n_options": 3,     # How many captain options to split across
}
```
