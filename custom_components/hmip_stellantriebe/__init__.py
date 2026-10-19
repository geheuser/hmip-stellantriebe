"""HmIP Stellantriebe: Schaltausgang der HmIP-Wandthermostate als Entität.

Die Original-Integration homematicip_cloud empfängt den Zustand des internen
Schaltausgangs (Kanal INTERNAL_SWITCH_CHANNEL, Feld valvePosition) bereits über
die Cloud, legt dafür aber keine Entität an. Diese Integration hängt sich an die
bestehende Verbindung an – keine zweite Cloud-Verbindung, keine eigenen Abfragen.
"""

from __future__ import annotations

from functools import partial

from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady

from .const import HMIP_DOMAIN

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
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Eintrag entladen."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


@callback
def _async_hmip_state_changed(
    hass: HomeAssistant, entry: ConfigEntry, hmip_entry: ConfigEntry
) -> None:
    """Auf Laden/Entladen von homematicip_cloud reagieren."""
    if hass.is_stopping:
        return
    if hmip_entry.state in (ConfigEntryState.LOADED, ConfigEntryState.NOT_LOADED):
        hass.config_entries.async_schedule_reload(entry.entry_id)
