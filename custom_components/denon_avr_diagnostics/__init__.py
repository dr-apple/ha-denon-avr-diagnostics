"""Denon AVR Diagnostics integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import DenonAvrClient, DenonAvrError
from .coordinator import DenonAvrDiagnosticsCoordinator

type DenonAvrDiagnosticsConfigEntry = ConfigEntry[DenonAvrDiagnosticsCoordinator]

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: DenonAvrDiagnosticsConfigEntry) -> bool:
    """Set up Denon AVR Diagnostics from a config entry."""
    client = DenonAvrClient(async_get_clientsession(hass), entry.data[CONF_HOST])
    try:
        await client.async_probe()
    except DenonAvrError as err:
        raise ConfigEntryNotReady(f"Unable to connect to receiver: {err}") from err
    coordinator = DenonAvrDiagnosticsCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: DenonAvrDiagnosticsConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload after options change."""
    await hass.config_entries.async_reload(entry.entry_id)
