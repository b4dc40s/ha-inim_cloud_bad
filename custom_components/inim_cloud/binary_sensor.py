"""Binary sensor platform for Inim Cloud."""

from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorDeviceClass,
)
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from .const import DOMAIN, COORDINATOR

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data[COORDINATOR]
    devices = coordinator.data or []

    entities: list[InimAlarmTriggeredSensor] = []
    for device in devices:
        _LOGGER.debug("Initializing Alarm sensor for device: %s", device)
        entities.append(InimAlarmTriggeredSensor(coordinator, entry, device))

    async_add_entities(entities)


class InimAlarmTriggeredSensor(CoordinatorEntity, BinarySensorEntity):
    """Binary sensor that reports whether the alarm is triggered."""

    _attr_has_entity_name = True
    _attr_name = "Alarm"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, entry, device: dict[str, Any]):
        super().__init__(coordinator)
        self._entry = entry
        self._device_id = device["id"]
        self._device = device
        self._attr_unique_id = f"{entry.entry_id}_alarm_triggered"

        self._attr_device_info = {
            "identifiers": {(DOMAIN, f"{entry.entry_id}_{self._device_id}")},
            "name": device.get("name", "Inim Alarm"),
            "manufacturer": "Inim",
            "model": "Cloud Alarm",
        }

    @property
    def is_on(self) -> bool:
        """Return True if device has alarm triggered event."""
        device = next((d for d in self.coordinator.data or [] if d["id"] == self._device_id), None)
        _LOGGER.debug("Alarm sensor seeing device: %s", device)
        return bool(device.get("triggered")) if device else False
