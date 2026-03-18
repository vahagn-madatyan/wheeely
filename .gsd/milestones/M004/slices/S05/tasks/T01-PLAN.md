---
estimated_steps: 7
estimated_files: 6
---

# T01: Switch screen + positions endpoints to auth + DB-stored keys

**Slice:** S05 — Screener UI
**Milestone:** M004

## Description

The screen and positions endpoints currently accept raw Alpaca API keys in request bodies (`PutScreenRequest`, `CallScreenRequest`) and query params (`GET /api/positions`, `GET /api/account`). The frontend doesn't have raw key values — they're encrypted in the DB — so these endpoints must switch to JWT auth + key retrieval from the DB using the same pattern established in `keys.py:verify_keys` (lines 162-206).

This task creates a shared `retrieve_alpaca_keys()` helper, updates both routers and their schemas, adds auth to the poll endpoint, and rewrites all 19 API tests to use `mock_auth` + `mock_db` fixtures from conftest.py.

## Steps

1. **Create `apps/api/services/key_retrieval.py`** — a `retrieve_alpaca_keys(user_id: str, db: asyncpg.Connection) -> tuple[str, str, bool]` function that:
   - Queries `SELECT key_name, encrypted_value, encrypted_dek, nonce, dek_nonce, is_paper FROM api_keys WHERE user_id = $1 AND provider = 'alpaca'`
   - If no rows, raises `HTTPException(400, "Alpaca API keys not configured. Add keys in Settings.")`
   - Decrypts each row using `decrypt_value()` from `services/encryption.py`
   - Validates both `api_key` and `secret_key` are present, raises 400 if not
   - Returns `(api_key, secret_key, is_paper)` with `is_paper` defaulting to `True` if `None`
   - Logs `"keys_retrieved"` on success with `provider` and `user_id` in extras (never logs key values)

2. **Update `apps/api/schemas.py`** — modify the screening request models:
   - `PutScreenRequest`: change from inheriting `AlpacaKeysMixin` to inheriting `BaseModel` directly. Keep only `symbols`, `buying_power`, `preset` fields.
   - `CallScreenRequest`: same change — keep only `symbol`, `cost_basis`, `preset`.
   - Remove `PositionsQuery` and `AccountQuery` models entirely (no longer needed — positions/account use auth now).
   - Keep `AlpacaKeysMixin` itself in the file — `KeyStoreRequest` doesn't use it, but it's still imported in type annotations. **Actually** — verify no other schema uses it. If `KeyStoreRequest` is independent (it is — it has its own fields), then `AlpacaKeysMixin` can be removed entirely. Check imports first.
   - Keep `KeyStoreRequest` untouched.

3. **Update `apps/api/routers/screen.py`** — wire auth + key retrieval:
   - Import `get_current_user` from `services.auth`, `get_db` from `services.database`, `retrieve_alpaca_keys` from `services.key_retrieval`.
   - For `submit_put_screen`: add `user_id: str = Depends(get_current_user)` and `db = Depends(get_db)` params. Replace `body.alpaca_api_key`/`body.alpaca_secret_key`/`body.is_paper` with `retrieve_alpaca_keys(user_id, db)` call. The `create_alpaca_clients()` call uses the retrieved values.
   - For `submit_call_screen`: same change.
   - For `get_run_status` (poll endpoint): add `user_id: str = Depends(get_current_user)` to require auth. No DB needed — just proving the user is authenticated. (Optionally: store user_id on TaskStore entries to prevent cross-user polling — but this is a defense-in-depth concern for S07.)
   - Remove `AlpacaKeysMixin` import if no longer used here.

4. **Update `apps/api/routers/positions.py`** — same auth + key retrieval pattern:
   - Import `get_current_user`, `get_db`, `retrieve_alpaca_keys`.
   - For `get_positions`: replace query params with `user_id = Depends(get_current_user)` and `db = Depends(get_db)`. Call `retrieve_alpaca_keys(user_id, db)` to get keys.
   - For `get_account`: same change.
   - Remove `Query` and `Depends` imports that are no longer needed; add `Depends` if not already present.

5. **Update `apps/api/tests/test_screen_endpoints.py`** — rewrite 11 tests:
   - Instead of passing `ALPACA_KEYS` in JSON bodies, use the `mock_auth` and `mock_db` fixtures from conftest.py.
   - Mock `retrieve_alpaca_keys` at `apps.api.routers.screen.retrieve_alpaca_keys` to return `("test-key", "test-secret", True)`.
   - Add `Authorization: Bearer <token>` headers using `auth_headers` fixture from conftest.
   - Add new tests: (a) missing auth returns 401, (b) missing keys returns 400.
   - Request bodies should now contain only screening params: `{"symbols": ["AAPL"], "buying_power": 50000.0}` (no key fields).
   - Poll endpoint tests also need auth headers now.

