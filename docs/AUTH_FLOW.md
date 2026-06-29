# Authentication Flow

**Method:** JWT (JSON Web Tokens)  
**Algorithm:** HS256  
**Access token expiry:** 24 hours  
**Refresh token expiry:** 30 days

---

## Registration Flow

```
Client                          API Server                     Database
  │                                  │                              │
  │  POST /api/v1/auth/register      │                              │
  │  {email, password, full_name}    │                              │
  │─────────────────────────────────►│                              │
  │                                  │ Validate email format        │
  │                                  │ Check password strength      │
  │                                  │ SELECT email FROM user       │
  │                                  │─────────────────────────────►│
  │                                  │◄─────────────────────────────│
  │                                  │ Email not taken?             │
  │                                  │ Hash password (bcrypt, 12)   │
  │                                  │ INSERT INTO user             │
  │                                  │─────────────────────────────►│
  │                                  │◄─────────────────────────────│
  │                                  │ Send verification email      │
  │                                  │ Generate access_token (JWT)  │
  │◄─────────────────────────────────│                              │
  │  201 {access_token, user}        │                              │
```

---

## Login Flow

```
Client                          API Server
  │                                  │
  │  POST /api/v1/auth/login         │
  │  {email, password}               │
  │─────────────────────────────────►│
  │                                  │ Fetch user by email
  │                                  │ bcrypt.verify(password, hash)
  │                                  │ Generate access_token
  │                                  │ Generate refresh_token
  │                                  │ Update last_login_at
  │◄─────────────────────────────────│
  │  200 {access_token,              │
  │       refresh_token,             │
  │       expires_in: 86400}         │
```

---

## Authenticated Request Flow

```
Client                          API Server                     Redis
  │                                  │                            │
  │  GET /api/v1/predict/team        │                            │
  │  Authorization: Bearer <token>   │                            │
  │─────────────────────────────────►│                            │
  │                                  │ Decode JWT                 │
  │                                  │ Verify signature           │
  │                                  │ Check expiry               │
  │                                  │ Check revocation list      │
  │                                  │───────────────────────────►│
  │                                  │◄───────────────────────────│
  │                                  │ Extract user_id, role      │
  │                                  │ Check rate limit           │
  │                                  │───────────────────────────►│
  │                                  │◄───────────────────────────│
  │                                  │ Process request...         │
  │◄─────────────────────────────────│                            │
  │  200 {response}                  │                            │
```

---

## Token Refresh Flow

```
Client                          API Server
  │                                  │
  │  POST /api/v1/auth/refresh       │
  │  {refresh_token: "..."}          │
  │─────────────────────────────────►│
  │                                  │ Verify refresh token
  │                                  │ Check not revoked
  │                                  │ Generate new access_token
  │                                  │ Optionally rotate refresh_token
  │◄─────────────────────────────────│
  │  200 {access_token,              │
  │       expires_in: 86400}         │
```

---

## JWT Payload Structure

```json
{
  "sub": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "role": "premium",
  "email": "rahul@example.com",
  "iat": 1750830000,
  "exp": 1750916400,
  "jti": "unique-token-id-for-revocation"
}
```

---

## Token Storage (Client-Side)

- **Web:** Store `access_token` in memory (not localStorage); `refresh_token` in httpOnly cookie
- **Mobile:** Secure storage (Keychain on iOS, Keystore on Android)
- **Never** store tokens in localStorage (XSS risk)

---

## Token Revocation

Revoked tokens stored in Redis as `revoked:jti:{token_jti}` with TTL = remaining token lifetime.  
Checked on every authenticated request before processing.

---

## Error Responses

| Scenario | HTTP | Code |
|----------|------|------|
| No Authorization header | 401 | `MISSING_TOKEN` |
| Malformed JWT | 401 | `INVALID_TOKEN` |
| Expired access token | 401 | `EXPIRED_TOKEN` |
| Revoked token | 401 | `REVOKED_TOKEN` |
| Wrong role | 403 | `INSUFFICIENT_ROLE` |
