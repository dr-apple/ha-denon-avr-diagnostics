"""Constants for Denon AVR Diagnostics."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "denon_avr_diagnostics"
DEFAULT_NAME = "Denon AVR Diagnostics"
DEFAULT_SCAN_INTERVAL = 5
MIN_SCAN_INTERVAL = 3
MAX_SCAN_INTERVAL = 60
DEFAULT_TIMEOUT = 4
HTTP_PORTS = (8080, 80)

CONF_SCAN_INTERVAL = "scan_interval"
CONF_USE_TELNET = "use_telnet"

UPDATE_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

APPCOMMAND_PATH = "/goform/AppCommand.xml"
APPCOMMAND_0300_PATH = "/goform/AppCommand0300.xml"
DEVICEINFO_PATH = "/goform/Deviceinfo.xml"
STATUS_PATHS = (
    "/goform/formMainZone_MainZoneXmlStatus.xml",
    "/goform/formMainZone_MainZoneXml.xml",
)

AUDIO_INFO = "GetAudioInfo"
INPUT_SIGNAL = "GetInputSignal"
ACTIVE_SPEAKER = "GetActiveSpeaker"
VIDEO_INFO = "GetVideoInfo"

CHANNEL_NAMES: dict[str, str] = {
    "FL": "Front Left",
    "FR": "Front Right",
    "C": "Center",
    "SW": "Subwoofer",
    "SW1": "Subwoofer 1",
    "SW2": "Subwoofer 2",
    "SL": "Surround Left",
    "SR": "Surround Right",
    "SBL": "Surround Back Left",
    "SBR": "Surround Back Right",
    "SB": "Surround Back",
    "FHL": "Front Height Left",
    "FHR": "Front Height Right",
    "TFL": "Top Front Left",
    "TFR": "Top Front Right",
    "TML": "Top Middle Left",
    "TMR": "Top Middle Right",
    "TRL": "Top Rear Left",
    "TRR": "Top Rear Right",
    "RHL": "Rear Height Left",
    "RHR": "Rear Height Right",
    "FDL": "Front Dolby Left",
    "FDR": "Front Dolby Right",
    "SDL": "Surround Dolby Left",
    "SDR": "Surround Dolby Right",
    "BDL": "Back Dolby Left",
    "BDR": "Back Dolby Right",
    "FWL": "Front Wide Left",
    "FWR": "Front Wide Right",
    "CH": "Center Height",
    "TS": "Top Surround",
}

HEIGHT_CHANNELS = {
    "FHL",
    "FHR",
    "TFL",
    "TFR",
    "TML",
    "TMR",
    "TRL",
    "TRR",
    "RHL",
    "RHR",
    "FDL",
    "FDR",
    "SDL",
    "SDR",
    "BDL",
    "BDR",
    "CH",
    "TS",
}
