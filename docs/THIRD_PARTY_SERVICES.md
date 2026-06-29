# Third-Party Services

Complete reference for every external service: auth, rate limits, costs, and failure handling.

---

## Anthropic Claude

| Property | Value |
|----------|-------|
| Purpose | LLM explanations + AI chat |
| SDK | `anthropic==0.28.0` |
| Auth | API key in `ANTHROPIC_API_KEY` |
| Model | `claude-sonnet-4-6` |
| Base URL | `https://api.anthropic.com` |
| Rate limits | 50,000 tokens/min (Tier 1); scales with usage |
| Context window | 200K tokens |

**Costs (approximate):**
- Input: $3.00 / 1M tokens
- Output: $15.00 / 1M tokens
- Avg per explanation: ~300 tokens → $0.005 per explanation
- Avg per chat turn: ~500 tokens → $0.009 per turn

**Failure handling:** Switch to OpenAI → Google; then fallback template.

---

## OpenAI GPT

| Property | Value |
|----------|-------|
| Purpose | LLM fallback provider |
| SDK | `openai==1.30.1` |
| Auth | API key in `OPENAI_API_KEY` |
| Model | `gpt-4o` |
| Rate limits | Tier 2: 90,000 tokens/min |

**Costs:** Input $2.50/1M · Output $10.00/1M tokens

---

## Google Gemini

| Property | Value |
|----------|-------|
| Purpose | LLM tertiary fallback |
| SDK | `google-generativeai==0.7.2` |
| Auth | API key in `GOOGLE_API_KEY` |
| Model | `gemini-2.0-flash` |
| Rate limits | 2M tokens/min (Flash) |

**Costs:** $0.075/1M input · $0.30/1M output (Flash) — cheapest option

---

## Supabase (PostgreSQL)

| Property | Value |
|----------|-------|
| Purpose | Primary relational database |
| SDK | `supabase-py==2.5.0` + `asyncpg` |
| Auth | Service key + connection string |
| Plan needed | Pro (for 200 connections) |
| Connection pool | PgBouncer (Supabase managed) |
| Backup | Daily + continuous WAL |
| SLA | 99.9% uptime |

**Costs (Pro plan):** $25/month · 8 GB storage included · $0.125/GB extra

---

## Redis (Railway Plugin)

| Property | Value |
|----------|-------|
| Purpose | Cache + Celery broker |
| Version | Redis 7 |
| Max memory | 512 MB (MVP) |
| Persistence | AOF enabled |
| Auth | Password via `REDIS_URL` |

**Costs (Railway):** ~$5–15/month for 512 MB instance

---

## Qdrant

| Property | Value |
|----------|-------|
| Purpose | Vector similarity (player embeddings, rule retrieval) |
| SDK | `qdrant-client==1.9.1` |
| Auth | API key (cloud) or no-auth (local) |
| Collections | `player_embeddings`, `human_rules` |

**Costs:** Free self-hosted · Qdrant Cloud from $25/month

---

## Razorpay

| Property | Value |
|----------|-------|
| Purpose | Subscription billing (INR) |
| SDK | `razorpay==1.4.1` |
| Auth | Key ID + Secret in env vars |
| Webhook | `POST /api/v1/payments/webhook` |
| Transaction fees | 2% per transaction |
| Payout | T+3 business days |

**Plan fees:** ₹299/month × 2% = ₹5.98 per subscriber/month in fees

---

## Telegram Bot API

| Property | Value |
|----------|-------|
| Purpose | Push notifications |
| SDK | `python-telegram-bot==21.3` |
| Auth | Bot token in `TELEGRAM_BOT_TOKEN` |
| Rate limits | 30 messages/second per bot |
| Group limits | 20 messages/minute per group |
| Message size | 4096 chars (Markdown) |

**Cost:** Free

---

## OpenWeatherMap

| Property | Value |
|----------|-------|
| Purpose | Pre-match weather data |
| Endpoint | `/forecast` (3-hour intervals) |
| Auth | API key in `WEATHER_API_KEY` |
| Rate limits | Free: 60 calls/min; paid: 600/min |
| Cache | 3 hours per city |

**Cost:** Free tier sufficient for MVP (< 1000 calls/day)

---

## AWS SES

| Property | Value |
|----------|-------|
| Purpose | Transactional emails (welcome, expiry, alerts) |
| SDK | `boto3==1.34.120` |
| Auth | IAM access key + secret |
| Rate limits | 14 emails/second (sandbox); production unlimited |

**Cost:** $0.10 / 1000 emails — effectively free at MVP scale

---

## Sentry

| Property | Value |
|----------|-------|
| Purpose | Error tracking + performance monitoring |
| SDK | `sentry-sdk[fastapi]==2.5.0` |
| Auth | DSN in `SENTRY_DSN` |
| Sampling | 10% transactions, 100% errors |

**Cost:** Free tier (5K errors/month) · Team plan $26/month (100K errors)

---

## Service Dependency Map

```
XithSense API
├── REQUIRED: Supabase (DB) — app non-functional without it
├── REQUIRED: Redis (cache + queue) — significant degradation without it
├── OPTIONAL: Anthropic/OpenAI/Google (LLM) — fallback templates used
├── OPTIONAL: Qdrant (vectors) — file-based rules used as fallback
├── OPTIONAL: Razorpay (payments) — billing fails; free tier still works
├── OPTIONAL: Telegram (notifications) — no push alerts sent
├── OPTIONAL: OpenWeatherMap (weather) — venue historical avg used
└── OPTIONAL: Sentry (monitoring) — errors untracked; no service impact
```
