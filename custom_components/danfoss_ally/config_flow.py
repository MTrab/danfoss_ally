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

from .const import (
    API_TIMEOUT,
    CONF_EXTERNAL_SENSORS,
    CONF_KEY,
    CONF_SECRET,
    DOMAIN,
    USER_AGENT_PREFIX,
)

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
