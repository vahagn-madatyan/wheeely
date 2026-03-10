"""Tests for core.cli_common and screener.export modules."""

import importlib
import pytest


# ── cli_common tests ──────────────────────────────────────────────────────────


def test_cli_common_returns_credentials_when_set(monkeypatch):
    """require_alpaca_credentials returns (key, secret, is_paper) when env vars are set."""
    monkeypatch.setenv("ALPACA_API_KEY", "test-key")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setenv("IS_PAPER", "true")

    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(creds_mod, "IS_PAPER", True)

    from core.cli_common import require_alpaca_credentials

    # Re-import to pick up patched values
    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    key, secret, is_paper = cli_mod.require_alpaca_credentials()
    assert key == "test-key"
    assert secret == "test-secret"
    assert is_paper is True


def test_cli_common_exits_when_api_key_missing(monkeypatch):
    """require_alpaca_credentials raises SystemExit when ALPACA_API_KEY is missing."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", None)
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")

    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    with pytest.raises(SystemExit, match="ALPACA_API_KEY"):
        cli_mod.require_alpaca_credentials()


def test_cli_common_exits_when_secret_key_missing(monkeypatch):
    """require_alpaca_credentials raises SystemExit when ALPACA_SECRET_KEY is missing."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", None)

    import core.cli_common as cli_mod

    importlib.reload(cli_mod)
    with pytest.raises(SystemExit, match="ALPACA_SECRET_KEY"):
        cli_mod.require_alpaca_credentials()


def test_cli_common_create_broker_client(monkeypatch):
    """create_broker_client returns a BrokerClient when credentials are valid."""
    import config.credentials as creds_mod

    monkeypatch.setattr(creds_mod, "ALPACA_API_KEY", "test-key")
    monkeypatch.setattr(creds_mod, "ALPACA_SECRET_KEY", "test-secret")
    monkeypatch.setattr(creds_mod, "IS_PAPER", True)

    # Mock BrokerClient to avoid real API calls
    class MockBrokerClient:
        def __init__(self, api_key, secret_key, paper):
            self.api_key = api_key
            self.secret_key = secret_key
            self.paper = paper

    import core.cli_common as cli_mod
    import core.broker_client as bc_mod

    monkeypatch.setattr(bc_mod, "BrokerClient", MockBrokerClient)
    importlib.reload(cli_mod)

    client = cli_mod.create_broker_client()
    assert client.api_key == "test-key"
    assert client.secret_key == "test-secret"
    assert client.paper is True
