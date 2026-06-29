# Team Optimization Engine Specification

**Module:** `optimizer/`  
**Libraries:** PuLP 2.8 (LP), DEAP 1.4 (GA)  
**Entry:** `optimizer/team_optimizer.py`

---

## 1. Problem Statement

Given a ranked list of N players with ensemble scores and credits, select exactly 11 players satisfying all Dream11 constraints, maximising total ensemble score.

---

## 2. Dream11 Constraints (Hard Constraints)

| Constraint | Rule |
|-----------|------|
| Team size | Exactly 11 players |
| Total credits | ≤ 100.0 |
| Max from one real team | ≤ 7 players |
| Min from one real team | ≥ 1 player (implicit) |
| Wicketkeepers | Min 1, Max 4 |
| Batters | Min 3, Max 6 |
| All-rounders | Min 1, Max 4 |
| Bowlers | Min 3, Max 6 |
| Captain | 1 player (2× fantasy points multiplier) |
| Vice-Captain | 1 player (1.5× fantasy points multiplier) |

---

## 3. Linear Programming Formulation (PuLP)

### 3.1 Variables

```
x_i ∈ {0, 1}     for i in 1..N    (player i selected)
c_i ∈ {0, 1}     for i in 1..N    (player i is captain)
v_i ∈ {0, 1}     for i in 1..N    (player i is vice-captain)
```

### 3.2 Objective Function

```
Maximise:
  Σ score_i * x_i
  + Σ score_i * c_i        (captain gets extra weight in selection priority)
  + Σ score_i * 0.5 * v_i  (vice-captain gets half extra)
```

### 3.3 Constraints

```
# Team size
Σ x_i = 11

# Credit budget
Σ credits_i * x_i ≤ 100.0

# Role constraints
Σ x_i [where role=WK]   ≥ 1
Σ x_i [where role=WK]   ≤ 4
Σ x_i [where role=BAT]  ≥ 3
Σ x_i [where role=BAT]  ≤ 6
Σ x_i [where role=AR]   ≥ 1
Σ x_i [where role=AR]   ≤ 4
Σ x_i [where role=BOWL] ≥ 3
Σ x_i [where role=BOWL] ≤ 6

# Team cap (for each real team t)
Σ x_i [where team=t] ≤ 7

# Captain / VC must be in selected team
c_i ≤ x_i   for all i
v_i ≤ x_i   for all i

# Exactly one captain, one VC
Σ c_i = 1
Σ v_i = 1

# Captain ≠ Vice-Captain
c_i + v_i ≤ 1   for all i
```

### 3.4 Solver

```python
prob = pulp.LpProblem("XithSense_Team", pulp.LpMaximize)
solver = pulp.PULP_CBC_CMD(msg=False, timeLimit=10)
status = prob.solve(solver)
```

---

## 4. Team Modes

### 4.1 Safe Mode

Objective: maximise expected fantasy points with lowest variance.

```python
# Score modifier for safe mode
safe_score_i = fp_avg_10_i - (0.3 * fp_std_10_i)

# Additional constraint: prefer consistent players
# Sort by fp_consistency; bonus applied to top-15 by consistency
consistency_bonus = {i: 5.0 if rank_consistency[i] <= 15 else 0.0}
```

### 4.2 Grand League Mode

Objective: maximise upside (ceiling) with preference for differential picks.

```python
# Score modifier for GL mode
gl_score_i = (fp_ceiling_i * 0.6) + (fp_avg_5_i * 0.4)
           + differential_bonus_i

# Differential bonus: boost players with ownership < 20%
def differential_bonus(ownership_pct: float) -> float:
    if ownership_pct < 5:   return 20.0
    if ownership_pct < 10:  return 12.0
    if ownership_pct < 20:  return 6.0
    return 0.0
```

### 4.3 Aggressive Mode

Objective: maximise total ceiling, ignoring consistency.

```python
# Score modifier: pure ceiling
aggressive_score_i = fp_ceiling_i

# Additional: relax consistency constraint
# Allow higher standard deviation players
```

### 4.4 Small League Mode

Objective: balanced between expected and ceiling, with moderate differential bias.

```python
small_league_score_i = (fp_avg_5_i * 0.5) + (fp_ceiling_i * 0.35) \
                     + (differential_bonus_i * 0.5)
```

---

## 5. Genetic Algorithm Fallback (DEAP)

Used when PuLP finds no feasible solution within time limit.

### 5.1 Chromosome Encoding

```python
# Individual = list of 11 player indices
# e.g., [3, 7, 12, 18, 21, 25, 30, 33, 38, 42, 47]
creator.create("FitnessMax", base.Fitness, weights=(1.0,))
creator.create("Individual", list, fitness=creator.FitnessMax)
```

### 5.2 Fitness Function

```python
def fitness(individual):
    if not satisfies_hard_constraints(individual):
        return (-1000.0,)   # heavy penalty for invalid team
    total_score = sum(player_scores[i] for i in individual)
    return (total_score,)
```

### 5.3 DEAP Configuration

```python
POPULATION_SIZE = 300
MAX_GENERATIONS = 150
CX_PROBABILITY  = 0.7    # crossover probability
MUT_PROBABILITY = 0.2    # mutation probability
TOURNAMENT_SIZE = 5
```

### 5.4 Operators

- **Selection:** Tournament selection (size 5)
- **Crossover:** Ordered crossover (OX) — preserves constraint validity
- **Mutation:** Swap mutation — replace one player with a random valid player

---

## 6. Multiple Team Generation

For Premium users requesting up to 20 unique teams:

```python
def generate_multiple_teams(n: int, mode: str) -> list[Team]:
    teams = []
    used_combos = set()

    # First team: pure LP optimal
    team_1 = solve_lp(mode)
    teams.append(team_1)
    used_combos.add(frozenset(team_1.player_ids))

    # Subsequent teams: LP with diversity constraint
    for k in range(1, n):
        # Forbid exact repeat
        # Add constraint: at least 2 players different from each previous team
        diversity_constraint = max_overlap(used_combos, max_overlap=9)
        team_k = solve_lp(mode, extra_constraints=[diversity_constraint])
        if team_k:
            teams.append(team_k)
            used_combos.add(frozenset(team_k.player_ids))

    return teams
```

---

## 7. Output Structure

```python
@dataclass
class GeneratedTeam:
    mode: str                     # safe | grand_league | aggressive | small_league
    players: list[PlayerSlot]     # 11 players with role and credits
    captain: PlayerSlot
    vice_captain: PlayerSlot
    total_credits: float
    predicted_total_fp: float     # sum of fp_predicted for all players
    team_ceiling: float           # sum of fp_ceiling for all players
    solver_used: str              # lp | genetic
    solve_time_ms: int
```

---

## 8. Performance Targets

| Metric | Target |
|--------|--------|
| Single team generation (LP) | < 500ms |
| 4-mode portfolio generation | < 3 seconds |
| 20-team generation (Premium) | < 15 seconds |
| LP infeasibility rate | < 2% of valid match inputs |
