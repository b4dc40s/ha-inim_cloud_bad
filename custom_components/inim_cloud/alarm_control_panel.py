"""Support for Inim Cloud alarm control panels."""

from __future__ import annotations

import logging

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import CONF_USERNAME, COORDINATOR, DOMAIN

_LOGGER = logging.getLogger(__name__)

# Map Inim Cloud states to Home Assistant states
STATE_MAP = {
    "disarmed": "disarmed",
    "armed_away": "armed_away",
    "armed_home": "armed_home",
    "triggered": "triggered",
    # Add more mappings as needed
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inim Cloud alarm control panel based on a config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data[COORDINATOR]
    api = data["api"]

    async_add_entities([InimAlarmControlPanel(coordinator, api, entry)])


class InimAlarmControlPanel(CoordinatorEntity, AlarmControlPanelEntity):
    """Representation of an Inim Cloud alarm control panel."""

    _attr_has_entity_name = True
    _attr_name = "Alarm"
    _attr_supported_features = (
        AlarmControlPanelEntityFeature.ARM_HOME
        | AlarmControlPanelEntityFeature.ARM_AWAY
        | AlarmControlPanelEntityFeature.DISARM
    )

    def __init__(
        self, coordinator: DataUpdateCoordinator, api, entry: ConfigEntry
    ) -> None:
        """Initialize the alarm control panel entity."""
        super().__init__(coordinator)
        self._api = api
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_alarm"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": f"Inim Cloud Alarm ({entry.data[CONF_USERNAME]})",
            "manufacturer": "Inim",
            "model": "Cloud Alarm",
        }

    @property
    def state(self) -> str:
        """Return the state of the alarm control panel."""
        # Map the API state to a Home Assistant state
        inim_state = self.coordinator.data.get("state", "unknown")
        return STATE_MAP.get(inim_state, "unknown")

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        """Send disarm command."""
        await self._api.set_alarm_state("disarmed")
        # Force state update
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        """Send arm home command."""
        await self._api.set_alarm_state("armed_home")
        # Force state update
        await self.coordinator.async_request_refresh()

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        """Send arm away command."""
        await self._api.set_alarm_state("armed_away")
        # Force state update
        await self.coordinator.async_request_refresh()
