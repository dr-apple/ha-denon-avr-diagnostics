"""Parser tests that do not require Home Assistant."""

from custom_components.denon_avr_diagnostics.api import (
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


def test_channel_layout() -> None:
    assert channel_layout(["FL", "FR", "C", "SL", "SR", "SW", "TML", "TMR"]) == "5.1.2"


def test_normalize_ipv6_host() -> None:
    assert normalize_host("[2001:db8::1]") == "2001:db8::1"


def test_basic_parser_uses_command_order() -> None:
    snapshot = parse_basic_response(BASIC_XML)
    assert snapshot.values == {
        "power": "ON",
        "source": "BD",
        "sound_mode": "DOLBY ATMOS",
    }
