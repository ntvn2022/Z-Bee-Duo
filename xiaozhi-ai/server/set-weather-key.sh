#!/usr/bin/env bash
# Dat OpenWeatherMap API key (thoi tiet chinh xac hon).
# Lay key mien phi tai: https://openweathermap.org/  (Sign up -> API keys)
# Chay:  bash set-weather-key.sh <API_KEY>
set -uo pipefail
C="xiaozhi-esp32-server"
KEY="${1:-}"
if [ -z "$KEY" ]; then
  echo "Thieu key. Cach dung:  bash set-weather-key.sh <OPENWEATHERMAP_API_KEY>"
  exit 1
fi

echo "==> Ghi owm_key vao config (LLM.RobotBridge.owm_key) ..."
docker exec -i -e OWM="$KEY" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
d.setdefault("LLM", {}).setdefault("RobotBridge", {})["owm_key"] = os.environ["OWM"]
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  da luu owm_key")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'thoi tiet Bac Ninh the nao'."
echo "    (Neu key vua tao, OpenWeatherMap can ~10-60 phut de kich hoat key.)"
