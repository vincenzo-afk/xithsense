"""
Validate all human-intelligence rule files (HUMAN_RULES_SPEC / RULE_SCHEMA.json).

Checks: required fields & types, id format, duplicate ids, impact/confidence ranges,
known condition keys, non-empty source. Exit code 1 on any error.
Usage: python -m human_rules.validate_rules
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from human_rules.loader import RULE_FILES, RULES_DIR

KNOWN_KEYS = {
    "match_type", "venue", "pitch_type", "is_chasing", "toss_decision", "opposition_bowling_type", "phase",
    "batting_position", "is_final_or_knockout", "home_match", "is_home", "rest_days", "batting_style",
    "primary_role", "bowling_style_contains",
}
RULE_TYPES = {"player", "venue", "matchup", "context"}


def validate(rules_dir: Path = RULES_DIR) -> list[str]:
    errors: list[str] = []
    seen: dict[str, str] = {}
    for fname in RULE_FILES:
        path = rules_dir / fname
        try:
            rules = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{fname}: cannot parse ({e})")
            continue
        for i, r in enumerate(rules):
            where = f"{fname}[{i}] {r.get('id', '?')}"
            rid = r.get("id", "")
            if not re.fullmatch(r"RULE-\d{4}", rid):
                errors.append(f"{where}: id must match RULE-NNNN")
            if rid in seen:
                errors.append(f"{where}: duplicate id (also in {seen[rid]})")
            seen[rid] = fname
            if r.get("rule_type") not in RULE_TYPES:
                errors.append(f"{where}: rule_type must be one of {sorted(RULE_TYPES)}")
            cond = r.get("condition")
            if not isinstance(cond, dict) or not cond:
                errors.append(f"{where}: condition must be a non-empty object")
            else:
                for k in set(cond) - KNOWN_KEYS:
                    errors.append(f"{where}: unknown condition key '{k}'")
            imp = r.get("impact_score")
            if not isinstance(imp, int) or not -100 <= imp <= 100:
                errors.append(f"{where}: impact_score must be an int in [-100, 100]")
            conf = r.get("confidence")
            if not isinstance(conf, (int, float)) or not 0 <= conf <= 1:
                errors.append(f"{where}: confidence must be in [0, 1]")
            if len(str(r.get("source") or "")) < 5:
                errors.append(f"{where}: source must be at least 5 characters")
            if r["rule_type"] == "player" and not r.get("player_key"):
                errors.append(f"{where}: player rules need a player_key")
    return errors


if __name__ == "__main__":
    errs = validate()
    total = sum(len(json.loads((RULES_DIR / f).read_text(encoding="utf-8"))) for f in RULE_FILES)
    if errs:
        print("\n".join(errs))
        print(f"\n✗ {len(errs)} problem(s) across {total} rules")
        sys.exit(1)
    print(f"✓ {total} rules valid")
