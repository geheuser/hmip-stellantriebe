"""Binärsensor: Stellantrieb offen/geschlossen."""

from __future__ import annotations

from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .entity import HmipSwitchChannelEntity, iter_switch_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Binärsensoren anlegen."""
    async_add_entities(
        HmipValveBinarySensor(device, index, device_entry)
        for device, index, device_entry in iter_switch_channels(
            hass, entry.runtime_data
        )
    )


class HmipValveBinarySensor(HmipSwitchChannelEntity, BinarySensorEntity):
    """An = Schaltausgang aktiv (Stellantrieb wird angesteuert)."""

    _attr_device_class = BinarySensorDeviceClass.OPENING

    def __init__(
        self, device: Any, channel_index: str, device_entry: DeviceEntry
    ) -> None:
        """Initialisieren."""
        super().__init__(device, channel_index, "valve", device_entry)

    @property
    def is_on(self) -> bool | None:
        """Ausgang aktiv, sobald die Ventilstellung über 0 liegt."""
        position = self.valve_position
        return None if position is None else position > 0

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Regelungsart mitgeben (Zweipunkt oder PWM)."""
        return {"climate_control_type": self.climate_control_type}
