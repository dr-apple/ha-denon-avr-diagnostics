"""Protocol parser and receiver client tests."""

from unittest.mock import AsyncMock

import pytest

from custom_components.denon_avr_diagnostics.api import (
    DETAIL_COMMANDS,
    DenonAvrClient,
    DenonAvrConnectionError,
    build_detail_request,
    channel_layout,
    normalize_host,
    parse_basic_response,
    parse_detail_response,
    parse_video_signal,
)

DETAIL_XML = b"""<?xml version="1.0"?>
<rx>
  <cmd><name>GetAudioInfo</name><list>
    <param name="inputmode">HDMI</param>
    <param name="output">Dolby Atmos</param>
    <param name="signal">Dolby TrueHD</param>
    <param name="sound">Dolby Atmos</param>
    <param name="fs">48 kHz</param>
  </list></cmd>
  <cmd><name>GetInputSignal</name><list>
    <param name="inputsiga1" control="2">FL</param>
    <param name="inputsigb1" control="2">FR</param>
    <param name="inputsigc1" control="2">C</param>
    <param name="inputsigb2" control="2">SW</param>
    <param name="inputsiga3" control="2">SL</param>
    <param name="inputsigb3" control="2">SR</param>
  </list></cmd>
  <cmd><name>GetActiveSpeaker</name><list>
    <param name="activespa1" control="2">FL</param>
    <param name="activespb1" control="2">FR</param>
    <param name="activespc1" control="1">C</param>
    <param name="activespd1" control="2">SW</param>
    <param name="activespa2" control="2">SL</param>
    <param name="activespb2" control="2">SR</param>
    <param name="activespc2" control="1">TML</param>
    <param name="activespd2" control="1">TMR</param>
  </list></cmd>
  <cmd><name>GetVideoInfo</name><list>
    <param name="videooutput">Monitor 1</param>
    <param name="hdmisigin">3840x2160p / 60 Hz YCbCr 4:2:2 10 bit HDR10</param>
    <param name="hdmisigout">3840x2160p / 60 Hz BT.2020 10 bit HDR10</param>
  </list></cmd>
</rx>"""

BASIC_XML = b"""<rx>
  <cmd><zone1>ON</zone1></cmd>
  <cmd><zone1>BD</zone1></cmd>
  <cmd><zone1><surround>DOLBY ATMOS</surround></zone1></cmd>
</rx>"""


def test_detail_parser() -> None:
    snapshot = parse_detail_response(DETAIL_XML)
    assert snapshot.values["audio_input_format"] == "Dolby TrueHD"
    assert snapshot.values["sampling_rate"] == 48000
    assert snapshot.values["input_channels"] == "5.1"
    assert snapshot.values["configured_speakers"] == "5.1.2"
    assert snapshot.values["active_output_channels"] == "4.1"
    assert snapshot.values["video_input_resolution"] == "3840×2160p"
    assert snapshot.values["video_input_frame_rate"] == 60.0
    assert snapshot.values["video_input_hdr"] == "HDR10"
    assert snapshot.values["video_input_color_depth"] == 10


def test_video_parser_short_resolution() -> None:
    parsed = parse_video_signal("1080p @ 23.976 Hz RGB 8 bit")
    assert parsed["resolution"] == "1080p"
    assert parsed["frame_rate"] == 23.976
    assert parsed["color_space"] == "RGB"


def test_video_signal_with_colon_frame_rate() -> None:
    # AVR-X1500H reports HDMI signals as "720p:50Hz".
    parsed = parse_video_signal("720p:50Hz")
    assert parsed["resolution"] == "720p"
    assert parsed["frame_rate"] == 50.0
    assert parse_video_signal("2160p:23.98Hz")["frame_rate"] == 23.98


def test_channel_layout() -> None:
    assert channel_layout(["FL", "FR", "C", "SL", "SR", "SW", "TML", "TMR"]) == "5.1.2"
    assert channel_layout(["FL", "FR", "LFE"]) == "2.1"


def test_input_parser_ignores_control_zero_channels() -> None:
    snapshot = parse_detail_response(
        b"""<rx><cmd><name>GetInputSignal</name><list>
        <param name="inputsiga1" control="2">FL</param>
        <param name="inputsigb1" control="2">FR</param>
        <param name="inputsigc1" control="2">LFE</param>
        <param name="inputsigc3" control="1">SR</param>
        <param name="inputsigc2" control="0">C</param>
        </list></cmd></rx>"""
    )
    assert snapshot.values["input_channels"] == "2.1"
    assert snapshot.attributes["input_channels"]["channels"] == ["FL", "FR", "LFE"]


def test_single_detail_request_contains_only_requested_command() -> None:
    request = build_detail_request((DETAIL_COMMANDS[1],))
    assert request.count(b"<cmd") == 1
    assert b"GetInputSignal" in request
    assert b"GetAudioInfo" not in request


def test_normalize_ipv6_host() -> None:
    assert normalize_host("[2001:db8::1]") == "2001:db8::1"


def test_basic_parser_uses_command_order() -> None:
    snapshot = parse_basic_response(BASIC_XML)
    assert snapshot.values == {
        "power": "ON",
        "source": "BD",
        "sound_mode": "DOLBY ATMOS",
    }


def test_missing_audio_and_video_parameters_are_not_marked_supported() -> None:
    snapshot = parse_detail_response(
        b"""<rx>
        <cmd><name>GetAudioInfo</name><list>
          <param name="signal">Dolby Digital</param>
        </list></cmd>
        <cmd><name>GetVideoInfo</name><list>
          <param name="hdmisigin">1920x1080p / 60 Hz</param>
        </list></cmd>
        </rx>"""
    )

    assert "audio_input_format" in snapshot.supported_fields
    assert "audio_output_format" not in snapshot.supported_fields
    assert "hdmi_input_signal" in snapshot.supported_fields
    assert "hdmi_output_signal" not in snapshot.supported_fields
    assert "video_input_resolution" in snapshot.supported_fields
    assert "video_input_hdr" not in snapshot.supported_fields


@pytest.mark.asyncio
async def test_disabled_telnet_fallback_is_not_used() -> None:
    client = DenonAvrClient(AsyncMock(), "avr.example")
    client.port = 80
    client._post = AsyncMock(side_effect=DenonAvrConnectionError("offline"))
    client._get = AsyncMock(side_effect=DenonAvrConnectionError("offline"))
    client._telnet_status = AsyncMock(return_value={"power": "ON"})

    with pytest.raises(DenonAvrConnectionError):
        await client.async_update(use_telnet=False)

    client._telnet_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_transport_only_reports_successful_telnet() -> None:
    client = DenonAvrClient(AsyncMock(), "avr.example")
    client.port = 80
    client._post = AsyncMock(
        side_effect=[
            b"<rx><cmd><zone1>ON</zone1></cmd></rx>",
            *(b"<rx/>" for _ in DETAIL_COMMANDS),
        ]
    )
    client._telnet_status = AsyncMock(side_effect=DenonAvrConnectionError("disabled"))

    snapshot = await client.async_update(use_telnet=True)

    assert snapshot.transport == "HTTP"


@pytest.mark.asyncio
async def test_telnet_only_transport_is_reported_accurately() -> None:
    client = DenonAvrClient(AsyncMock(), "avr.example")
    client.port = 80
    client._post = AsyncMock(side_effect=DenonAvrConnectionError("offline"))
    client._get = AsyncMock(side_effect=DenonAvrConnectionError("offline"))
    client._telnet_status = AsyncMock(return_value={"power": "ON"})

    snapshot = await client.async_update(use_telnet=True)

    assert snapshot.transport == "Telnet"
