"""Diagnostics support for Danfoss Ally."""

from __future__ import annotations

from homeassistant.components.diagnostics import async_redact_data

from .const import CONF_KEY, CONF_SECRET
from .coordinator import DanfossConfigEntry

TO_REDACT = {CONF_KEY, CONF_SECRET, "token"}


async def async_get_config_entry_diagnostics(hass, entry: DanfossConfigEntry) -> dict:
    """Return diagnostics for a config entry."""
    return async_redact_data(
        {
            "entry": {
                "entry_id": entry.entry_id,
                "title": entry.title,
                "data": dict(entry.data),
            },
            "devices": entry.runtime_data.coordinator.data,
        },
        TO_REDACT,
    )
