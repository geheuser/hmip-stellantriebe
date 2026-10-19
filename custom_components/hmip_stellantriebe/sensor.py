"""Sensor: Ventilstellung in Prozent (sinnvoll vor allem bei PWM-Regelung)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import PWM_CONTROL
from .entity import HmipSwitchChannelEntity, iter_switch_channels


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Sensoren anlegen."""
    async_add_entities(
        HmipValvePositionSensor(device, index, device_entry)
        for device, index, device_entry in iter_switch_channels(
            hass, entry.runtime_data
        )
    )


class HmipValvePositionSensor(HmipSwitchChannelEntity, SensorEntity):
    """Ventilstellung 0–100 %."""

    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_suggested_display_precision = 0

    def __init__(
        self, device: Any, channel_index: str, device_entry: DeviceEntry
    ) -> None:
        """Initialisieren – bei Zweipunktregelung standardmäßig deaktiviert (nur 0/100)."""
        super().__init__(device, channel_index, "valve_position", device_entry)
        self._attr_entity_registry_enabled_default = (
            self.climate_control_type == PWM_CONTROL
        )

    @property
    def native_value(self) -> float | None:
        """Ventilstellung in Prozent."""
        position = self.valve_position
        return None if position is None else round(position * 100, 1)
