---
id: S02
parent: M004
milestone: M004
provides:
  - Envelope encryption service (encrypt_value / decrypt_value) with per-key random DEK wrapped by APP_ENCRYPTION_SECRET
  - SQL migration with 4 tables (profiles, api_keys, screening_runs, screening_results), RLS policies, profile auto-creation trigger
  - JWT auth middleware (get_current_user FastAPI dependency) verifying Supabase HS256 tokens
  - Async database connection pool via asyncpg (get_db_pool, get_db, close_db_pool)
  - 4 key management endpoints (POST store, GET status, DELETE, POST verify) with auth + encryption + DB integration
  - Key management Pydantic schemas (KeyStoreRequest, KeyStatusItem, KeyStatusResponse, KeyVerifyResponse)
  - Test fixtures (mock_auth, mock_db, mock_encryption) reusable by downstream S04-S06 tests
requires: []
affects:
  - S03  # consumes Supabase auth config, JWT middleware, profiles table
  - S04  # consumes api_keys table, key CRUD endpoints, encryption service
  - S05  # consumes screening_runs/results tables, key decryption for screener clients
  - S06  # consumes screening tables for rate limiting, key decryption for positions
  - S07  # consumes all auth + DB infrastructure for deployment
key_files:
  - apps/api/services/encryption.py
  - apps/api/services/auth.py
  - apps/api/services/database.py
  - apps/api/routers/keys.py
  - apps/api/migrations/001_initial_schema.sql
  - apps/api/tests/test_encryption.py
  - apps/api/tests/test_auth.py
  - apps/api/tests/test_keys_endpoints.py
  - apps/api/tests/conftest.py
  - apps/api/schemas.py
  - apps/api/main.py
  - apps/api/requirements.txt
key_decisions:
  - "D054: Envelope encryption with APP_ENCRYPTION_SECRET wrapping per-key DEKs (AESGCM 256-bit)"
  - "D059: asyncpg with connection pool (min=2, max=10) for async Supabase Postgres access"
  - "D060: HS256 JWT verification with SUPABASE_JWT_SECRET, audience=authenticated"
  - "RLS policies use (select auth.uid()) subselect pattern per Supabase best practices"
  - "Pure crypto functions with no logging — key material must never appear in log output"
  - "Verify endpoint uses asyncio.to_thread for blocking Alpaca/Finnhub SDK calls"
  - "Provider validation via explicit set check + 422, not Enum path parameter"
patterns_established:
  - "Envelope encryption: per-value random DEK + nonces, KEK from env var, 4-tuple return (encrypted_value, encrypted_dek, nonce, dek_nonce)"
  - "Auth dependency: Depends(get_current_user) returns user_id UUID string from JWT sub claim"
  - "Test fixtures: mock_auth overrides get_current_user, mock_db provides AsyncMock connection, mock_encryption sets APP_ENCRYPTION_SECRET"
  - "Migration files in apps/api/migrations/ numbered sequentially (001_, 002_, etc.)"
  - "Module-level pool cache with lazy init — import never fails, pool created on first use"
observability_surfaces:
  - "logger.info('key_stored', provider=..., key_name=..., user_id=...) on successful key storage"
  - "logger.info('key_deleted', provider=..., user_id=...) on key deletion"
  - "logger.info('key_verified', provider=..., valid=True/False) on verify"
  - "logger.warning('auth_failed', extra={'reason': ...}) on expired/invalid/malformed JWT"
  - "logger.warning('key_verify_decrypt_failed', ...) when decryption fails at verify time"
  - "GET /api/keys/status — runtime key state per user without exposing values"
  - "401 responses include detail string describing failure reason (expired, invalid, missing sub)"
  - "ValueError on missing APP_ENCRYPTION_SECRET, SUPABASE_JWT_SECRET, or DATABASE_URL"
drill_down_paths:
  - .gsd/milestones/M004/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M004/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M004/slices/S02/tasks/T03-SUMMARY.md
  - .gsd/milestones/M004/slices/S02/tasks/T04-SUMMARY.md
duration: 41m
verification_result: passed
completed_at: 2026-03-16
---

# S02: Supabase auth + database + encrypted key storage

**Envelope encryption, JWT auth, 4-table schema with RLS, and key management CRUD endpoints — all wired, tested (31 S02 tests), with zero regressions (425 CLI + 31 S01 tests pass).**

