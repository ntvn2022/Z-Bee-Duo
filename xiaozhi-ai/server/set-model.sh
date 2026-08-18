#!/usr/bin/env bash
# Doi model LLM cho bot (tra loi chat + l, robot). Vi du:
#   bash set-model.sh gemini-3.7-flash     # Flash moi nhat: nhanh, re, thong minh (khuyen dung)
#   bash set-model.sh gemini-3.1-pro       # Manh nhat nhung dat + cham
#   bash set-model.sh gemini-2.5-flash-lite
set -uo pipefail
C="xiaozhi-esp32-server"
M="${1:-}"
if [ -z "$M" ]; then
  echo "Thieu ten model. Vi du: bash set-model.sh gemini-3.7-flash"
  exit 1
fi
echo "==> Dat LLM.RobotBridge.model_name = $M ..."
docker exec -i -e M="$M" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
d.setdefault("LLM", {}).setdefault("RobotBridge", {})["model_name"] = os.environ["M"]
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  da dat model =", os.environ["M"])
PY
echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'loi robot 11'."
