"""Tests for JWT authentication middleware (apps/api/services/auth.py).

Uses python-jose to craft test JWTs and a tiny FastAPI test endpoint that
depends on ``get_current_user``.
"""

import time

import httpx
import pytest
from fastapi import Depends, FastAPI
from jose import jwt

from apps.api.services.auth import get_current_user

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "test-supabase-jwt-secret-at-least-32-chars-long!!"
TEST_USER_ID = "550e8400-e29b-41d4-a716-446655440000"

# ---------------------------------------------------------------------------
# Isolated test app — avoids polluting the main app's routes
# ---------------------------------------------------------------------------

_test_app = FastAPI()


@_test_app.get("/test-auth")
async def _test_auth_endpoint(user_id: str = Depends(get_current_user)):
    return {"user_id": user_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_token(
    sub: str | None = TEST_USER_ID,
    aud: str = "authenticated",
    exp_offset: int = 3600,
    secret: str = TEST_JWT_SECRET,
) -> str:
    """Create a signed HS256 JWT for testing."""
    payload: dict = {"aud": aud, "exp": int(time.time()) + exp_offset}
    if sub is not None:
        payload["sub"] = sub
    return jwt.encode(payload, secret, algorithm="HS256")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valid_token_returns_user_id(monkeypatch):
    """Valid JWT with correct sub/aud/exp returns 200 and user_id."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    token = _make_token()

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test-auth",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 200
    assert resp.json()["user_id"] == TEST_USER_ID


@pytest.mark.asyncio
async def test_expired_token_returns_401(monkeypatch):
    """JWT with exp in the past returns 401 with 'expired' in detail."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    token = _make_token(exp_offset=-3600)  # expired 1 hour ago

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test-auth",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401
    assert "expired" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_missing_auth_header_returns_401(monkeypatch):
    """Request without Authorization header returns 401 (HTTPBearer auto_error).

    Note: FastAPI >=0.109 changed HTTPBearer from 403 to 401. Our version
    (0.135.1) returns 401.
    """
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/test-auth")

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_malformed_token_returns_401(monkeypatch):
    """Garbage Bearer value returns 401."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test-auth",
            headers={"Authorization": "Bearer not-a-jwt"},
        )

    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_missing_sub_claim_returns_401(monkeypatch):
    """Valid JWT without sub claim returns 401 with 'sub' in detail."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    token = _make_token(sub=None)

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test-auth",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401
    assert "sub" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_wrong_secret_returns_401(monkeypatch):
    """JWT signed with a different secret returns 401."""
    monkeypatch.setenv("SUPABASE_JWT_SECRET", TEST_JWT_SECRET)
    token = _make_token(secret="wrong-secret-that-is-also-at-least-32-chars!!")

    transport = httpx.ASGITransport(app=_test_app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get(
            "/test-auth",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert resp.status_code == 401
