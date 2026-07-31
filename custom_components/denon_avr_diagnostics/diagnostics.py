"""Diagnostics support for Denon AVR Diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from . import DenonAvrDiagnosticsConfigEntry

TO_REDACT = {"host", "serial_number"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: DenonAvrDiagnosticsConfigEntry
) -> dict[str, Any]:
    """Return privacy-conscious diagnostics."""
    coordinator = entry.runtime_data
    snapshot = coordinator.data
    info = coordinator.client.info
    return {
        "entry": async_redact_data(
            {"data": dict(entry.data), "options": dict(entry.options)}, TO_REDACT
        ),
        "receiver": async_redact_data(
            {
                "manufacturer": info.manufacturer,
                "model": info.model,
                "serial_number": info.serial_number,
                "firmware": info.firmware,
                "http_port": coordinator.client.port,
            },
            TO_REDACT,
        ),
        "coordinator": {
            "last_update_success": coordinator.last_update_success,
            "transport": snapshot.transport,
            "supported_commands": sorted(snapshot.supported_commands),
            "unavailable_commands": sorted(snapshot.unavailable_commands),
            "supported_fields": sorted(snapshot.supported_fields),
            "values": snapshot.values,
            "attributes": snapshot.attributes,
            "transport_notes": snapshot.raw,
        },
    }
