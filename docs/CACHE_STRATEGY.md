# Cache Strategy

**Technology:** Redis 7 (single instance MVP; cluster at 10k DAU)  
**Eviction policy:** `allkeys-lru` (evict least-recently-used when memory full)  
**Max memory:** 512 MB (MVP)

---

## Cache Layers

| Layer | What | Key Pattern | TTL | Invalidation |
|-------|------|-------------|-----|-------------|
| Feature cache | Player feature vectors | `feat:{player_id}:{match_type}:{date}` | 6 hours | On new match ingested for that player |
| Venue stats | Venue feature dict | `venue_stat:{venue_id}:{match_type}` | 24 hours | On new match at that venue ingested |
| Matchup stats | Batter vs bowler-type | `matchup:{player_id}:{bowler_type}:{match_type}` | 24 hours | On new match ingested |
| Match detail | Match metadata | `match:{match_id}` | 10 minutes | On match update (toss, XI) |
| Playing XI | XI per match | `xi:{match_id}` | 5 minutes | On EVT-01, EVT-03, EVT-04 |
| Prediction (pre-toss) | Full prediction result | `pred:{match_id}:{mode}:pre_toss` | 60 minutes | On toss or XI change |
| Prediction (post-toss) | Full prediction result | `pred:{match_id}:{mode}:post_toss` | 30 minutes | On injury or XI change |
| LLM explanation | Player explanation | `explain:{match_id}:{player_id}:{phase}` | 60 minutes | On prediction refresh |
| User session | Auth user object | `user:{user_id}` | 5 minutes | On user.role change |
| Rate limit | Request counter | `rate:{user_id}:{minute_bucket}` | 60 seconds | Natural expiry |
| Token revocation | Revoked JWTs | `revoked:jti:{jti}` | = token remaining TTL | Manual invalidation |
| Notification dedup | Sent notification flags | `notif:dedup:{user_id}:{match_id}:{event}` | 24 hours | Natural expiry |

---

## Cache Key Naming Convention

```
{entity}:{identifier}[:{sub-identifier}][:{context}]

Examples:
feat:d4e5f6a7-b8c9-0123-defa-bc4567890123:T20:2026-06-25
venue_stat:f6a7b8c9-d0e1-2345-fabc-de6789012345:IPL
matchup:d4e5f6a7:pace_left:T20
match:1535465
xi:1535465
pred:1535465:grand_league:post_toss
explain:1535465:d4e5f6a7-b8c9-0123-defa-bc4567890123:post_toss
user:a1b2c3d4-e5f6-7890-abcd-ef1234567890
rate:a1b2c3d4:1750831260
```

---

## Cache-Aside Pattern (Read-Through)

```python
async def get_rolling_features(player_id: UUID, match_type: str, date: date) -> RollingFeature:
    key = f"feat:{player_id}:{match_type}:{date}"

    # Try cache first
    cached = await redis.get(key)
    if cached:
        cache_hits.inc()
        return RollingFeature.parse_raw(cached)

    # Cache miss: fetch from DB
    cache_misses.inc()
    feature = await feature_repo.get_latest(player_id, match_type, date)

    # Populate cache
    await redis.setex(key, FEATURE_TTL, feature.json())
    return feature
```

---

## Bulk Cache Warm-Up

Before peak match windows (e.g. IPL evening matches), pre-warm the cache:

```python
# scripts/warm_cache.py
async def warm_prediction_cache(hours_ahead: int = 6):
    """Pre-generate and cache predictions for all upcoming matches."""
    upcoming = await match_repo.get_upcoming(hours=hours_ahead)
    tasks = [
        prediction_service.generate_and_cache(match.id, mode)
        for match in upcoming
        for mode in ["safe", "grand_league", "aggressive", "small_league"]
    ]
    await asyncio.gather(*tasks, return_exceptions=True)
    log.info("cache_warmed", match_count=len(upcoming))
```

Run at 4 PM IST for 7 PM matches: `python scripts/warm_cache.py --hours-ahead 6`

---

## Cache Invalidation Patterns

### Pattern 1: Event-Driven Invalidation (Preferred)

```python
# On toss event
async def invalidate_on_toss(match_id: str):
    patterns = [
        f"xi:{match_id}",
        f"match:{match_id}",
        f"pred:{match_id}:*",         # all modes, all phases
        f"explain:{match_id}:*",      # all player explanations
    ]
    for pattern in patterns:
        keys = await redis.keys(pattern)
        if keys:
            await redis.delete(*keys)
```

### Pattern 2: TTL-Based Expiry (Fallback)

All cache entries have TTLs as the last line of defence. Even if explicit invalidation fails, stale data expires within its TTL window.

---

## Cache Monitoring

```python
# Prometheus metrics
cache_hit_rate = Gauge("cache_hit_rate", "Cache hit ratio by type", ["cache_type"])
cache_memory = Gauge("redis_memory_bytes", "Redis used memory")

# Alert if hit rate drops below 70%
# Alert if memory > 80% of maxmemory
```
