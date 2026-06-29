# Scaling Strategy

## Traffic Patterns

XithSense has highly predictable traffic spikes:
- **Pre-match window:** 2 hours before each IPL match (7–9 PM IST)
- **Toss time:** Sharp spike 15 minutes before match start
- **Post-toss:** 5-minute burst of prediction requests

## Scaling Triggers

| Metric | Scale-Out Trigger | Scale-In Trigger |
|--------|------------------|-----------------|
| CPU > 70% for 3 min | Add 1 API replica | CPU < 40% for 10 min |
| Request queue > 100 | Add 1 API replica | Queue < 20 for 10 min |
| Celery task queue > 200 | Add 1 worker | Queue < 50 for 10 min |
| Memory > 80% | Add 1 replica | Memory < 60% for 10 min |

## Horizontal Scaling Architecture

```
API Service: stateless — scale freely
Worker Service: stateless — scale freely
Scheduler: singleton — do not replicate

Redis: single instance (MVP); upgrade to cluster at 10k DAU
PostgreSQL: connection pooling via PgBouncer (Supabase managed)
Qdrant: single node (MVP); cluster at 50k daily queries
```

## Pre-Scaling for IPL Season

Before each IPL match window:
1. Manually scale API replicas to minimum 3 (Railway override)
2. Pre-warm Redis cache: run prediction for all upcoming matches at 4 PM IST
3. Verify Celery worker count ≥ 4 before 7 PM IST

## Database Connection Limits

| Plan | Max Connections | PgBouncer Pool |
|------|---------------|----------------|
| Supabase Free | 60 | 20 per service |
| Supabase Pro | 200 | 50 per service |
| Supabase Team | 500 | 100 per service |

Scale to Supabase Pro before going live. Never exceed 80% of max connections.

## Cost Optimisation

- Scale workers down to 1 during off-peak hours (midnight – 8 AM IST)
- Redis `maxmemory-policy allkeys-lru` prevents memory bloat
- Celery task result TTL: 1 hour (avoid result backend bloat)
- Delete model artifacts older than 3 versions
