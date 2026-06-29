# Infrastructure Architecture

## MVP Deployment (Railway / Render)

```
Internet
    │
    ▼
Cloudflare (CDN + DDoS protection)
    │
    ▼
Load Balancer (Railway/Render managed)
    │
    ├──► API Container (FastAPI + Gunicorn, 4 workers)
    │         │
    │         ├──► Supabase PostgreSQL (managed, external)
    │         ├──► Redis (Railway Redis plugin)
    │         └──► Qdrant (Railway Docker service)
    │
    ├──► Worker Container (Celery, 4 concurrency)
    │
    └──► Scheduler Container (Celery Beat)
```

## Resource Sizing (MVP)

| Service | CPU | RAM | Disk |
|---------|-----|-----|------|
| API | 1 vCPU | 1 GB | — |
| Worker | 2 vCPU | 2 GB | — |
| Scheduler | 0.5 vCPU | 256 MB | — |
| Redis | Shared | 512 MB | 1 GB |
| Qdrant | 1 vCPU | 1 GB | 5 GB |
| PostgreSQL | Supabase managed | — | 8 GB |
| Model artifacts | — | — | 5 GB |

## AWS Architecture (Scale-up Path)

```
Route 53 (DNS)
    │
    ▼
CloudFront (CDN)
    │
    ▼
ALB (Application Load Balancer)
    │
    ├──► ECS Fargate: API tasks (auto-scale 2–10)
    ├──► ECS Fargate: Worker tasks (auto-scale 2–8)
    │
    ├──► ElastiCache Redis (cluster mode)
    ├──► RDS PostgreSQL (multi-AZ)
    └──► EC2: Qdrant (i3 instance, NVMe storage)

S3: Model artifacts, backups
ECR: Docker image registry
Secrets Manager: All environment secrets
CloudWatch: Logs and metrics
```

## Environments

| Environment | Platform | DB | Notes |
|------------|----------|-----|-------|
| Local dev | Docker Compose | Local PG / Supabase | `.env` file |
| Staging | Railway | Supabase (separate project) | Auto-deploy on `develop` branch |
| Production | Railway / AWS | Supabase (production) | Auto-deploy on `main` tag |

## Secrets Management

- Local: `.env` file (never committed)
- Staging/Production: Railway environment variables or AWS Secrets Manager
- Rotate all secrets every 90 days
- Database passwords: 32-char random; rotated every 30 days
