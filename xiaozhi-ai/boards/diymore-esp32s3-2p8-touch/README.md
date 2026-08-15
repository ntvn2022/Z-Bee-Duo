# DIYMORE ESP32-S3 2.8" Capacitive Touch LCD — xiaozhi board config

Custom board definition for the **DIYMORE ESP32-S3 2.8" LCD** module used with the
[78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32) AI chatbot firmware.

## Hardware

| Part      | Detail                                             |
|-----------|----------------------------------------------------|
| MCU       | ESP32-S3 (dual-core, up to 240 MHz)                |
| Display   | 2.8" IPS TFT, 240×320, driver **ILI9341V**, 4-line SPI |
| Touch     | **FT6336G** capacitive, I2C, address `0x38`        |
| Audio     | **ES8311** codec — built-in mic + speaker port     |
| Storage   | MicroSD slot                                        |
| Other     | RGB LED, battery port, USB Type-C, RESET/BOOT       |

This board shares the reference design of the **Freenove / LCDwiki ES3C28P**
"Cheap Yellow Display S3" family, so the pin map is taken from that known-good
configuration. If audio or the screen misbehaves, verify the pins in `config.h`
against your unit's silkscreen/schematic.

## Files

- `config.h` — pin map and display parameters
- `config.json` — build target metadata (`esp32s3`)
- `diymore-esp32s3-2p8-touch.cc` — board class (display, FT6336 touch, ES8311 audio)

## Build

From the repo root, after registering this board (see `../../setup.sh`):

```bash
idf.py set-target esp32s3
idf.py menuconfig      # Xiaozhi Assistant → Board Type → DIYMORE ESP32-S3 2.8"
idf.py build
idf.py -p <PORT> flash monitor
```
