# Security Requirements

## Authentication

- JWT signed with HS256 (secret ≥ 256 bits) or RS256
- Token expiry: 24 hours access token, 30-day refresh token
- Passwords hashed with bcrypt, cost factor ≥ 12
- Email verification required before first prediction request

## Authorisation

- Role-based: `free`, `premium`, `admin`
- All endpoints except `/health` and `/api/v1/auth/*` require valid JWT
- Admin endpoints check `role=admin` claim in JWT
- Rate limiting enforced per user per minute (Free: 30, Premium: 300, Admin: 1000)

## Input Validation

- All request bodies validated via Pydantic models
- String fields sanitised: strip whitespace, max length enforced
- UUIDs validated before DB queries
- SQL queries use SQLAlchemy ORM parameterised queries only
- Never use string concatenation for SQL

## API Security

- CORS restricted to `ALLOWED_ORIGINS` env var
- HTTPS enforced in production (no HTTP fallback)
- `X-Content-Type-Options: nosniff` header on all responses
- `X-Frame-Options: DENY` header on all responses
- Rate limit headers included: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

## Data Security

- No PII in logs (no email, phone, or payment details in log output)
- Razorpay webhook signature verified before processing
- API keys and secrets only in `.env` / deployment secret manager
- No secrets in source code, comments, or test files

## OWASP Top 10 Mitigations

| OWASP Risk | Mitigation |
|---|---|
| A01 Broken Access Control | Role checks on every protected route |
| A02 Cryptographic Failures | bcrypt passwords, HTTPS, encrypted DB at rest |
| A03 Injection | Parameterised queries, Pydantic validation |
| A04 Insecure Design | Security review before major feature launch |
| A05 Security Misconfiguration | `.env.example` with safe defaults, Docker non-root user |
| A07 Identification and Auth Failures | JWT expiry, bcrypt, rate limiting |
| A09 Security Logging | Structured logs with request_id; no PII |
