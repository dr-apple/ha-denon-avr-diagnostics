"""Home Assistant integration tests."""

from unittest.mock import patch

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.denon_avr_diagnostics.api import ReceiverInfo, ReceiverSnapshot
from custom_components.denon_avr_diagnostics.const import (
    ACTIVE_SPEAKER,
    DOMAIN,
    INPUT_SIGNAL,
)


async def _async_probe(client) -> ReceiverInfo:
    client.port = 80
    client.info = ReceiverInfo(
        manufacturer="Denon",
        model="AVR-X1500H",
        serial_number="test-serial",
        friendly_name="Test AVR",
        firmware="test-firmware",
    )
    return client.info


async def _async_update(client, *, use_telnet: bool = False) -> ReceiverSnapshot:
    return ReceiverSnapshot(
        values={
            "power": "ON",
            "input_channels": "2.0",
            "configured_speakers": "2.0",
            "active_output_channels": "2.0",
        },
        attributes={
            "input_channels": {"channels": ["FL", "FR"]},
            "configured_speakers": {"channels": ["FL", "FR"]},
            "active_output_channels": {"channels": ["FL", "FR"]},
        },
        supported_fields={
            "power",
            "input_channels",
            "configured_speakers",
            "active_output_channels",
        },
        supported_commands={INPUT_SIGNAL, ACTIVE_SPEAKER},
        transport="HTTP",
    )


async def test_setup_uses_single_config_entry_device(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test AVR",
        data={CONF_HOST: "192.0.2.10"},
        unique_id="192.0.2.10",
    )
    entry.add_to_hass(hass)

    with (
        patch(
            "custom_components.denon_avr_diagnostics.api.DenonAvrClient.async_probe",
            _async_probe,
        ),
        patch(
            "custom_components.denon_avr_diagnostics.api.DenonAvrClient.async_update",
            _async_update,
        ),
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    devices = dr.async_entries_for_config_entry(dr.async_get(hass), entry.entry_id)
    assert len(devices) == 1
    assert devices[0].config_entry_id == entry.entry_id

    assert await hass.config_entries.async_unload(entry.entry_id)
