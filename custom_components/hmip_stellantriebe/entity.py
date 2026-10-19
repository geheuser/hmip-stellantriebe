"""Gemeinsame Basis für die Entitäten."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import CHANNEL_TYPE, CLIMATE_CONTROL_TYPE, HMIP_DOMAIN, VALVE_POSITION


def _channels(device: Any) -> dict[str, dict[str, Any]]:
    """Rohdaten der Kanäle eines Geräts.

    Die homematicip-Bibliothek parst valvePosition beim INTERNAL_SWITCH_CHANNEL
    nicht, hält aber das komplette Geräte-JSON in _rawJSONData aktuell
    (wird bei jedem DEVICE_CHANGED-Event neu gesetzt).
    """
    raw = getattr(device, "_rawJSONData", None) or {}
    return raw.get("functionalChannels") or {}


def iter_switch_channels(haps: list[Any]) -> Iterator[tuple[Any, str]]:
    """Alle Geräte mit internem Schaltausgang: (Gerät, Kanalindex)."""
    for hap in haps:
        for device in hap.home.devices:
            for index, channel in _channels(device).items():
                if (
                    channel.get("functionalChannelType") == CHANNEL_TYPE
                    and VALVE_POSITION in channel
                ):
                    yield device, index


class HmipSwitchChannelEntity(Entity):
    """Entität für den Schaltausgang eines HmIP-Wandthermostats."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, device: Any, channel_index: str, key: str) -> None:
        """Initialisieren."""
        self._device = device
        self._channel_index = channel_index
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.id}_{channel_index}_{key}"
        # Nur verlinken: das Gerät gehört homematicip_cloud.
        self._attr_device_info = DeviceInfo(identifiers={(HMIP_DOMAIN, device.id)})

    @property
    def _channel(self) -> dict[str, Any]:
        return _channels(self._device).get(self._channel_index) or {}

    @property
    def valve_position(self) -> float | None:
        """Ventilstellung 0.0–1.0 (Zweipunktregelung: nur 0 oder 1)."""
        value = self._channel.get(VALVE_POSITION)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return None
        return float(value)

    @property
    def climate_control_type(self) -> str | None:
        """TWO_POINT_CONTROL oder PWM_CONTROL."""
        return self._channel.get(CLIMATE_CONTROL_TYPE)

    @property
    def available(self) -> bool:
        """Nicht verfügbar, wenn das Gerät unerreichbar ist oder kein Wert vorliegt."""
        base = _channels(self._device).get("0") or {}
        return not base.get("unreach") and self.valve_position is not None

    async def async_added_to_hass(self) -> None:
        """Am Update-Callback des Geräts anmelden."""
        self._device.on_update(self._async_device_changed)
        self.async_on_remove(
            lambda: self._device.remove_callback(self._async_device_changed)
        )

    @callback
    def _async_device_changed(self, *args: Any, **kwargs: Any) -> None:
        self.async_write_ha_state()
