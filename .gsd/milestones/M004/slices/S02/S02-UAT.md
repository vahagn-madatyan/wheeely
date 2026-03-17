# S02: Supabase auth + database + encrypted key storage — UAT

**Milestone:** M004
**Written:** 2026-03-16

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S02 is pure backend infrastructure (encryption, auth, DB schema, key CRUD). All behavior is verified by 31 automated tests against mocked dependencies. No frontend, no live runtime needed. Real Supabase integration is a deployment concern (S07).

## Preconditions

- Python virtual environment activated: `source .venv/bin/activate`
- All dependencies installed: `pip install -r apps/api/requirements.txt`
- No env vars needed for test execution (tests mock all secrets)

## Smoke Test

```bash
source .venv/bin/activate && python -m pytest apps/api/tests/test_encryption.py apps/api/tests/test_auth.py apps/api/tests/test_keys_endpoints.py -v
```
**Expected:** 31 tests pass (11 encryption + 6 auth + 14 keys). If any fail, investigate before proceeding.

## Test Cases

### 1. Encryption round-trip integrity

1. Run `python -m pytest apps/api/tests/test_encryption.py::TestEncryptDecryptRoundTrip -v`
2. **Expected:** `test_encrypt_decrypt_round_trip` passes — encrypting "my-secret-api-key" and decrypting returns the exact original string.
3. **Expected:** `test_returns_four_bytes_tuple` passes — encrypt_value returns a 4-tuple of bytes (encrypted_value, encrypted_dek, nonce, dek_nonce).

### 2. Encryption security properties

1. Run `python -m pytest apps/api/tests/test_encryption.py::TestWrongKEK -v`
2. **Expected:** `test_wrong_kek_raises` passes — decrypting with a different KEK raises `InvalidTag`.
3. Run `python -m pytest apps/api/tests/test_encryption.py::TestNonceUniqueness -v`
4. **Expected:** `test_nonce_uniqueness` passes — 10 consecutive encryptions of the same value produce 10 unique nonces.
5. **Expected:** `test_encrypted_values_differ` passes — encrypting the same plaintext twice produces different ciphertext.

### 3. Encryption edge cases

1. Run `python -m pytest apps/api/tests/test_encryption.py::TestEdgeCases -v`
2. **Expected:** `test_empty_string` passes — empty string round-trips correctly.
3. **Expected:** `test_long_string` passes — 10,000-character string round-trips correctly.
4. **Expected:** `test_special_characters` passes — unicode, emoji, special chars round-trip correctly.

### 4. KEK validation

1. Run `python -m pytest apps/api/tests/test_encryption.py::TestMissingKEK -v`
2. **Expected:** `test_missing_kek_raises` — missing APP_ENCRYPTION_SECRET raises ValueError.
3. **Expected:** `test_invalid_base64_kek_raises` — non-base64 value raises ValueError.
4. **Expected:** `test_wrong_length_kek_raises` — key shorter than 32 bytes raises ValueError.

### 5. JWT authentication — valid token

1. Run `python -m pytest apps/api/tests/test_auth.py::test_valid_token_returns_user_id -v`
2. **Expected:** A correctly signed HS256 JWT with `sub` claim and `aud=authenticated` returns the user_id UUID string with HTTP 200.

### 6. JWT authentication — rejection cases

1. Run `python -m pytest apps/api/tests/test_auth.py -k "not valid_token" -v`
2. **Expected:** All 5 rejection tests pass:
   - Expired token → 401 with "Token has expired"
   - Missing Authorization header → 401 with "Not authenticated"
   - Malformed token (not a JWT) → 401 with "Invalid token"
   - Missing `sub` claim → 401 with "Token missing sub claim"
   - Wrong secret → 401 with "Invalid token"

### 7. Key storage — store Alpaca keys

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_store_alpaca_key -v`
2. **Expected:** POST /api/keys/alpaca with `{"key_value": "AKTEST123", "key_name": "api_key"}` returns 200 with `{"status": "stored", "provider": "alpaca", "key_name": "api_key"}`.
3. **Expected:** Mock DB received bytes (not plaintext string) for encrypted_value, encrypted_dek, nonce, dek_nonce.
4. **Expected:** Original key value `b"AKTEST123"` does NOT appear in the encrypted_value bytes.

### 8. Key storage — invalid inputs

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py -k "invalid" -v`
2. **Expected:** `test_store_invalid_provider` — POST /api/keys/stripe returns 422 with "Invalid provider".
3. **Expected:** `test_store_invalid_key_name` — POST /api/keys/alpaca with key_name="password" returns 422.

