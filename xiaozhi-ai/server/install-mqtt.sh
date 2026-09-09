#!/usr/bin/env bash
# Cai MQTT broker (mosquitto) tren VPS de bot dieu khien "may 1" (ESP32-S3 thu 2).
# Chay TREN VPS (khong trong container):
#   bash install-mqtt.sh <mqtt_user> <mqtt_pass>
# Sau do:
#   - Nap firmware may1-controller voi cung user/pass + host = IP VPS.
#   - Chay set-mqtt-key.sh de bao robot_bridge biet user/pass (xem file do).
set -uo pipefail
USER_="${1:-}"
PASS_="${2:-}"
if [ -z "$USER_" ] || [ -z "$PASS_" ]; then
  echo "Cach dung: bash install-mqtt.sh <mqtt_user> <mqtt_pass>"
  exit 1
fi

echo "==> Cai mosquitto ..."
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update -y
  sudo apt-get install -y mosquitto mosquitto-clients
else
  echo "  (khong phai he apt; hay cai mosquitto thu cong)"; exit 1
fi

echo "==> Tao user/mat khau ..."
sudo mosquitto_passwd -b -c /etc/mosquitto/passwd "$USER_" "$PASS_"

echo "==> Cau hinh listener 1883 (khong cho an danh) ..."
sudo tee /etc/mosquitto/conf.d/may1.conf >/dev/null <<CONF
listener 1883 0.0.0.0
allow_anonymous false
password_file /etc/mosquitto/passwd
CONF

echo "==> Mo port 1883 (neu co ufw) ..."
if command -v ufw >/dev/null 2>&1; then sudo ufw allow 1883/tcp || true; fi

echo "==> Khoi dong lai mosquitto ..."
sudo systemctl enable mosquitto >/dev/null 2>&1 || true
sudo systemctl restart mosquitto
sleep 1
echo "==> Test publish/subscribe cuc bo ..."
mosquitto_sub -h 127.0.0.1 -p 1883 -u "$USER_" -P "$PASS_" -t 'may1/test' -C 1 -W 3 &
sleep 1
mosquitto_pub -h 127.0.0.1 -p 1883 -u "$USER_" -P "$PASS_" -t 'may1/test' -m 'ok' || true
wait 2>/dev/null || true
echo "==> XONG. Broker chay tai <IP_VPS>:1883 (user=$USER_)."
echo "    LUU Y BAO MAT: port 1883 mo ra internet chi bao ve bang user/pass."
echo "    Dat mat khau manh. (Co the them TLS 8883 sau neu can.)"
echo "    Tiep theo: bash set-mqtt-key.sh $USER_ '<mat_khau>'"
