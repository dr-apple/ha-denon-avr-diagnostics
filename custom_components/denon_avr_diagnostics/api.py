"""Local HTTP and Telnet client for Denon/Marantz AV receivers."""

from __future__ import annotations

import asyncio
import ipaddress
import logging
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlsplit

from aiohttp import ClientError, ClientSession

from .const import (
    ACTIVE_SPEAKER,
    APPCOMMAND_0300_PATH,
    APPCOMMAND_PATH,
    AUDIO_INFO,
    CHANNEL_NAMES,
    DEFAULT_TIMEOUT,
    DEVICEINFO_PATH,
    HEIGHT_CHANNELS,
    HTTP_PORTS,
    INPUT_SIGNAL,
    STATUS_PATHS,
    VIDEO_INFO,
)

_LOGGER = logging.getLogger(__name__)

_RESOLUTION_RE = re.compile(
    r"(?P<width>\d{3,4})\s*[xX×]\s*(?P<height>\d{3,4})(?P<scan>[pi])?", re.I
)
_SHORT_RESOLUTION_RE = re.compile(
    r"\b(?P<height>480|576|720|1080|1440|2160|4320)(?P<scan>[pi])\b", re.I
)
_FRAME_RATE_RE = re.compile(r"(?:@|/|\s)(?P<rate>\d{2,3}(?:\.\d{1,3})?)\s*(?:Hz|fps)\b", re.I)
_DEPTH_RE = re.compile(r"\b(?P<depth>8|10|12|14|16)\s*(?:bit|bits|bpc)\b", re.I)
_SAMPLE_RATE_RE = re.compile(r"(?P<rate>\d+(?:\.\d+)?)\s*(?P<unit>k?Hz)\b", re.I)
_BIT_RATE_RE = re.compile(r"(?P<rate>\d+(?:\.\d+)?)\s*(?P<unit>[kKmM]?(?:bit|bps)(?:/s)?)\b")
_CHANNEL_TOKEN_RE = re.compile(r"\b[A-Z][A-Z0-9]{0,3}\b")

_HDR_FORMATS = ("Dolby Vision", "HDR10+", "HDR10", "HLG", "HDR")
_COLOR_SPACES = (
    "BT.2020",
    "BT2020",
    "BT.709",
    "BT709",
    "YCbCr 4:4:4",
    "YCbCr 4:2:2",
    "YCbCr 4:2:0",
    "RGB",
)


class DenonAvrError(Exception):
    """Base error for this integration."""


class DenonAvrConnectionError(DenonAvrError):
    """Raised when a receiver cannot be reached."""


class DenonAvrInvalidResponseError(DenonAvrError):
    """Raised when a receiver returns malformed data."""


@dataclass(slots=True)
class ReceiverInfo:
    """Receiver identity."""

    manufacturer: str = "Denon/Marantz"
    model: str = "AV Receiver"
    serial_number: str | None = None
    friendly_name: str | None = None
    firmware: str | None = None


@dataclass(slots=True)
class ReceiverSnapshot:
    """Normalized state returned to Home Assistant."""

    values: dict[str, Any] = field(default_factory=dict)
    attributes: dict[str, dict[str, Any]] = field(default_factory=dict)
    supported_fields: set[str] = field(default_factory=set)
    supported_commands: set[str] = field(default_factory=set)
    unavailable_commands: set[str] = field(default_factory=set)
    transport: str = "unknown"
    raw: dict[str, Any] = field(default_factory=dict)


DETAIL_COMMANDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    (AUDIO_INFO, ("inputmode", "output", "signal", "sound", "fs")),
    (INPUT_SIGNAL, ("inputsigall",)),
    (ACTIVE_SPEAKER, ("activespall",)),
    (VIDEO_INFO, ("videooutput", "hdmisigin", "hdmisigout")),
)

BASIC_COMMANDS = (
    "GetAllZonePowerStatus",
    "GetAllZoneSource",
    "GetSurroundModeStatus",
)


def normalize_host(value: str) -> str:
    """Validate and normalize a host or IP without accepting URL paths."""
    value = value.strip()
    if "://" in value:
        parsed = urlsplit(value)
        if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("A host or IP address is required")
        value = parsed.hostname or ""
    value = value.strip("[]").rstrip(".").lower()
    if not value or "/" in value or " " in value:
        raise ValueError("A host or IP address is required")
    if ":" in value:
        try:
            value = ipaddress.IPv6Address(value).compressed
        except ipaddress.AddressValueError as err:
            raise ValueError("A host or IP address is required") from err
    return value


