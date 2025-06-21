"""Config flow for Inim Cloud integration."""

from __future__ import annotations

from datetime import datetime, timedelta

import voluptuous as vol
import logging

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .api import InimCloudAPI, InimCloudAuthError, InimCloudConnectionError
from .const import CONF_PASSWORD, CONF_PIN, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Inim Cloud."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            try:
                api = InimCloudAPI()
                auth_data = await api.authenticate(
                    user_input[CONF_USERNAME],
                    user_input[CONF_PASSWORD],
                    user_input[CONF_PIN],
                )

                data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_PIN: user_input[CONF_PIN],
                    "token": auth_data.get("Token"),
                    "token_id": auth_data.get("TokenId"),
                    "token_expiry": (
                        datetime.now() + timedelta(seconds=auth_data.get("TTL", 0))
                    ).isoformat(),
                    "role": auth_data.get("Role", 1),
                }

                _LOGGER.info("Authenticated successfully: %s", data)

                return self.async_create_entry(
                    title=user_input[CONF_USERNAME], data=data
                )
            except InimCloudAuthError:
                errors["base"] = "invalid_auth"
            except InimCloudConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                errors["base"] = "unknown"

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_PIN): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )
