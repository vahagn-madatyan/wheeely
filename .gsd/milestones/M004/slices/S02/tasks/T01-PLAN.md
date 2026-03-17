---
estimated_steps: 5
estimated_files: 3
---

# T01: Build envelope encryption service with tests

**Slice:** S02 — Supabase auth + database + encrypted key storage
**Milestone:** M004

## Description

Implement the envelope encryption service that all API key storage flows depend on. This is pure cryptography code with zero external service dependencies — the highest-risk piece that must work before anything else. Uses two-layer AES-GCM encryption per decision D054: a per-key DEK (Data Encryption Key) encrypts the actual API key value, and the DEK itself is encrypted with the KEK (Key Encryption Key) loaded from the `APP_ENCRYPTION_SECRET` env var. Both layers use AESGCM with 256-bit keys and 12-byte random nonces.

## Steps

1. **Add `cryptography` to requirements** — Append `cryptography>=43.0.0` to `apps/api/requirements.txt`. Run `pip install cryptography>=43.0.0` to install. Do NOT modify `pyproject.toml` (CLI deps must stay untouched).

2. **Create `apps/api/services/encryption.py`** — Implement two public functions:
   - `encrypt_value(plaintext: str) -> tuple[bytes, bytes, bytes, bytes]`: Generate random 32-byte DEK via `AESGCM.generate_key(bit_length=256)`. Generate two 12-byte nonces (`os.urandom(12)`) — one for data encryption, one for DEK wrapping. Encrypt plaintext with DEK+nonce. Encrypt DEK with KEK+dek_nonce. Return `(encrypted_value, encrypted_dek, nonce, dek_nonce)`.
   - `decrypt_value(encrypted_value: bytes, encrypted_dek: bytes, nonce: bytes, dek_nonce: bytes) -> str`: Load KEK from env. Decrypt DEK using KEK+dek_nonce. Decrypt value using DEK+nonce. Return plaintext string.
   - Internal `_get_kek() -> bytes`: Load `APP_ENCRYPTION_SECRET` from env var, base64-decode it, validate it's exactly 32 bytes. Raise `ValueError` with clear message if missing or wrong length.
   - Use `from cryptography.hazmat.primitives.ciphers.aead import AESGCM`.

3. **Create `apps/api/tests/test_encryption.py`** — Write tests (all using a test `APP_ENCRYPTION_SECRET` set via `monkeypatch.setenv`):
   - `test_encrypt_decrypt_round_trip`: encrypt a known string → decrypt → assert matches original
   - `test_wrong_kek_raises`: encrypt with one KEK, swap env to different KEK, decrypt raises `InvalidTag`
   - `test_nonce_uniqueness`: call encrypt twice on same plaintext, assert nonces differ (both data nonce and dek_nonce)
   - `test_empty_string`: encrypt/decrypt empty string works
   - `test_long_string`: encrypt/decrypt a 1000-char string works
   - `test_special_characters`: encrypt/decrypt string with unicode, newlines, special chars
   - `test_missing_kek_raises`: unset `APP_ENCRYPTION_SECRET`, assert `encrypt_value` raises `ValueError`
   - Use `import base64, os` to generate a valid test KEK: `base64.b64encode(os.urandom(32)).decode()`

## Must-Haves

- [ ] `encrypt_value()` returns 4-tuple of bytes `(encrypted_value, encrypted_dek, nonce, dek_nonce)`
- [ ] `decrypt_value()` returns original plaintext string for any valid encrypted tuple
- [ ] Fresh random DEK generated per `encrypt_value()` call (never reused)
- [ ] Fresh random nonces generated per call (12 bytes each, never deterministic)
- [ ] KEK loaded from `APP_ENCRYPTION_SECRET` env var (base64-encoded 32 bytes)
- [ ] Wrong KEK raises `cryptography.exceptions.InvalidTag`
- [ ] Missing `APP_ENCRYPTION_SECRET` raises `ValueError`
- [ ] `cryptography` added to `apps/api/requirements.txt`, NOT to `pyproject.toml`

## Verification

- `source .venv/bin/activate && pip install cryptography>=43.0.0 && python -m pytest apps/api/tests/test_encryption.py -v` — all 7+ tests pass
- `source .venv/bin/activate && python -m pytest tests/ -q` — 425 CLI tests still pass
- `source .venv/bin/activate && python -m pytest apps/api/tests/ -q` — S01 tests still pass (31)

## Inputs

- `apps/api/requirements.txt` — existing file with FastAPI, uvicorn, httpx, pytest-asyncio, pydantic
- `apps/api/services/__init__.py` — existing empty init file

## Expected Output

- `apps/api/services/encryption.py` — envelope encryption service with `encrypt_value()` and `decrypt_value()`
- `apps/api/tests/test_encryption.py` — 7+ tests proving round-trip, error cases, nonce uniqueness
- `apps/api/requirements.txt` — updated with `cryptography>=43.0.0`