def _clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = " ".join(value.split()).strip()
    if not cleaned or cleaned in {"-", "--", "---", "N/A", "Unknown"}:
        return None
    return cleaned


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _find_text(root: ET.Element, *names: str) -> str | None:
    wanted = {name.casefold() for name in names}
    for element in root.iter():
        if _local_name(element.tag).casefold() in wanted:
            text = _clean_text(element.text)
            if text:
                return text
    return None


def _xml_root(payload: bytes | str) -> ET.Element:
    try:
        return ET.fromstring(payload)
    except (ET.ParseError, ValueError, TypeError) as err:
        raise DenonAvrInvalidResponseError("Receiver returned invalid XML") from err


def build_detail_request(
    commands: Iterable[tuple[str, tuple[str, ...]]] = DETAIL_COMMANDS,
) -> bytes:
    """Build an AppCommand0300 query."""
    root = ET.Element("tx")
    for name, params in commands:
        cmd = ET.SubElement(root, "cmd", {"id": "3"})
        ET.SubElement(cmd, "name").text = name
        param_list = ET.SubElement(cmd, "list")
        for param in params:
            ET.SubElement(param_list, "param", {"name": param})
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def build_basic_request(commands: Iterable[str] = BASIC_COMMANDS) -> bytes:
    """Build an AppCommand query."""
    root = ET.Element("tx")
    for name in commands:
        ET.SubElement(root, "cmd", {"id": "1"}).text = name
    return ET.tostring(root, encoding="utf-8", xml_declaration=True)


def _command_name(command: ET.Element) -> str | None:
    name = command.find("./name")
    if name is not None:
        return _clean_text(name.text)
    return command.get("cmd_text")


def _param_values(command: ET.Element) -> list[dict[str, Any]]:
    values: list[dict[str, Any]] = []
    for param in command.iter():
        if _local_name(param.tag) != "param":
            continue
        item: dict[str, Any] = {
            "name": param.get("name", ""),
            "text": _clean_text(param.text),
        }
        control = param.get("control")
        if control is not None:
            try:
                item["control"] = int(control)
            except ValueError:
                item["control"] = control
        nested: dict[str, str] = {}
        for child in param.iter():
            if child is param:
                continue
            text = _clean_text(child.text)
            if text:
                nested[_local_name(child.tag).casefold()] = text
        if nested:
            item["nested"] = nested
        values.append(item)
    return values


def _channel_codes(items: Iterable[dict[str, Any]]) -> list[str]:
    result: list[str] = []
    for item in items:
        candidates = [item.get("text")]
        candidates.extend((item.get("nested") or {}).values())
        for candidate in candidates:
            if not candidate:
                continue
            for token in _CHANNEL_TOKEN_RE.findall(candidate.upper()):
                if token in CHANNEL_NAMES and token not in result:
                    result.append(token)
    return result


def channel_layout(channels: Iterable[str]) -> str | None:
    """Return a conventional x.y.z channel layout."""
    unique = list(dict.fromkeys(channel.upper() for channel in channels))
    if not unique:
        return None
    # Denon uses SW for active speakers and may use LFE for the input signal.
    subwoofers = sum(
        channel == "LFE" or channel == "SW" or channel.startswith("SW")
        for channel in unique
    )
    heights = sum(channel in HEIGHT_CHANNELS for channel in unique)
    # EXT is a flag/extension position in Denon's app, not a bed channel.
    bed = len(unique) - subwoofers - heights - ("EXT" in unique)
    layout = f"{bed}.{subwoofers}"
    return f"{layout}.{heights}" if heights else layout


def _parse_sample_rate(value: str | None) -> int | None:
    if not value:
        return None
    match = _SAMPLE_RATE_RE.search(value)
    if not match:
        return None
    rate = float(match.group("rate"))
    if match.group("unit").casefold().startswith("k"):
        rate *= 1000
    return int(rate)


def _parse_bit_rate(value: str | None) -> float | None:
    if not value:
        return None
    match = _BIT_RATE_RE.search(value)
    if not match:
        return None
    rate = float(match.group("rate"))
    unit = match.group("unit").casefold()
    if unit.startswith("m"):
        return rate * 1000
    if not unit.startswith("k"):
        return rate / 1000
    return rate


