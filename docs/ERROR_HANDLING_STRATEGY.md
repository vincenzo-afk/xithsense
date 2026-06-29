# Error Handling Strategy

## Principles

1. **Fail loudly internally, gracefully externally.** Every error is logged with full context. Users receive a clean, actionable message.
2. **Never swallow exceptions silently.** `except: pass` is forbidden.
3. **Domain errors vs infrastructure errors.** Handle them differently.
4. **Partial success is better than full failure.** If LLM fails for 2 of 11 players, return the team with fallback explanations for those 2.

---

## Exception Hierarchy

```python
# backend/exceptions.py

class XithSenseError(Exception):
    """Base exception for all XithSense domain errors."""
    http_status: int = 500
    error_code: str = "INTERNAL_ERROR"

class NotFoundError(XithSenseError):
    http_status = 404

class MatchNotFoundError(NotFoundError):
    error_code = "MATCH_NOT_FOUND"

class PlayerNotFoundError(NotFoundError):
    error_code = "PLAYER_NOT_FOUND"

class PredictionError(XithSenseError):
    http_status = 400

class OptimizerInfeasibleError(PredictionError):
    error_code = "OPTIMIZER_INFEASIBLE"

class InsufficientDataError(PredictionError):
    error_code = "PREDICTION_NO_PLAYERS"

class AuthenticationError(XithSenseError):
    http_status = 401
    error_code = "INVALID_TOKEN"

class AuthorizationError(XithSenseError):
    http_status = 403
    error_code = "INSUFFICIENT_ROLE"

class PaymentRequiredError(XithSenseError):
    http_status = 402
    error_code = "PREMIUM_REQUIRED"

class RateLimitError(XithSenseError):
    http_status = 429
    error_code = "RATE_LIMIT_EXCEEDED"

class ExternalServiceError(XithSenseError):
    http_status = 503
    """Raised when a third-party service (LLM, Razorpay) is unavailable."""
```

---

## Global Exception Handler (FastAPI)

```python
# backend/middleware/error_handler.py

@app.exception_handler(XithSenseError)
async def xithsense_error_handler(request: Request, exc: XithSenseError):
    log.error(
        "domain_error",
        error_code=exc.error_code,
        message=str(exc),
        path=request.url.path,
        request_id=request.state.request_id,
    )
    return JSONResponse(
        status_code=exc.http_status,
        content={"error": {
            "code": exc.error_code,
            "message": str(exc),
            "details": getattr(exc, "details", {}),
            "request_id": str(request.state.request_id),
        }}
    )

@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    sentry_sdk.capture_exception(exc)
    log.error("unhandled_error", exc_info=exc, request_id=request.state.request_id)
    return JSONResponse(
        status_code=500,
        content={"error": {
            "code": "INTERNAL_ERROR",
            "message": "An unexpected error occurred. Our team has been notified.",
            "request_id": str(request.state.request_id),
        }}
    )
```

---

## Service-Level Error Handling

### LLM Errors

```python
async def safe_explain(player, context) -> str:
    try:
        return await llm_explainer.explain(player, context)
    except (anthropic.RateLimitError, openai.RateLimitError) as e:
        log.warning("llm_rate_limit", provider=settings.LLM_PROVIDER)
        await asyncio.sleep(2)
        return await llm_explainer.explain(player, context)   # one retry
    except ExternalServiceError:
        return build_fallback_explanation(player)   # never raise to user
```

### Database Errors

```python
async def safe_db_write(session, obj) -> bool:
    try:
        session.add(obj)
        await session.commit()
        return True
    except IntegrityError as e:
        await session.rollback()
        if "unique constraint" in str(e):
            log.info("duplicate_insert_skipped", table=obj.__tablename__)
            return False
        raise
    except SQLAlchemyError as e:
        await session.rollback()
        log.error("db_write_failed", error=str(e))
        raise XithSenseError("Database write failed") from e
```

---

## Error Propagation Rules

| Layer | Action |
|-------|--------|
| Route handler | Catch all; convert to HTTPException with error_code |
| Service | Raise domain exceptions; log with context |
| Repository | Raise SQLAlchemy errors (wrapped by service) |
| External clients | Catch service errors; implement fallback or raise ExternalServiceError |
| Celery tasks | Use `autoretry_for` for transient errors; DLQ for permanent failures |
