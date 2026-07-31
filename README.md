# Denon AVR Diagnostics for Home Assistant

A HACS-compatible custom integration that exposes the audio and video signal
diagnostics available in the Denon/Marantz AVR app as native Home Assistant
sensors.

It is designed primarily around the **Denon AVR-X1500H** and the 2016-generation
AppCommand interface, with feature detection and fallbacks for related modern
Denon and Marantz network receivers.

> This integration complements Home Assistant's built-in Denon AVR media player.
> It uses the separate domain `denon_avr_diagnostics` and does not override the
> built-in integration.

## What it exposes

Depending on what the receiver and current source report:

- Audio input mode, input codec/format, audio output destination and active sound mode
- Sampling rate and bitrate when the receiver provides them
- Input channel layout plus separate on/off entities for FL, FR, C, LFE,
  surround, back, wide and height channels
- Configured speakers and currently active output channels, also as separate
  per-channel on/off entities
- Video/HDMI input and output signal descriptions
- Input/output resolution and frame rate
- HDR10, HDR10+, Dolby Vision, HLG and generic HDR markers
- Color space and color depth
- Video output/monitor information
- Receiver model, manufacturer, firmware and serial number as device metadata
- Downloadable Home Assistant diagnostics with host and serial number redacted

Channel summary sensors use a familiar state such as `5.1` or `5.1.2`. In
addition, the integration creates binary sensors such as **Input channel FL**,
**Input channel C**, **Active output channel FL** and **Active output channel
LFE/SW**. Their on/off state lets a normal Home Assistant grid highlight every
channel independently, just like the channel matrix in the Denon app.

The Denon app's stable input positions (FHL, LFE, EXT, FHR, FWL, FL, C, FR,
FWR, SL, SR, SBL, SB and SBR) are always created. Any additional height or
Dolby speaker positions reported by the receiver are added during setup.

Unsupported values are marked unavailable. The integration does not guess a
codec, channel or video property that the AVR did not return.

## Protocol and compatibility

The client tries the receiver's local HTTP interfaces on ports 8080 and 80. It
uses:

- `/goform/AppCommand0300.xml` for `GetAudioInfo`, `GetInputSignal`,
  `GetActiveSpeaker` and `GetVideoInfo`
- `/goform/AppCommand.xml` for common zone, source and surround state
- Legacy main-zone status XML as a fallback
- Optional Denon control-protocol Telnet queries (`PW?`, `SI?`, `MS?`) for basic
  state fallback

Denon firmware varies substantially by model and region. Amp assignment is not a
stable field in the X1500H signal-status endpoint; configured speaker channels
are exposed whenever `GetActiveSpeaker` provides them. Bitrate is likewise only
available on models/firmware that include it in their audio response.

The optional Telnet fallback is disabled by default because some receivers allow
only one Telnet client at a time.

## Installation with HACS

1. Open HACS in Home Assistant.
2. Select **Integrations**.
3. Open the three-dot menu and select **Custom repositories**.
4. Add:

   `https://github.com/dr-apple/ha-denon-avr-diagnostics`

5. Select the category **Integration**, then add the repository.
6. Install **Denon AVR Diagnostics**.
7. Restart Home Assistant.
8. Go to **Settings → Devices & services → Add integration**.
9. Search for **Denon AVR Diagnostics** and enter the receiver's local IP address
   or host name.

Assign the AVR a DHCP reservation so its address remains stable.

## Options

Open the integration and select **Configure** to change:

- Update interval: 3–60 seconds (default: 5 seconds)
- Telnet fallback: off by default

## Lovelace example

Entity IDs include the Home Assistant device name. Replace the example IDs below
with the IDs created on your system.

### Denon-style input channel map

Binary-sensor button cards automatically use the active color while a channel
is present. The fixed grid below follows the position order shown in the Denon
AVR Remote app.

```yaml
type: grid
title: AVR input channels
columns: 4
square: false
cards:
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fhl
    name: FHL
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_lfe
    name: LFE
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_ext
    name: EXT
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fhr
    name: FHR
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fwl
    name: FWL
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fl
    name: FL
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_c
    name: C
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fr
    name: FR
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_fwr
    name: FWR
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_sl
    name: SL
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_sr
    name: SR
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_sbl
    name: SBL
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_sb
    name: SB
    show_state: false
  - type: button
    entity: binary_sensor.denon_avr_input_channel_sbr
    name: SBR
    show_state: false
```

Duplicate the grid and replace `input_channel` with `output_channel` to show
which loudspeakers the AVR is currently driving. Use `configured_channel` for
the installed/configured speaker map.

### Signal details

```yaml
type: sections
max_columns: 3
sections:
  - type: grid
    cards:
      - type: heading
        heading: Audio input
        icon: mdi:audio-input-stereo-minijack
      - type: tile
        entity: sensor.denon_avr_audio_input_format
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_sampling_rate
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_input_channels
        grid_options:
          columns: 12
          rows: auto

  - type: grid
    cards:
      - type: heading
        heading: Processing and output
        icon: mdi:speaker-multiple
      - type: tile
        entity: sensor.denon_avr_sound_mode
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_audio_output_format
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_active_output_channels
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_configured_speakers
        grid_options:
          columns: 6
          rows: auto

  - type: grid
    cards:
      - type: heading
        heading: HDMI video
        icon: mdi:hdmi-port
      - type: tile
        entity: sensor.denon_avr_video_input_resolution
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_video_input_hdr
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_video_output_resolution
        grid_options:
          columns: 6
          rows: auto
      - type: tile
        entity: sensor.denon_avr_video_output_hdr
        grid_options:
          columns: 6
          rows: auto
      - type: entities
        entities:
          - sensor.denon_avr_hdmi_input_signal
          - sensor.denon_avr_hdmi_output_signal
          - sensor.denon_avr_video_input_color_space
          - sensor.denon_avr_video_input_color_depth
        grid_options:
          columns: 12
          rows: auto
```

## Troubleshooting

- Ensure **Network Control** or **IP Control** is enabled on the AVR, including
  in standby if standby access is required.
- Confirm the receiver and Home Assistant are on networks that can reach each
  other without client isolation.
- If a specific sensor is unavailable, the current receiver firmware or source
  may not expose that property.
- Use **Settings → Devices & services → Denon AVR Diagnostics → Download
  diagnostics** when reporting an issue.
- Disable Telnet fallback if another application already owns the receiver's
  Telnet connection.

## Technical references

- [Denon AVR-X1500H manual: sound modes and channel output](https://manuals.denon.com/AVRX1500H/NA/EN/GFNFSYrvfbzbgs.php)
- [Denon AVR control protocol (official PDF)](https://downloads.denon.com/documentmaster/us/avr-2308ciserialprotocol_ver540.pdf)
- [Established `denonavr` Python library and captured X1500H AppCommand traffic](https://github.com/ol-iver/denonavr)
- [Home Assistant integration file structure](https://developers.home-assistant.io/docs/creating_integration_file_structure/)
- [Home Assistant diagnostics guidance](https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/diagnostics/)

The AppCommand endpoints are local, unauthenticated interfaces used by Denon's
own AVR remote apps but are not covered by a complete public vendor specification.
This project therefore treats every detailed command as optional.

## Development

Validate the standalone protocol parser:

```bash
python -m pytest -q
```

Validate Python and JSON without installing Home Assistant:

```bash
python -m compileall -q custom_components tests
python -m json.tool custom_components/denon_avr_diagnostics/manifest.json >/dev/null
python -m json.tool custom_components/denon_avr_diagnostics/translations/en.json >/dev/null
```

## License

MIT
