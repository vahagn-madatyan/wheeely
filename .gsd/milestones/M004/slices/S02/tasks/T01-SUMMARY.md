---
id: T01
parent: S02
milestone: M004
provides:
  - Envelope encryption service with encrypt_value() / decrypt_value()
  - 11 passing tests covering round-trip, wrong KEK, nonce uniqueness, edge cases
key_files:
  - apps/api/services/encryption.py
  - apps/api/tests/test_encryption.py
  - apps/api/requirements.txt
key_decisions:
  - Pure functions with no logging — crypto ops must not emit key material
patterns_established:
  - Envelope encryption pattern: per-value random DEK wrapped by KEK from env var
  - Test KEK generation via base64.b64encode(os.urandom(32)).decode() in fixtures
observability_surfaces:
  - No runtime signals (pure crypto functions) — correctness verified via tests only
  - ValueError on missing/malformed APP_ENCRYPTION_SECRET
  - InvalidTag on wrong KEK at decrypt time
duration: 8m
verification_result: passed
completed_at: 2026-03-16
blocker_discovered: false
---

# T01: Build envelope encryption service with tests

**Implemented two-layer AES-GCM envelope encryption with 11 passing tests covering all must-haves.**

## What Happened

Added `cryptography>=43.0.0` to `apps/api/requirements.txt`. Created `apps/api/services/encryption.py` with:
- `encrypt_value(plaintext)` → generates fresh random 32-byte DEK and two 12-byte nonces per call, encrypts plaintext with DEK, wraps DEK with KEK from `APP_ENCRYPTION_SECRET` env var, returns 4-tuple of bytes.
- `decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)` → unwraps DEK with KEK, decrypts value, returns original string.
- `_get_kek()` → loads and validates env var (base64-decoded 32 bytes).

Created 11 tests in `apps/api/tests/test_encryption.py` organized into 4 test classes.

## Verification

- `python -m pytest apps/api/tests/test_encryption.py -v` — **11/11 passed** (round-trip, 4-tuple type check, wrong KEK raises InvalidTag, nonce uniqueness, ciphertext uniqueness, empty string, long string, special chars/unicode, missing KEK, invalid base64 KEK, wrong-length KEK)
- `python -m pytest tests/ -q` — **425 passed** (CLI tests unaffected)
- `python -m pytest apps/api/tests/ -q` — **42 passed** (31 S01 + 11 new encryption tests)

### Slice-level verification status (T01 checkpoint):
- ✅ `python -m pytest apps/api/tests/test_encryption.py -v` — all pass
- ⬜ `python -m pytest apps/api/tests/test_auth.py -v` — not yet created (T03)
- ⬜ `python -m pytest apps/api/tests/test_keys_endpoints.py -v` — not yet created (T04)
- ✅ `python -m pytest tests/ -q` — 425 pass
- ✅ `python -m pytest apps/api/tests/ -q` — 42 pass

## Diagnostics

- No runtime logging from encryption module (intentional — crypto ops must not emit key material).
- Run `python -m pytest apps/api/tests/test_encryption.py -v` to verify service works.
- `APP_ENCRYPTION_SECRET` must be set as base64-encoded 32 bytes. Missing/invalid raises `ValueError`. Wrong KEK at decrypt time raises `cryptography.exceptions.InvalidTag`.

## Deviations

Added 4 extra tests beyond the 7 specified: `test_returns_four_bytes_tuple`, `test_encrypted_values_differ`, `test_invalid_base64_kek_raises`, `test_wrong_length_kek_raises` — all strengthen coverage without changing the plan.

## Known Issues

None.

## Files Created/Modified

- `apps/api/services/encryption.py` — new: envelope encryption service with encrypt_value/decrypt_value
- `apps/api/tests/test_encryption.py` — new: 11 tests for encryption round-trip and error cases
- `apps/api/requirements.txt` — modified: added cryptography>=43.0.0
- `.gsd/milestones/M004/slices/S02/tasks/T01-PLAN.md` — modified: added Observability Impact section
