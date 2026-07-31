"""Per-channel binary sensors for Denon AVR Diagnostics."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import DenonAvrDiagnosticsConfigEntry
from .const import (
    ACTIVE_SPEAKER,
    APP_INPUT_CHANNEL_MAP,
    CHANNEL_NAMES,
    CHANNEL_ORDER,
    DOMAIN,
    INPUT_SIGNAL,
)
from .coordinator import DenonAvrDiagnosticsCoordinator


@dataclass(frozen=True, kw_only=True)
class DenonChannelEntityDescription(BinarySensorEntityDescription):
    """Describe one input, configured or active output channel."""

    attribute_key: str
    command: str
    channel: str


def _channel_descriptions(
    channels: tuple[str, ...],
) -> tuple[DenonChannelEntityDescription, ...]:
    descriptions: list[DenonChannelEntityDescription] = []
    for channel in channels:
        for prefix, translation_key, attribute_key, command, icon in (
            (
                "input",
                "input_channel",
                "input_channels",
                INPUT_SIGNAL,
                "mdi:audio-input-stereo-minijack",
            ),
            (
                "configured",
                "configured_channel",
                "configured_speakers",
                ACTIVE_SPEAKER,
                "mdi:speaker",
            ),
            (
                "output",
                "output_channel",
                "active_output_channels",
                ACTIVE_SPEAKER,
                "mdi:speaker-wireless",
            ),
        ):
            descriptions.append(
                DenonChannelEntityDescription(
                    key=f"{prefix}_channel_{channel.lower()}",
                    translation_key=translation_key,
                    icon=icon,
                    attribute_key=attribute_key,
                    command=command,
                    channel=channel,
                )
            )
    return tuple(descriptions)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: DenonAvrDiagnosticsConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up individual channel indicators."""
    reported_channels = set(APP_INPUT_CHANNEL_MAP)
    for attribute_key in (
        "input_channels",
        "configured_speakers",
        "active_output_channels",
    ):
        reported_channels.update(
            entry.runtime_data.data.attributes.get(attribute_key, {}).get(
                "channels", []
            )
        )
    channels = tuple(
        channel for channel in CHANNEL_ORDER if channel in reported_channels
    )
    async_add_entities(
        DenonAvrChannelBinarySensor(entry.runtime_data, description)
        for description in _channel_descriptions(channels)
    )


class DenonAvrChannelBinarySensor(
    CoordinatorEntity[DenonAvrDiagnosticsCoordinator], BinarySensorEntity
):
    """Represent whether one channel is present in the current signal."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: DenonAvrDiagnosticsCoordinator,
        description: DenonChannelEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.unique_id}_{description.key}"
        )
        self._attr_translation_placeholders = {"channel": description.channel}

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
        """Return whether the AVR supports this channel group."""
        return (
            super().available
            and self.entity_description.command
            in self.coordinator.data.supported_commands
        )

    @property
    def is_on(self) -> bool:
        """Return whether this exact channel is present or active."""
        attributes = self.coordinator.data.attributes.get(
            self.entity_description.attribute_key, {}
        )
        return self.entity_description.channel in attributes.get("channels", [])

    @property
    def extra_state_attributes(self) -> dict[str, str | None]:
        """Expose the code, friendly position and current aggregate layout."""
        return {
            "channel_code": self.entity_description.channel,
            "channel_name": CHANNEL_NAMES[self.entity_description.channel],
            "channel_group": self.entity_description.attribute_key,
            "layout": self.coordinator.data.values.get(
                self.entity_description.attribute_key
            ),
        }
