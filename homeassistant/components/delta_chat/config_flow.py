"""Config flow for the Delta Chat integration."""

from __future__ import annotations

import logging
from typing import Any, Final

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_EMAIL, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
import homeassistant.helpers.config_validation as cv

from .bot import DeltaBot
from .const import CONF_ADD_ANOTHER, CONF_DELTACHAT_RELAY, DEFAULT_RELAY, DOMAIN

_LOGGER = logging.getLogger(__name__)

IDENTIFIER: Final = "delta_chat"

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_DELTACHAT_RELAY, default=DEFAULT_RELAY): cv.string,
    }
)

STEP_EMAIL_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_EMAIL): cv.string,
        vol.Optional(CONF_NAME): cv.string,
        vol.Optional(CONF_ADD_ANOTHER): cv.boolean,
    }
)


class PlaceholderHub:
    """Placeholder class to make tests pass.

    TODO Remove this placeholder class and replace with things from your PyPI package.
    """

    def __init__(self, host: str) -> None:
        """Initialize."""
        self.host = host

    async def authenticate(self, username: str, password: str) -> bool:
        """Test if we can authenticate with the host."""
        return True


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> str:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    hub = DeltaBot(data[CONF_DELTACHAT_RELAY])

    qrdata = await hub.init()

    if qrdata is None:
        raise CannotConnect
    return qrdata


class DeltaChatConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Delta Chat."""

    VERSION = 1

    data: dict[str, Any]

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                qrdata = await validate_input(self.hass, user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                self.data = user_input
                self.data[CONF_EMAIL] = []
                self.data["qrdata"] = qrdata

                return await self.async_step_email()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_email(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Second step in config flow to add emails to notify."""
        errors: dict[str, str] = {}
        if user_input is not None:
            self.data[CONF_EMAIL].append(
                {
                    "email": user_input[CONF_EMAIL],
                    "name": user_input.get(CONF_NAME, user_input[CONF_EMAIL]),
                }
            )
            # If user ticked the box show this form again so they can add an
            # additional email.
            if user_input.get(CONF_ADD_ANOTHER, False):
                return await self.async_step_email()

            # User is done adding emails, create the config entry.
            await self.async_set_unique_id(IDENTIFIER)
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title="Delta Bot", data=self.data)

        return self.async_show_form(
            step_id="email", data_schema=STEP_EMAIL_SCHEMA, errors=errors
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle reconfiguration of the integration."""
        errors: dict[str, str] = {}
        if not hasattr(self, "data"):
            self.data = {}
        if CONF_EMAIL not in self.data:
            self.data[CONF_EMAIL] = []
        if user_input:
            self.data[CONF_EMAIL].append(
                {
                    "email": user_input[CONF_EMAIL],
                    "name": user_input.get(CONF_NAME, user_input[CONF_EMAIL]),
                }
            )
            # If user ticked the box show this form again so they can add an
            # additional email.
            if user_input.get(CONF_ADD_ANOTHER, False):
                return await self.async_step_reconfigure()
            await self.async_set_unique_id(IDENTIFIER)
            self._abort_if_unique_id_mismatch(reason="wrong_account")
            _LOGGER.info("RECONFIGURE, %s", self.data)
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data_updates=self.data,
            )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=STEP_EMAIL_SCHEMA,
            errors=errors,
        )


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
