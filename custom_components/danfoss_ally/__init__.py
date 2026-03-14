"""The Danfoss Ally integration."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import device_registry as dr

from .const import CONF_KEY, CONF_SECRET, DOMAIN, PLATFORMS
from .coordinator import (
    DanfossConfigEntry,
    DanfossAllyRuntimeData,
    DanfossAllyDataUpdateCoordinator,
    create_client,
)

_LOGGER = logging.getLogger(__name__)

CONFIG_SCHEMA = vol.Schema(
    {
        DOMAIN: vol.All(
            cv.ensure_list,
            [
                {
                    vol.Required(CONF_KEY): cv.string,
                    vol.Required(CONF_SECRET): cv.string,
                }
            ],
        )
    },
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Import legacy YAML configuration."""
    if DOMAIN not in config:
        return True

    for conf in config[DOMAIN]:
        hass.async_create_task(
            hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": SOURCE_IMPORT},
                data=conf,
            )
        )

    return True


async def async_setup_entry(hass: HomeAssistant, entry: DanfossConfigEntry) -> bool:
    """Set up Danfoss Ally from a config entry."""
    client = create_client()

    try:
        authorized = await client.initialize(
            entry.data[CONF_KEY],
            entry.data[CONF_SECRET],
        )
    except TimeoutError as err:
        await client.aclose()
        raise ConfigEntryNotReady("Timeout connecting to Danfoss Ally") from err
    except ConnectionError as err:
        await client.aclose()
        raise ConfigEntryNotReady("Could not connect to Danfoss Ally") from err
    except Exception as err:  # pylint: disable=broad-except
        await client.aclose()
        raise ConfigEntryNotReady("Unexpected Danfoss Ally setup failure") from err

    if not authorized:
        await client.aclose()
        raise ConfigEntryAuthFailed("Authentication with Danfoss Ally failed")

    coordinator = DanfossAllyDataUpdateCoordinator(hass, client, entry)

    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await client.aclose()
        raise

    _async_remove_stale_devices(hass, entry, coordinator.data)

    entry.runtime_data = DanfossAllyRuntimeData(client=client, coordinator=coordinator)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate older Danfoss Ally config entries."""
    if entry.version > 2:
        _LOGGER.error("Unsupported config entry version %s", entry.version)
        return False

    if entry.version == 1:
        _LOGGER.info("Migrating Danfoss Ally config entry from version 1 to 2")
        hass.config_entries.async_update_entry(
            entry,
            data={**entry.data},
            version=2,
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: DanfossConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.aclose()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: DanfossConfigEntry) -> None:
    """Reload a config entry."""
    await hass.config_entries.async_reload(entry.entry_id)


def _async_remove_stale_devices(
    hass: HomeAssistant,
    entry: DanfossConfigEntry,
    devices: dict[str, dict[str, object]],
) -> None:
    """Remove devices that are no longer reported by the API."""
    device_registry = dr.async_get(hass)
    valid_identifiers = {(DOMAIN, device_id) for device_id in devices}

    for device_entry in dr.async_entries_for_config_entry(
        device_registry, entry.entry_id
    ):
        if not (device_entry.identifiers & valid_identifiers):
            _LOGGER.warning(
                "Removing device no longer reported by API: %s", device_entry.id
            )
            device_registry.async_remove_device(device_entry.id)
