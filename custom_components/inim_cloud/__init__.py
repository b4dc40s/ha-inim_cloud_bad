"""The Inim Cloud integration."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import json
import async_timeout
import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryAuthFailed

from .api import InimCloudAPI, InimCloudAuthError, InimCloudError
from .const import CONF_USERNAME, CONF_PASSWORD, COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.ALARM_CONTROL_PANEL, Platform.BINARY_SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    _LOGGER.info("Setting up Inim Cloud integration")

    client_id = entry.data.get("client_id")
    token = entry.data.get("token")
    token_expiry = None
    if "token_expiry" in entry.data:
        try:
            token_expiry = datetime.fromisoformat(entry.data["token_expiry"])
        except (ValueError, TypeError):
            token_expiry = None

    api = InimCloudAPI(
        hass, client_id=client_id, token=token, token_expiry=token_expiry
    )

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
            _LOGGER.debug("Token expired or invalid, re-authenticating")
            auth_data = await api.authenticate(
                entry.data[CONF_USERNAME], entry.data[CONF_PASSWORD]
            )

            new_data = { ... }
            hass.config_entries.async_update_entry(entry, data=new_data)

        except InimCloudAuthError as err:
            _LOGGER.error("Failed to authenticate: %s", err)
            return False
        except Exception as err:
            _LOGGER.exception("Unexpected error during authentication: %s", err)
            return False

    async def async_update_data():
        """Fetch devices and latest alarm events."""
        _LOGGER.info("Fetching devices from Inim Cloud API")
        devices = await api.get_devices()

        # ───── Nuova logica eventi ─────
        try:
            alerts = await api.get_alerts()
            latest_alerts = {e.get("DeviceId"): e for e in alerts if e.get("Type") == "Alarm"}
        except Exception:
            latest_alerts = {}

        for dev in devices:
            dev["triggered"] = bool(latest_alerts.get(dev.get("id")))
        # ─────────────────────────────────

        return devices

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name=DOMAIN,
        update_method=async_update_data,
        update_interval=timedelta(seconds=30),
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "api": api,
        COORDINATOR: coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        api = hass.data[DOMAIN][entry.entry_id]["api"]
        await api.close()
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok
