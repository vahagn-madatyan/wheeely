"""Tests for Redis-based sliding window rate limiter.

Covers:
- Unit tests for RateLimiter class (sliding window logic, no-op, 429 response)
- Endpoint integration tests (put/call rate limiting, shared counter)

Uses an in-memory FakeAsyncRedis to exercise real sorted-set logic without
requiring a running Redis instance.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient

from apps.api.main import app
from apps.api.services.rate_limiter import RateLimiter, MAX_REQUESTS, WINDOW_SECONDS
from apps.api.tests.conftest import SAMPLE_PUT, SAMPLE_CALL


# ---------------------------------------------------------------------------
# In-memory Redis fake (implements sorted set ops used by RateLimiter)
# ---------------------------------------------------------------------------


class FakePipeline:
    """Fake Redis pipeline that executes against FakeAsyncRedis storage."""

    def __init__(self, redis):
        self._redis = redis
        self._commands = []

    def zremrangebyscore(self, key, min_score, max_score):
        self._commands.append(("zremrangebyscore", key, min_score, max_score))
        return self

    def zcard(self, key):
        self._commands.append(("zcard", key))
        return self

    async def execute(self):
        results = []
        for cmd in self._commands:
            if cmd[0] == "zremrangebyscore":
                key, min_s, max_s = cmd[1], cmd[2], cmd[3]
                data = self._redis._data.get(key, {})
                to_remove = [m for m, s in data.items() if min_s <= s <= max_s]
                for m in to_remove:
                    del data[m]
                results.append(len(to_remove))
            elif cmd[0] == "zcard":
                key = cmd[1]
                results.append(len(self._redis._data.get(key, {})))
        self._commands = []
        return results


class FakeAsyncRedis:
    """In-memory async Redis substitute for testing sorted set operations."""

    def __init__(self):
        self._data = {}  # key -> {member: score}

    def pipeline(self):
        return FakePipeline(self)

    async def zrange(self, key, start, stop, withscores=False):
        members = sorted(
            self._data.get(key, {}).items(), key=lambda x: x[1]
        )
        actual_stop = len(members) if stop == -1 else stop + 1
        result = members[start:actual_stop]
        if withscores:
            return result
        return [m for m, _s in result]

    async def zadd(self, key, mapping):
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(mapping)
        return len(mapping)

    async def expire(self, key, ttl):
        pass  # no-op in tests

    async def aclose(self):
        pass


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_redis():
    """Fresh in-memory Redis for each test."""
    return FakeAsyncRedis()


@pytest.fixture
def limiter(fake_redis):
    """RateLimiter wired to the in-memory fake Redis."""
    return RateLimiter(fake_redis)


@pytest.fixture
def noop_limiter():
    """RateLimiter with no Redis — no-op mode."""
    return RateLimiter(None)


@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture
def mock_auth():
    """Override auth to return a fixed test user_id."""
    from apps.api.services.auth import get_current_user
    from apps.api.tests.conftest import TEST_USER_ID

    app.dependency_overrides[get_current_user] = lambda: TEST_USER_ID
    yield TEST_USER_ID
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_db():
    """Override DB dependency with AsyncMock."""
    from unittest.mock import AsyncMock
    from apps.api.services.database import get_db

    mock_conn = AsyncMock()
    mock_conn.fetch.return_value = []

    async def _override():
        yield mock_conn

    app.dependency_overrides[get_db] = _override
    yield mock_conn
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def mock_key_retrieval():
    """Mock key retrieval to return test credentials."""
    with patch(
        "apps.api.routers.screen.retrieve_alpaca_keys",
        return_value=("test-key", "test-secret", True),
    ) as m:
        yield m


@pytest.fixture
def rate_limited_app(fake_redis):
    """Install a real RateLimiter with fake Redis on the app state.

    This replaces the default no-op limiter created by the lifespan
    so endpoint tests actually enforce rate limits.
    """
    limiter = RateLimiter(fake_redis)
    original = getattr(app.state, "rate_limiter", None)
    app.state.rate_limiter = limiter
    yield limiter
    if original is not None:
        app.state.rate_limiter = original


# ---------------------------------------------------------------------------
# Unit tests: RateLimiter class
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_three_requests_pass(limiter):
    """Three requests within the window should all succeed."""
    for i in range(MAX_REQUESTS):
        remaining = await limiter.check_rate_limit("user-1")
        assert remaining == MAX_REQUESTS - i - 1


@pytest.mark.asyncio
async def test_fourth_request_returns_429(limiter):
    """The 4th request should raise HTTPException with status 429."""
    for _ in range(MAX_REQUESTS):
        await limiter.check_rate_limit("user-1")

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit("user-1")

    assert exc_info.value.status_code == 429


@pytest.mark.asyncio
async def test_window_expiry_resets_counter(fake_redis):
    """After old entries expire past the window, the counter resets."""
    limiter = RateLimiter(fake_redis)

    # Simulate 3 requests that happened 25 hours ago (expired)
    old_time = time.time() - WINDOW_SECONDS - 3600
    key = "rate_limit:user-1"
    for i in range(3):
        ts = old_time + i
        await fake_redis.zadd(key, {str(ts): ts})

    # Next check should prune all 3 old entries, allowing a new one
    remaining = await limiter.check_rate_limit("user-1")
    assert remaining == MAX_REQUESTS - 1  # 2 remaining after this new request


@pytest.mark.asyncio
async def test_no_redis_skips_enforcement(noop_limiter):
    """RateLimiter(None) allows unlimited requests without error."""
    for _ in range(10):
        remaining = await noop_limiter.check_rate_limit("user-1")
        assert remaining == MAX_REQUESTS


@pytest.mark.asyncio
async def test_429_response_includes_retry_after(limiter):
    """429 response body must include 'remaining' and 'retry_after' fields."""
    for _ in range(MAX_REQUESTS):
        await limiter.check_rate_limit("user-1")

    with pytest.raises(HTTPException) as exc_info:
        await limiter.check_rate_limit("user-1")

    detail = exc_info.value.detail
    assert detail["remaining"] == 0
    assert "retry_after" in detail
    assert isinstance(detail["retry_after"], int)
    assert detail["retry_after"] > 0


@pytest.mark.asyncio
async def test_different_users_independent(limiter):
    """Each user has their own rate limit counter."""
    for _ in range(MAX_REQUESTS):
        await limiter.check_rate_limit("user-a")

    # user-a is exhausted
    with pytest.raises(HTTPException):
        await limiter.check_rate_limit("user-a")

    # user-b should still be fine
    remaining = await limiter.check_rate_limit("user-b")
    assert remaining == MAX_REQUESTS - 1


# ---------------------------------------------------------------------------
# Endpoint integration tests
# ---------------------------------------------------------------------------


MOCK_PUT_RESULTS = [SAMPLE_PUT]
MOCK_CALL_RESULTS = [SAMPLE_CALL]


@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_rate_limit_blocks_put_screen_endpoint(
    mock_clients,
    mock_screen,
    client,
    mock_auth,
    mock_db,
    mock_key_retrieval,
    rate_limited_app,
):
    """Submit 3 put screens, verify 4th returns 429."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    auth_headers = {"Authorization": "Bearer fake"}

    for _ in range(MAX_REQUESTS):
        resp = client.post(
            "/api/screen/puts",
            json={"symbols": ["AAPL"], "buying_power": 50000.0},
            headers=auth_headers,
        )
        assert resp.status_code == 202

    # 4th request should be rate-limited
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    assert resp.status_code == 429
    data = resp.json()
    assert data["detail"]["remaining"] == 0
    assert "retry_after" in data["detail"]


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_rate_limit_blocks_call_screen_endpoint(
    mock_clients,
    mock_screen,
    client,
    mock_auth,
    mock_db,
    mock_key_retrieval,
    rate_limited_app,
):
    """Submit 3 call screens, verify 4th returns 429."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    auth_headers = {"Authorization": "Bearer fake"}

    for _ in range(MAX_REQUESTS):
        resp = client.post(
            "/api/screen/calls",
            json={"symbol": "AAPL", "cost_basis": 195.0},
            headers=auth_headers,
        )
        assert resp.status_code == 202

    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    assert resp.status_code == 429
    data = resp.json()
    assert data["detail"]["remaining"] == 0


@patch("apps.api.routers.screen.screen_calls", return_value=MOCK_CALL_RESULTS)
@patch("apps.api.routers.screen.screen_puts", return_value=MOCK_PUT_RESULTS)
@patch("apps.api.routers.screen.create_alpaca_clients")
def test_put_and_call_share_same_counter(
    mock_clients,
    mock_screen_puts,
    mock_screen_calls,
    client,
    mock_auth,
    mock_db,
    mock_key_retrieval,
    rate_limited_app,
):
    """2 puts + 1 call = 3 total; the 4th request (either) returns 429."""
    mock_clients.return_value = (MagicMock(), MagicMock(), MagicMock())
    auth_headers = {"Authorization": "Bearer fake"}

    # 2 put screens
    for _ in range(2):
        resp = client.post(
            "/api/screen/puts",
            json={"symbols": ["AAPL"], "buying_power": 50000.0},
            headers=auth_headers,
        )
        assert resp.status_code == 202

    # 1 call screen
    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    assert resp.status_code == 202

    # 4th request (call) should hit rate limit
    resp = client.post(
        "/api/screen/calls",
        json={"symbol": "AAPL", "cost_basis": 195.0},
        headers=auth_headers,
    )
    assert resp.status_code == 429

    # Confirm a put is also blocked
    resp = client.post(
        "/api/screen/puts",
        json={"symbols": ["AAPL"], "buying_power": 50000.0},
        headers=auth_headers,
    )
    assert resp.status_code == 429
