---
estimated_steps: 5
estimated_files: 4
---

# T03: Build JWT auth middleware with Pydantic schemas and tests

**Slice:** S02 — Supabase auth + database + encrypted key storage
**Milestone:** M004

## Description

Implement the JWT authentication middleware that protects all new endpoints and produce the Pydantic request/response models for key management. The auth middleware is a FastAPI dependency (`get_current_user`) that extracts a Bearer token from the Authorization header, verifies it with the Supabase JWT secret using HS256, and returns the user_id UUID string. Supabase uses HS256 by default — simpler than RS256/JWKS.

The key management Pydantic schemas are defined here (not in T04) so T04 can focus purely on endpoint logic and wiring.

## Steps

1. **Add `python-jose` to requirements** — Append `python-jose[cryptography]>=3.3.0` to `apps/api/requirements.txt`. Install it. Note: `python-jose[cryptography]` uses the `cryptography` backend (already installed from T01) for better performance.

2. **Create `apps/api/services/auth.py`** — Implement:
   ```python
   from fastapi import Depends, HTTPException, status
   from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
   from jose import jwt, JWTError, ExpiredSignatureError
   import os
   import logging

   logger = logging.getLogger(__name__)
   security = HTTPBearer()

   def _get_jwt_secret() -> str:
       secret = os.environ.get("SUPABASE_JWT_SECRET")
       if not secret:
           raise ValueError("SUPABASE_JWT_SECRET environment variable is not set")
       return secret

   async def get_current_user(
       credentials: HTTPAuthorizationCredentials = Depends(security),
   ) -> str:
       token = credentials.credentials
       try:
           payload = jwt.decode(
               token,
               _get_jwt_secret(),
               algorithms=["HS256"],
               audience="authenticated",
           )
       except ExpiredSignatureError:
           logger.warning("auth_failed", extra={"reason": "token_expired"})
           raise HTTPException(status_code=401, detail="Token has expired")
       except JWTError as e:
           logger.warning("auth_failed", extra={"reason": str(e)})
           raise HTTPException(status_code=401, detail="Invalid token")

       user_id = payload.get("sub")
       if not user_id:
           raise HTTPException(status_code=401, detail="Token missing sub claim")
       return user_id
   ```
   Key details: `HTTPBearer()` automatically returns 403 when no Authorization header is present. The `audience="authenticated"` matches Supabase's default JWT audience claim.

3. **Add key management Pydantic schemas to `apps/api/schemas.py`** — Append these models (do NOT modify existing models):
   - `KeyStoreRequest(BaseModel)`: `key_value: str` (the plaintext API key), `is_paper: Optional[bool] = None` (only used for alpaca provider)
   - `KeyStatusItem(BaseModel)`: `provider: str`, `connected: bool`, `is_paper: Optional[bool] = None`, `key_names: list[str]` (which key_names are stored, e.g. ["api_key", "secret_key"])
   - `KeyStatusResponse(BaseModel)`: `providers: list[KeyStatusItem]`
   - `KeyVerifyResponse(BaseModel)`: `provider: str`, `valid: bool`, `error: Optional[str] = None`

4. **Create `apps/api/tests/test_auth.py`** — Write tests using `python-jose` to craft test JWTs:
   ```python
   TEST_JWT_SECRET = "test-supabase-jwt-secret-at-least-32-chars-long!!"
   TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"
   ```
   - `test_valid_token_returns_user_id`: Create JWT with `sub=TEST_USER_ID`, `aud="authenticated"`, `exp=future`. Make a request to a test endpoint that uses `get_current_user`. Assert returns 200 with correct user_id.
   - `test_expired_token_returns_401`: Create JWT with `exp=past`. Assert 401 with "expired" in detail.
   - `test_missing_auth_header_returns_403`: Request without Authorization header. Assert 403 (HTTPBearer default).
   - `test_malformed_token_returns_401`: Send `Authorization: Bearer not-a-jwt`. Assert 401.
   - `test_missing_sub_claim_returns_401`: Create valid JWT but without `sub` field. Assert 401 with "sub" in detail.
   - `test_wrong_secret_returns_401`: Create JWT signed with different secret. Assert 401.
   - Create a tiny test endpoint in the test file: `@app.get("/test-auth")` that depends on `get_current_user` and returns `{"user_id": user_id}`. Use `monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)`.

5. **Verify** — Run auth tests and confirm existing tests still pass.

## Must-Haves

- [ ] `get_current_user()` is an async FastAPI dependency using `HTTPBearer`
- [ ] Verifies HS256 JWT with `SUPABASE_JWT_SECRET` env var and `audience="authenticated"`
- [ ] Returns user_id (UUID string) from `sub` claim
- [ ] Expired tokens return 401
- [ ] Missing Authorization header returns 403
- [ ] Malformed/wrong-secret tokens return 401
- [ ] Missing `sub` claim returns 401
- [ ] Key management Pydantic schemas added to `schemas.py` without modifying existing models
- [ ] `python-jose[cryptography]>=3.3.0` added to `apps/api/requirements.txt`

## Verification

- `source .venv/bin/activate && pip install "python-jose[cryptography]>=3.3.0" && python -m pytest apps/api/tests/test_auth.py -v` — all 6+ tests pass
- `source .venv/bin/activate && python -m pytest apps/api/tests/ -q` — S01 tests still pass
- `source .venv/bin/activate && python -m pytest tests/ -q` — 425 CLI tests still pass

## Observability Impact

- **New log events:** `logger.warning("auth_failed", extra={"reason": ...})` emitted on expired, malformed, or invalid tokens — enables auth failure monitoring.
- **Inspection surface:** `get_current_user()` dependency returns 401/403 with structured `detail` messages describing failure reason (expired, invalid, missing sub). No secrets in error responses.
- **Failure visibility:** Missing `SUPABASE_JWT_SECRET` env var raises `ValueError` at decode time — surfaces immediately on first authenticated request, not silently.
- **Downstream impact:** T04 endpoints will depend on `get_current_user` — auth failures propagate as 401/403 before any business logic runs.

## Inputs

- `apps/api/schemas.py` — existing file with `AlpacaKeysMixin`, screen/position models (do not modify these)
- `apps/api/requirements.txt` — file from T01/T02 with cryptography and asyncpg already added
- `apps/api/tests/conftest.py` — existing fixtures (will be extended in T04, not this task)

## Expected Output

- `apps/api/services/auth.py` — JWT auth middleware with `get_current_user()` dependency
- `apps/api/tests/test_auth.py` — 6+ tests covering all JWT validation scenarios
- `apps/api/schemas.py` — updated with `KeyStoreRequest`, `KeyStatusItem`, `KeyStatusResponse`, `KeyVerifyResponse` appended
- `apps/api/requirements.txt` — updated with `python-jose[cryptography]>=3.3.0`
