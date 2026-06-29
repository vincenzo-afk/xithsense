# Prompt Engineering Guide

**Module:** `llm/`  
**Versioning:** Prompts are versioned by git commit; major changes logged in EXPERIMENT_TRACKING.md

---

## Prompt Design Principles

1. **Ground every claim in data.** Include actual numbers in the context; instruct the LLM to use them.
2. **Define the output format explicitly.** Tell the LLM exactly what to produce (max words, structure).
3. **Use positive instructions.** "Generate a 70-word explanation" beats "Don't write too much."
4. **Separate system from user context.** System prompt defines persona and rules; context provides data.
5. **Test for hallucination.** After generating, verify any number in the output appears in the context.

---

## Prompt Versioning

Every prompt has a version string. Changes to prompts require:
1. New version in the prompt file header
2. A/B test on 20+ explanations before switching production
3. Entry in `EXPERIMENT_TRACKING.md`

```python
# llm/prompts/explanation.py
EXPLANATION_SYSTEM_PROMPT_V2 = """..."""
EXPLANATION_SYSTEM_PROMPT_VERSION = "v2.0"
```

---

## System Prompt Design

The system prompt is sent as the `system` parameter in every API call. It defines:
- Persona and expertise
- Rules the LLM must follow
- What data the LLM has access to
- Output format constraints
- What the LLM must not do

```python
SYSTEM_PROMPT = """
You are XithSense, an expert fantasy cricket analyst trusted by serious players.

## Your Role
Generate data-driven, concise player explanations and answer fantasy cricket questions.

## Rules
1. Use ONLY numbers from the data provided. Never invent statistics.
2. Maximum 80 words per player explanation. 120 for captain picks.
3. Lead with the single strongest selection reason.
4. End every explanation with: "Confidence: High/Medium/Low."
5. Never mention ML models, algorithms, or technical terms.
6. If data is missing for a factor, skip that factor entirely.
7. Never guarantee outcomes. Use "strong pick," "high probability," not "will score."

## Your Knowledge
You have access to player rolling form, venue averages, matchup data, and specialist rules.
"""
```

---

## Context Injection Pattern

Context is injected as a structured block before the user's question:

```python
def build_context_block(match: Match, players: list[PredictedPlayer]) -> str:
    context = f"""
[MATCH CONTEXT]
{match.team_a} vs {match.team_b}
Venue: {match.venue_name} | Format: {match.match_type}
Toss: {match.toss_winner} elected to {match.toss_decision}
Date: {match.match_date}

[TOP PREDICTED PLAYERS — post toss]
"""
    for p in sorted(players, key=lambda x: x.ensemble_score, reverse=True)[:15]:
        context += f"""
{p.full_name} ({p.primary_role}) | {p.team}
  FP predicted: {p.fp_predicted:.0f} | Ceiling: {p.fp_ceiling:.0f} | Floor: {p.fp_floor:.0f}
  Last 5 avg: {p.fp_avg_5:.1f} | Last 3 avg: {p.fp_avg_3:.1f} | Consistency: {'High' if p.fp_consistency < 0.4 else 'Medium' if p.fp_consistency < 0.7 else 'Low'}
  Confidence: {p.confidence}%
  Rules: {', '.join(p.rules_descriptions) or 'None'}
"""
    return context
```

---

## Prompt Templates

### Player Explanation (Role-Specific)

```python
BATTER_EXPLANATION_PROMPT = """
Data for {player_name} (Batter):
- Last 3 T20 FP: {fp_avg_3:.1f} | Last 5: {fp_avg_5:.1f} | Last 10: {fp_avg_10:.1f}
- FP Ceiling: {fp_ceiling:.1f} | Floor: {fp_floor:.1f}
- SR (last 5): {avg_sr_5:.1f} | Avg runs: {avg_runs_5:.1f}
- Venue runs avg: {venue_avg_runs:.1f}
- vs Pace SR: {matchup_sr_pace:.0f} | vs Spin SR: {matchup_sr_spin:.0f}
- Chasing today: {is_chasing_label}
- Rules triggered: {rules_descriptions}

Write a 70-word selection rationale. Lead with the strongest number. End with Confidence: {confidence_label}.
"""
```

### Chat Intent Classification

```python
INTENT_PROMPT = """
Classify this fantasy cricket question into ONE of:
TEAM_PICK | CAPTAIN_PICK | DIFFERENTIAL | PLAYER_EXPLAIN | MATCHUP_QUERY | VENUE_QUERY | GENERAL_STRATEGY | OUT_OF_SCOPE

Question: "{message}"

Reply with ONLY the intent name. Nothing else.
"""
```

---

## Anti-Hallucination Controls

```python
def validate_explanation_numbers(explanation: str, context: dict) -> bool:
    """
    Check that any number mentioned in explanation appears in context.
    Returns False if hallucinated number detected.
    """
    import re
    numbers_in_explanation = re.findall(r'\b\d+\.?\d*\b', explanation)
    context_values = set()
    for v in context.values():
        if isinstance(v, (int, float)):
            context_values.add(str(round(v, 1)))
            context_values.add(str(int(v)))

    for num in numbers_in_explanation:
        if num not in context_values and float(num) not in [0, 1, 2, 3, 4, 5, 6, 10, 11, 50, 100]:
            log.warning("possible_hallucination", number=num, explanation=explanation[:100])
            return False
    return True
```

---

## Prompt A/B Testing Protocol

When changing a prompt:

1. Deploy new prompt to staging with feature flag `USE_NEW_PROMPT=true`
2. Generate 50 explanations with old and new prompt for the same 50 player/match combinations
3. Human evaluation on 3 dimensions: Accuracy (1-5), Clarity (1-5), Helpfulness (1-5)
4. If new prompt scores ≥ old on all 3 dimensions with p < 0.05 → promote
5. Log results in `EXPERIMENT_TRACKING.md` under "Prompt Experiments" section

---

## Token Budget Management

| Prompt Type | Input Budget | Output Budget | Strategy if Exceeded |
|---|---|---|---|
| Player explanation | 600 tokens | 150 tokens | Truncate older chat history |
| Captain pick | 400 tokens | 100 tokens | Remove lower-ranked players from context |
| Chat response | 2,000 tokens | 300 tokens | Summarise older turns; keep last 4 |
| Batch explanations | 4,000 tokens | 1,200 tokens | Split into 2 API calls |
