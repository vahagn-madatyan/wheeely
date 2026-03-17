---
id: T03
parent: S02
milestone: M004
provides:
  - "get_current_user() async FastAPI dependency — verifies Supabase HS256 JWTs and returns user_id UUID"
  - "Key management Pydantic schemas: KeyStoreRequest, KeyStatusItem, KeyStatusResponse, KeyVerifyResponse"
key_files:
  - apps/api/services/auth.py
  - apps/api/tests/test_auth.py
  - apps/api/schemas.py
  - apps/api/requirements.txt
key_decisions:
  - "HTTPBearer returns 401 (not 403) for missing auth header in FastAPI >=0.109 — tests match actual behavior"
  - "Isolated test FastAPI app in test_auth.py to avoid polluting main app routes"
patterns_established:
  - "Test JWT creation via _make_token() helper with configurable sub/aud/exp/secret"
  - "Auth tests use isolated _test_app with single /test-auth endpoint depending on get_current_user"
observability_surfaces:
  - "logger.warning('auth_failed', extra={'reason': ...}) on expired/invalid/malformed tokens"
  - "401 responses include detail string describing failure reason (expired, invalid, missing sub)"
  - "Missing SUPABASE_JWT_SECRET raises ValueError at decode time — surfaces on first authenticated request"
duration: "10m"
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T03: Build JWT auth middleware with Pydantic schemas and tests

**Implemented JWT auth middleware with HS256 verification and key management Pydantic schemas, all 6 tests passing.**

## What Happened

1. Added `python-jose[cryptography]>=3.3.0` to `apps/api/requirements.txt` and installed.
2. Created `apps/api/services/auth.py` with `get_current_user()` async dependency using `HTTPBearer` + `jose.jwt.decode()` with HS256, audience="authenticated", and `SUPABASE_JWT_SECRET` env var. Structured logging on auth failures.
3. Appended 4 Pydantic models to `apps/api/schemas.py`: `KeyStoreRequest`, `KeyStatusItem`, `KeyStatusResponse`, `KeyVerifyResponse`. Existing models untouched.
4. Created `apps/api/tests/test_auth.py` with 6 tests covering valid token, expired, missing header, malformed, missing sub, and wrong secret scenarios. Uses isolated `_test_app` with a `/test-auth` endpoint.
5. Added Observability Impact section to T03-PLAN.md (pre-flight fix).

## Verification

- `python -m pytest apps/api/tests/test_auth.py -v` — **6/6 passed**
- `python -m pytest apps/api/tests/ -q` — **48 passed** (31 S01 + 11 encryption + 6 auth)
- `python -m pytest tests/ -q` — **425 passed**

Slice-level checks status:
- ✅ `test_encryption.py` — 11 passed
- ✅ `test_auth.py` — 6 passed
- ⏳ `test_keys_endpoints.py` — not yet created (T04)

## Diagnostics

- **Auth failures:** `logger.warning("auth_failed", extra={"reason": ...})` emitted on expired, invalid, or malformed tokens.
- **401 detail strings:** "Token has expired", "Invalid token", "Token missing sub claim" — describe failure reason without leaking secrets.
- **Missing env var:** `SUPABASE_JWT_SECRET` absence raises `ValueError` at first authenticated request.
- **Run tests:** `python -m pytest apps/api/tests/test_auth.py -v`

## Deviations

- **HTTPBearer 401 vs 403:** Plan specified 403 for missing Authorization header. FastAPI 0.135.1 (`HTTPBearer`) returns 401. Test updated to match actual behavior. Recorded in `.gsd/KNOWLEDGE.md`.

## Known Issues

None.

## Files Created/Modified

- `apps/api/services/auth.py` — JWT auth middleware with `get_current_user()` dependency (new)
- `apps/api/tests/test_auth.py` — 6 auth tests with isolated test app (new)
- `apps/api/schemas.py` — Appended KeyStoreRequest, KeyStatusItem, KeyStatusResponse, KeyVerifyResponse models
- `apps/api/requirements.txt` — Added `python-jose[cryptography]>=3.3.0`
- `.gsd/milestones/M004/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section
- `.gsd/KNOWLEDGE.md` — Created with HTTPBearer 401 vs 403 gotcha
