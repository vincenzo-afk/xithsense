# Security Test Cases

**Tool:** OWASP ZAP (automated), manual pen testing  
**Run:** Before every major release, after any auth/security code changes

---

## Authentication Security Tests

| ID | Test | Expected Result |
|----|------|----------------|
| ST-01 | Submit login with correct email, wrong password | 401; no user data leaked |
| ST-02 | Submit login with non-existent email | 401; same response as wrong password (no enumeration) |
| ST-03 | Use expired JWT | 401 `EXPIRED_TOKEN` |
| ST-04 | Tamper JWT payload (change role to admin) | 401 `INVALID_TOKEN` |
| ST-05 | Submit 11+ login attempts with wrong password in 15 min | 429 after 10th attempt |
| ST-06 | Use valid JWT after user account suspended | 401 `ACCOUNT_SUSPENDED` |
| ST-07 | Access admin endpoint with Premium JWT | 403 `INSUFFICIENT_ROLE` |
| ST-08 | Access another user's predictions by guessing prediction_id UUID | 404 (not 403) — UUIDs are unguessable |

---

## Input Injection Tests

| ID | Test | Expected Result |
|----|------|----------------|
| ST-10 | SQL injection in `match_id`: `1535465' OR '1'='1` | 422 `VALIDATION_ERROR` (pattern mismatch) |
| ST-11 | SQL injection in search: `'; DROP TABLE player; --` | 422; no DB effect |
| ST-12 | XSS in chat message: `<script>alert('xss')</script>` | Stored as plain text; never executed |
| ST-13 | SSTI in chat message: `{{7*7}}` | Returned as literal string `{{7*7}}` |
| ST-14 | Path traversal in any string field: `../../../etc/passwd` | 422 or sanitised |
| ST-15 | Oversized request body (10MB JSON) | 413 `REQUEST_TOO_LARGE` |
| ST-16 | Null bytes in string fields: `player\x00admin` | 422 |

---

## OWASP Top 10 Verification

| OWASP ID | Test | Pass Condition |
|----------|------|---------------|
| A01 Broken Access Control | Access other user's data by manipulating IDs | 404 returned; no data leaked |
| A02 Cryptographic Failures | Intercept API traffic over HTTP | Redirect to HTTPS; HSTS header present |
| A03 Injection | All injection tests above | All pass |
| A05 Misconfig | Review response headers for security headers | `X-Content-Type-Options: nosniff` present |
| A07 Auth Failures | All auth tests above | All pass |
| A09 Security Logging | Trigger 5 failed logins; check Sentry | Alert fired within 1 minute |

---

## Sensitive Data Exposure

| ID | Test | Expected Result |
|----|------|----------------|
| ST-20 | Check error responses for stack traces | No stack trace in production |
| ST-21 | Check error responses for DB error messages | No raw SQL in responses |
| ST-22 | Check logs for password strings | Password never appears in logs |
| ST-23 | Check API responses for password_hash | Field never returned in any response |
| ST-24 | Search codebase for hardcoded API keys | Zero results |
| ST-25 | Verify `.env` not accessible via HTTP | Returns 404 |

---

## Rate Limiting Tests

| ID | Test | Expected Result |
|----|------|----------------|
| ST-30 | Send 31 requests in 1 minute as Free user | 31st request → 429 with `Retry-After` header |
| ST-31 | Send 301 requests in 1 minute as Premium user | 301st request → 429 |
| ST-32 | Send 6 registration requests from same IP in 1 hour | 6th request → 429 |
| ST-33 | Send 11 login attempts from same IP in 15 min | 11th attempt → 429 |

---

## Webhook Security

| ID | Test | Expected Result |
|----|------|----------------|
| ST-40 | Send Razorpay webhook with invalid signature | 400 `Invalid signature` |
| ST-41 | Replay a valid webhook (same ID, 2nd time) | 200 `already_processed` (idempotent) |
| ST-42 | Send webhook with `payment.captured` but wrong amount | 400 (validation failure) |
