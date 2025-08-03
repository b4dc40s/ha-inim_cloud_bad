"""Binary sensor platform for Inim Cloud."""

from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Inim Cloud binary sensors from config entry."""
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data[COORDINATOR]
    devices = coordinator.data if coordinator.data else []

    entities = []

    for device in devices:
        entities.append(InimAlarmTriggeredSensor(coordinator, entry, device))

    async_add_entities(entities)


class InimAlarmTriggeredSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor for alarm triggered state."""

    _attr_has_entity_name = True
    _attr_name = "Alarm"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, entry, device):
        _LOGGER.warning("🧪 InimAlarmTriggeredSensor initialized for device: %s", device)
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = device["id"]
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_alarm_triggered"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_{self._device_id}")},
            "name": self._device.get("name", "Inim Alarm"),
            "manufacturer": "Inim",
            "model": "Cloud Alarm",
        }

    @property
    def is_on(self) -> bool:
        """Return true if alarm is currently triggered."""
        device = next((d for d in self.coordinator.data if d["id"] == self._device_id), None)
        _LOGGER.debug("🔍 Inim device data: %s", device)

        if device and "ares" in device:
            for area in device["ares"]:
                _LOGGER.debug("📦 Area: %s", area)
            return any(area.get("alarm") for area in device["ares"])

        return False
