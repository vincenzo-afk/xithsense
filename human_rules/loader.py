"""
Human Rules Loader: reads all rule JSON files from human_rules/ at startup.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

_RULE_FILES = [
    "PLAYER_RULES.json",
    "VENUE_RULES.json",
    "MATCHUP_RULES.json",
    "CONTEXT_RULES.json",
]

# Global registry: rule_id → rule dict
_RULES: Dict[str, dict] = {}


def load_all_rules(rules_dir: str = "human_rules") -> Dict[str, dict]:
    """Load all rule JSON files into the in-memory registry."""
    global _RULES
    _RULES = {}
    base = Path(rules_dir)

    for filename in _RULE_FILES:
        path = base / filename
        if not path.exists():
            logger.warning(f"Rule file not found: {path}")
            continue
        try:
            with path.open("r", encoding="utf-8") as f:
                rules: List[dict] = json.load(f)
            for rule in rules:
                rule_id = rule.get("id")
                if rule_id and rule.get("is_active", True):
                    _RULES[rule_id] = rule
            logger.info(f"Loaded {len(rules)} rules from {filename}")
        except Exception as e:
            logger.error(f"Failed to load {filename}: {e}")

    logger.info(f"Total active rules loaded: {len(_RULES)}")
    return _RULES


def get_all_rules() -> Dict[str, dict]:
    if not _RULES:
        load_all_rules()
    return _RULES


def get_rule(rule_id: str) -> dict | None:
    return get_all_rules().get(rule_id)
