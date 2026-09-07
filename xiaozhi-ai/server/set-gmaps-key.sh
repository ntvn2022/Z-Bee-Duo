#!/usr/bin/env bash
# Dat Google Maps API key cho tinh nang chi duong / giao thong (Directions API).
# Trong Google Cloud Console: bat "Directions API", tao API key, roi:
#   bash set-gmaps-key.sh <API_KEY>
set -uo pipefail
C="xiaozhi-esp32-server"
KEY="${1:-}"
if [ -z "$KEY" ]; then
  echo "Thieu key. Cach dung:  bash set-gmaps-key.sh <GOOGLE_MAPS_API_KEY>"
  exit 1
fi
echo "==> Ghi gmaps_key vao config (LLM.RobotBridge.gmaps_key) ..."
docker exec -i -e K="$KEY" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
d.setdefault("LLM", {}).setdefault("RobotBridge", {})["gmaps_key"] = os.environ["K"]
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  da luu gmaps_key")
PY
echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'tu Binh Duong den Ho Chi Minh di mat bao lau'."
