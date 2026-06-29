# Explanation Generation Prompts

These prompts generate per-player selection explanations. Used by `llm/explainer.py`.

---

## Batter Explanation Prompt

```
You are a fantasy cricket expert writing a brief player analysis.
Generate a selection rationale for {player_name} in maximum 70 words.
Use ONLY the data below. Be specific with numbers. No fluff.

Role: Batter
Recent FP (last 3): {fp_avg_3:.1f} | Last 5: {fp_avg_5:.1f} | Last 10: {fp_avg_10:.1f}
FP Ceiling: {fp_ceiling:.1f} | FP Floor: {fp_floor:.1f}
Consistency: {consistency_label} (CV: {fp_consistency:.2f})
Venue runs average: {venue_avg_runs:.1f}
vs Pace SR: {matchup_sr_pace:.1f} | vs Spin SR: {matchup_sr_spin:.1f}
Is chasing: {is_chasing}
Rules fired: {rules_descriptions}
Confidence: {confidence}%

Format: Lead with strongest reason. End with confidence level (High/Medium/Low).
```

---

## Bowler Explanation Prompt

```
You are a fantasy cricket expert writing a brief player analysis.
Generate a selection rationale for {player_name} in maximum 70 words.
Use ONLY the data below. Be specific with numbers. No fluff.

Role: Bowler
Recent FP (last 3): {fp_avg_3:.1f} | Last 5: {fp_avg_5:.1f}
FP Ceiling: {fp_ceiling:.1f}
Wickets per match (last 5): {avg_wickets_5:.2f}
Economy (last 5): {avg_economy_5:.2f}
Venue wickets average: {venue_avg_wickets:.2f}
Venue pitch type: {pitch_type}
Opposition batting strength: {batting_strength_label}
Rules fired: {rules_descriptions}
Confidence: {confidence}%

Format: Lead with strongest reason. End with confidence level (High/Medium/Low).
```

---

## All-Rounder Explanation Prompt

```
You are a fantasy cricket expert writing a brief player analysis.
Generate a selection rationale for {player_name} in maximum 80 words.
Use ONLY the data below. Highlight their dual-contribution value.

Role: All-rounder
Recent FP (last 5): {fp_avg_5:.1f} | Ceiling: {fp_ceiling:.1f}
Batting avg (last 5): {avg_runs_5:.1f} runs | SR: {avg_sr_5:.1f}
Wickets (last 5): {avg_wickets_5:.2f} | Economy: {avg_economy_5:.2f}
Primary contribution: {primary_contribution}
Rules fired: {rules_descriptions}
Confidence: {confidence}%

Format: Mention both batting and bowling value. End with confidence.
```

---

## Wicketkeeper Explanation Prompt

```
You are a fantasy cricket expert writing a brief player analysis.
Generate a selection rationale for {player_name} (Wicketkeeper) in maximum 70 words.
Use ONLY the data below.

Recent FP (last 5): {fp_avg_5:.1f} | Ceiling: {fp_ceiling:.1f}
Batting avg (last 5): {avg_runs_5:.1f} | Batting order: {batting_position_label}
Stumpings + catches per match (last 5): {fielding_contribution:.2f}
Venue batting average: {venue_avg_runs:.1f}
Rules fired: {rules_descriptions}
Confidence: {confidence}%

Format: Lead with batting or keeping strength, whichever is higher contribution.
```

---

## Captain Explanation Prompt

```
In maximum 50 words, explain why {player_name} is the {captain_type} captain pick for this match.
Use ONLY this data:

Ceiling: {fp_ceiling:.1f} | Recent form: {fp_avg_5:.1f} avg (last 5)
Key advantage: {top_reason}
Ownership estimate: {ownership_estimate}
Confidence: {confidence}%

Be direct. One clear reason why they're the captain pick.
```

---

## Fallback Template (LLM Unavailable)

When LLM API is down, use this template:

```python
FALLBACK = (
    "{name} selected for {form_label} recent form "
    "({fp_avg_5:.1f} avg FP, last 5 {match_type} matches), "
    "{venue_label} venue record"
    "{rules_suffix}. "
    "Confidence: {confidence_label}."
)

# rules_suffix = ", and {n} specialist rules firing" if rules_fired else ""
```
