"""Config flow for Danfoss Ally."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.exceptions import HomeAssistantError
from pydanfossally import DanfossAlly, exceptions

from .const import API_TIMEOUT, CONF_KEY, CONF_SECRET, DOMAIN, USER_AGENT_PREFIX, CONF_EXTERNAL_SENSORS, CONF_ENTITY_ID

_LOGGER = logging.getLogger(__name__)

STEP_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_KEY): str,
        vol.Required(CONF_SECRET): str,
    }
)


def _format_error(err: BaseException | None) -> str:
    """Return a useful error string even for exceptions without a message."""
    if err is None:
        return "UnknownError"
    return str(err) or err.__class__.__name__


async def validate_input(data: Mapping[str, str]) -> dict[str, str]:
    """Validate credentials against the Danfoss Ally API."""
    client = DanfossAlly(
        timeout=API_TIMEOUT,
        user_agent_prefix=USER_AGENT_PREFIX,
    )
    try:
        authorized = await client.initialize(data[CONF_KEY], data[CONF_SECRET])
    except TimeoutError as err:
        raise CannotConnectTimeout from err
    except exceptions.ForbiddenError as err:
        raise CannotConnectForbidden from err
    except exceptions.RateLimitError as err:
        raise CannotConnectRateLimited from err
    except exceptions.InternalServerError as err:
        raise CannotConnectServerError from err
    except (ConnectionError, exceptions.APIError) as err:
        raise CannotConnect from err
    except exceptions.UnexpectedError as err:
        raise UnknownError from err
    finally:
        await client.aclose()

    if not authorized:
        raise InvalidAuth

    return {"title": "Danfoss Ally"}


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle Danfoss Ally config and re-auth flows."""

    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial setup step."""
        return await self._async_handle_credentials_step("user", user_input)

    async def async_step_reauth(self, _: dict[str, Any]) -> FlowResult:
        """Begin re-authentication."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle credential updates for re-authentication."""
        return await self._async_handle_credentials_step("reauth_confirm", user_input)

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle credential updates for reconfiguration."""
        return await self._async_handle_credentials_step("reconfigure", user_input)

    async def _async_handle_credentials_step(
        self,
        step_id: str,
        user_input: dict[str, Any] | None,
    ) -> FlowResult:
        """Validate credentials and create/update the entry."""
        errors: dict[str, str] = {}
        description_placeholders: dict[str, str] | None = None

        if user_input is not None:
            try:
                validated = await validate_input(user_input)
            except CannotConnectTimeout:
                errors["base"] = "cannot_connect_timeout"
            except CannotConnectForbidden:
                errors["base"] = "cannot_connect_forbidden"
            except CannotConnectRateLimited:
                errors["base"] = "cannot_connect_rate_limited"
            except CannotConnectServerError:
                errors["base"] = "cannot_connect_server_error"
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except UnknownError as err:
                _LOGGER.exception("Unexpected API exception during config flow")
                errors["base"] = "unknown"
                description_placeholders = {
                    "error": _format_error(err.__cause__ or err)
                }
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception during config flow")
                errors["base"] = "unknown"
                description_placeholders = {"error": _format_error(err)}
            else:
                if step_id == "user":
                    duplicate_abort = self._async_abort_if_duplicate_key(
                        user_input[CONF_KEY]
                    )
                    if duplicate_abort is not None:
                        return duplicate_abort
                    
                    # Initialize external sensors config
                    entry_data = {
                        **user_input,
                        CONF_EXTERNAL_SENSORS: {},
                    }
                    
                    return self.async_create_entry(
                        title=validated["title"], data=entry_data
                    )

                entry = (
                    self._get_reauth_entry()
                    if step_id == "reauth_confirm"
                    else self._get_reconfigure_entry()
                )
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    reason=(
                        "reauth_successful"
                        if step_id == "reauth_confirm"
                        else "reconfigure_successful"
                    ),
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=STEP_SCHEMA,
            errors=errors,
            description_placeholders=description_placeholders,
        )

    @callback
    def _async_abort_if_duplicate_key(self, key: str) -> FlowResult | None:
        """Abort when the same API key is already configured."""
        for entry in self._async_current_entries():
            if entry.data.get(CONF_KEY) == key:
                return self.async_abort(reason="already_configured")
        return None


ConfigFlow.async_get_options_flow = staticmethod(  # type: ignore[assignment]
    lambda config_entry: OptionsFlowHandler(config_entry)
)


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class CannotConnectTimeout(HomeAssistantError):
    """Error to indicate the API request timed out."""


class CannotConnectForbidden(HomeAssistantError):
    """Error to indicate the API denied access."""


class CannotConnectRateLimited(HomeAssistantError):
    """Error to indicate the API is throttling requests."""


class CannotConnectServerError(HomeAssistantError):
    """Error to indicate the API returned a server-side failure."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class UnknownError(HomeAssistantError):
    """Error to indicate an unexpected integration or API failure."""


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Danfoss Ally."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Manage options."""
        return await self.async_step_configure_devices(user_input)

    async def async_step_configure_devices(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Select which device to configure external temperature sensor for."""
        errors: dict[str, str] = {}

        if user_input is not None:
            selected_device_id = user_input.get("device_id")
            if selected_device_id:
                return await self.async_step_configure_device_sensor(
                    device_id=selected_device_id
                )

        # Get coordinator from entry runtime data
        coordinator = None
        if self.config_entry and hasattr(self.config_entry, "runtime_data"):
            if self.config_entry.runtime_data:
                coordinator = self.config_entry.runtime_data.coordinator

        devices = {}
        if coordinator and coordinator.data:
            # Build list of thermostat devices
            for device_id, device_data in coordinator.data.items():
                if device_data.get("isThermostat"):
                    device_name = device_data.get("name", device_id)
                    devices[device_id] = device_name

        if not devices:
            return self.async_abort(reason="no_devices")

        schema = vol.Schema({
            vol.Required("device_id"): vol.In(devices),
        })

        return self.async_show_form(
            step_id="configure_devices",
            data_schema=schema,
            errors=errors,
            description_placeholders={"devices": str(len(devices))},
        )

    async def async_step_configure_device_sensor(
        self,
        user_input: dict[str, Any] | None = None,
        device_id: str | None = None,
    ) -> FlowResult:
        """Configure external temperature sensor for a specific device."""
        errors: dict[str, str] = {}

        # Get device_id from user input if not provided
        if device_id is None and user_input and "device_id" in user_input:
            device_id = user_input["device_id"]

        if device_id is None:
            return await self.async_step_configure_devices()

        NONE_OPTION = "— ingen sensor —"

        if user_input is not None:
            raw_entity = user_input.get(CONF_ENTITY_ID, "")
            selected_entity = "" if (not raw_entity or raw_entity == NONE_OPTION) else raw_entity

            # Update entry data with external sensors configuration
            current_external_sensors = dict(
                self.config_entry.data.get(CONF_EXTERNAL_SENSORS, {})
            )
            had_sensor = device_id in current_external_sensors

            if selected_entity:
                current_external_sensors[device_id] = selected_entity
            else:
                current_external_sensors.pop(device_id, None)

            # If sensor was removed, send -8000 to disable on device before reload
            if had_sensor and not selected_entity:
                coordinator = None
                if hasattr(self.config_entry, "runtime_data") and self.config_entry.runtime_data:
                    coordinator = self.config_entry.runtime_data.coordinator
                if coordinator:
                    await coordinator.async_disable_external_temperature(device_id)

            # Update config entry
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data={
                    **self.config_entry.data,
                    CONF_EXTERNAL_SENSORS: current_external_sensors,
                },
            )

            # Reload the entry to apply changes
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)

            return self.async_abort(reason="external_sensor_configured")

        # Get coordinator from entry runtime data
        coordinator = None
        if hasattr(self.config_entry, "runtime_data") and self.config_entry.runtime_data:
            coordinator = self.config_entry.runtime_data.coordinator

        # Get device name for display
        device_name = device_id
        if coordinator and coordinator.data and device_id in coordinator.data:
            device_name = coordinator.data[device_id].get("name", device_id)

        # Build entity selector - allow any entity with temperature-like state
        entity_options = {}
        for state in self.hass.states.async_all():
            # Look for entities with numeric state (temperature sensors, climate entities, etc.)
            try:
                float(state.state)
                # Include unit_of_measurement if present
                unit = state.attributes.get("unit_of_measurement", "")
                if unit:
                    entity_options[state.entity_id] = f"{state.entity_id} ({unit})"
                else:
                    entity_options[state.entity_id] = state.entity_id
            except (ValueError, TypeError):
                continue

        if not entity_options:
            errors["base"] = "no_entities"

        # Get current selection for this device
        current_external_sensors = self.config_entry.data.get(CONF_EXTERNAL_SENSORS, {})
        current_entity = current_external_sensors.get(device_id, "")

        # Add a blank option so the user can clear the selection
        options_with_none = {NONE_OPTION: NONE_OPTION, **entity_options}

        schema = vol.Schema({
            vol.Optional(
                CONF_ENTITY_ID,
                default=current_entity if current_entity in entity_options else NONE_OPTION,
            ): vol.In(options_with_none),
        })

        return self.async_show_form(
            step_id="configure_device_sensor",
            data_schema=schema,
            errors=errors,
            description_placeholders={
                "device": device_name,
            },
        )
