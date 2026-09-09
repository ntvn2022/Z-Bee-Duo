#!/usr/bin/env bash
# Bao robot_bridge biet thong tin MQTT broker de dieu khien "may 1".
# Chay TREN VPS:
#   bash set-mqtt-key.sh <mqtt_user> <mqtt_pass> [host] [port]
# Mac dinh host = 42.112.26.67 (IP VPS), port = 1883. Dung IP cong khai de ca
# container server lan ESP32 thu 2 deu ket noi duoc.
set -uo pipefail
C="xiaozhi-esp32-server"
USER_="${1:-}"
PASS_="${2:-}"
HOST_="${3:-42.112.26.67}"
PORT_="${4:-1883}"
if [ -z "$USER_" ] || [ -z "$PASS_" ]; then
  echo "Cach dung: bash set-mqtt-key.sh <mqtt_user> <mqtt_pass> [host] [port]"
  exit 1
fi
echo "==> Cai paho-mqtt trong container ..."
docker exec "$C" pip install -q -U paho-mqtt >/dev/null 2>&1 || \
  docker exec "$C" pip3 install -q -U paho-mqtt >/dev/null 2>&1 || true

echo "==> Ghi cau hinh MQTT vao .config.yaml (LLM.RobotBridge.mqtt_*) ..."
docker exec -i -e U="$USER_" -e P="$PASS_" -e H="$HOST_" -e PT="$PORT_" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
rb = d.setdefault("LLM", {}).setdefault("RobotBridge", {})
rb["mqtt_host"] = os.environ["H"]
rb["mqtt_port"] = int(os.environ["PT"])
rb["mqtt_user"] = os.environ["U"]
rb["mqtt_pass"] = os.environ["P"]
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  mqtt_host=%s port=%s user=%s" % (os.environ["H"], os.environ["PT"], os.environ["U"]))
PY
echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lệnh máy 1' -> 'bật đầu ra 1' -> 'kết thúc máy 1'."