## What Happened

Built the security and data foundation for multi-tenant key storage in four tasks:

**T01 (encryption):** Implemented two-layer AES-GCM envelope encryption in `apps/api/services/encryption.py`. Each `encrypt_value()` call generates a fresh random 256-bit DEK and two 12-byte nonces, encrypts the plaintext with the DEK, then wraps the DEK with the KEK loaded from `APP_ENCRYPTION_SECRET` env var. `decrypt_value()` reverses the process. Pure functions with no logging — crypto ops must never emit key material. 11 tests cover round-trip, wrong KEK rejection (InvalidTag), nonce uniqueness, empty/long/unicode strings, and malformed KEK env vars.

**T02 (database):** Created `apps/api/migrations/001_initial_schema.sql` with all 4 tables (`profiles`, `api_keys`, `screening_runs`, `screening_results`), RLS policies using the `(select auth.uid())` subselect pattern, and a `handle_new_user()` trigger function with `security definer set search_path = ''`. Built `apps/api/services/database.py` with a module-level asyncpg connection pool (lazy init, min=2, max=10) and `get_db()` FastAPI dependency.

**T03 (auth):** Built `apps/api/services/auth.py` with `get_current_user()` async FastAPI dependency that verifies Supabase HS256 JWTs using `python-jose`, audience="authenticated", extracting user_id from the `sub` claim. Added structured warning logs on auth failures with reason strings. Created key management Pydantic schemas (`KeyStoreRequest`, `KeyStatusItem`, `KeyStatusResponse`, `KeyVerifyResponse`) in `schemas.py`. 6 tests with isolated test app cover valid/expired/malformed/missing-sub/wrong-secret token scenarios.

**T04 (key endpoints):** Created `apps/api/routers/keys.py` with 4 endpoints integrating encryption + auth + DB: `POST /api/keys/{provider}` (encrypt and store), `GET /api/keys/status` (list providers, never expose values), `DELETE /api/keys/{provider}` (remove all keys), `POST /api/keys/{provider}/verify` (decrypt, test connectivity via `asyncio.to_thread`). Wired into `main.py`. Added reusable `mock_auth`, `mock_db`, `mock_encryption` fixtures to `conftest.py`. 14 endpoint tests with mocked DB verify store/status/delete/verify flows and auth enforcement.

## Verification

All 5 slice-level verification checks pass:

| Check | Result |
|-------|--------|
| `python -m pytest apps/api/tests/test_encryption.py -v` | **11 passed** |
| `python -m pytest apps/api/tests/test_auth.py -v` | **6 passed** |
| `python -m pytest apps/api/tests/test_keys_endpoints.py -v` | **14 passed** |
| `python -m pytest tests/ -q` | **425 passed** (CLI unchanged) |
| `python -m pytest apps/api/tests/ -q` | **62 passed** (31 S01 + 31 S02) |

Additional checks:
- Plaintext leakage: `test_store_alpaca_key` asserts DB mock received `bytes` for all encrypted fields and original key value not present in ciphertext
- Observability: `logger.warning("auth_failed")` and `logger.info("key_stored"/"key_deleted"/"key_verified")` confirmed in source

## Requirements Advanced

- **WEB-01** — JWT auth middleware verifies Supabase tokens; `get_current_user` dependency ready for all authenticated endpoints; profiles table auto-created on signup via trigger
- **WEB-02** — Alpaca keys encrypted via envelope encryption (AESGCM); store/status/delete/verify endpoints operational; paper/live toggle supported via `is_paper` field on `KeyStoreRequest`
- **WEB-03** — Finnhub key encrypted identically to Alpaca keys; same CRUD endpoints, same encryption service
- **WEB-10** — RLS policies on all 4 tables enforce `(select auth.uid())` isolation; endpoint tests verify unauthenticated requests rejected

## Requirements Validated

- None moved to validated — S02 proves contract-level behavior (mocked DB); real Supabase integration validation deferred to S07 deployment

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **HTTPBearer 401 vs 403:** Plan specified 403 for missing Authorization header. FastAPI 0.135.1 returns 401. Tests updated to match actual behavior. Recorded in `.gsd/KNOWLEDGE.md`.
- **key_name in KeyStoreRequest body:** Plan had separate path params per key type. T04 added `key_name: str` field to body for cleaner REST contract — allows alpaca to store `api_key` and `secret_key` separately while finnhub stores `api_key`.
- **Finnhub key_name:** Plan suggested `"finnhub_key"` as key_name. Used `"api_key"` instead for cross-provider naming consistency.

