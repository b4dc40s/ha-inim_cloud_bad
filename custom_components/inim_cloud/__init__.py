"""The Inim Cloud integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
import json

import async_timeout
import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import InimCloudAPI, InimCloudAuthError, InimCloudError
from .const import CONF_USERNAME, CONF_PASSWORD, COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Inim Cloud from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("Setting up Inim Cloud integration")

    client_id = entry.data.get("client_id")
    token = entry.data.get("token")
    token_expiry = None
    if entry.data.get("token_expiry"):
        try:
            token_expiry = datetime.fromisoformat(entry.data["token_expiry"])
        except (ValueError, TypeError):
            token_expiry = None

    api = InimCloudAPI(hass, client_id=client_id, token=token, token_expiry=token_expiry)
    need_auth = True
    if api.is_token_valid():
        try:
            if await api.validate_token():
                _LOGGER.debug("Using existing valid token")
                need_auth = False
        except Exception as ex:
            _LOGGER.warning("Token validation failed: %s", ex)

    if need_auth:
        try:
            _LOGGER.debug("Re‑authenticating with cloud")
            auth_data = await api.authenticate(entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD])
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
        except InimCloudAuthError as err:
            _LOGGER.error("Failed to authenticate: %s", err)
            return False
        except Exception as err:
            _LOGGER.exception("Unexpected error: %s", err)
            return False

    async def async_update_data():
        """Fetch data and optionally poll alarm flags."""
        try:
            # Step 1: Get list of device IDs
            raw_devices = await api.get_devices()
        except InimCloudAuthError as err:
            raise ConfigEntryAuthFailed(f"Error retrieving devices: {err}")
        except (aiohttp.ClientError, async_timeout.TimeoutError) as err:
            raise UpdateFailed(f"Network error fetching devices: {err}")
        except Exception as err:
            raise UpdateFailed(f"Uncaught error: {err}")

        # Attempt a RequestPoll for each device
        for dev in raw_devices:
            try:
                await api.request_poll(dev["id"])
            except Exception as exc:
                _LOGGER.debug("RequestPoll failed for device %s: %s", dev["id"], exc)

        try:
            # Refresh device list after poll
            devices = await api.get_devices()
        except Exception as err:
            raise UpdateFailed(f"Failed re‑fetching post‑poll: {err}")

        _LOGGER.debug("Fetched %d devices after poll", len(devices))
        return devices

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()
    hass.data[DOMAIN][entry.entry_id] = {"api": api, COORDINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await api.close()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
