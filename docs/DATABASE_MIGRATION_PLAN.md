# Database Migration Plan

**Tool:** Alembic 1.13 · **DB:** Supabase PostgreSQL 15 · **Convention:** sequential IDs, always reversible

---

## Migration Philosophy

1. **Schema first, data second.** Schema migrations and data migrations are separate scripts.
2. **Never break existing queries.** Add columns as nullable; backfill; then add NOT NULL constraint.
3. **One concern per migration.** A migration adds one table, one column, or one index — not all three.
4. **Always test downgrade.** Every `upgrade()` must have a working `downgrade()`.

---

## Safe Column Addition Pattern

```python
# WRONG — breaks immediately if rows exist
def upgrade():
    op.add_column("player", sa.Column("debut_year", sa.Integer(), nullable=False))

# CORRECT — nullable first, backfill, then constrain
def upgrade():
    # Step 1: add nullable
    op.add_column("player", sa.Column("debut_year", sa.Integer(), nullable=True))
    # Step 2: backfill via data migration script (separate PR)
    # Step 3: (next migration) add NOT NULL once backfill is confirmed
```

---

## Large Table Index Pattern (No Locking)

```python
def upgrade():
    op.execute("SET statement_timeout = '0'")
    op.create_index(
        "idx_delivery_batter_new",
        "delivery", ["batter"],
        postgresql_concurrently=True    # Non-blocking on PostgreSQL
    )

def downgrade():
    op.drop_index("idx_delivery_batter_new", table_name="delivery",
                  postgresql_concurrently=True)
```

---

## Schema Evolution Rules

| Change | Safe? | Method |
|--------|-------|--------|
| Add nullable column | ✅ Yes | Direct `add_column` |
| Add NOT NULL column | ⚠️ Careful | Add nullable → backfill → add constraint |
| Rename column | ❌ Breaking | Add new column → migrate data → deprecate old |
| Drop column | ❌ Breaking | Deprecate in code first → remove after 1 release |
| Add table | ✅ Yes | Direct `create_table` |
| Drop table | ❌ Breaking | Remove all code references first |
| Add index | ✅ Yes | Use `postgresql_concurrently=True` |
| Change column type | ⚠️ Careful | Add new column → migrate → swap |
| Add FK constraint | ⚠️ Careful | Ensure referential integrity first |

---

## Rollback Procedure

```bash
# Check current migration state
alembic current

# Roll back one step
alembic downgrade -1

# Roll back to specific revision
alembic downgrade 0008

# Emergency: roll back all
alembic downgrade base
```

**After rollback in production:**
1. Verify `alembic current` shows correct revision
2. Verify API `/health` returns `ok`
3. Run smoke tests
4. Notify team via Slack

---

## Migration Checklist

Before merging any migration PR:
- [ ] `alembic upgrade head` runs clean on fresh test DB
- [ ] `alembic downgrade -1` runs clean
- [ ] No raw SQL strings (use SQLAlchemy operations)
- [ ] Large table indexes use `postgresql_concurrently=True`
- [ ] New NOT NULL columns have a default or backfill strategy
- [ ] Migration tested against copy of production data (if schema-breaking)
- [ ] Documentation updated: `docs/DATABASE_SCHEMA.md`, `docs/TABLE_COLUMN_DEFINITIONS.md`

---

## Pending Migrations Queue

| Priority | Migration | Reason |
|----------|-----------|--------|
| P1 | `0013_add_player_credits` | Dream11 credits per player per season |
| P1 | `0014_add_super_over_flag` | Tag super overs in innings |
| P2 | `0015_add_live_match_state` | WebSocket state persistence |
| P2 | `0016_add_ownership_estimate` | Store crowd-sourced ownership % |
| P3 | `0017_add_user_saved_team` | Allow users to save their own teams |
