# Chat Assistant Prompts

Prompts used by `llm/chat_assistant.py` for the conversational AI assistant.

---

## Intent Classification Prompt

Used to route user messages to the correct handler before building full context.

```
Classify the user's fantasy cricket question into exactly one of these intents:
- TEAM_PICK: asking which players to pick
- CAPTAIN_PICK: asking about captain or vice-captain
- DIFFERENTIAL: asking about low-ownership or risky picks
- PLAYER_EXPLAIN: asking why a specific player was or was not selected
- MATCHUP_QUERY: asking about player vs bowler type performance
- VENUE_QUERY: asking about venue conditions or history
- GENERAL_STRATEGY: general fantasy strategy question
- OUT_OF_SCOPE: not related to fantasy cricket for this match

User message: "{message}"
Reply with ONLY the intent name. Nothing else.
```

---

## Canonical Responses

### Why not [Player]?

```
Context: {match_context}
User asks: Why not pick {player_name}?

Player data:
- Predicted FP: {fp_predicted:.1f} | Rank: {rank} of {total_players}
- Recent form: {fp_avg_5:.1f} avg (last 5) — {form_label}
- Ceiling: {fp_ceiling:.1f}
- Concern: {top_concern}
- Rules that penalised: {penalty_rules}

Explain in 60 words why this player was ranked lower. Be honest and specific.
If the player IS a good pick but just missed the cut, say so clearly.
```

### Give me differential picks

```
Context: {match_context}

These are the top differential candidates (low ownership, high ceiling):
{differential_list}

In 80 words, recommend 2–3 differential picks for grand leagues.
Explain what makes each one a differential (low ownership + high upside).
Format: bullet points, one per player.
```

### Who is the best captain?

```
Context: {match_context}

Captain candidates:
{captain_candidates_list}

In 60 words, recommend the best captain.
Give ONE clear primary reason backed by the data.
If safe vs risky differs, mention both options briefly.
```

---

## Multi-Turn Context Handling

Chat history is maintained in the session. Inject previous turns as:

```
[CONVERSATION HISTORY]
User: {prev_message_1}
Assistant: {prev_response_1}
User: {prev_message_2}
Assistant: {prev_response_2}

[CURRENT QUESTION]
User: {current_message}
```

Keep last 6 turns maximum to stay within token budget.

---

## Out-of-Scope Response Template

```
"I can only help with fantasy cricket decisions for matches on XithSense. 
For {topic}, I'd suggest checking a cricket news site. 
Is there anything about your team selection I can help with?"
```
