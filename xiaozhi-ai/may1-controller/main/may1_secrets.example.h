// [custom] EXAMPLE secrets header. The GitHub Actions build generates the real
// main/may1_secrets.h from workflow inputs (Wi-Fi + MQTT), so real credentials
// are never committed. For a LOCAL build, copy this to may1_secrets.h and edit.
#pragma once

#define WIFI_SSID      "your-wifi-name"
#define WIFI_PASSWORD  "your-wifi-password"

// MQTT broker on the VPS. Use the public IP so both the device and the server
// container can reach it. Port 1883 (plain) — see install-mqtt.sh.
#define MQTT_HOST      "42.112.26.67"
#define MQTT_PORT      1883
#define MQTT_USERNAME  "may1"
#define MQTT_PASSWORD  "changeme"
