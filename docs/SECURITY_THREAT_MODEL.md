# Security Threat Model

**Methodology:** STRIDE (Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege)

---

## Assets to Protect

| Asset | Sensitivity | Value |
|-------|------------|-------|
| User PII (email, phone) | High | Privacy compliance |
| User passwords | Critical | Account security |
| JWT signing secret | Critical | Authentication integrity |
| Razorpay API keys | Critical | Financial |
| Anthropic/OpenAI API keys | High | Cost (API abuse) |
| Prediction algorithms | Medium | Competitive advantage |
| Training data (features) | Medium | Product quality |
| ML model weights | Medium | Competitive advantage |

---

## Threat Analysis (STRIDE)

### S — Spoofing

| Threat | Attack Vector | Mitigation |
|--------|-------------|-----------|
| Impersonate a user | Stolen JWT | Short expiry (24h), revocation list in Redis |
| Impersonate admin | Role tampering in JWT payload | JWT signature verified server-side; role in payload signed |
| Impersonate Razorpay webhook | Fake webhook POST | HMAC-SHA256 signature verification; reject if mismatch |
| Brute force login | Password spray | 10 attempts/15min per IP; bcrypt cost 12 (slow) |
| Session fixation | Reuse old token | New JWT issued on login; old tokens revocable |

---

### T — Tampering

| Threat | Attack Vector | Mitigation |
|--------|-------------|-----------|
| SQL injection | Malicious input in queries | SQLAlchemy ORM parameterised queries only |
| Modify prediction in transit | MITM attack | HTTPS enforced; HSTS header |
| Tamper model artifacts | Malicious insider | S3 bucket with versioning; access logging |
| Inject into LLM prompt | Prompt injection in chat | Injection pattern detection; guardrails in llm/GUARDRAILS.md |
| Modify human rules | Unauthorised rule change | Admin-only rule endpoints; all changes audit-logged |

---

### R — Repudiation

| Threat | Mitigation |
|--------|-----------|
| Admin denies making a change | `admin_action` audit log (immutable, permanent) |
| User denies subscribing | Razorpay subscription record + webhook log |
| Payment dispute | Razorpay transaction IDs + our `subscription` table |

---

### I — Information Disclosure

| Threat | Attack Vector | Mitigation |
|--------|-------------|-----------|
| User data leak | DB breach | Data encrypted at rest (Supabase AES-256) |
| API key leak | Source code commit | `.env` in `.gitignore`; pre-commit hooks; secret scanning |
| Password in logs | Logging middleware | Structlog processor strips sensitive fields |
| Stack trace in response | Unhandled exception | Production error handler returns generic message only |
| Enumerate users via login | Timing attack on email check | Constant-time email comparison; same response for wrong email/password |
| Model weight extraction | Model API inference | Rate limiting; no raw model endpoint; only prediction API |

---

### D — Denial of Service

| Threat | Attack Vector | Mitigation |
|--------|-------------|-----------|
| API flooding | High request volume | Rate limiting: 30 RPM free, 300 RPM premium |
| Large payload attack | 10MB+ request body | Body size limit: 1 MB max |
| Slow POST attack | Very slow body uploads | Request timeout: 30 seconds |
| Layer 7 DDoS | Bot traffic | Cloudflare DDoS protection |
| Resource exhaustion via LP | Complex optimizer request | LP solver timeout: 10 seconds; DEAP timeout: 30 seconds |
| Redis memory exhaustion | Cache flooding | `maxmemory-policy allkeys-lru`; 512 MB cap |

---

### E — Elevation of Privilege

| Threat | Attack Vector | Mitigation |
|--------|-------------|-----------|
| Free user accessing premium | JWT role manipulation | Server-side role verification; JWT signed and verified |
| Admin endpoint access | IDOR attack | Strict role check on every admin route |
| Horizontal privilege | Access other user's predictions | Predictions scoped by `user_id` in all queries |
| Container escape | Malicious dependency | Docker non-root user; minimal base image; dependency scanning |

---

## Security Posture Summary

| Control | Status | Notes |
|---------|--------|-------|
| HTTPS everywhere | ✅ | Cloudflare handles TLS; HSTS header |
| Input validation | ✅ | Pydantic on all request bodies |
| Parameterised queries | ✅ | SQLAlchemy ORM enforced |
| Authentication | ✅ | JWT HS256, 24h expiry |
| Authorisation | ✅ | Role-based on every route |
| Rate limiting | ✅ | Redis sliding window |
| Secrets management | ✅ | Platform env vars, never in code |
| Audit logging | ✅ | All admin actions logged |
| Data encryption at rest | ✅ | Supabase AES-256 |
| Webhook signature verification | ✅ | HMAC-SHA256 |
| OWASP ZAP scan | ✅ | Required before each major release |
| Dependency scanning | 🔲 | Planned: Dependabot |
| Penetration testing | 🔲 | Planned: before Year 1 launch |
