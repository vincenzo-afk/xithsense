# Human Intelligence Rules Specification

**Module:** `human_rules/`  
**Validator:** `human_rules/validate_rules.py`  
**Loading:** Rules loaded at API startup from JSON files; hot-reloadable via admin API

---

## 1. Purpose

The Human Rules Engine captures domain knowledge that statistical models cannot reliably learn from historical data alone — particularly for:

- Small sample sizes (new venues, rare matchups)
- Psychological and situational factors (pressure, home crowd, rivalry)
- Regime changes (player role change, new captain, injury return)
- Known biases in aggregate stats (player missing recent form due to rest)

---

## 2. Rule JSON Schema

Every rule must conform to `human_rules/RULE_SCHEMA.json`.

### 2.1 Schema Definition

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "HumanRule",
  "type": "object",
  "required": ["id", "rule_type", "condition", "impact_score", "confidence", "source"],
  "properties": {
    "id": {
      "type": "string",
      "pattern": "^RULE-[0-9]{4}$",
      "description": "Unique rule identifier e.g. RULE-0042"
    },
    "rule_type": {
      "type": "string",
      "enum": ["player", "venue", "matchup", "context"]
    },
    "player_key": {
      "type": ["string", "null"],
      "description": "Cricsheet registry key. NULL means rule applies to all players matching condition."
    },
    "condition": {
      "type": "object",
      "description": "Key-value pairs that must ALL be true for rule to fire",
      "additionalProperties": {
        "type": ["string", "number", "boolean", "array"]
      }
    },
    "impact_score": {
      "type": "integer",
      "minimum": -100,
      "maximum": 100,
      "description": "Score adjustment applied to ensemble. Positive = boost. Negative = penalty."
    },
    "confidence": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0,
      "description": "Rule reliability. Effective impact = impact_score * confidence."
    },
    "source": {
      "type": "string",
      "description": "Evidence reference: analyst note, match ID, or statistical finding"
    },
    "description": {
      "type": "string",
      "description": "Human-readable explanation of what this rule captures"
    },
    "is_active": {
      "type": "boolean",
      "default": true
    },
    "match_types": {
      "type": ["array", "null"],
      "items": {"type": "string"},
      "description": "If set, rule only fires for these match types. NULL = all types."
    },
    "valid_from": {
      "type": ["string", "null"],
      "format": "date"
    },
    "valid_until": {
      "type": ["string", "null"],
      "format": "date"
    }
  }
}
```

---

## 3. Condition Keys

The `condition` object supports these keys:

| Key | Type | Description | Example |
|-----|------|-------------|---------|
| `venue` | string | Venue name (partial match) | `"Wankhede"` |
| `toss_decision` | string | `"bat"` or `"field"` | `"field"` |
| `is_chasing` | boolean | Team is batting second | `true` |
| `pitch_type` | string | `"spin"`, `"pace"`, `"batting"`, `"bowling"` | `"spin"` |
| `match_type` | string or array | Match format | `"T20"` or `["T20","IPL"]` |
| `opposition` | string | Opposition team name (partial) | `"Australia"` |
| `opposition_bowling_type` | string | Dominant bowling type | `"spin_heavy"` |
| `batting_position` | integer or array | Expected batting position | `[1,2]` |
| `phase` | string | `"powerplay"`, `"middle"`, `"death"` | `"death"` |
| `home_match` | boolean | Playing at home ground | `true` |
| `is_final_or_knockout` | boolean | High-pressure match | `true` |
| `rest_days` | object | Min/max days since last match | `{"min": 5}` |
| `season` | string | Current season | `"2026"` |

---

## 4. Impact Score Calibration

| Impact Range | Effect | Usage |
|---|---|---|
| +51 to +100 | Strong boost | Exceptional condition advantage (e.g. specialist at home venue) |
| +21 to +50 | Moderate boost | Clear situational advantage |
| +1 to +20 | Mild boost | Slight edge |
| 0 | Neutral | No adjustment |
| -1 to -20 | Mild penalty | Minor disadvantage |
| -21 to -50 | Moderate penalty | Notable weakness in this condition |
| -51 to -100 | Strong penalty | Avoid unless data strongly contradicts |

**Effective impact** applied to ensemble score:

```
effective_impact = impact_score × confidence
final_rules_score += effective_impact
```

---

## 5. Rule Types and Files

### 5.1 PLAYER_RULES.json — Player-Specific Intelligence

Rules tied to a specific player (identified by `player_key`).

Example:
```json
{
  "id": "RULE-0001",
  "rule_type": "player",
  "player_key": "Kohli, V",
  "condition": {
    "is_chasing": true,
    "match_type": ["T20", "IPL"]
  },
  "impact_score": 22,
  "confidence": 0.85,
  "description": "Virat Kohli averages significantly higher while chasing in T20s",
  "source": "Career chasing avg 54.2 vs setting avg 34.1 (Cricsheet 2016-2026 T20s)",
  "match_types": ["T20", "IPL"],
  "is_active": true
}
```

### 5.2 VENUE_RULES.json — Venue-Specific Intelligence

Rules about how a venue affects player or team performance.

Example:
```json
{
  "id": "RULE-0101",
  "rule_type": "venue",
  "player_key": null,
  "condition": {
    "venue": "Wankhede Stadium",
    "toss_decision": "field",
    "match_type": "T20"
  },
  "impact_score": 15,
  "confidence": 0.78,
  "description": "Batting second at Wankhede is significantly advantageous due to dew",
  "source": "Wankhede T20 chasing win rate: 68% (2019-2026, Cricsheet)",
  "is_active": true
}
```

### 5.3 MATCHUP_RULES.json — Batter vs Bowler Type

Rules about specific batter weaknesses or strengths against bowling types.

Example:
```json
{
  "id": "RULE-0201",
  "rule_type": "matchup",
  "player_key": "Rohit, RG",
  "condition": {
    "opposition_bowling_type": "pace_left",
    "pitch_type": "pace"
  },
  "impact_score": -18,
  "confidence": 0.82,
  "description": "Rohit Sharma has a notable weakness against left-arm pace on bouncy pitches",
  "source": "Dismissal rate vs left-arm pace: 0.042/ball vs 0.021/ball overall (Cricsheet)",
  "is_active": true
}
```

### 5.4 CONTEXT_RULES.json — Situational/Contextual Rules

Rules about match context independent of specific players.

Example:
```json
{
  "id": "RULE-0301",
  "rule_type": "context",
  "player_key": null,
  "condition": {
    "is_final_or_knockout": true,
    "batting_position": [1, 2, 3]
  },
  "impact_score": 12,
  "confidence": 0.70,
  "description": "Top-order batters generally score more in knockout matches due to increased match overs allocation",
  "source": "IPL Knockout batting analysis 2013-2026",
  "match_types": ["IPL", "T20"],
  "is_active": true
}
```

---

## 6. Rule Evaluation Algorithm

```python
def evaluate_rules(player: Player, match_context: MatchContext) -> float:
    """
    Returns total rules adjustment score for a player.
    """
    total_adjustment = 0.0
    fired_rules = []

    for rule in active_rules:
        if rule.player_key and rule.player_key != player.cricsheet_key:
            continue
        if rule.match_types and match_context.match_type not in rule.match_types:
            continue
        if not is_date_valid(rule):
            continue
        if evaluate_condition(rule.condition, player, match_context):
            effective_impact = rule.impact_score * rule.confidence
            total_adjustment += effective_impact
            fired_rules.append(rule.id)

    return total_adjustment, fired_rules
```

---

## 7. Rule Validation

Run before every commit:

```bash
python human_rules/validate_rules.py
```

Checks:
- Schema compliance for every rule
- No duplicate IDs
- `player_key` values exist in the player table
- `confidence` is in range [0.0, 1.0]
- `impact_score` is in range [-100, 100]
- `source` field is non-empty
- Condition keys are valid
- No circular dependencies

---

## 8. Adding New Rules — Checklist

- [ ] Assign next available RULE-XXXX ID
- [ ] Choose correct file: PLAYER, VENUE, MATCHUP, or CONTEXT
- [ ] Set confidence based on sample size (n < 20: max 0.6; n 20–50: max 0.75; n > 50: up to 1.0)
- [ ] Provide a real source (match IDs, statistics, expert reference)
- [ ] Write a clear description a non-technical person can understand
- [ ] Run `validate_rules.py`
- [ ] Backtest the change: `make backtest`
- [ ] Document in `RULE_SOURCES.md`
