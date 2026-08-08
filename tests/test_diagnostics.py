"""Tests for privacy-conscious diagnostics."""

from types import SimpleNamespace

from custom_components.denon_avr_diagnostics.api import ReceiverInfo, ReceiverSnapshot
from custom_components.denon_avr_diagnostics.diagnostics import (
    async_get_config_entry_diagnostics,
)


async def test_diagnostics_do_not_expose_error_messages() -> None:
    host = "192.0.2.10"
    snapshot = ReceiverSnapshot(
        raw={"errors": [f"AppCommand: Cannot connect to http://{host}/goform/AppCommand.xml"]}
    )
    coordinator = SimpleNamespace(
        data=snapshot,
        last_update_success=True,
        client=SimpleNamespace(
            host=host,
            port=80,
            info=ReceiverInfo(serial_number="secret-serial"),
        ),
    )
    entry = SimpleNamespace(data={"host": host}, options={}, runtime_data=coordinator)

    result = await async_get_config_entry_diagnostics(None, entry)
    serialized = str(result)

    assert host not in serialized
    assert "secret-serial" not in serialized
    assert result["coordinator"]["transport_notes"]["error_sources"] == ["AppCommand"]
