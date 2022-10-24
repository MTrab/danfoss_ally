"""Provides device automations for Climate."""
from __future__ import annotations

import json
import logging

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant.components.climate import ATTR_PRESET_MODE, ATTR_PRESET_MODES
from homeassistant.components.climate import DOMAIN as CLIMATE_DOMAIN
from homeassistant.components.climate import SERVICE_SET_TEMPERATURE
from homeassistant.const import (
    ATTR_ENTITY_ID,
    ATTR_TEMPERATURE,
    CONF_DEVICE_ID,
    CONF_DOMAIN,
    CONF_ENTITY_ID,
    CONF_TYPE,
)
from homeassistant.core import Context, HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry
from homeassistant.helpers.entity import get_capability, get_supported_features

from .const import ACTION_TYPE_SET_PRESET_TEMPERATURE, ATTR_SETPOINT, DOMAIN

_LOGGER = logging.getLogger(__name__)

ACTION_TYPES = {ACTION_TYPE_SET_PRESET_TEMPERATURE}

SET_SETPOINT_SCHEMA = cv.DEVICE_ACTION_BASE_SCHEMA.extend(
    {
        vol.Required(CONF_TYPE): ACTION_TYPE_SET_PRESET_TEMPERATURE,
        vol.Required(CONF_ENTITY_ID): cv.entity_domain(CLIMATE_DOMAIN),
        vol.Required(ATTR_TEMPERATURE): vol.Coerce(float),
        vol.Optional(ATTR_PRESET_MODE): str,
    }
)

ACTION_SCHEMA = vol.Any(SET_SETPOINT_SCHEMA)


async def async_get_actions(
    hass: HomeAssistant, device_id: str
) -> list[dict[str, str]]:
    """List device actions for Climate devices."""
    registry = entity_registry.async_get(hass)
    actions = []

    # Get all the integrations entities for this device
    for entry in entity_registry.async_entries_for_device(registry, device_id):
        if entry.domain != CLIMATE_DOMAIN:
            continue

        supported_features = get_supported_features(hass, entry.entity_id)

        base_action = {
            CONF_DEVICE_ID: device_id,
            CONF_DOMAIN: DOMAIN,
            CONF_ENTITY_ID: entry.entity_id,
        }

        _LOGGER.debug(
            "Action: "
            + json.dumps({**base_action, CONF_TYPE: ACTION_TYPE_SET_PRESET_TEMPERATURE})
        )

        actions.append({**base_action, CONF_TYPE: ACTION_TYPE_SET_PRESET_TEMPERATURE})
        # if supported_features & const.SUPPORT_PRESET_MODE:
        #     actions.append({**base_action, CONF_TYPE: "set_preset_mode"})

    return actions


async def async_call_action_from_config(
    hass: HomeAssistant, config: dict, variables: dict, context: Context | None
) -> None:
    """Execute a device action."""
    service_data = {ATTR_ENTITY_ID: config[CONF_ENTITY_ID]}

    if config[CONF_TYPE] == ACTION_TYPE_SET_PRESET_TEMPERATURE:
        service = ACTION_TYPE_SET_PRESET_TEMPERATURE
        service_data[ATTR_TEMPERATURE] = config[ATTR_TEMPERATURE]
        if ATTR_PRESET_MODE in config:
            service_data[ATTR_PRESET_MODE] = config[ATTR_PRESET_MODE]
        domain = DOMAIN  # danfoss_ally

    await hass.services.async_call(
        domain, service, service_data, blocking=True, context=context
    )


async def async_get_action_capabilities(hass, config):
    """List action capabilities."""
    action_type = config[CONF_TYPE]

    fields = {}

    if action_type == ACTION_TYPE_SET_PRESET_TEMPERATURE:
        try:
            preset_modes = (
                get_capability(hass, config[ATTR_ENTITY_ID], ATTR_PRESET_MODES) or []
            )
        except HomeAssistantError:
            preset_modes = []

        preset_modes_kv = {}
        for entry in preset_modes:
            preset_modes_kv[entry.lower()] = entry.capitalize()

        fields[vol.Required(ATTR_TEMPERATURE)] = vol.Coerce(float)
        fields[vol.Optional(ATTR_PRESET_MODE)] = vol.In(preset_modes_kv)

    return {"extra_fields": vol.Schema(fields)}
