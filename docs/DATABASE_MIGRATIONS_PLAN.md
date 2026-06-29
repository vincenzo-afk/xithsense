# Database Migrations Plan

**Tool:** Alembic 1.13  
**Location:** `alembic/versions/`  
**Convention:** One migration per logical change. Always include `upgrade()` and `downgrade()`.

---

## Migration History

| Migration ID | Description | Depends On | Status |
|-------------|-------------|-----------|--------|
| `0001_initial_schema` | Create all base tables | — | Applied |
| `0002_add_venue_stats` | Add `venue_stat` table | 0001 | Applied |
| `0003_add_rolling_features` | Add `rolling_feature` table | 0001 | Applied |
| `0004_add_human_rules` | Add `human_rule` and `rule_trigger` tables | 0001 | Applied |
| `0005_add_predictions` | Add `prediction`, `predicted_player`, `recommended_team`, `team_player` | 0001 | Applied |
| `0006_add_subscriptions` | Add `subscription` table, add `role` to `user` | 0001 | Applied |
| `0007_add_notifications` | Add `notification` table | 0001 | Applied |
| `0008_add_chat` | Add `chat_session` and `chat_message` tables | 0001 | Applied |
| `0009_add_backtest` | Add `backtest_run` and `backtest_result` tables | 0005 | Applied |
| `0010_add_model_version` | Add `model_version` table | 0001 | Applied |
| `0011_add_admin_action` | Add `admin_action` table | 0001 | Applied |
| `0012_add_indexes` | Add performance indexes on hot query paths | 0001–0011 | Applied |

---

## Migration Template

```python
# alembic/versions/0013_example.py
"""Add example column

Revision ID: 0013
Revises: 0012
Create Date: 2026-06-25
"""
from alembic import op
import sqlalchemy as sa

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column(
        "player",
        sa.Column("debut_year", sa.Integer(), nullable=True)
    )

def downgrade() -> None:
    op.drop_column("player", "debut_year")
```

---

## Migration Rules

1. **Never edit** an already-applied migration file.
2. **Always test** `alembic downgrade -1` after writing `upgrade()`.
3. **No data migrations in schema migrations.** Use a separate data migration script.
4. **Batch operations** for large tables: use `op.batch_alter_table` on SQLite, direct `op.alter_column` on PostgreSQL.
5. **Index creation:** use `op.create_index` with `postgresql_concurrently=True` on large tables to avoid locking.

```python
# Non-locking index creation for large tables
op.create_index(
    "idx_delivery_batter",
    "delivery",
    ["batter"],
    postgresql_concurrently=True
)
```

---

## Pending Migrations (Planned)

| ID | Description | Target Date |
|----|-------------|------------|
| `0013_add_player_credits` | Add `credits` column to `player` for Dream11 credit tracking | Phase 2 |
| `0014_add_ownership_estimates` | Add `ownership_estimate` table for crowd-sourced ownership data | Phase 2 |
| `0015_add_live_match` | Add `live_match_state` table for WebSocket state | Phase 2 |
| `0016_add_user_team` | Add `user_saved_team` for user to save their own teams | Phase 2 |

---

## Running Migrations

```bash
# Apply all pending
make migrate

# Apply up to specific revision
alembic upgrade 0008

# Check current revision
alembic current

# Show migration history
alembic history --verbose

# Downgrade one step
make migrate-down

# Generate new migration from model changes
make migrate-create MSG="add debut_year to player"
```
