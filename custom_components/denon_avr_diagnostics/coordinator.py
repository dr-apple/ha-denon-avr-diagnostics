"""Data update coordinator for Denon AVR Diagnostics."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import DenonAvrClient, DenonAvrError, ReceiverSnapshot
from .const import CONF_SCAN_INTERVAL, CONF_USE_TELNET, DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)


class DenonAvrDiagnosticsCoordinator(DataUpdateCoordinator[ReceiverSnapshot]):
    """Coordinate receiver polling across all entities."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: DenonAvrClient) -> None:
        self.config_entry = entry
        self.client = client
        scan_interval = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    async def _async_update_data(self) -> ReceiverSnapshot:
        try:
            return await self.client.async_update(
                use_telnet=self.config_entry.options.get(CONF_USE_TELNET, False)
            )
        except DenonAvrError as err:
            raise UpdateFailed(f"Unable to update receiver: {err}") from err
