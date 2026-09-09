// [custom] Compile-time configuration for the "Máy 1" 3-output controller.
// Wi-Fi / MQTT SECRETS are NOT here — the build workflow generates
// may1_secrets.h from GitHub Actions inputs so nothing sensitive is committed.
#pragma once

// ---- Relay / output GPIOs (change to match your wiring) ----
// Three outputs. On an ESP32-S3 these are safe general GPIOs.
#define OUT1_GPIO   4
#define OUT2_GPIO   5
#define OUT3_GPIO   6

// Relay drive level: 1 = active-HIGH (GPIO HIGH turns the relay ON),
// 0 = active-LOW (common for cheap opto-isolated relay boards: LOW = ON).
#define RELAY_ACTIVE_HIGH  1

// ---- MQTT topics (must match the server side in robot_bridge.py) ----
#define TOPIC_CMD     "may1/cmd"       // server -> device (commands)
#define TOPIC_STATUS  "may1/status"    // device -> server (retained state)
#define TOPIC_ONLINE  "may1/online"    // device -> server (LWT: "1"/"0")

// How often (seconds) the device republishes its status.
#define STATUS_PERIOD_S   15

// Timezone (Vietnam, UTC+7) for the on/off schedule and elapsed timing.
#define DEVICE_TZ  "ICT-7"
