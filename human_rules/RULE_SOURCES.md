# Rule Sources

All human intelligence rules must cite a verifiable source. This file catalogues sources used.

## Source Types

| Type | Code | Description |
|------|------|-------------|
| Cricsheet statistical analysis | `CS-YYYY` | Computed from Cricsheet ball-by-ball data |
| Expert analyst note | `EX-YYYY` | Published analysis by recognised cricket analysts |
| Match observation | `MO-YYYY` | Specific match-based observation |

## Source Register

| Source ID | Rule IDs | Description |
|-----------|----------|-------------|
| CS-2026-001 | RULE-0001 | Kohli T20 chasing avg vs setting avg, 2016–2026 |
| CS-2026-002 | RULE-0002 | Rohit vs left-arm pace dismissal rate analysis |
| CS-2026-003 | RULE-0003 | Russell FP on batting vs bowling pitches |
| CS-2026-004 | RULE-0101 | Wankhede chasing win rate T20 2019–2026 |
| CS-2026-005 | RULE-0102 | Chepauk spin wicket percentage |
| CS-2026-006 | RULE-0201 | LHB vs left-arm orthodox dismissal rate |

## Adding New Sources

When adding a rule referencing a statistical source:
1. Run the analysis query against the `delivery` and `player_match_performance` tables
2. Verify with at least 30 sample matches
3. Add the source here with the query used
4. Reference the source ID in the rule's `source` field
