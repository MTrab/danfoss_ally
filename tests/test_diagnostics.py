"""Diagnostics tests for Danfoss Ally."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from custom_components.danfoss_ally.diagnostics import (
    async_get_config_entry_diagnostics,
)


@pytest.mark.asyncio
async def test_diagnostics_redacts_secrets() -> None:
    """Diagnostics should not expose credentials."""
    entry = SimpleNamespace(
        entry_id="entry-1",
        title="Danfoss Ally",
        data={"key": "secret-key", "secret": "secret-value"},
        runtime_data=SimpleNamespace(
            coordinator=SimpleNamespace(data={"device-1": {"name": "Living room"}})
        ),
    )

    diagnostics = await async_get_config_entry_diagnostics(None, entry)

    assert diagnostics["entry"]["data"]["key"] == "**REDACTED**"
    assert diagnostics["entry"]["data"]["secret"] == "**REDACTED**"
