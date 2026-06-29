# Caching Strategy

**Technology:** Redis 7 · **Eviction:** `allkeys-lru` · **Max Memory:** 512 MB (MVP)

---

## Redis Key Structure

All keys follow: `{namespace}:{identifier}[:{sub-key}]`

```
Namespace       Key Pattern                                     TTL
─────────       ───────────                                     ───
feat:           feat:{player_uuid}:{match_type}:{YYYY-MM-DD}   6h
venue:          venue_stat:{venue_uuid}:{match_type}            24h
matchup:        matchup:{player_uuid}:{bowler_type}:{type}      24h
match:          match:{match_id}                                10m
xi:             xi:{match_id}                                   5m
pred:           pred:{match_id}:{mode}:{phase}                  30m–60m
explain:        explain:{match_id}:{player_uuid}:{phase}        60m
user:           user:{user_uuid}                                5m
rate:           rate:{user_uuid}:{minute_epoch}                 60s
revoked:        revoked:jti:{jti}                               = token TTL
notif:          notif:dedup:{user_uuid}:{match_id}:{event_id}   24h
health:         health:db, health:redis, health:model           30s
warm:           warm:status:{match_id}                          12h
```

---

## TTL Definitions

```python
# backend/cache/ttl.py

class TTL:
    FEATURE_VECTOR      = 6 * 3600       # 6 hours — features don't change intra-day
    VENUE_STAT          = 24 * 3600      # 24 hours — venue stats stable
    MATCHUP_STAT        = 24 * 3600      # 24 hours — matchup stats stable
    MATCH_DETAIL        = 10 * 60        # 10 min — may update with toss/XI
    PLAYING_XI          = 5 * 60         # 5 min — changes on injury/update
    PREDICTION_PRE_TOSS = 60 * 60        # 60 min — valid until toss
    PREDICTION_POST_TOSS= 30 * 60        # 30 min — refreshed after each event
    EXPLANATION         = 60 * 60        # 60 min — same as prediction
    USER_SESSION        = 5 * 60         # 5 min — role change propagation
    RATE_LIMIT          = 60             # 60 sec — sliding window
    NOTIFICATION_DEDUP  = 24 * 3600      # 24 hours — prevent duplicate sends
    HEALTH_CHECK        = 30             # 30 sec — status cache
```

---

## Cache Operations

```python
# backend/cache/client.py

class CacheClient:
    def __init__(self, redis: Redis):
        self.redis = redis

    async def get_feature(self, player_id: UUID, match_type: str, date: date) -> dict | None:
        key = f"feat:{player_id}:{match_type}:{date}"
        raw = await self.redis.get(key)
        return json.loads(raw) if raw else None

    async def set_feature(self, player_id: UUID, match_type: str, date: date,
                          data: dict) -> None:
        key = f"feat:{player_id}:{match_type}:{date}"
        await self.redis.setex(key, TTL.FEATURE_VECTOR, json.dumps(data))

    async def invalidate_match(self, match_id: str) -> int:
        """Invalidate all cache entries for a match. Returns count deleted."""
        patterns = [
            f"match:{match_id}",
            f"xi:{match_id}",
        ]
        keys_to_scan = [f"pred:{match_id}:*", f"explain:{match_id}:*"]
        deleted = 0
        for key in patterns:
            deleted += await self.redis.delete(key)
        for pattern in keys_to_scan:
            async for key in self.redis.scan_iter(pattern):
                deleted += await self.redis.delete(key)
        return deleted

    async def increment_rate(self, user_id: UUID) -> int:
        """Sliding window rate limiting. Returns current count."""
        bucket = int(time.time() / 60)   # 1-minute buckets
        key = f"rate:{user_id}:{bucket}"
        count = await self.redis.incr(key)
        await self.redis.expire(key, TTL.RATE_LIMIT)
        return count
```

---

## Cache Invalidation Events

| Trigger | Keys Invalidated |
|---------|-----------------|
| New match ingested | `match:{id}`, `venue_stat:*` (if new venue data) |
| Playing XI confirmed | `xi:{match_id}`, `pred:{match_id}:*` |
| Toss completed | `match:{match_id}`, `xi:{match_id}`, `pred:{match_id}:*`, `explain:{match_id}:*` |
| Injury alert | Same as toss + `feat:{injured_player_id}:*` |
| New feature computed | `feat:{player_id}:{match_type}:{date}` |
| User role changed | `user:{user_id}` |
| Model version promoted | No cache invalidation (model loaded fresh per prediction) |

---

## Cache Warm-Up Script

```bash
# Warm cache before peak IPL window (run at 4 PM IST)
python scripts/warm_cache.py --hours-ahead 6

# Warm specific match
python scripts/warm_cache.py --match-id 1539584

# Warm all upcoming matches
python scripts/warm_cache.py --all-upcoming
```

```python
async def warm_prediction_cache(match_ids: list[str]):
    tasks = [
        prediction_service.generate_and_cache(mid, mode)
        for mid in match_ids
        for mode in ["safe", "grand_league", "aggressive", "small_league"]
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    errors = [r for r in results if isinstance(r, Exception)]
    log.info("cache_warm_complete",
             match_count=len(match_ids),
             errors=len(errors))
```

---

## Memory Budget Breakdown (512 MB)

| Data Type | Estimated Size | Count | Total |
|-----------|--------------|-------|-------|
| Feature vectors (47 floats × 22 players per match) | ~4 KB | 500 matches | ~2 MB |
| Predictions (11 players × 4 modes) | ~8 KB | 200 matches | ~1.6 MB |
| Explanations (text, ~200 chars each) | ~2 KB | 2200 per match × 200 | ~440 MB |
| User sessions | ~0.5 KB | 5000 users | ~2.5 MB |
| Rate limit counters | ~100 bytes | 10000 | ~1 MB |
| Other (XI, match detail, dedup) | — | — | ~10 MB |

**Total estimate: ~460 MB** — within 512 MB limit with `allkeys-lru` eviction.

When memory pressure increases, LRU evicts least recently used explanation caches first (largest data, lowest access frequency).