## Known Limitations

- **No real DB tests:** All endpoint tests use mocked asyncpg connections. Real Supabase integration requires a running instance — validated manually or during S07 deployment.
- **S01 endpoints remain unprotected:** Auth middleware exists but is not retrofitted onto S01's screening/positions endpoints. S04-S05 will wire auth into those endpoints.
- **Migration not auto-applied:** SQL migration file must be manually run against Supabase via SQL editor. No migration runner built.
- **No key rotation:** If `APP_ENCRYPTION_SECRET` changes, existing encrypted keys become unreadable. No rotation mechanism built.

## Follow-ups

- S03 needs `NEXT_PUBLIC_SUPABASE_URL` and `NEXT_PUBLIC_SUPABASE_ANON_KEY` for frontend auth client
- S04 will consume the key CRUD endpoints and needs the `conftest.py` mock fixtures
- S05-S06 need a utility to decrypt stored keys for per-request client construction — the `decrypt_value()` function exists but the "fetch from DB → decrypt → construct client" flow isn't wired yet
- S07 must run `001_initial_schema.sql` against the real Supabase project during deployment

## Files Created/Modified

- `apps/api/services/encryption.py` — Envelope encryption with encrypt_value/decrypt_value (new)
- `apps/api/services/auth.py` — JWT auth middleware with get_current_user dependency (new)
- `apps/api/services/database.py` — Async connection pool with get_db_pool/get_db/close_db_pool (new)
- `apps/api/routers/keys.py` — 4 key management endpoints with auth + encryption + DB (new)
- `apps/api/migrations/001_initial_schema.sql` — 4-table schema, RLS policies, profile trigger (new)
- `apps/api/tests/test_encryption.py` — 11 encryption tests (new)
- `apps/api/tests/test_auth.py` — 6 auth tests (new)
- `apps/api/tests/test_keys_endpoints.py` — 14 endpoint tests (new)
- `apps/api/tests/conftest.py` — Added mock_auth, mock_db, mock_encryption, auth_headers fixtures
- `apps/api/schemas.py` — Added KeyStoreRequest, KeyStatusItem, KeyStatusResponse, KeyVerifyResponse
- `apps/api/main.py` — Added keys.router import and include_router call
- `apps/api/requirements.txt` — Added cryptography>=43.0.0, asyncpg>=0.29.0, python-jose[cryptography]>=3.3.0

## Forward Intelligence

### What the next slice should know
- `get_current_user` returns a plain `str` (UUID as string), not a UUID object — downstream code should treat it as string
- `KeyStoreRequest` has three fields: `key_value` (str), `key_name` (str), `is_paper` (Optional[bool]) — the `key_name` field distinguishes alpaca `api_key` vs `secret_key`
- The `conftest.py` fixtures (`mock_auth`, `mock_db`, `mock_encryption`) are function-scoped and auto-applied via `autouse` where noted — S04+ tests should use the same patterns
- `GET /api/keys/status` returns `{"keys": [{"provider": "alpaca", "connected": true, "is_paper": true}]}` — frontend should check this before allowing screener runs

### What's fragile
- **asyncpg pool + Supabase connection string** — `DATABASE_URL` must include `?sslmode=require` for Supabase; pool creation will fail silently at startup if the URL is wrong (error surfaces on first query)
- **JWT secret mismatch** — `SUPABASE_JWT_SECRET` must exactly match the Supabase project's JWT secret; a mismatch returns 401 on every request with no obvious error besides "Invalid token"

### Authoritative diagnostics
- `python -m pytest apps/api/tests/test_encryption.py apps/api/tests/test_auth.py apps/api/tests/test_keys_endpoints.py -v` — 31 tests prove the full S02 contract in <1s
- `GET /api/keys/status` — runtime inspection of per-user key state without exposing values

### What assumptions changed
- Plan assumed 403 for missing auth header → FastAPI >=0.109 returns 401 (recorded in KNOWLEDGE.md)
- Plan assumed separate key_name path params → cleaner as body field on KeyStoreRequest
