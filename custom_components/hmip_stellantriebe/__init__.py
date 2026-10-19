"""HmIP Stellantriebe: Schaltausgang der HmIP-Wandthermostate als Entität.

Die Original-Integration homematicip_cloud empfängt den Zustand des internen
Schaltausgangs (Kanal INTERNAL_SWITCH_CHANNEL, Feld valvePosition) bereits über
die Cloud, legt dafür aber keine Entität an. Diese Integration hängt sich an die
bestehende Verbindung an – keine zweite Cloud-Verbindung, keine eigenen Abfragen.
"""

from __future__ import annotations

from collections.abc import Callable
from functools import partial
from typing import Any

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from . import climate_status
from .const import HMIP_DOMAIN
from .entity import iter_switch_channels

PLATFORMS = [Platform.BINARY_SENSOR, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eintrag einrichten."""
    hmip_entries = hass.config_entries.async_entries(HMIP_DOMAIN)
    loaded = [e for e in hmip_entries if e.state is ConfigEntryState.LOADED]
    if not loaded:
        raise ConfigEntryNotReady("HomematicIP Cloud ist (noch) nicht geladen")

    # Ein HomematicipHAP je Access Point.
    entry.runtime_data = [e.runtime_data for e in loaded]

    # Wird homematicip_cloud neu geladen, entstehen neue Geräte-Objekte –
    # dann neu laden, damit die Entitäten an den neuen Objekten hängen.
    for hmip_entry in hmip_entries:
        entry.async_on_unload(
            hmip_entry.async_on_state_change(
                partial(_async_hmip_state_changed, hass, entry, hmip_entry)
            )
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Heizstatus (hvac_action) an den HmIP-Thermostaten der Räume.
    if climate_status.async_patch():
        devices = {device for device, _, _ in iter_switch_channels(hass, entry.runtime_data)}
        for device in devices:
            handler = _group_refresh_handler(hass, device)
            device.on_update(handler)
            entry.async_on_unload(partial(device.remove_callback, handler))
        entry.async_on_unload(partial(_async_restore_climate, hass))
        climate_status.async_refresh_groups(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eintrag entladen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


def _group_refresh_handler(hass: HomeAssistant, device: Any) -> Callable[..., None]:
    """Update-Callback je Wandthermostat: zugehörige Klimaentität neu schreiben."""

    @callback
    def _handler(*_args: Any, **_kwargs: Any) -> None:
        climate_status.async_refresh_groups(hass, device)

    return _handler


@callback
def _async_restore_climate(hass: HomeAssistant) -> None:
    """Beim Entladen: Original-hvac_action zurück und Zustände neu schreiben."""
    climate_status.async_unpatch()
    climate_status.async_refresh_groups(hass)


@callback
def _async_hmip_state_changed(
    hass: HomeAssistant, entry: ConfigEntry, hmip_entry: ConfigEntry
) -> None:
    """Auf Laden/Entladen von homematicip_cloud reagieren."""
    if hass.is_stopping:
        return
    if hmip_entry.state in (ConfigEntryState.LOADED, ConfigEntryState.NOT_LOADED):
        hass.config_entries.async_schedule_reload(entry.entry_id)
