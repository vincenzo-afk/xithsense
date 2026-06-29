# Disaster Recovery Plan

---

## RTO and RPO Targets

| Scenario | RTO (Recovery Time Objective) | RPO (Recovery Point Objective) |
|----------|-------------------------------|-------------------------------|
| API pod crash | < 30 seconds | 0 (stateless) |
| Redis failure | < 2 minutes | 0 (cache rebuilds) |
| Single DB connection failure | < 1 minute | 0 |
| Full Supabase region outage | < 2 hours | 24 hours (daily backup) |
| Model artifact corruption | < 2 hours (restore) or 4 hours (retrain) | Last training run |
| Full infrastructure rebuild | < 4 hours | 24 hours |
| Data centre total loss | < 8 hours | 24 hours |

---

## Disaster Scenarios and Recovery Steps

### Scenario 1: API Container Crash

```
Impact: API unavailable
Detection: UptimeRobot alert; Sentry uptime alert

Steps:
1. Docker auto-restarts container (restart: unless-stopped)
   → Usually resolves in 15–30 seconds; no action needed

2. If auto-restart fails (3 attempts):
   On-call engineer receives PagerDuty alert

3. Manual intervention:
   docker compose logs api --tail=100     # identify cause
   docker compose restart api             # restart
   curl https://api.xithsense.com/health  # verify

4. If container fails repeatedly:
   Check host disk space: df -h
   Check host memory: free -h
   Check for OOM: dmesg | grep -i "out of memory"
   Scale to second instance
```

### Scenario 2: PostgreSQL Data Loss

```
Impact: Predictions unavailable; data integrity risk
Detection: DB health check fails; application errors

Steps:
1. Assess damage scope
   - Which tables affected?
   - What was the last successful backup timestamp?

2. Notify team and post status update

3. Restore from Supabase backup:
   - Supabase dashboard → Settings → Database → Backups
   - Choose point-in-time recovery timestamp
   - Estimated restore time: 30–60 minutes

4. Post-restore verification:
   alembic current                    # verify migration state
   python scripts/run_quality_checks.py  # verify data integrity
   make test-integration              # run integration tests

5. Re-run feature pipeline for any matches after restore point:
   python scripts/build_features.py --from {restore_date}

6. Verify predictions for upcoming matches:
   curl /api/v1/predict/team -d '{"match_id": "...", "mode": "safe"}'
```

### Scenario 3: Model Artifacts Lost

```
Impact: ML predictions unavailable; form-only fallback active
Detection: ModelNotFoundError in logs; Sentry alert

Steps:
1. Immediate: form-only fallback activates automatically
   (ensemble: ML 0%, Rules 50%, Form 40%, Live 10%)
   Users continue to get predictions with lower accuracy

2. Attempt S3 restore:
   aws s3 ls s3://xithsense-models/                        # list available
   aws s3 cp s3://xithsense-models/ models/artifacts/ --recursive

3. Verify restored model:
   python training/verify_model.py --model-dir models/artifacts/

4. If S3 restore fails → emergency retrain:
   python training/train_ensemble.py --format T20 --fast-mode
   # fast-mode: last 2 years only, fewer estimators; ~90 minutes

5. Once model restored: verify predictions improve over form-only baseline
```

### Scenario 4: Complete Railway/Render Outage

```
Impact: All services down
Detection: UptimeRobot; Railway status page

Steps:
1. Verify it's platform issue: check Railway status page

2. If platform outage (estimated > 2 hours):
   Spin up emergency deployment on Render:
     render.com → New Web Service → Connect xithsense repo
     Copy all env vars from Railway
     Deploy: ~10 minutes

3. Update DNS:
   Cloudflare → DNS → api.xithsense.com → new Render URL
   TTL: 60 seconds (ensure low TTL pre-configured)

4. Post status update to users: @XithSenseBot Telegram broadcast

5. After Railway recovers:
   Verify data consistency between platforms
   Switch DNS back to Railway
```

---

## Backup Verification Schedule

| Backup | Verification | Frequency |
|--------|-------------|-----------|
| PostgreSQL daily backup | Restore to test schema; run quality checks | Weekly |
| Model artifacts (S3) | Download and verify with verify_model.py | After each training run |
| Redis (AOF) | Check `INFO persistence` for last save time | Daily |
| Audit logs (S3) | Spot-check 10 records for integrity | Monthly |

---

## Emergency Contacts

| Role | Contact | When to Call |
|------|---------|-------------|
| On-call engineer | PagerDuty rotation | Any critical alert |
| Supabase support | support@supabase.com | DB-level emergencies |
| Railway support | support@railway.app | Platform outages |
| Razorpay support | support@razorpay.com | Payment failures |

---

## Quarterly DR Drill

Conduct every 3 months:
1. Simulate DB restore from 3-day-old backup in staging
2. Verify feature rebuild completes correctly
3. Run full test suite against restored data
4. Measure actual RTO vs target
5. Document results and gaps
