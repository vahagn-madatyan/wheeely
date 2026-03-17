"""Tests for the envelope encryption service (D054)."""

from __future__ import annotations

import base64
import os

import pytest
from cryptography.exceptions import InvalidTag

from apps.api.services.encryption import decrypt_value, encrypt_value


def _make_kek() -> str:
    """Generate a valid base64-encoded 32-byte KEK for testing."""
    return base64.b64encode(os.urandom(32)).decode()


@pytest.fixture(autouse=True)
def _set_kek(monkeypatch: pytest.MonkeyPatch) -> None:
    """Set a valid APP_ENCRYPTION_SECRET for all tests by default."""
    monkeypatch.setenv("APP_ENCRYPTION_SECRET", _make_kek())


class TestEncryptDecryptRoundTrip:
    def test_encrypt_decrypt_round_trip(self) -> None:
        plaintext = "sk-test-alpaca-api-key-12345"
        encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value(plaintext)

        result = decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)
        assert result == plaintext

    def test_returns_four_bytes_tuple(self) -> None:
        result = encrypt_value("test")
        assert isinstance(result, tuple)
        assert len(result) == 4
        for item in result:
            assert isinstance(item, bytes)


class TestWrongKEK:
    def test_wrong_kek_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Encrypt with the original KEK (set by autouse fixture)
        encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value("secret")

        # Swap to a different KEK
        monkeypatch.setenv("APP_ENCRYPTION_SECRET", _make_kek())

        with pytest.raises(InvalidTag):
            decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)


class TestNonceUniqueness:
    def test_nonce_uniqueness(self) -> None:
        _, _, nonce1, dek_nonce1 = encrypt_value("same-plaintext")
        _, _, nonce2, dek_nonce2 = encrypt_value("same-plaintext")

        # Both data nonces and DEK nonces must differ across calls
        assert nonce1 != nonce2
        assert dek_nonce1 != dek_nonce2

    def test_encrypted_values_differ(self) -> None:
        """Even with same plaintext, ciphertext differs due to random DEK + nonce."""
        ev1, ed1, _, _ = encrypt_value("same-plaintext")
        ev2, ed2, _, _ = encrypt_value("same-plaintext")

        assert ev1 != ev2
        assert ed1 != ed2


class TestEdgeCases:
    def test_empty_string(self) -> None:
        encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value("")
        result = decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)
        assert result == ""

    def test_long_string(self) -> None:
        plaintext = "A" * 1000
        encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value(plaintext)
        result = decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)
        assert result == plaintext

    def test_special_characters(self) -> None:
        plaintext = "héllo\nwörld\t🔑 key=val&foo=bår «special»"
        encrypted_value, encrypted_dek, nonce, dek_nonce = encrypt_value(plaintext)
        result = decrypt_value(encrypted_value, encrypted_dek, nonce, dek_nonce)
        assert result == plaintext


class TestMissingKEK:
    def test_missing_kek_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("APP_ENCRYPTION_SECRET", raising=False)
        with pytest.raises(ValueError, match="APP_ENCRYPTION_SECRET.*not set"):
            encrypt_value("test")

    def test_invalid_base64_kek_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("APP_ENCRYPTION_SECRET", "not-valid-base64!!!")
        with pytest.raises(ValueError):
            encrypt_value("test")

    def test_wrong_length_kek_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # 16 bytes instead of 32
        short_key = base64.b64encode(os.urandom(16)).decode()
        monkeypatch.setenv("APP_ENCRYPTION_SECRET", short_key)
        with pytest.raises(ValueError, match="32 bytes"):
            encrypt_value("test")
