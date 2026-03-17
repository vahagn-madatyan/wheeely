"""Envelope encryption service using AES-GCM (D054).

Two-layer encryption:
- A fresh random DEK (Data Encryption Key) encrypts the plaintext value.
- The DEK itself is encrypted ("wrapped") with the KEK (Key Encryption Key)
  loaded from the APP_ENCRYPTION_SECRET environment variable.

Both layers use AESGCM with 256-bit keys and 12-byte random nonces.
"""

from __future__ import annotations

import base64
import os

from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def _get_kek() -> bytes:
    """Load and validate the Key Encryption Key from environment.

    APP_ENCRYPTION_SECRET must be a base64-encoded 32-byte value.

    Raises:
        ValueError: If the env var is missing or decodes to wrong length.
    """
    secret = os.environ.get("APP_ENCRYPTION_SECRET")
    if not secret:
        raise ValueError(
            "APP_ENCRYPTION_SECRET environment variable is not set. "
            "It must be a base64-encoded 32-byte key."
        )
    try:
        kek = base64.b64decode(secret)
    except Exception as exc:
        raise ValueError(
            "APP_ENCRYPTION_SECRET is not valid base64."
        ) from exc

    if len(kek) != 32:
        raise ValueError(
            f"APP_ENCRYPTION_SECRET must decode to exactly 32 bytes, "
            f"got {len(kek)} bytes."
        )
    return kek


def encrypt_value(plaintext: str) -> tuple[bytes, bytes, bytes, bytes]:
    """Encrypt a plaintext string using envelope encryption.

    Args:
        plaintext: The value to encrypt (e.g. an API key).

    Returns:
        A 4-tuple of bytes:
            (encrypted_value, encrypted_dek, nonce, dek_nonce)
    """
    kek = _get_kek()

    # Generate a fresh random DEK for this value
    dek = AESGCM.generate_key(bit_length=256)

    # Generate unique nonces for each encryption layer
    nonce = os.urandom(12)
    dek_nonce = os.urandom(12)

    # Layer 1: Encrypt plaintext with DEK
    data_cipher = AESGCM(dek)
    encrypted_value = data_cipher.encrypt(nonce, plaintext.encode("utf-8"), None)

    # Layer 2: Wrap (encrypt) DEK with KEK
    kek_cipher = AESGCM(kek)
    encrypted_dek = kek_cipher.encrypt(dek_nonce, dek, None)

    return (encrypted_value, encrypted_dek, nonce, dek_nonce)


def decrypt_value(
    encrypted_value: bytes,
    encrypted_dek: bytes,
    nonce: bytes,
    dek_nonce: bytes,
) -> str:
    """Decrypt an envelope-encrypted value.

    Args:
        encrypted_value: The ciphertext of the original value.
        encrypted_dek: The wrapped (encrypted) DEK.
        nonce: The nonce used to encrypt the value.
        dek_nonce: The nonce used to wrap the DEK.

    Returns:
        The original plaintext string.

    Raises:
        cryptography.exceptions.InvalidTag: If the KEK is wrong or data is
            tampered with.
    """
    kek = _get_kek()

    # Unwrap DEK using KEK
    kek_cipher = AESGCM(kek)
    dek = kek_cipher.decrypt(dek_nonce, encrypted_dek, None)

    # Decrypt value using DEK
    data_cipher = AESGCM(dek)
    plaintext_bytes = data_cipher.decrypt(nonce, encrypted_value, None)

    return plaintext_bytes.decode("utf-8")
