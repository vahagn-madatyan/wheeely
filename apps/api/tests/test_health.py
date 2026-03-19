"""Tests for the /api/health endpoint."""

import os
from unittest.mock import patch

import pytest


@pytest.mark.asyncio
async def test_health_returns_ok(app_client):
    """GET /api/health returns 200 with {"status": "ok"}."""
    resp = await app_client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_cors_default_origins(app_client):
    """Without CORS_ORIGINS env var, wildcard origin is allowed."""
    resp = await app_client.options(
        "/api/health",
        headers={"Origin": "http://example.com", "Access-Control-Request-Method": "GET"},
    )
    # Wildcard allows any origin
    assert resp.headers.get("access-control-allow-origin") in ("*", "http://example.com")
