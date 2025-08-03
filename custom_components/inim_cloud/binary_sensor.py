"""Binary sensor platform for Inim Cloud."""

from __future__ import annotations

import logging
from typing import Any

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
    hass,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """
    Set up binary sensors for Inim Cloud.

    With RequestPoll support, if "alarm" is flagged in an area, sensor flips on.
    """
    data = hass.data[DOMAIN][entry.entry_id]
    coordinator = data[COORDINATOR]
    devices = coordinator.data or []

    entities: list[InimAlarmTriggeredSensor] = []
    for device in devices:
        _LOGGER.debug("Initializing Alarm sensor for device: %s", device)
        entities.append(InimAlarmTriggeredSensor(coordinator, entry, device))

    async_add_entities(entities)


class InimAlarmTriggeredSensor(CoordinatorEntity, BinarySensorEntity):
    """
    Binary sensor indicating alarm triggered state.

    Turns ON only if `device["ares"][].alarm is True` after RequestPoll.
    """
    _attr_has_entity_name = True
    _attr_name = "Alarm"
    _attr_device_class = BinarySensorDeviceClass.SAFETY

    def __init__(self, coordinator, entry, device: dict[str, Any]) -> None:
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
        """
        Returns True if ANY area in `ares` has alarm==True.

        Triggered only if RequestPoll happened during coordinator update.
        """
        device = next(
            (d for d in self.coordinator.data or [] if d.get("id") == self._device_id),
            None
        )
        _LOGGER.debug("Alarm sensor checking device: %s", device)

        if not device:
            return False

        ares = device.get("ares", [])
        if not ares:
            return False

        alarmed = any(area.get("alarm") for area in ares)
        _LOGGER.debug("Alarm state (any area.alarm=True): %s", alarmed)
        return bool(alarmed)
