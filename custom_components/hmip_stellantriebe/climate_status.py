"""hvac_action („Heizt“/„Untätig“) für HmIP-Heizgruppen mit Wandthermostat-Schaltausgang.

homematicip_cloud setzt hvac_action nur bei Heizkörperthermostaten. Hier wird die
Eigenschaft der Klasse HomematicipHeatingGroup erweitert: Gehört zur Gruppe ein
Gerät mit internem Schaltausgang (z. B. HmIP-BWTH), gilt „heizt“, sobald einer
davon aktiv ist. Alle anderen Gruppen behalten das Original-Verhalten, und jeder
Fehler fällt auf das Original zurück – die Klimaentität selbst wird nie gestört.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.climate import HVACAction
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import entity_platform

from .const import HMIP_DOMAIN
from .entity import valve_positions

_LOGGER = logging.getLogger(__name__)
_ORIGINAL = "_hmip_stellantriebe_original_hvac_action"


def _heating_group_class() -> type | None:
    try:
        from homeassistant.components.homematicip_cloud.climate import (  # noqa: PLC0415
            HomematicipHeatingGroup,
        )
    except ImportError:
        return None
    return HomematicipHeatingGroup


def _patched(original: property) -> property:
    def hvac_action(self: Any) -> HVACAction | None:
        try:
            group = self._device
            if not group.cooling:
                positions = [p for d in group.devices or [] for p in valve_positions(d)]
                if positions:
                    return HVACAction.HEATING if any(positions) else HVACAction.IDLE
        except Exception:  # noqa: BLE001
            _LOGGER.debug("hvac_action für %s nicht ermittelbar", self, exc_info=True)
        return original.fget(self)

    return property(hvac_action)


def async_patch() -> bool:
    """hvac_action der HmIP-Heizgruppen erweitern. False, wenn nicht möglich."""
    cls = _heating_group_class()
    original = cls.__dict__.get("hvac_action") if cls else None
    if cls is None or not isinstance(original, property):
        _LOGGER.warning(
            "HomematicipHeatingGroup.hvac_action nicht gefunden – Heizstatus an den "
            "Thermostaten nicht verfügbar (die Stellantrieb-Sensoren funktionieren weiter)"
        )
        return False
    if not hasattr(cls, _ORIGINAL):
        setattr(cls, _ORIGINAL, original)
        cls.hvac_action = _patched(original)
    return True


def async_unpatch() -> None:
    """Original-Verhalten wiederherstellen."""
    cls = _heating_group_class()
    if cls is not None and (original := cls.__dict__.get(_ORIGINAL)) is not None:
        cls.hvac_action = original
        delattr(cls, _ORIGINAL)


@callback
def async_refresh_groups(hass: HomeAssistant, device: Any | None = None) -> None:
    """Zustand der HmIP-Klimaentitäten neu schreiben (alle oder die mit diesem Gerät).

    Schaltet ein Wandthermostat seinen Ausgang, meldet die Cloud nur das Gerät,
    nicht die Heizgruppe – ohne diesen Anstoß käme hvac_action erst mit der
    nächsten Gruppenänderung.
    """
    for platform in entity_platform.async_get_platforms(hass, HMIP_DOMAIN):
        if platform.domain != "climate":
            continue
        for entity in list(platform.entities.values()):
            group = getattr(entity, "_device", None)
            if entity.hass is None or not hasattr(group, "devices"):
                continue
            if device is None or device in (group.devices or []):
                entity.async_write_ha_state()
