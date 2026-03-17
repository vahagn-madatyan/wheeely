---
estimated_steps: 7
estimated_files: 5
---

# T04: Build key management endpoints, wire into main.py, verify full suite

**Slice:** S02 — Supabase auth + database + encrypted key storage
**Milestone:** M004

## Description

Integrate the encryption service (T01), database pool (T02), and auth middleware (T03) into 4 key management endpoints that S04's frontend will consume. Wire the new router into `main.py`. Write endpoint tests with mocked DB and encryption. Run the complete test suite to prove nothing is broken.

This is the integration task — it brings all three independent units together and exercises the full contract that downstream slices depend on.

## Steps

1. **Create `apps/api/routers/keys.py`** — Implement router with `prefix="/api/keys"`, `tags=["keys"]`. All 4 endpoints use `user_id: str = Depends(get_current_user)` for authentication:

   **`POST /{provider}`** — Store an API key:
   - Validate `provider` is "alpaca" or "finnhub" (raise 422 otherwise)
   - Accept `KeyStoreRequest` body (`key_value: str`, `is_paper: Optional[bool]`)
   - For alpaca: the `key_name` must be specified or inferred. Alpaca requires TWO keys stored separately (api_key + secret_key). Accept an additional path or body param to distinguish. Simplest approach: provider path is `alpaca_key`, `alpaca_secret`, `finnhub` — OR — keep provider as `alpaca`/`finnhub` and add a `key_name` field to `KeyStoreRequest`. **Use the body field approach**: add `key_name: str` to `KeyStoreRequest` with allowed values: `"api_key"`, `"secret_key"` for alpaca, `"api_key"` for finnhub.
   - Call `encrypt_value(request.key_value)` to get `(encrypted_value, encrypted_dek, nonce, dek_nonce)`
   - Upsert into `api_keys` table: `INSERT ... ON CONFLICT (user_id, provider, key_name) DO UPDATE SET encrypted_value=..., encrypted_dek=..., nonce=..., dek_nonce=..., is_paper=..., updated_at=now()`
   - Return `{"status": "stored", "provider": provider, "key_name": key_name}`
   - DB interaction: use `db: asyncpg.Connection = Depends(get_db)` dependency

   **`GET /status`** — List stored key providers:
   - Query `SELECT DISTINCT provider, key_name, is_paper FROM api_keys WHERE user_id = $1`
   - Group by provider, return list of `KeyStatusItem` (provider, connected=True, is_paper from first row, key_names list)
   - NEVER return key values — only which providers have keys stored
   - Return `KeyStatusResponse`

   **`DELETE /{provider}`** — Remove all keys for a provider:
   - `DELETE FROM api_keys WHERE user_id = $1 AND provider = $2`
   - Return `{"status": "deleted", "provider": provider}`

   **`POST /{provider}/verify`** — Test key connectivity:
   - Fetch all keys for user+provider from DB
   - Decrypt each via `decrypt_value()`
   - For alpaca: construct `TradingClient` from decrypted api_key + secret_key, call `get_account()` in `asyncio.to_thread()`
   - For finnhub: construct `FinnhubClient` from decrypted key, call a lightweight endpoint
   - Return `KeyVerifyResponse(provider=provider, valid=True/False, error=str(exc) if failed)`
   - Catch exceptions and return valid=False with error message (don't expose stack traces)

2. **Update `apps/api/schemas.py`** — If T03 didn't add `key_name` to `KeyStoreRequest`, add it now: `key_name: str = Field(..., description="Key identifier: api_key, secret_key, or finnhub_key")`. Ensure all Pydantic models from T03 are present.

3. **Wire router into `apps/api/main.py`** — Add:
   ```python
   from apps.api.routers import keys
   app.include_router(keys.router)
   ```
   Do NOT add auth middleware globally — only the new `keys` router uses `get_current_user`. S01 endpoints (`screen`, `positions`) remain unprotected for now (S05 refactors them).

4. **Update `apps/api/tests/conftest.py`** — Add auth helper fixtures:
   - `TEST_JWT_SECRET` and `TEST_USER_ID` constants
   - `mock_auth` fixture: overrides `get_current_user` dependency on the app to return `TEST_USER_ID` without JWT validation. Use `app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID` pattern.
   - `auth_headers` fixture: returns `{"Authorization": f"Bearer {valid_test_jwt}"}` with a JWT crafted using `python-jose` and `TEST_JWT_SECRET`.
   - `mock_db` fixture: returns a `MagicMock` or `AsyncMock` that mimics asyncpg connection. Override `get_db` dependency.

5. **Create `apps/api/tests/test_keys_endpoints.py`** — Write endpoint tests with mocked DB:
   - `test_store_alpaca_key`: POST `/api/keys/alpaca` with `{"key_value": "test-key", "key_name": "api_key"}` → 200, status="stored"
   - `test_store_finnhub_key`: POST `/api/keys/finnhub` with `{"key_value": "fh-key", "key_name": "api_key"}` → 200
   - `test_store_invalid_provider`: POST `/api/keys/invalid` → 422
   - `test_get_key_status`: GET `/api/keys/status` → returns providers list with connected=True, no key values exposed
   - `test_get_key_status_empty`: GET `/api/keys/status` with no keys stored → empty list
   - `test_delete_keys`: DELETE `/api/keys/alpaca` → 200, status="deleted"
   - `test_verify_alpaca_keys_success`: POST `/api/keys/alpaca/verify` with mocked successful `get_account()` → valid=True
   - `test_verify_alpaca_keys_failure`: POST `/api/keys/alpaca/verify` with mocked failed API call → valid=False, error message present
   - `test_unauthenticated_request_rejected`: Request without auth → 403 (no `mock_auth` override)
   - All tests use `mock_auth` and `mock_db` fixtures from conftest. Tests verify that stored values are encrypted (not plaintext in mock DB calls).

6. **Verify full test suite** — Run in sequence:
   - `python -m pytest apps/api/tests/test_keys_endpoints.py -v` — new tests pass
   - `python -m pytest apps/api/tests/ -q` — all API tests pass (S01 31 + S02 new)
   - `python -m pytest tests/ -q` — 425 CLI tests still pass

7. **Verify no plaintext leakage** — In the store endpoint test, assert that the mock DB insert call received `bytes` values for `encrypted_value`/`encrypted_dek`/`nonce`/`dek_nonce` — not the original plaintext string.

## Must-Haves

- [ ] `POST /api/keys/{provider}` encrypts and stores key (not plaintext)
- [ ] `GET /api/keys/status` returns provider list without key values
- [ ] `DELETE /api/keys/{provider}` removes keys
- [ ] `POST /api/keys/{provider}/verify` tests key connectivity
- [ ] All endpoints require `get_current_user` authentication
- [ ] Provider validation: only "alpaca" and "finnhub" accepted
- [ ] Router wired into `main.py` without breaking S01 endpoints
- [ ] Unauthenticated requests return 403 (no token) or 401 (bad token)
- [ ] 31 S01 API tests still pass
- [ ] 425 CLI tests still pass

## Verification

- `source .venv/bin/activate && python -m pytest apps/api/tests/test_keys_endpoints.py -v` — all key endpoint tests pass
- `source .venv/bin/activate && python -m pytest apps/api/tests/ -q` — all API tests pass (S01 + S02)
- `source .venv/bin/activate && python -m pytest tests/ -q` — 425 CLI tests pass

## Observability Impact

- Signals added/changed: `logger.info("key_stored", ...)` on successful store, `logger.info("key_deleted", ...)` on delete, `logger.info("key_verified", ...)` with valid=True/False on verify. `logger.warning("auth_failed", ...)` propagated from auth.py.
- How a future agent inspects this: `GET /api/keys/status` returns current key state per user. Logs show key operations without plaintext values.
- Failure state exposed: verify endpoint returns `valid=False` with sanitized error message. Auth failures return 401/403 with reason in `detail`.

## Inputs

- `apps/api/services/encryption.py` — T01's `encrypt_value()` and `decrypt_value()` functions
- `apps/api/services/auth.py` — T03's `get_current_user()` dependency
- `apps/api/services/database.py` — T02's `get_db()` dependency
- `apps/api/schemas.py` — T03's `KeyStoreRequest`, `KeyStatusItem`, `KeyStatusResponse`, `KeyVerifyResponse`
- `apps/api/services/clients.py` — S01's `create_alpaca_clients()` for verify endpoint
- `apps/api/main.py` — existing app with screen + positions routers
- `apps/api/tests/conftest.py` — existing fixtures with `app_client`, `ALPACA_KEYS`, etc.

## Expected Output

- `apps/api/routers/keys.py` — 4 key management endpoints with auth + encryption + DB
- `apps/api/tests/test_keys_endpoints.py` — 9+ endpoint tests with mocked DB
- `apps/api/main.py` — updated with `keys.router` included
- `apps/api/tests/conftest.py` — updated with `mock_auth`, `auth_headers`, `mock_db` fixtures
- `apps/api/schemas.py` — may be updated if `key_name` field needed on `KeyStoreRequest`
