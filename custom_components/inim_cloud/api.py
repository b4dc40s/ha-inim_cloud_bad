"""API client for Inim Cloud."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import requests
import json


class InimCloudAuthError(Exception):
    """Exception to indicate authentication error."""


class InimCloudError(Exception):
    """Exception to indicate a general Inim Cloud error."""


class InimCloudAPI:
    """API client for Inim Cloud."""

    def __init__(
        self,
        client_id: str,
        token: str | None = None,
        token_expiry: datetime | None = None,
    ) -> None:
        """Initialize the API client."""
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

    def authenticate(self, username: str, password: str) -> dict[str, Any]:
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
            response = requests.get(
                self.base_url,
                params={"req": json.dumps(payload)},
                headers=self._default_headers,
            )

            response.raise_for_status()

            json_data = response.json()
            if json_data["Status"] != 0:
                raise InimCloudAuthError(
                    f"Authentication failed: {json_data.get('ErrMsg', 'Unknown error')}"
                )

            data = json_data.get("Data", {})
            if not data:
                raise InimCloudAuthError("No data received from Inim Cloud")

            if not data.get("Token"):
                raise InimCloudAuthError("No token received from Inim Cloud")
            self.token = data["Token"]
            ttl_seconds = data.get("TTL", 0)
            self.token_expiry = datetime.now() + timedelta(seconds=ttl_seconds)

            return json_data

        except Exception as err:
            raise InimCloudAuthError("An unexpected error occurred") from err

    def validate_token(self) -> bool:
        """Check if the client is authenticated."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "Authenticate",
        }

        try:
            response = requests.get(
                self.base_url,
                params={"req": json.dumps(payload)},
                headers=self._default_headers,
            )
            response.raise_for_status()

            json_data = response.json()
            if json_data["Status"] != 0:
                raise InimCloudAuthError(
                    f"Authentication check failed: {json_data.get('ErrMsg', 'Unknown error')}"
                )
            return True
        except Exception:
            return False

    def is_token_valid(self) -> bool:
        """Check if token is valid based on expiry time."""
        if not self.token:
            return False
        return datetime.now() < self.token_expiry

    def get_devices(self) -> list[dict[str, Any]]:
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "GetDevicesExtended",
            "Params": {"Info": "17301503"},
        }

        try:
            response = requests.get(
                self.base_url,
                params={"req": json.dumps(payload)},
                headers=self._default_headers,
            )
            response.raise_for_status()

            json_data = response.json()
            if json_data["Status"] != 0:
                raise InimCloudAuthError(
                    f"Authentication check failed: {json_data.get('ErrMsg', 'Unknown error')}"
                )
            devices = json_data.get("Data", {}).get("Devices", [])
            if not devices:
                raise InimCloudAuthError("No devices found")

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
        except Exception:
            raise InimCloudError("An unexpected error occurred while fetching devices")

    def activate_scenario(self, device_id: str, scenario_id: str) -> dict[str, Any]:
        """Activate a scenario on a device."""
        if not self.token:
            raise InimCloudAuthError("Not authenticated")

        payload = {
            **self._default_params,
            "Method": "ActivateScenario",
            "Params": {
                "DeviceId": device_id,
                "ScenarioId": scenario_id,
            },
        }

        try:
            response = requests.get(
                self.base_url,
                params={"req": json.dumps(payload)},
                headers=self._default_headers,
            )
            response.raise_for_status()

            json_data = response.json()
            if json_data["Status"] != 0:
                raise InimCloudError(
                    f"Failed to activate scenario: {json_data.get('ErrMsg', 'Unknown error')}"
                )
            return json_data
        except Exception as err:
            raise InimCloudError(f"An unexpected error occurred: {err}") from err

    # async def get_alarm_status(self) -> dict[str, Any]:
    #     """Get the current alarm status."""
    #     if not self.token or not self.session:
    #         raise InimCloudAuthError("Not authenticated")

    #     try:
    #         async with asyncio.timeout(10):
    #             response = await self.session.get(
    #                 f"{self.base_url}/alarm/status",
    #                 headers={"Authorization": f"Bearer {self.token}"},
    #             )
    #             response.raise_for_status()
    #             return await response.json()

    # async def set_alarm_state(self, state: str) -> dict[str, Any]:
    #     """Set the alarm state."""
    #     if not self.token or not self.session:
    #         raise InimCloudAuthError("Not authenticated")

    #     try:
    #         async with asyncio.timeout(10):
    #             response = await self.session.post(
    #                 f"{self.base_url}/alarm/set",
    #                 headers={"Authorization": f"Bearer {self.token}"},
    #                 json={"state": state},
    #             )
    #             response.raise_for_status()
    #             return await response.json()
    #     except aiohttp.ClientError as err:
    #         raise InimCloudConnectionError(f"Connection error: {err}") from err
    #     except TimeoutError as err:
    #         raise InimCloudConnectionError("Connection timeout") from err