### 9. Key status — returns providers without values

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_get_key_status -v`
2. **Expected:** GET /api/keys/status returns provider names and connected boolean — never returns key values.
3. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_get_key_status_empty -v`
4. **Expected:** Returns empty list when no keys stored.

### 10. Key deletion

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_delete_keys -v`
2. **Expected:** DELETE /api/keys/alpaca returns 200 with `{"status": "deleted"}`.
3. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_delete_invalid_provider -v`
4. **Expected:** DELETE /api/keys/stripe returns 422.

### 11. Key verification

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py -k "verify" -v`
2. **Expected:** `test_verify_alpaca_keys_success` — POST /api/keys/alpaca/verify with stored keys returns `{"provider": "alpaca", "valid": true}`.
3. **Expected:** `test_verify_alpaca_keys_failure` — When SDK call fails, returns `{"provider": "alpaca", "valid": false, "error": "..."}`.
4. **Expected:** `test_verify_no_keys_stored` — When no keys exist, returns valid=false with appropriate error.
5. **Expected:** `test_verify_invalid_provider` — Invalid provider returns 422.

### 12. Auth enforcement on key endpoints

1. Run `python -m pytest apps/api/tests/test_keys_endpoints.py::test_unauthenticated_request_rejected -v`
2. **Expected:** GET /api/keys/status without Authorization header returns 401 or 403.

### 13. CLI test regression

1. Run `python -m pytest tests/ -q`
2. **Expected:** 425 tests pass. Zero failures, zero errors. No S02 changes affected CLI code.

### 14. Full API test suite

1. Run `python -m pytest apps/api/tests/ -q`
2. **Expected:** 62 tests pass (31 S01 + 31 S02). All tests are independent and can run in any order.

## Edge Cases

### Empty key_value

1. POST /api/keys/alpaca with `{"key_value": "", "key_name": "api_key"}`
2. **Expected:** Encryption service handles empty string (test_empty_string proves this). Endpoint should store it — validation of key correctness is the verify endpoint's job.

### Concurrent nonce safety

1. Run `python -m pytest apps/api/tests/test_encryption.py::TestNonceUniqueness -v`
2. **Expected:** 10 rapid sequential calls produce unique nonces — `os.urandom(12)` provides cryptographic randomness.

### KEK rotation (not implemented)

1. Change APP_ENCRYPTION_SECRET after keys are stored.
2. **Expected:** Decrypt will raise InvalidTag. No rotation mechanism exists — this is a known limitation documented in the slice summary.

## Failure Signals

- Any pytest failure in the 31 S02 tests indicates a broken S02 contract
- `ImportError` for `cryptography`, `jose`, or `asyncpg` indicates missing dependencies — run `pip install -r apps/api/requirements.txt`
- `ValueError("APP_ENCRYPTION_SECRET...")` at runtime means env var not set or malformed
- `ValueError("SUPABASE_JWT_SECRET...")` at runtime means JWT secret not configured
- `ValueError("DATABASE_URL...")` at runtime means Postgres connection string not set
- CLI tests failing (anything in `tests/` directory) would indicate S02 accidentally modified CLI code — this should never happen

## Requirements Proved By This UAT

- **WEB-01** — JWT auth middleware verifies tokens and extracts user_id; profiles table schema with auto-creation trigger exists
- **WEB-02** — Alpaca keys encrypted via envelope encryption; store/status/delete/verify endpoints tested; paper/live toggle via is_paper field
- **WEB-03** — Finnhub key encrypted identically; same CRUD endpoints handle both providers
- **WEB-10** — RLS policies defined on all 4 tables; auth enforcement tested (unauthenticated → 401/403)
- **CLI-COMPAT-01** — 425 CLI tests pass unchanged

## Not Proven By This UAT

- **Real Supabase integration** — all tests use mocked DB; actual Supabase connectivity, RLS enforcement, and profile trigger execution are deployment concerns (S07)
- **WEB-04** — Key verification UI (S04 concern — this slice only proves the API endpoint)
- **WEB-13** — Key deletion UI (S04 concern — this slice only proves the API endpoint)
- **Multi-user isolation at runtime** — RLS policies are defined in SQL but not exercised against a real Supabase instance in tests

## Notes for Tester

- All tests run in <1 second — no network calls, no real DB connections
- The `conftest.py` fixtures auto-mock auth/db/encryption for key endpoint tests — if adding new tests, use the same fixture pattern
- HTTPBearer returns 401 (not 403) for missing auth in FastAPI >=0.109 — this is correct behavior, not a bug
- The SQL migration file is meant to be run manually in Supabase SQL editor during S07 deployment — there's no automated migration runner
