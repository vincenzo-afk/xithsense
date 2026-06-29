# Secrets Management

## Secret Categories

| Category | Examples | Storage |
|----------|---------|---------|
| Database credentials | `DATABASE_URL`, `SUPABASE_SERVICE_KEY` | Platform secrets + local `.env` |
| External API keys | `ANTHROPIC_API_KEY`, `RAZORPAY_KEY_SECRET` | Platform secrets |
| Internal signing keys | `SECRET_KEY`, `XITHSENSE_API_KEY` | Platform secrets |
| Notification tokens | `TELEGRAM_BOT_TOKEN`, `SMTP_PASSWORD` | Platform secrets |

---

## Storage by Environment

| Environment | Storage Method |
|------------|----------------|
| Local dev | `.env` file (git-ignored) |
| Staging | Railway environment variables |
| Production | Railway environment variables OR AWS Secrets Manager |
| CI (GitHub Actions) | GitHub Encrypted Secrets |

---

## Rotation Schedule

| Secret | Rotation Frequency | Method |
|--------|-------------------|--------|
| `SECRET_KEY` (JWT) | 90 days | Generate new 64-char random string; rolling deployment |
| `DATABASE_URL` password | 30 days | Supabase dashboard → regenerate |
| `ANTHROPIC_API_KEY` | 90 days | Anthropic console |
| `RAZORPAY_KEY_SECRET` | On compromise only | Razorpay dashboard |
| `TELEGRAM_BOT_TOKEN` | On compromise only | BotFather `/revoke` |

---

## Secret Generation

```bash
# Generate SECRET_KEY (64 chars)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate XITHSENSE_API_KEY
python -c "import secrets; print('xs-live-' + secrets.token_urlsafe(32))"
```

---

## Rules

1. **Never commit** `.env`, API keys, or passwords to any repository — public or private.
2. **Never log** secrets. The structlog processor strips known secret field names.
3. **Never pass** secrets as command-line arguments (visible in `ps aux`). Use environment variables only.
4. **Use `.env.example`** with placeholder values only, committed to the repository.
5. **Rotate immediately** if a secret is accidentally exposed (committed, logged, or shared).
6. **Principle of least privilege** — each service only gets the secrets it needs. Workers don't get `RAZORPAY_KEY_SECRET`.

---

## Secret Rotation Procedure

```bash
# 1. Generate new secret
NEW_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

# 2. Update in Railway (staging first)
railway variables set SECRET_KEY="$NEW_SECRET" --environment staging

# 3. Test staging deployment
curl https://staging-api.xithsense.com/health

# 4. Update production
railway variables set SECRET_KEY="$NEW_SECRET" --environment production

# 5. Trigger rolling restart
railway redeploy --environment production

# 6. Verify all services healthy
curl https://api.xithsense.com/health

# Note: Existing JWT tokens signed with old key become invalid.
# Users must log in again. Acceptable for 90-day rotation.
```

---

## Incident Response: Leaked Secret

1. **Immediately revoke** the exposed secret in the provider's dashboard
2. **Generate** a new secret
3. **Update** all environments
4. **Audit** logs for any unauthorised use of the exposed secret
5. **Notify** affected users if their data may have been compromised
6. **Document** in incident log