def parse_video_signal(value: str | None) -> dict[str, Any]:
    """Extract common HDMI signal details while retaining the raw value."""
    if not value:
        return {}
    result: dict[str, Any] = {"raw": value}
    resolution = _RESOLUTION_RE.search(value)
    if resolution:
        scan = (resolution.group("scan") or "").lower()
        result["resolution"] = f"{resolution.group('width')}×{resolution.group('height')}{scan}"
    else:
        short = _SHORT_RESOLUTION_RE.search(value)
        if short:
            result["resolution"] = f"{short.group('height')}{short.group('scan').lower()}"
    frame_rate = _FRAME_RATE_RE.search(value)
    if frame_rate:
        result["frame_rate"] = float(frame_rate.group("rate"))
    depth = _DEPTH_RE.search(value)
    if depth:
        result["color_depth"] = int(depth.group("depth"))
    lowered = value.casefold()
    for hdr_format in _HDR_FORMATS:
        if hdr_format.casefold() in lowered:
            result["hdr"] = hdr_format
            break
    for color_space in _COLOR_SPACES:
        if color_space.casefold() in lowered:
            result["color_space"] = color_space.replace("BT2020", "BT.2020").replace(
                "BT709", "BT.709"
            )
            break
    return result


def _put(snapshot: ReceiverSnapshot, key: str, value: Any, *, supported: bool = True) -> None:
    snapshot.values[key] = value
    if supported:
        snapshot.supported_fields.add(key)


def parse_detail_response(
    payload: bytes | str, snapshot: ReceiverSnapshot | None = None
) -> ReceiverSnapshot:
    """Parse detailed AppCommand0300 response."""
    snapshot = snapshot or ReceiverSnapshot()
    root = _xml_root(payload)
    if _local_name(root.tag).casefold() == "html":
        raise DenonAvrInvalidResponseError("Receiver returned HTML instead of XML")

    for command in root:
        if _local_name(command.tag) == "error":
            continue
        name = _command_name(command)
        if not name:
            continue
        params = _param_values(command)
        if not params and _clean_text(command.text) in {"ERROR", "NG"}:
            snapshot.unavailable_commands.add(name)
            continue
        snapshot.supported_commands.add(name)
        by_name = {item["name"].casefold(): item for item in params if item["name"]}

        if name == AUDIO_INFO:
            mapping = {
                "inputmode": "audio_input_mode",
                "output": "audio_output_format",
                "signal": "audio_input_format",
                "sound": "sound_mode",
                "fs": "sampling_rate",
            }
            for param, key in mapping.items():
                raw = (by_name.get(param) or {}).get("text")
                _put(snapshot, key, _parse_sample_rate(raw) if key == "sampling_rate" else raw)
            all_audio_text = " ".join(item["text"] or "" for item in params)
            _put(
                snapshot,
                "bit_rate",
                _parse_bit_rate(all_audio_text),
                supported="bit" in all_audio_text.casefold(),
            )

        elif name == INPUT_SIGNAL:
            channels = _channel_codes(
                item
                for item in params
                # AppCommand0300 uses control=2 for a channel that is actually
                # present in the current input signal. control=1 only marks a
                # position the receiver can display in its channel matrix.
                if item.get("control") in (2, "2")
            )
            _put(snapshot, "input_channels", channel_layout(channels))
            snapshot.attributes["input_channels"] = {
                "channels": channels,
                "channel_names": [CHANNEL_NAMES.get(channel, channel) for channel in channels],
            }

        elif name == ACTIVE_SPEAKER:
            configured = _channel_codes(
                item for item in params if item.get("control") in (1, 2, "1", "2")
            )
            active = _channel_codes(item for item in params if item.get("control") in (2, "2"))
            _put(snapshot, "configured_speakers", channel_layout(configured))
            _put(snapshot, "active_output_channels", channel_layout(active))
            snapshot.attributes["configured_speakers"] = {
                "channels": configured,
                "channel_names": [CHANNEL_NAMES.get(channel, channel) for channel in configured],
            }
            snapshot.attributes["active_output_channels"] = {
                "channels": active,
                "channel_names": [CHANNEL_NAMES.get(channel, channel) for channel in active],
            }

        elif name == VIDEO_INFO:
            for param, key in (
                ("videooutput", "video_output"),
                ("hdmisigin", "hdmi_input_signal"),
                ("hdmisigout", "hdmi_output_signal"),
            ):
                item = by_name.get(param) or {}
                raw = item.get("text")
                nested = item.get("nested") or {}
                if nested:
                    raw = " · ".join(dict.fromkeys(nested.values()))
                _put(snapshot, key, raw)
                snapshot.attributes[key] = nested

            for direction, source_key in (
                ("input", "hdmi_input_signal"),
                ("output", "hdmi_output_signal"),
            ):
                details = parse_video_signal(snapshot.values.get(source_key))
                for field in ("resolution", "frame_rate", "hdr", "color_space", "color_depth"):
                    _put(snapshot, f"video_{direction}_{field}", details.get(field))

    snapshot.raw["appcommand0300"] = {
        "commands": sorted(snapshot.supported_commands),
        "unavailable_commands": sorted(snapshot.unavailable_commands),
    }
    return snapshot


