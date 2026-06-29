# Backup and Recovery

## Backup Schedule

| Data | Method | Frequency | Retention |
|------|--------|-----------|-----------|
| PostgreSQL (Supabase) | Supabase managed backups | Daily | 30 days |
| PostgreSQL point-in-time | Supabase WAL | Continuous | 7 days |
| Redis | AOF persistence | Continuous | N/A (cache is re-buildable) |
| Model artifacts | Copy to S3 / Railway volume | After each training run | 5 versions |
| Cricsheet raw data | Already in `data/raw/` | On ingest | Permanent |
| Human rules JSON | Git repository | On every commit | Git history |

## Recovery Procedures

### Database Corruption / Data Loss

```bash
# 1. Restore from Supabase backup (via Supabase dashboard)
# 2. Or point-in-time recovery to specific timestamp
# 3. Re-run feature pipeline for any matches after restore point
python scripts/build_features.py --from {restore_date}
```

### Model Artifact Loss

```bash
# Restore from S3
aws s3 cp s3://xithsense-artifacts/models/ models/artifacts/ --recursive

# Or retrain from scratch (takes ~90 min)
python training/train_ensemble.py
```

### Redis Cache Loss

Redis cache is fully re-buildable. After Redis restart:
```bash
# Warm the cache for upcoming matches
python scripts/warm_cache.py --hours-ahead 12
```

### Complete Service Outage

```bash
# 1. Verify database is accessible
# 2. Start fresh Docker environment
docker compose down && docker compose up -d

# 3. Verify health
curl https://api.xithsense.com/health

# 4. Check Celery workers
docker compose logs worker
```

## Recovery Time Objectives

| Scenario | RTO | RPO |
|----------|-----|-----|
| API pod restart | < 30 seconds | 0 |
| Redis failure | < 2 minutes | 0 (cache re-warmed) |
| Database restore from backup | < 2 hours | 24 hours (daily backup) |
| Full infrastructure rebuild | < 4 hours | 24 hours |

## Disaster Recovery Drill

Run quarterly:
1. Simulate database restore from 3-day-old backup
2. Rebuild features from restored data
3. Verify prediction quality matches pre-disaster metrics
4. Document RTO achieved vs target
