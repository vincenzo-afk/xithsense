# Cost Estimation

Monthly cost breakdown at three scales: MVP launch, 1,000 users, and 10,000 users.

---

## Infrastructure Costs

### MVP Launch (~100 active users)

| Service | Tier | Monthly Cost (INR) |
|---------|------|-------------------|
| Supabase PostgreSQL | Pro | ₹2,080 ($25) |
| Railway API container | Starter (1 vCPU, 512MB) | ₹830 ($10) |
| Railway Worker container | Starter | ₹830 ($10) |
| Railway Redis | Plugin | ₹415 ($5) |
| Railway Qdrant | Docker service | ₹415 ($5) |
| Sentry | Free tier | ₹0 |
| OpenWeatherMap | Free tier | ₹0 |
| AWS SES | Pay-per-use | ~₹85 ($1) |
| **Total Infrastructure** | | **~₹4,655/month** |

---

### 1,000 Active Users (month 6)

| Service | Tier | Monthly Cost (INR) |
|---------|------|-------------------|
| Supabase PostgreSQL | Pro | ₹2,080 |
| Railway API (2 replicas) | Pro | ₹3,320 ($40) |
| Railway Worker (2 replicas) | Pro | ₹2,490 ($30) |
| Railway Redis (1 GB) | Upgraded | ₹1,245 ($15) |
| Railway Qdrant | | ₹830 ($10) |
| Sentry Team | Error tracking | ₹2,160 ($26) |
| **Total Infrastructure** | | **~₹12,125/month** |

---

### 10,000 Active Users (year 1)

| Service | Tier | Monthly Cost (INR) |
|---------|------|-------------------|
| Supabase PostgreSQL | Team ($599/mo) | ₹49,800 |
| AWS ECS Fargate API (4 tasks) | | ₹16,600 ($200) |
| AWS ECS Fargate Worker (4 tasks) | | ₹12,450 ($150) |
| ElastiCache Redis (r6g.large) | | ₹20,750 ($250) |
| EC2 Qdrant (i3.xlarge) | | ₹12,450 ($150) |
| CloudFront CDN | | ₹2,490 ($30) |
| Sentry Business | | ₹7,470 ($90) |
| **Total Infrastructure** | | **~₹122,010/month** |

---

## LLM Costs

| Model | Tokens/Request | Requests/Day | Cost/Day | Cost/Month |
|-------|---------------|-------------|---------|-----------|
| Explanation (Claude Sonnet) | 300 avg | 500 | $0.75 | $22.50 |
| Chat turns (Claude Sonnet) | 500 avg | 200 | $0.50 | $15.00 |
| **Total LLM (MVP)** | | | **$1.25/day** | **$37.50** |

**LLM cost at 1,000 users:**
- Explanations: 5,000/day → $7.50/day → $225/month
- Chat: 2,000/day → $5.00/day → $150/month
- **Total: ~$375/month (~₹31,200)**

**LLM cost control measures:**
- Cache all explanations for 1 hour (reduces calls by ~80%)
- Use Gemini Flash as fallback (8× cheaper than Claude Sonnet)
- Rate-limit chat at 20 turns/user/match

---

## Payment Processing Costs (Razorpay)

At 2% transaction fee:

| Monthly Subscribers | MRR | Razorpay Fees |
|--------------------|-----|---------------|
| 100 Premium Monthly | ₹29,900 | ₹598 |
| 400 Premium Monthly | ₹1,19,600 | ₹2,392 |
| 2,000 Premium Monthly | ₹5,98,000 | ₹11,960 |

---

## Total Cost Summary

| Scale | Infra | LLM | Payment Fees | Total Monthly |
|-------|-------|-----|-------------|---------------|
| MVP (100 users) | ₹4,655 | ₹3,120 | ₹598 | **₹8,373** |
| 1K users | ₹12,125 | ₹31,200 | ₹2,392 | **₹45,717** |
| 10K users | ₹1,22,010 | ₹1,20,000 | ₹11,960 | **₹2,53,970** |

---

## Revenue vs Cost (Break-Even Analysis)

| Subscribers | MRR | Total Costs | Net |
|------------|-----|-------------|-----|
| 100 | ₹29,900 | ₹8,373 | **+₹21,527** |
| 400 | ₹1,19,600 | ₹45,717 | **+₹73,883** |
| 2,000 | ₹5,98,000 | ₹2,53,970 | **+₹3,44,030** |

Break-even: ~30 Premium Monthly subscribers.

---

## Cost Optimization Strategies

1. **LLM caching** — 80% cache hit rate reduces LLM costs by 4×
2. **Gemini Flash fallback** — 8× cheaper than Claude when accuracy is acceptable
3. **Batch explanations** — Generate all 11 player explanations in one LLM call where possible
4. **Reserved instances** — Move to AWS 1-year reserved at 10k users (saves ~30%)
5. **Model artifacts on S3** — $0.023/GB vs Railway volume at $0.25/GB
