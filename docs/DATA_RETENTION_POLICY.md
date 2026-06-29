# Data Retention Policy

---

## Retention Schedule

| Data Category | Table(s) | Retention | Deletion Method |
|---|---|---|---|
| Ball-by-ball match data | `match`, `innings`, `delivery` | Permanent | Never deleted |
| Player profiles | `player` | Permanent | Never deleted |
| Player match performances | `player_match_performance` | Permanent | Never deleted |
| Rolling features | `rolling_feature` | 2 years of history | Delete entries older than 2 years on monthly job |
| Venue stats | `venue_stat` | Permanent | Never deleted |
| Matchup stats | `matchup_stat` | Permanent | Never deleted |
| User accounts | `user` | Until account deletion + 30 days | Soft-delete then hard-delete |
| Subscriptions | `subscription` | 7 years (tax compliance) | Anonymise after 7 years |
| Payment records | (Razorpay records) | 7 years | Razorpay handles; reference IDs kept |
| Predictions | `prediction`, `predicted_player`, `recommended_team` | 90 days | Batch delete monthly |
| Chat sessions | `chat_session`, `chat_message` | 30 days | Delete on session expiry |
| Notifications | `notification` | 30 days | Batch delete monthly |
| Audit log | `admin_action` | Permanent (archive after 1 year) | Archive to S3 yearly |
| Backtest runs | `backtest_run`, `backtest_result` | 1 year | Delete on annual job |
| Model artifacts | `models/artifacts/` | 3 most recent versions per model | Delete older on new version |
| Log files | stdout / drain | 30 days (Railway) | Automatic |
| Redis cache | All keys | Per-TTL (5 min – 24h) | Automatic expiry |

---

## User Data Deletion (DPDP Act Compliance)

When a user requests account deletion:

```python
async def delete_user_account(user_id: UUID) -> None:
    # 1. Soft delete: mark inactive, clear PII immediately
    await db.execute("""
        UPDATE "user" SET
            is_active = false,
            email = 'deleted-' || id || '@xithsense.deleted',
            full_name = 'Deleted User',
            phone = NULL,
            password_hash = NULL,
            google_id = NULL,
            deleted_at = NOW()
        WHERE id = :id
    """, {"id": user_id})

    # 2. Cancel active subscriptions (via Razorpay API)
    await cancel_razorpay_subscription(user_id)

    # 3. Delete personal content
    await db.execute("DELETE FROM chat_session WHERE user_id = :id", {"id": user_id})
    await db.execute("DELETE FROM notification WHERE user_id = :id", {"id": user_id})
    # Predictions kept for model training (anonymised — user_id = NULL)
    await db.execute("UPDATE prediction SET user_id = NULL WHERE user_id = :id", {"id": user_id})

    # 4. Revoke all tokens
    await revoke_all_user_tokens(user_id)

    # 5. Hard delete after 30-day grace period (scheduled job)
    await schedule_hard_delete(user_id, delay_days=30)
```

---

## Archival Rules

**Rolling feature cleanup (monthly job):**
```sql
DELETE FROM rolling_feature
WHERE as_of_date < NOW() - INTERVAL '2 years'
  AND player_id NOT IN (
    SELECT DISTINCT player_id FROM player_team_match
    WHERE match_id IN (
      SELECT id FROM match WHERE match_date > NOW() - INTERVAL '6 months'
    )
  );
```

**Prediction cleanup (monthly job):**
```sql
DELETE FROM prediction WHERE generated_at < NOW() - INTERVAL '90 days';
-- CASCADE deletes predicted_player, recommended_team, team_player
```

**Audit log archival (annual job):**
```bash
# Export to S3 before deletion
python scripts/archive_audit_log.py --year 2025 \
  --output s3://xithsense-audit/admin_action_2025.csv
```

---

## Data Residency

All data is stored in Supabase (primary region: `ap-south-1` — Mumbai).  
Backups replicated to `ap-southeast-1` (Singapore).  
No user data stored outside India or Singapore.

---

## Legal Basis for Retention

| Data | Legal Basis | Duration |
|------|------------|---------|
| User PII | Contract (service agreement) | Duration of account |
| Payment records | Legal obligation (GST/income tax) | 7 years |
| Match data | Legitimate interest (product improvement) | Permanent |
| Audit logs | Legal obligation (compliance) | Permanent |
