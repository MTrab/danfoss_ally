"""Config flow tests for Danfoss Ally."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest

from custom_components.danfoss_ally.config_flow import InvalidAuth, validate_input


@pytest.mark.asyncio
async def test_validate_input_success(monkeypatch) -> None:
    """Valid credentials should pass validation."""
    client = AsyncMock()
    client.initialize.return_value = True
    client.aclose.return_value = None

    monkeypatch.setattr(
        "custom_components.danfoss_ally.config_flow.DanfossAlly",
        lambda *args, **kwargs: client,
    )

    result = await validate_input({"key": "abc", "secret": "def"})

    assert result == {"title": "Danfoss Ally"}


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
