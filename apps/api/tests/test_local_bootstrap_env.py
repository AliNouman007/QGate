import pytest
from pydantic import ValidationError
from suitest_api.settings import Settings


def test_mode_defaults_to_server(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SUITEST_MODE", raising=False)
    assert Settings().mode == "server"


def test_mode_local_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUITEST_MODE", "local")
    assert Settings().mode == "local"


def test_mode_typo_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SUITEST_MODE", "locaal")
    with pytest.raises(ValidationError):
        Settings()


def test_local_auth_bypass_defaults_off(monkeypatch: pytest.MonkeyPatch) -> None:
    """Deleting the secure default or changing it to true must fail this test."""
    monkeypatch.delenv("SUITEST_LOCAL_AUTH_BYPASS", raising=False)
    assert getattr(Settings(), "local_auth_bypass", False) is False


def test_local_auth_bypass_can_be_enabled_only_in_local_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Allowing the bypass in server mode would weaken deployment security."""
    monkeypatch.setenv("SUITEST_LOCAL_AUTH_BYPASS", "true")
    monkeypatch.setenv("SUITEST_MODE", "server")
    with pytest.raises(ValueError, match="only be enabled when SUITEST_MODE=local"):
        Settings()

    monkeypatch.setenv("SUITEST_MODE", "local")
    assert getattr(Settings(), "local_auth_bypass", False) is True