6. **Update `apps/api/tests/test_positions_account.py`** — rewrite 8 tests:
   - Same pattern: use `mock_auth`, mock `retrieve_alpaca_keys`, use `auth_headers`.
   - Remove `ALPACA_QUERY_PARAMS` from all `params=` calls.
   - Positions/account endpoints are now `GET /api/positions` and `GET /api/account` with no query params (just Bearer token).
   - Update missing-keys tests: instead of testing 422 for missing query params, test 401 for missing auth and 400 for missing stored keys.

7. **Run both test suites** — verify:
   - `python -m pytest apps/api/tests/ -v` — all pass
   - `python -m pytest tests/ -q` — 425 pass

## Must-Haves

- [ ] `retrieve_alpaca_keys()` helper exists in `services/key_retrieval.py` and is used by both `screen.py` and `positions.py`
- [ ] `PutScreenRequest` and `CallScreenRequest` no longer contain Alpaca key fields
- [ ] `PositionsQuery` and `AccountQuery` are removed from schemas
- [ ] All screen/positions endpoints require `Depends(get_current_user)`
- [ ] Poll endpoint requires auth
- [ ] All API tests pass with mock auth + mock key retrieval (no raw keys in test payloads)
- [ ] 425 CLI tests still pass

## Verification

- `python -m pytest apps/api/tests/ -v` — all tests pass (expect ≥21 tests: 11 screen + 8 positions + 2 new error-path tests)
- `python -m pytest tests/ -q` — 425 passed
- `grep -c "ALPACA_KEYS" apps/api/tests/test_screen_endpoints.py` returns 0 (no raw keys in screen test payloads)
- `grep -c "ALPACA_QUERY_PARAMS" apps/api/tests/test_positions_account.py` returns 0 (no raw keys in position test payloads)
- `python -c "from apps.api.services.key_retrieval import retrieve_alpaca_keys; print('OK')"` — import succeeds

## Observability Impact

- Signals added: `retrieve_alpaca_keys` logs `"keys_retrieved"` with `provider=alpaca` and `user_id` on success
- How a future agent inspects this: check `apps.api.services.key_retrieval` logs; HTTPException messages are descriptive ("Alpaca API keys not configured. Add keys in Settings.", "Alpaca requires both api_key and secret_key", "Failed to decrypt stored keys")
- Failure state exposed: 400 for missing/incomplete keys, 401 for missing auth, 502 for Alpaca API errors (unchanged)

## Inputs

- `apps/api/routers/keys.py:162-206` — the `verify_keys` endpoint is the pattern to copy for key retrieval + decryption. The exact query, decrypt loop, and validation logic are authoritative.
- `apps/api/services/auth.py` — `get_current_user` dependency, returns `user_id: str`
- `apps/api/services/database.py` — `get_db` dependency, yields `asyncpg.Connection`
- `apps/api/services/encryption.py` — `decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce) -> str`
- `apps/api/tests/conftest.py` — provides `mock_auth`, `mock_db`, `auth_headers`, `mock_encryption` fixtures. `mock_auth` overrides `get_current_user` to return `TEST_USER_ID`. `mock_db` provides an `AsyncMock` connection.
- `apps/api/schemas.py` — current schemas with `AlpacaKeysMixin`. `KeyStoreRequest` is independent and must NOT be changed.

## Expected Output

- `apps/api/services/key_retrieval.py` — new file, ~50 lines, exports `retrieve_alpaca_keys()`
- `apps/api/schemas.py` — `PutScreenRequest` and `CallScreenRequest` no longer inherit `AlpacaKeysMixin`. `PositionsQuery` and `AccountQuery` removed. `AlpacaKeysMixin` itself removed if no other schema uses it.
- `apps/api/routers/screen.py` — all 3 endpoints use `Depends(get_current_user)`. PUT/CALL submit endpoints use `retrieve_alpaca_keys()`. No `body.alpaca_api_key` references.
- `apps/api/routers/positions.py` — both endpoints use `Depends(get_current_user)` + `retrieve_alpaca_keys()`. No query params for keys.
- `apps/api/tests/test_screen_endpoints.py` — all tests use mock auth + mock key retrieval. ≥13 tests (11 existing + 2 new error paths).
- `apps/api/tests/test_positions_account.py` — all tests use mock auth + mock key retrieval. ≥10 tests (8 existing + 2 new error paths).
