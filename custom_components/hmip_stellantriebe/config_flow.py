"""Config-Flow für HmIP Stellantriebe."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .const import DOMAIN, HMIP_DOMAIN


class HmipStellantriebeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung ohne Eingaben – nutzt die vorhandene HomematicIP-Cloud-Verbindung."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Bestätigungsschritt."""
        if not self.hass.config_entries.async_entries(HMIP_DOMAIN):
            return self.async_abort(reason="no_hmip")
        if user_input is not None:
            return self.async_create_entry(title="HmIP Stellantriebe", data={})
        return self.async_show_form(step_id="user")
