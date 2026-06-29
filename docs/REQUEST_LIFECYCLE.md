# Request Lifecycle

Every API request passes through a defined middleware chain and service layers.

---

## HTTP Request Lifecycle

```
Client Request
    │
    ▼
[1] Cloudflare / CDN
    └── TLS termination, DDoS protection, static caching

    │
    ▼
[2] Load Balancer (Railway/Render)
    └── Round-robin to API container pool

    │
    ▼
[3] Gunicorn / Uvicorn worker
    └── Accepts connection, spawns async handler

    │
    ▼
[4] FastAPI Middleware Chain (in order)

  [4a] RequestID Middleware
       └── Generate UUID, bind to structlog context
       └── Add X-Request-ID to response headers

  [4b] Timing Middleware
       └── Start timer

  [4c] CORS Middleware
       └── Check Origin against ALLOWED_ORIGINS
       └── Return 403 if not allowed

  [4d] Rate Limit Middleware
       └── Identify user (JWT or IP)
       └── Increment Redis counter
       └── Return 429 if over limit

  [4e] Authentication Middleware (for protected routes)
       └── Extract Bearer token from Authorization header
       └── Decode JWT, verify signature and expiry
       └── Load user from DB (cached in Redis 5 min)
       └── Inject user into request.state

    │
    ▼
[5] Route Handler
    └── Validate request body via Pydantic

    │
    ▼
[6] Feature Gate Check
    └── Verify user.role has access to this feature

    │
    ▼
[7] Service Layer (business logic)
    └── Orchestrates DB, Redis, ML, LLM calls

    │
    ▼
[8] Repository Layer (data access)
    └── Executes SQLAlchemy queries
    └── Returns domain models

    │
    ▼
[9] Response Building
    └── Serialize to Pydantic response model
    └── Add standard headers

    │
    ▼
[10] Response Middleware
    └── Stop timer, log request duration
    └── Emit Prometheus metric

    │
    ▼
Client Response
```

---

## Async Request Pattern (Prediction)

```python
# Prediction endpoint simplified

@router.post("/predict/team", response_model=TeamPredictionResponse)
async def predict_team(
    request: TeamPredictionRequest,            # [5] Pydantic validation
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),    # [4e] Auth
    _: None = Depends(check_rate_limit),       # [4d] Rate limit
):
    # [6] Feature gate
    gate = FeatureGate.can_generate_team(user, request.count, request.mode)
    if not gate.allowed:
        raise PaymentRequiredError(gate.message)

    # [7] Service layer
    result = await prediction_service.generate_team(
        match_id=request.match_id,
        mode=request.mode,
        count=request.count,
        user=user,
        db=db,
    )

    # [9] Response
    return TeamPredictionResponse.from_domain(result)
```

---

## WebSocket Lifecycle

```
Client                    API Server                  Redis
  │                           │                          │
  │  GET /api/v1/live/:id     │                          │
  │  Upgrade: websocket       │                          │
  │──────────────────────────►│                          │
  │                           │ Validate JWT (query param)
  │                           │ Check premium access      │
  │◄──────────────────────────│                          │
  │  101 Switching Protocols  │                          │
  │                           │                          │
  │                           │  Subscribe to channel    │
  │                           │  match_updates:1535465   │
  │                           │─────────────────────────►│
  │                           │                          │
  │   {event: match_update}  ◄── Publish from           │
  │◄──────────────────────────│   toss update task       │
  │                           │                          │
  │   (every 30s)             │                          │
  │   {action: ping}          │                          │
  │──────────────────────────►│                          │
  │   {action: pong}          │                          │
  │◄──────────────────────────│                          │
  │                           │                          │
  │                           │ [match ends]             │
  │   {event: match_ended}    │                          │
  │◄──────────────────────────│                          │
  │  Connection closed        │                          │
```

---

## Celery Task Lifecycle

```
API Layer                 Redis (Broker)              Worker
    │                          │                          │
    │  task.delay(args)        │                          │
    │─────────────────────────►│                          │
    │                          │  task queued             │
    │  (returns task_id)       │─────────────────────────►│
    │◄─────────────────────────│                          │ execute()
    │                          │                          │ success/failure
    │                          │◄─────────────────────────│
    │                          │  result stored           │
```
