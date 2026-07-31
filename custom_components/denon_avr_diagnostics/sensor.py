"""Sensors for Denon AVR Diagnostics."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.const import UnitOfFrequency
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DenonAvrDiagnosticsConfigEntry
from .api import ReceiverSnapshot
from .const import DOMAIN
from .coordinator import DenonAvrDiagnosticsCoordinator


@dataclass(frozen=True, kw_only=True)
class DenonSensorEntityDescription(SensorEntityDescription):
    """Describe a Denon diagnostic sensor."""

    value_fn: Callable[[ReceiverSnapshot], Any] | None = None
    supported_by: tuple[str, ...] = ()


SENSORS: tuple[DenonSensorEntityDescription, ...] = (
    DenonSensorEntityDescription(key="power", translation_key="power", icon="mdi:power"),
    DenonSensorEntityDescription(key="source", translation_key="source", icon="mdi:import"),
    DenonSensorEntityDescription(
        key="audio_input_mode",
        translation_key="audio_input_mode",
        icon="mdi:audio-input-stereo-minijack",
    ),
    DenonSensorEntityDescription(
        key="audio_input_format", translation_key="audio_input_format", icon="mdi:surround-sound"
    ),
    DenonSensorEntityDescription(
        key="audio_output_format",
        translation_key="audio_output_format",
        icon="mdi:speaker-multiple",
    ),
    DenonSensorEntityDescription(
        key="sound_mode", translation_key="sound_mode", icon="mdi:movie-open"
    ),
    DenonSensorEntityDescription(
        key="sampling_rate",
        translation_key="sampling_rate",
        icon="mdi:sine-wave",
        device_class=SensorDeviceClass.FREQUENCY,
        native_unit_of_measurement=UnitOfFrequency.HERTZ,
    ),
    DenonSensorEntityDescription(
        key="bit_rate",
        translation_key="bit_rate",
        icon="mdi:speedometer",
        native_unit_of_measurement="kbit/s",
    ),
    DenonSensorEntityDescription(
        key="input_channels", translation_key="input_channels", icon="mdi:surround-sound-5-1"
    ),
    DenonSensorEntityDescription(
        key="configured_speakers", translation_key="configured_speakers", icon="mdi:speaker"
    ),
    DenonSensorEntityDescription(
        key="active_output_channels",
        translation_key="active_output_channels",
        icon="mdi:speaker-wireless",
    ),
    DenonSensorEntityDescription(
        key="video_output", translation_key="video_output", icon="mdi:video-output"
    ),
    DenonSensorEntityDescription(
        key="hdmi_input_signal", translation_key="hdmi_input_signal", icon="mdi:hdmi-port"
    ),
    DenonSensorEntityDescription(
        key="video_input_resolution",
        translation_key="video_input_resolution",
        icon="mdi:aspect-ratio",
    ),
    DenonSensorEntityDescription(
        key="video_input_frame_rate",
        translation_key="video_input_frame_rate",
        icon="mdi:video-high-definition",
        native_unit_of_measurement="fps",
    ),
    DenonSensorEntityDescription(
        key="video_input_hdr", translation_key="video_input_hdr", icon="mdi:brightness-7"
    ),
    DenonSensorEntityDescription(
        key="video_input_color_space", translation_key="video_input_color_space", icon="mdi:palette"
    ),
    DenonSensorEntityDescription(
        key="video_input_color_depth",
        translation_key="video_input_color_depth",
        icon="mdi:gradient-horizontal",
        native_unit_of_measurement="bit",
    ),
    DenonSensorEntityDescription(
        key="hdmi_output_signal", translation_key="hdmi_output_signal", icon="mdi:hdmi-port"
    ),
    DenonSensorEntityDescription(
        key="video_output_resolution",
        translation_key="video_output_resolution",
        icon="mdi:aspect-ratio",
    ),
    DenonSensorEntityDescription(
        key="video_output_frame_rate",
        translation_key="video_output_frame_rate",
        icon="mdi:video-high-definition",
        native_unit_of_measurement="fps",
    ),
    DenonSensorEntityDescription(
        key="video_output_hdr", translation_key="video_output_hdr", icon="mdi:brightness-7"
    ),
    DenonSensorEntityDescription(
        key="video_output_color_space",
        translation_key="video_output_color_space",
        icon="mdi:palette",
    ),
    DenonSensorEntityDescription(
        key="video_output_color_depth",
        translation_key="video_output_color_depth",
        icon="mdi:gradient-horizontal",
        native_unit_of_measurement="bit",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DenonAvrDiagnosticsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Denon AVR diagnostic sensors."""
    async_add_entities(
        DenonAvrDiagnosticsSensor(entry.runtime_data, description) for description in SENSORS
    )


class DenonAvrDiagnosticsSensor(CoordinatorEntity[DenonAvrDiagnosticsCoordinator], SensorEntity):
    """A receiver diagnostic sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DenonAvrDiagnosticsCoordinator,
        description: DenonSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{coordinator.config_entry.unique_id}_{description.key}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return receiver device metadata."""
        info = self.coordinator.client.info
        host = self.coordinator.client.host
        url_host = f"[{host}]" if ":" in host else host
        return DeviceInfo(
            identifiers={(DOMAIN, self.coordinator.config_entry.unique_id or host)},
            name=info.friendly_name or f"{info.manufacturer} {info.model}",
            manufacturer=info.manufacturer,
            model=info.model,
            serial_number=info.serial_number,
            sw_version=info.firmware,
            configuration_url=f"http://{url_host}:{self.coordinator.client.port}",
        )

    @property
    def available(self) -> bool:
        """Return whether the entity and its source field are supported."""
        return (
            super().available
            and self.entity_description.key in self.coordinator.data.supported_fields
        )

    @property
    def native_value(self) -> Any:
        """Return the sensor state."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return self.coordinator.data.values.get(self.entity_description.key)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return detailed channel or signal attributes."""
        return self.coordinator.data.attributes.get(self.entity_description.key)
