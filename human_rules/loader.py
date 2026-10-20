"""
Human Rules Loader: JSON rule files (curated) + database rules (created by admins).

DB rules override JSON rules with the same id.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

RULE_FILES = [
    "PLAYER_RULES.json",
    "VENUE_RULES.json",
    "MATCHUP_RULES.json",
    "CONTEXT_RULES.json",
]
RULES_DIR = Path(__file__).resolve().parent

_FILE_RULES: Dict[str, dict] = {}
_DB_RULES: Dict[str, dict] = {}
_RULES: Dict[str, dict] = {}


def _rebuild() -> None:
    global _RULES
    _RULES = {**_FILE_RULES, **_DB_RULES}
    _RULES = {k: v for k, v in _RULES.items() if v.get("is_active", True)}


def load_file_rules(rules_dir: Path | str = RULES_DIR) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    base = Path(rules_dir)
    for filename in RULE_FILES:
        path = base / filename
        if not path.exists():
            logger.warning("Rule file not found: %s", path)
            continue
        try:
            rules: List[dict] = json.loads(path.read_text(encoding="utf-8"))
            for rule in rules:
                if rule.get("id"):
                    out[rule["id"]] = {**rule, "origin": "file"}
        except Exception as e:
            logger.error("Failed to load %s: %s", filename, e)
    return out


def load_all_rules(rules_dir: Path | str = RULES_DIR) -> Dict[str, dict]:
    """Load all rule JSON files into the in-memory registry."""
    global _FILE_RULES
    _FILE_RULES = load_file_rules(rules_dir)
    _rebuild()
    logger.info("Human rules loaded: %d active (%d file, %d db)", len(_RULES), len(_FILE_RULES), len(_DB_RULES))
    return _RULES


def set_db_rules(rules: List[dict]) -> None:
    """Replace the DB-sourced portion of the registry (called at startup / after admin edits)."""
    global _DB_RULES
    _DB_RULES = {r["id"]: {**r, "origin": "db"} for r in rules if r.get("id")}
    _rebuild()


def get_all_rules() -> Dict[str, dict]:
    if not _RULES and not _FILE_RULES:
        load_all_rules()
    return _RULES


def get_rule(rule_id: str) -> dict | None:
    return get_all_rules().get(rule_id)


def all_rules_including_inactive() -> Dict[str, dict]:
    if not _FILE_RULES:
        load_all_rules()
    return {**_FILE_RULES, **_DB_RULES}
