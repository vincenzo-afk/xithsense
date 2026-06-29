# Release Process

---

## Release Types

| Type | Trigger | Requires | Examples |
|------|---------|----------|---------|
| **Patch** | Bug fix, dependency update | 1 approver + CI green | Fix wide-ball parsing, update redis-py |
| **Minor** | New feature, new endpoint | 1 approver + CI + staging smoke test | Add chat endpoint, new team mode |
| **Major** | Breaking API change, new major version | 2 approvers + load test + staging 24h soak | v2 API, schema redesign |
| **Hotfix** | Critical production bug | 1 approver + CI + immediate deploy | Fix prediction returning 500 |

---

## Standard Release Workflow

```
1. PREPARE
   ├── Create feature/fix branch from main
   ├── Implement changes with tests
   ├── Update CHANGELOG.md under [Unreleased]
   └── Open PR with description

2. REVIEW
   ├── CI must be green (lint + unit + integration tests)
   ├── At least 1 approving review
   ├── Coverage must not drop below module targets
   └── Documentation updated

3. STAGING DEPLOY (automatic on merge to develop)
   ├── GitHub Action: deploy-staging.yml triggers
   ├── Railway deploys to staging environment
   ├── Run smoke tests: python scripts/smoke_test.py --env staging
   └── Verify /health, predict/team, auth endpoints

4. RELEASE
   ├── Bump version in pyproject.toml
   ├── Move [Unreleased] CHANGELOG entries under new version heading
   ├── Create PR: "release: v0.6.0"
   ├── After merge: git tag v0.6.0 && git push origin v0.6.0
   └── GitHub Action: deploy-production.yml triggers on tag

5. POST-DEPLOY VERIFICATION
   ├── curl https://api.xithsense.com/health → {"status": "ok"}
   ├── Run production smoke test (read-only): python scripts/smoke_test.py --env prod
   ├── Check Sentry: no new error spikes
   ├── Check Grafana: p95 latency within normal range
   └── Monitor for 30 minutes
```

---

## Deployment Checklist

### Pre-Deploy
- [ ] All tests pass: `make test`
- [ ] Linting clean: `make lint`
- [ ] CHANGELOG.md updated
- [ ] `pyproject.toml` version bumped
- [ ] Any new env vars added to `.env.example` and platform secrets
- [ ] Database migrations created and tested
- [ ] Breaking changes documented and versioned

### Deploy
- [ ] Staging deployment succeeds
- [ ] Staging smoke tests pass
- [ ] Production deployment triggered via git tag
- [ ] Zero-downtime rolling restart confirmed

### Post-Deploy
- [ ] `GET /health` returns `{"status": "ok"}`
- [ ] `POST /predict/team` returns valid team for known match
- [ ] No 5xx errors in first 5 minutes of traffic
- [ ] Sentry: no new critical errors
- [ ] Grafana: latency and error rate within normal bounds
- [ ] Notify team via Telegram: `✅ v0.6.0 deployed successfully`

---

## Hotfix Process

For critical production bugs only:

```bash
# 1. Branch from main (not develop)
git checkout main
git checkout -b hotfix/fix-prediction-crash

# 2. Fix, test
pytest tests/unit/ -v -k "test_affected_area"

# 3. PR directly to main (bypass staging)
# Requires 1 approver + CI green

# 4. Tag immediately after merge
git tag v0.5.1
git push origin v0.5.1

# 5. Also merge to develop
git checkout develop && git merge main
```

---

## Rollback Procedure

```bash
# Identify last stable version
git tag --sort=-version:refname | head -5

# Revert to previous tag
git checkout v0.5.0
docker compose build api
docker compose up -d api

# If DB migration needs rollback
alembic downgrade -1

# Verify
curl https://api.xithsense.com/health
```

---

## Release Communication

| Audience | Channel | Content |
|----------|---------|---------|
| Engineers | GitHub release notes | Technical changelog |
| Users (major features) | Telegram @XithSenseBot | User-friendly feature summary |
| Admin | Email | Migration instructions if any |
