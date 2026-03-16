"""Config flow tests for Danfoss Ally."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from pydanfossally import exceptions

from custom_components.danfoss_ally.const import USER_AGENT_PREFIX
from custom_components.danfoss_ally.config_flow import (
    CannotConnect,
    CannotConnectForbidden,
    CannotConnectRateLimited,
    CannotConnectServerError,
    CannotConnectTimeout,
    InvalidAuth,
    UnknownError,
    validate_input,
)


@pytest.mark.asyncio
async def test_validate_input_success(monkeypatch) -> None:
    """Valid credentials should pass validation."""
    client = AsyncMock()
    client.initialize.return_value = True
    client.aclose.return_value = None
    created_kwargs: dict[str, object] = {}

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: created_kwargs.update(kwargs) or client,
    )

    result = await validate_input({"key": "abc", "secret": "def"})

    assert result == {"title": "Danfoss Ally"}
    assert created_kwargs["user_agent_prefix"] == USER_AGENT_PREFIX


@pytest.mark.asyncio
async def test_validate_input_invalid_auth(monkeypatch) -> None:
    """Rejected credentials should raise InvalidAuth."""
    client = AsyncMock()
    client.initialize.return_value = False
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(InvalidAuth):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_timeout(monkeypatch) -> None:
    """Timeouts should raise a dedicated timeout error."""
    client = AsyncMock()
    client.initialize.side_effect = TimeoutError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(CannotConnectTimeout):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_forbidden(monkeypatch) -> None:
    """HTTP 403 should raise a dedicated forbidden error."""
    client = AsyncMock()
    client.initialize.side_effect = exceptions.ForbiddenError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(CannotConnectForbidden):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_rate_limited(monkeypatch) -> None:
    """HTTP 429 should raise a dedicated rate limit error."""
    client = AsyncMock()
    client.initialize.side_effect = exceptions.RateLimitError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(CannotConnectRateLimited):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_server_error(monkeypatch) -> None:
    """HTTP 5xx should raise a dedicated server-side error."""
    client = AsyncMock()
    client.initialize.side_effect = exceptions.InternalServerError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(CannotConnectServerError):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_connection_error(monkeypatch) -> None:
    """Connection failures should raise a generic connectivity error."""
    client = AsyncMock()
    client.initialize.side_effect = ConnectionError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(CannotConnect):
        await validate_input({"key": "abc", "secret": "def"})


@pytest.mark.asyncio
async def test_validate_input_unexpected_error(monkeypatch) -> None:
    """Unexpected API errors should map to the unknown error bucket."""
    client = AsyncMock()
    client.initialize.side_effect = exceptions.UnexpectedError
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    with pytest.raises(UnknownError):
        await validate_input({"key": "abc", "secret": "def"})
