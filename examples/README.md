# App-style dashboard card

[`denon-avr-dashboard-card.yaml`](denon-avr-dashboard-card.yaml) is the complete
three-tab card used for the Denon-style **Input / Output / Signal** view. It is
self-contained: all channel-button styling is inline, so the card can be copied
between dashboards without a separate `button_card_templates` section.

## Required frontend cards

Install these five frontend cards from HACS before adding the example:

- [Button Card](https://github.com/custom-cards/button-card)
- [Mushroom](https://github.com/piitaya/lovelace-mushroom)
- [Stack In Card](https://github.com/custom-cards/stack-in-card)
- [Tabbed Card](https://github.com/kinghat/tabbed-card)
- [Card Mod](https://github.com/thomasloven/lovelace-card-mod)

Reload the browser after installing or updating frontend cards.

## Add the card

1. Open a Home Assistant dashboard and select **Edit dashboard**.
2. Select **Add card**, then **Manual**.
3. Copy the complete contents of
   [`denon-avr-dashboard-card.yaml`](denon-avr-dashboard-card.yaml) into the
   manual card editor.
4. Replace the example entity IDs with the entities created by your Denon AVR
   Diagnostics device.
5. Save the card.

Do not copy only one inner stack. The complete file begins with
`custom:tabbed-card` and contains all three tabs.

## Match the entity IDs

Home Assistant derives entity IDs from the device name, language and area, so
the exact IDs differ between installations. The example deliberately uses the
neutral prefix `denon_avr` and does not contain IDs from a real system.

Open **Settings → Devices & services → Denon AVR Diagnostics → your AVR**, then
open each entity to see its entity ID. Replace the examples in the YAML. The
card uses these sensor groups:

| Purpose | Example entity ID |
| --- | --- |
| Input channel summary | `sensor.denon_avr_input_channels` |
| Input format and mode | `sensor.denon_avr_audio_input_format`, `sensor.denon_avr_audio_input_mode` |
| Sampling rate | `sensor.denon_avr_sampling_rate` |
| Active output summary | `sensor.denon_avr_active_output_channels` |
| Configured speakers | `sensor.denon_avr_configured_speakers` |
| Sound and output format | `sensor.denon_avr_sound_mode`, `sensor.denon_avr_audio_output_format` |
| Power | `sensor.denon_avr_power` |
| Video input/output | `sensor.denon_avr_video_input_resolution`, `sensor.denon_avr_video_output_resolution` |
| HDR | `sensor.denon_avr_video_input_hdr`, `sensor.denon_avr_video_output_hdr` |
| HDMI signal | `sensor.denon_avr_hdmi_input_signal`, `sensor.denon_avr_hdmi_output_signal` |
| Color information | `sensor.denon_avr_video_input_color_space`, `sensor.denon_avr_video_input_color_depth` |
| Monitor/output | `sensor.denon_avr_video_output` |

The channel buttons follow these patterns:

- `binary_sensor.denon_avr_input_channel_<channel>`
- `binary_sensor.denon_avr_output_channel_<channel>`

For example, replace `binary_sensor.denon_avr_input_channel_fl` with the actual
**Input channel FL** entity from your AVR device. Repeat this for FL, FR, C,
LFE/SW, surround, back, wide and height channels. An entity that your model
does not create can be left in the card; it will remain dim/unavailable.

## Deutsche Kurzfassung

Installiere zuerst die fünf oben verlinkten Karten über **HACS → Frontend**.
Öffne danach dein Dashboard, wähle **Dashboard bearbeiten → Karte hinzufügen →
Manuell** und füge den kompletten Inhalt der YAML-Datei ein. Ersetze anschließend
die neutralen Beispiel-IDs durch die Entity-IDs deines AVR-Geräts unter
**Einstellungen → Geräte & Dienste**. Die Datei enthält bereits alle drei Reiter
**Eingang**, **Ausgang** und **Signal** sowie sämtliche Kanal-Styles und kann
deshalb als eine einzige Karte kopiert werden.
