"""Tests for the Home Assistant config flow."""

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from custom_components.denon_avr_diagnostics.api import ReceiverInfo
from custom_components.denon_avr_diagnostics.const import DOMAIN


async def test_user_flow_on_home_assistant_2026_8(
    hass: HomeAssistant, enable_custom_integrations: None
) -> None:
    with patch(
        "custom_components.denon_avr_diagnostics.api.DenonAvrClient.async_probe",
        return_value=ReceiverInfo(
            manufacturer="Denon",
            model="AVR-X1500H",
            friendly_name="Living Room AVR",
        ),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_USER},
            data={CONF_HOST: "AVR.EXAMPLE."},
        )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Living Room AVR"
    assert result["data"] == {CONF_HOST: "avr.example"}
    assert result["result"].unique_id == "avr.example"
