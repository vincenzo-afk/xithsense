# Data Architecture

## Data Sources

| Source | Type | Update Frequency | Volume |
|--------|------|-----------------|--------|
| Cricsheet JSON | Ball-by-ball match files | After each match (manual/scheduled) | 22,062 matches, ~3.8 GB |
| Weather API (OpenWeatherMap) | Match-day weather | 3 hours before match | Per match |
| Manual playing XI | Admin-entered or scraped | 30–60 min before match | Per match |
| User inputs | Chat, feedback | Real-time | Per interaction |

## Data Flow

```
RAW                PROCESSED              FEATURES             PREDICTIONS
  │                    │                     │                     │
  │  ingest_cricsheet   │  aggregate_per_match │  rolling windows    │  ensemble
  ├──────────────────►  ├──────────────────►  ├──────────────────►  │
  │  Cricsheet JSON     │  player_match_perf   │  rolling_feature    │  predicted_player
  │  22,062 files       │  table               │  venue_stat         │  recommended_team
  │  data/raw/          │                     │  matchup_stat       │
```

## Storage Tiers

| Tier | Technology | Purpose | TTL |
|------|-----------|---------|-----|
| Primary | Supabase PostgreSQL | All structured data | Permanent |
| Cache | Redis | Feature vectors, predictions | 1h–6h |
| Vector | Qdrant | Player embeddings, rule similarity | Permanent |
| Artifact | Local filesystem / S3 | Trained model files | Versioned |

## Data Governance

- All PII (user email, phone) stored encrypted at rest (Supabase handles this)
- Match data from Cricsheet is open-source (CC BY 4.0 or equivalent)
- User data never shared with third parties except Razorpay (for billing)
- Data retention: user accounts kept until deletion requested; match data permanent
