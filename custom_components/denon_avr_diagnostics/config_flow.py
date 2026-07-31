"""Config flow for Denon AVR Diagnostics."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.const import CONF_HOST
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DenonAvrClient, DenonAvrConnectionError, DenonAvrError, normalize_host
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_USE_TELNET,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)


class DenonAvrDiagnosticsConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Handle manual setup."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                host = normalize_host(user_input[CONF_HOST])
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                client = DenonAvrClient(async_get_clientsession(self.hass), host)
                info = await client.async_probe()
            except ValueError:
                errors["base"] = "invalid_host"
            except DenonAvrConnectionError:
                errors["base"] = "cannot_connect"
            except DenonAvrError:
                errors["base"] = "unknown"
            else:
                title = info.friendly_name or f"{info.manufacturer} {info.model}"
                return self.async_create_entry(title=title, data={CONF_HOST: host})

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_HOST): str}),
            errors=errors,
        )

    @staticmethod
    def async_get_options_flow(config_entry: Any) -> DenonAvrDiagnosticsOptionsFlow:
        """Return the options flow."""
        return DenonAvrDiagnosticsOptionsFlow()


class DenonAvrDiagnosticsOptionsFlow(OptionsFlow):
    """Configure polling and optional Telnet fallback."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Manage options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=self.config_entry.options.get(
                            CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL
                        ),
                    ): vol.All(
                        vol.Coerce(int),
                        vol.Range(min=MIN_SCAN_INTERVAL, max=MAX_SCAN_INTERVAL),
                    ),
                    vol.Required(
                        CONF_USE_TELNET,
                        default=self.config_entry.options.get(CONF_USE_TELNET, False),
                    ): bool,
                }
            ),
        )