def parse_basic_response(
    payload: bytes | str, snapshot: ReceiverSnapshot | None = None
) -> ReceiverSnapshot:
    """Parse common AppCommand response with tolerant tag matching."""
    snapshot = snapshot or ReceiverSnapshot()
    root = _xml_root(payload)
    commands = [child for child in root if _local_name(child.tag) == "cmd"]
    power = _find_text(commands[0], "zone1", "power", "Power") if commands else None
    source = (
        _find_text(commands[1], "zone1", "source", "InputFuncSelect", "input")
        if len(commands) > 1
        else None
    )
    surround = (
        _find_text(commands[2], "surround", "zone1", "surroundmode", "selectSurround")
        if len(commands) > 2
        else None
    )
    power = power or _find_text(root, "Power")
    source = source or _find_text(root, "source", "InputFuncSelect", "input")
    surround = surround or _find_text(root, "surround", "surroundmode", "selectSurround")
    if power:
        _put(snapshot, "power", power)
    if source:
        _put(snapshot, "source", source)
    if surround:
        _put(snapshot, "sound_mode", surround)
    return snapshot


def parse_legacy_status(
    payload: bytes | str, snapshot: ReceiverSnapshot | None = None
) -> ReceiverSnapshot:
    """Parse legacy main-zone XML as a fallback."""
    snapshot = snapshot or ReceiverSnapshot()
    root = _xml_root(payload)
    for key, names in {
        "power": ("Power", "ZonePower"),
        "source": ("InputFuncSelect", "InputFuncName"),
        "sound_mode": ("selectSurround", "SurroundMode"),
    }.items():
        value = _find_text(root, *names)
        if value:
            _put(snapshot, key, value)
    return snapshot


def parse_device_info(payload: bytes | str) -> ReceiverInfo:
    """Parse Deviceinfo.xml."""
    root = _xml_root(payload)
    manufacturer = _find_text(root, "Manufacturer", "manufacturer") or "Denon/Marantz"
    model = _find_text(root, "ModelName", "modelName", "Model") or "AV Receiver"
    return ReceiverInfo(
        manufacturer=manufacturer,
        model=model,
        serial_number=_find_text(root, "SerialNumber", "serialNumber"),
        friendly_name=_find_text(root, "FriendlyName", "friendlyName"),
        firmware=_find_text(root, "FirmwareVersion", "version", "CommApiVers"),
    )


