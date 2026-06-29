# Explainability Engine Specification

**Module:** `llm/`  
**Entry:** `llm/explainer.py`

## Purpose

Convert structured player prediction data (scores, features, rules) into plain-English explanations that users can read and act on.

## Explanation Structure

Every explanation must contain:
1. Opening sentence: player name + overall recommendation strength
2. Recent form summary (last 3–5 match FP average)
3. Venue context (player average at this ground)
4. Matchup assessment (vs expected bowling attack)
5. Situational factor (toss/chasing/pitch)
6. Confidence statement

## Prompt Template

```python
EXPLANATION_SYSTEM_PROMPT = """
You are an expert fantasy cricket analyst for the XithSense platform.
Generate a concise, data-driven player selection explanation.
- Use plain English. Maximum 80 words.
- Lead with the strongest reason.
- Reference specific numbers from the data provided.
- End with confidence level: High / Medium / Low.
- Never mention model names or ML terms.
- Never make claims not supported by the data provided.
"""

def build_explanation_prompt(player_data: dict) -> str:
    return f"""
Player: {player_data['full_name']}
Role: {player_data['primary_role']}
Recent FP (last 5): {player_data['fp_avg_5']:.1f}
Recent FP (last 3): {player_data['fp_avg_3']:.1f}
FP Ceiling: {player_data['fp_ceiling']:.1f}
Venue average runs: {player_data.get('venue_avg_runs', 'N/A')}
vs Pace SR: {player_data.get('matchup_sr_vs_pace_right', 'N/A')}
vs Spin SR: {player_data.get('matchup_sr_vs_spin_left', 'N/A')}
Is chasing: {player_data.get('is_chasing', False)}
Rules fired: {player_data.get('rules_fired_descriptions', [])}
Ensemble confidence: {player_data['confidence']}%

Generate explanation:
"""
```

## Caching

- Key: `explain:{match_id}:{player_id}:{match_phase}`
- TTL: 3600 seconds (1 hour)
- Cache invalidated when match_phase changes (pre_toss → post_toss)

## Fallback Template

When LLM is unavailable:

```python
FALLBACK_TEMPLATE = (
    "{name} selected based on {form_label} recent form "
    "({fp_avg_5:.1f} avg FP last 5 matches), "
    "{venue_label} venue record, and {confidence}% confidence."
)
```
