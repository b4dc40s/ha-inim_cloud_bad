"""API client for Inim Cloud."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
import json
from typing import Any

import aiohttp
import async_timeout
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed


_LOGGER = logging.getLogger(__name__)


class InimCloudAuthError(Exception):
    """Exception to indicate authentication error."""


class InimCloudError(Exception):
    """Exception to indicate a general Inim Cloud error."""


class InimCloudAPI:
    """API client for Inim Cloud."""

    def __init__(
        self,
        hass: HomeAssistant,
        client_id: str,
        token: str | None = None,
        token_expiry: datetime | None = None,
    ) -> None:
        """Initialize the API client."""
        self.hass = hass
        self.session = async_get_clientsession(hass)
        self.client_id = client_id
        self.token = token
        self.token_expiry = token_expiry
        self.base_url = "https://api.inimcloud.com"

    @property
    def _default_params(self) -> dict[str, Any]:
        """Get default parameters for API requests."""
        return {
            "Node": "inimhome",
            "Name": "it.inim.inimutenti",
            "ClientIP": "127.0.0.1",
            "Method": None,
            "Token": self.token,
            "ClientId": self.client_id,
            "Context": None,
            "Params": {},
        }

    @property
    def _default_headers(self) -> dict[str, str]:
        """Get default headers for API requests."""
        return {
            "Accept": "*/*",
            "Accept-Language": "en-GB,en;q=0.9",
            "User-Agent": "inimhome/377 CFNetwork/3826.500.131 Darwin/24.5.0",
        }

    async def authenticate(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate with Inim Cloud and return auth data."""

        payload = {
            **self._default_params,
            "Method": "RegisterClient",
            "Token": None,
            "Params": {
                "Username": username,
                "Password": password,
                "ClientId": self.client_id,
                "ClientName": "iPhone",
                "ClientInfo": json.dumps(
                    {
                        "version": "2.4.29",
                        "name": "Inim+Home",
                        "platform": "iOS",
                        "device": "iPhone16,2",
                        "screen_height": "",
                        "screen_width": "",
                        "brand": "Apple",
                        "osversion": "iOS+v.18.5",
                    }
                ),
                "ClientApp": "it.inim.inimutenti",
                "ClientVersion": "2.4.29377",
                "ClientPlatform": "ios",
                "Role": 1,
                "Brand": 0,
            },
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    self.base_url,
                    params={"req": json.dumps(payload)},
                    headers=self._default_headers,
                )

                response.raise_for_status()
                json_data = await response.json()

                if json_data["Status"] != 0:
                    raise InimCloudAuthError(
                        f"Authentication failed: {json_data.get('ErrMsg', 'Unknown error')}"
                    )

                data = json_data.get("Data", {})
                if not data:
                    _LOGGER.error("No data in authentication response: %s", json_data)
                    raise InimCloudAuthError("No data received from Inim Cloud")

                if not data.get("Token"):
                    _LOGGER.error("No token in authentication data: %s", data)
                    raise InimCloudAuthError("No token received from Inim Cloud")

                self.token = data["Token"]
                ttl_seconds = data.get("TTL", 0)
                self.token_expiry = datetime.now() + timedelta(seconds=ttl_seconds)

                return data

        except aiohttp.ClientError as err:
            raise InimCloudAuthError(f"Connection error: {err}") from err
        except asyncio.TimeoutError as err:
            raise InimCloudAuthError("Connection timeout") from err
        except Exception as err:
            raise InimCloudAuthError(f"An unexpected error occurred: {err}") from err

    async def validate_token(self) -> bool:
        """Check if the client is authenticated."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "Authenticate",
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    self.base_url,
                    params={"req": json.dumps(payload)},
                    headers=self._default_headers,
                )

                response.raise_for_status()
                json_data = await response.json()

                if json_data["Status"] != 0:
                    raise InimCloudAuthError(
                        f"Authentication check failed: {json_data.get('ErrMsg', 'Unknown error')}"
                    )
                return True

        except (aiohttp.ClientError, asyncio.TimeoutError):
            return False
        except Exception:
            return False

    def is_token_valid(self) -> bool:
        """Check if token is valid based on expiry time."""
        if not self.token or not self.token_expiry:
            return False
        return datetime.now() < self.token_expiry

    async def get_devices(self) -> list[dict[str, Any]]:
        """Get list of devices from Inim Cloud."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "GetDevicesExtended",
            "Params": {"Info": "17301503"},
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    self.base_url,
                    params={"req": json.dumps(payload)},
                    headers=self._default_headers,
                )

                response.raise_for_status()
                json_data = await response.json()

                if json_data["Status"] != 0:
                    if json_data.get("ErrMsg") == "Token not valid or expired":
                        raise InimCloudAuthError("Token expired or invalid")
                    raise InimCloudError(
                        f"API error: {json_data.get('ErrMsg', 'Unknown error')}"
                    )

                devices = json_data.get("Data", {}).get("Devices", [])
                if not devices:
                    return []

                return [
                    {
                        "id": device.get("DeviceId"),
                        "active_scenario": device.get("ActiveScenario"),
                        "name": device.get("Name"),
                        "scenarios": [
                            {
                                "id": s.get("ScenarioId"),
                                "name": s.get("Name"),
                            }
                            for s in device.get("Scenarios", [])
                        ],
                        "ares": [
                            {
                                "id": a.get("AresId"),
                                "name": a.get("Name"),
                                "armed": a.get("Armed"),
                                "alarm": a.get("Alarm"),
                            }
                            for a in device.get("Ares", [])
                        ],
                        "zones": [
                            {
                                "id": z.get("ZoneId"),
                                "type": z.get("Type"),
                                "name": z.get("Name"),
                                "area": z.get("Areas"),
                                "status": z.get("Status"),
                                "visibility": z.get("Visibility"),
                            }
                            for z in device.get("Zones", [])
                        ],
                    }
                    for device in devices
                ]
        except aiohttp.ClientError as err:
            raise InimCloudError(f"Connection error: {err}") from err
        except asyncio.TimeoutError:
            raise InimCloudError("Connection timeout") from err
        except InimCloudAuthError:
            raise
        except Exception as err:
            raise InimCloudError(
                f"An unexpected error occurred while fetching devices: {err}"
            ) from err

    async def activate_scenario(
        self, device_id: str | int, scenario_id: str | int
    ) -> dict[str, Any]:
        """Activate a scenario on a device."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        device_id_str = str(device_id)
        scenario_id_str = str(scenario_id)

        payload = {
            **self._default_params,
            "Method": "ActivateScenario",
            "Params": {
                "DeviceId": device_id_str,
                "ScenarioId": scenario_id_str,
            },
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    self.base_url,
                    params={"req": json.dumps(payload)},
                    headers=self._default_headers,
                )

                response.raise_for_status()
                json_data = await response.json()

                if json_data["Status"] != 0:
                    if json_data.get("ErrMsg") == "Token not valid or expired":
                        raise InimCloudAuthError("Token expired or invalid")
                    raise InimCloudError(
                        f"Failed to activate scenario: {json_data.get('ErrMsg', 'Unknown error')}"
                    )

                return json_data

        except aiohttp.ClientError as err:
            raise InimCloudError(f"Connection error: {err}") from err
        except asyncio.TimeoutError:
            raise InimCloudError("Connection timeout") from err
        except InimCloudAuthError:
            raise
        except Exception as err:
            raise InimCloudError(f"An unexpected error occurred: {err}") from err

    async def get_active_scenario(self, device_id: str) -> dict[str, Any]:
        """Get the active scenario for a device."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "GetDevicesExtended",
            "Params": {"Info": "11335", "DeviceIds": [device_id]},
        }

        try:
            async with async_timeout.timeout(10):
                response = await self.session.get(
                    self.base_url,
                    params={"req": json.dumps(payload)},
                    headers=self._default_headers,
                )

                response.raise_for_status()
                json_data = await response.json()

                if json_data["Status"] != 0:
                    if json_data.get("ErrMsg") == "Token not valid or expired":
                        raise InimCloudAuthError("Token expired or invalid")
                    raise InimCloudError(
                        f"Failed to get active scenario: {json_data.get('ErrMsg', 'Unknown error')}"
                    )

                devices = json_data.get("Data", {}).get("Devices", [])
                if not devices:
                    raise InimCloudError("No devices found")

                device = next(
                    (d for d in devices if str(d.get("DeviceId")) == device_id), None
                )
                if not device:
                    raise InimCloudError(f"Device {device_id} not found")

                return {
                    "id": device.get("DeviceId"),
                    "active_scenario": device.get("ActiveScenario"),
                    "name": device.get("Name"),
                    "scenarios": [
                        {
                            "id": s.get("ScenarioId"),
                            "name": s.get("Name"),
                        }
                        for s in device.get("Scenarios", [])
                    ],
                }

        except aiohttp.ClientError as err:
            raise InimCloudError(f"Connection error: {err}") from err
        except asyncio.TimeoutError:
            raise InimCloudError("Connection timeout") from err
        except InimCloudAuthError:
            raise
        except Exception as err:
            raise InimCloudError(f"An unexpected error occurred: {err}") from err