class DenonAvrClient:
    """Asynchronous receiver client using Home Assistant's shared session."""

    def __init__(
        self, session: ClientSession, host: str, *, timeout: int = DEFAULT_TIMEOUT
    ) -> None:
        self.session = session
        self.host = normalize_host(host)
        self.timeout = timeout
        self.port: int | None = None
        self.info = ReceiverInfo()

    def _url(self, path: str, port: int | None = None) -> str:
        selected_port = port if port is not None else self.port
        if selected_port is None:
            raise DenonAvrConnectionError("Receiver HTTP port has not been detected")
        url_host = f"[{self.host}]" if ":" in self.host else self.host
        return f"http://{url_host}:{selected_port}{path}"

    async def _get(self, path: str, *, port: int | None = None) -> bytes:
        try:
            async with asyncio.timeout(self.timeout):
                response = await self.session.get(self._url(path, port))
                response.raise_for_status()
                return await response.read()
        except (TimeoutError, ClientError, OSError) as err:
            raise DenonAvrConnectionError(str(err)) from err

    async def _post(self, path: str, body: bytes, *, port: int | None = None) -> bytes:
        try:
            async with asyncio.timeout(self.timeout):
                response = await self.session.post(
                    self._url(path, port),
                    data=body,
                    headers={"Content-Type": "text/xml; charset=utf-8"},
                )
                response.raise_for_status()
                return await response.read()
        except (TimeoutError, ClientError, OSError) as err:
            raise DenonAvrConnectionError(str(err)) from err

    async def async_probe(self) -> ReceiverInfo:
        """Detect the HTTP port and read receiver identity."""
        errors: list[str] = []
        probe = build_basic_request(("GetAllZonePowerStatus",))
        for port in HTTP_PORTS:
            self.port = port
            try:
                payload = await self._post(APPCOMMAND_PATH, probe)
                root = _xml_root(payload)
                if _local_name(root.tag).casefold() != "rx":
                    raise DenonAvrInvalidResponseError("Not a Denon AppCommand response")
                break
            except DenonAvrError as err:
                errors.append(f"{port}: {err}")
                try:
                    payload = await self._get(DEVICEINFO_PATH)
                    self.info = parse_device_info(payload)
                    break
                except DenonAvrError as device_err:
                    errors.append(f"{port} device info: {device_err}")
        else:
            self.port = None
            raise DenonAvrConnectionError("; ".join(errors))

        try:
            self.info = parse_device_info(await self._get(DEVICEINFO_PATH))
        except DenonAvrError:
            _LOGGER.debug("Deviceinfo.xml is not available on %s", self.host)
        return self.info

    async def async_update(self, *, use_telnet: bool = False) -> ReceiverSnapshot:
        """Fetch all supported status endpoints."""
        if self.port is None:
            await self.async_probe()

        snapshot = ReceiverSnapshot()
        successes = 0
        errors: list[str] = []

        # Older receivers such as the AVR-X1500H do not reliably return every
        # command when multiple AppCommand0300 queries are bundled in one POST.
        # They are also prone to dropping responses when both AppCommand
        # endpoints are queried concurrently. Keep all receiver traffic
        # sequential and request each detailed command on its own.
        try:
            parse_basic_response(
                await self._post(APPCOMMAND_PATH, build_basic_request()), snapshot
            )
            successes += 1
        except DenonAvrError as err:
            errors.append(f"AppCommand: {err}")

        for command in DETAIL_COMMANDS:
            name = command[0]
            try:
                parse_detail_response(
                    await self._post(
                        APPCOMMAND_0300_PATH,
                        build_detail_request((command,)),
                    ),
                    snapshot,
                )
                if name in snapshot.supported_commands:
                    successes += 1
                else:
                    snapshot.unavailable_commands.add(name)
                    errors.append(f"AppCommand0300 {name}: command not returned")
            except DenonAvrError as err:
                errors.append(f"AppCommand0300 {name}: {err}")
                snapshot.unavailable_commands.add(name)

        if not {"power", "source", "sound_mode"} & snapshot.supported_fields:
            for path in STATUS_PATHS:
                try:
                    parse_legacy_status(await self._get(path), snapshot)
                    successes += 1
                    break
                except DenonAvrError as err:
                    errors.append(f"{path}: {err}")

        if use_telnet or successes == 0:
            try:
                telnet = await self._telnet_status()
                for key, value in telnet.items():
                    _put(snapshot, key, value)
                successes += 1
            except DenonAvrError as err:
                errors.append(f"Telnet: {err}")

        if successes == 0:
            raise DenonAvrConnectionError("; ".join(errors))
        snapshot.transport = "HTTP + Telnet" if use_telnet else "HTTP"
        snapshot.raw["errors"] = errors
        return snapshot

    async def _telnet_status(self) -> dict[str, str]:
        """Read basic status through the documented Denon control port."""
        writer: asyncio.StreamWriter | None = None
        try:
            async with asyncio.timeout(self.timeout):
                reader, writer = await asyncio.open_connection(self.host, 23)
                writer.write(b"PW?\rSI?\rMS?\r")
                await writer.drain()
                lines: list[str] = []
                while len(lines) < 8:
                    try:
                        line = await asyncio.wait_for(reader.readuntil(b"\r"), timeout=0.5)
                    except (TimeoutError, asyncio.IncompleteReadError, asyncio.LimitOverrunError):
                        break
                    lines.append(line.decode(errors="replace").strip())
        except (TimeoutError, OSError) as err:
            raise DenonAvrConnectionError(str(err)) from err
        finally:
            if writer is not None:
                writer.close()
                await writer.wait_closed()

        result: dict[str, str] = {}
        for line in lines:
            if line.startswith("PW"):
                result["power"] = line[2:]
            elif line.startswith("SI"):
                result["source"] = line[2:]
            elif line.startswith("MS"):
                result["sound_mode"] = line[2:]
        if not result:
            raise DenonAvrInvalidResponseError("No Telnet status response")
        return result
