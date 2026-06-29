# LLM Guardrails

Rules that constrain LLM outputs for safety, accuracy, and brand protection.

---

## Content Guardrails

### Never Do

| Rule | Reason |
|------|--------|
| Never recommend placing bets on cricket markets | Legal and ethical risk |
| Never claim 100% prediction accuracy | Factually false; damages trust |
| Never insult or demean players, teams, or countries | Brand safety |
| Never make up statistics not in the context | Hallucination risk |
| Never discuss player personal lives, injuries not in data | Privacy |
| Never provide advice outside the match context provided | Accuracy |
| Never encourage excessive gambling behaviour | Responsible gaming |

### Always Do

| Rule | Reason |
|------|--------|
| Always cite the data being used ("based on last 5 matches...") | Transparency |
| Always acknowledge uncertainty ("likely", "strong pick", not "will score") | Honesty |
| Always recommend consulting the live XI before locking teams | User safety |
| Always stay within the provided match context | Accuracy |

---

## Output Validation

After LLM generates a response, validate:

```python
def validate_llm_output(response: str, context: dict) -> bool:
    # No hallucinated numbers (check any number mentioned appears in context)
    # No prohibited phrases
    # Length within bounds (20–200 words)
    # Contains at least one specific data point
    ...
```

### Prohibited Phrases

```python
PROHIBITED_PHRASES = [
    "100% certain", "guaranteed", "definitely will",
    "place a bet", "I recommend betting",
    "insider information", "sure thing",
    "money-back guarantee",
]
```

---

## Rate Limiting and Abuse Prevention

- User messages containing offensive content → return polite refusal, do not pass to LLM
- Messages attempting prompt injection (`ignore previous instructions`) → return refusal
- Messages > 500 characters → truncate to 500 before sending to LLM

```python
INJECTION_PATTERNS = [
    r"ignore (previous|all|prior) instructions",
    r"you are now",
    r"new persona",
    r"system prompt",
    r"jailbreak",
]
```

---

## Token Budget

| Request Type | Max Input Tokens | Max Output Tokens |
|---|---|---|
| Player explanation | 800 | 150 |
| Captain explanation | 500 | 100 |
| Chat response | 2000 | 300 |

Exceeding budget: truncate context (remove older chat turns first; keep player data).
