"""Gemeinsame Basis für die Entitäten."""

from __future__ import annotations

from collections.abc import Iterator
import logging
from typing import Any

from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.entity import Entity

from .const import CHANNEL_TYPE, CLIMATE_CONTROL_TYPE, HMIP_DOMAIN, VALVE_POSITION

_LOGGER = logging.getLogger(__name__)


def _channels(device: Any) -> dict[str, dict[str, Any]]:
    """Rohdaten der Kanäle eines Geräts.

    Die homematicip-Bibliothek parst valvePosition beim INTERNAL_SWITCH_CHANNEL
    nicht, hält aber das komplette Geräte-JSON in _rawJSONData aktuell
    (wird bei jedem DEVICE_CHANGED-Event neu gesetzt).
    """
    raw = getattr(device, "_rawJSONData", None) or {}
    return raw.get("functionalChannels") or {}


def valve_positions(device: Any) -> list[float]:
    """Ventilstellungen aller internen Schaltausgänge eines Geräts (leer = keine)."""
    return [
        float(value)
        for channel in _channels(device).values()
        if channel.get("functionalChannelType") == CHANNEL_TYPE
        and isinstance(value := channel.get(VALVE_POSITION), (int, float))
        and not isinstance(value, bool)
    ]


def iter_switch_channels(
    hass: HomeAssistant, haps: list[Any]
) -> Iterator[tuple[Any, str, dr.DeviceEntry]]:
    """Alle Geräte mit internem Schaltausgang: (Gerät, Kanalindex, HA-Gerät).

    Geräte-Kennungen sind in HA nur je Config-Entry eindeutig – das HA-Gerät
    wird deshalb im Eintrag von homematicip_cloud gesucht, nicht per DeviceInfo
    (das würde ein Doppel-Gerät unter dieser Integration anlegen).
    """
    dev_reg = dr.async_get(hass)
    for hap in haps:
        ha_devices = {
            ident: entry
            for entry in dr.async_entries_for_config_entry(
                dev_reg, hap.config_entry.entry_id
            )
            for domain, ident in entry.identifiers
            if domain == HMIP_DOMAIN
        }
        for device in hap.home.devices:
            for index, channel in _channels(device).items():
                if (
                    channel.get("functionalChannelType") != CHANNEL_TYPE
                    or VALVE_POSITION not in channel
                ):
                    continue
                if (device_entry := ha_devices.get(device.id)) is None:
                    _LOGGER.warning(
                        "Kein HA-Gerät für %s (%s) gefunden, übersprungen",
                        device.label,
                        device.id,
                    )
                    continue
                yield device, index, device_entry


class HmipSwitchChannelEntity(Entity):
    """Entität für den Schaltausgang eines HmIP-Wandthermostats."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(
        self,
        device: Any,
        channel_index: str,
        key: str,
        device_entry: dr.DeviceEntry,
    ) -> None:
        """Initialisieren."""
        self._device = device
        self._channel_index = channel_index
        self._attr_translation_key = key
        self._attr_unique_id = f"{device.id}_{channel_index}_{key}"
        # An das vorhandene Gerät von homematicip_cloud hängen (wie switch_as_x),
        # ohne dieses Gerät zu verändern.
        self.device_entry = device_entry

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
