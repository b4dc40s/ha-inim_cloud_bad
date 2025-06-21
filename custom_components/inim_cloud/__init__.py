"""The Inim Cloud integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import InimCloudAPI, InimCloudAuthError
from .const import CONF_PASSWORD, CONF_PIN, CONF_USERNAME, COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# List of platforms to support
PLATFORMS = [Platform.ALARM_CONTROL_PANEL]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Inim Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    _LOGGER.info("Setting up Inim Cloud integration")

    # Initialize API client with existing token if available
    token = entry.data.get("token")
    token_expiry = None

    if "token_expiry" in entry.data:
        try:
            token_expiry = datetime.fromisoformat(entry.data["token_expiry"])
        except (ValueError, TypeError):
            token_expiry = None

    api = InimCloudAPI(token=token, token_expiry=token_expiry)

    # Try to use existing token or re-authenticate if needed
    need_auth = True

    if api.is_token_valid():
        # Token looks valid based on expiry time, verify with API
        try:
            if await api.validate_token():
                _LOGGER.info("Using existing valid token")
                need_auth = False
        except Exception as ex:
            _LOGGER.warning("Token validation failed: %s", ex)

    # if need_auth:
    # try:
    #     _LOGGER.info("Token expired or invalid, re-authenticating")
    #     auth_data = await api.authenticate(
    #         entry.data[CONF_USERNAME],
    #         entry.data[CONF_PASSWORD],
    #         entry.data[CONF_PIN],
    #     )

    #     # Update the stored token in config entry
    #     new_data = {
    #         **entry.data,
    #         "token": auth_data.get("Token"),
    #         "token_id": auth_data.get("TokenId"),
    #         "token_expiry": (
    #             datetime.now() + timedelta(seconds=auth_data.get("TTL", 0))
    #         ).isoformat(),
    #         "role": auth_data.get("Role", 1),
    #     }

    #     hass.config_entries.async_update_entry(entry, data=new_data)

    # except (InimCloudAuthError, InimCloudConnectionError) as err:
    #     _LOGGER.error("Failed to authenticate: %s", err)
    #     return False

    # Create update coordinator with token refresh capability
    async def async_update_data():
        """Fetch data from API with token refresh if needed."""
        try:
            # First try with current token
            return await api.get_alarm_status()
        except InimCloudAuthError:
            # Token might be expired, try to re-authenticate
            try:
                auth_data = await api.authenticate(
                    entry.data[CONF_USERNAME],
                    entry.data[CONF_PASSWORD],
                    entry.data[CONF_PIN],
                )

                # Update the stored token
                new_data = {
                    **entry.data,
                    "token": auth_data.get("Token"),
                    "token_id": auth_data.get("TokenId"),
                    "token_expiry": (
                        datetime.now() + timedelta(seconds=auth_data.get("TTL", 0))
                    ).isoformat(),
                    "role": auth_data.get("Role", 1),
                }

                hass.config_entries.async_update_entry(entry, data=new_data)

                # Try again with new token
                return await api.get_alarm_status()

            except InimCloudAuthError as err:
                raise UpdateFailed(f"Error re-authenticating: {err}")
        # except InimCloudConnectionError as err:
        #     raise UpdateFailed(f"Error communicating with API: {err}")

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),  # Update every 30 seconds
    )

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Store API and coordinator in hass.data
    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        COORDINATOR: coordinator,
    }

    # Set up all platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # Clean up
    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await api.close()
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
