#!/usr/bin/env bash
# Cai cau noi giong noi "robot bridge" cho Jarvis:
#   - Copy provider robot_bridge.py vao container xiaozhi.
#   - Doi LLM sang RobotBridge (ke thua Gemini: chat thuong van nhu cu,
#     chi chan khi vao che do robot -> goi n8n).
#   - Restart.
# Chay tren VPS: bash setup-robot-bridge.sh
#   Tuy chon: N8N_URL=... bash setup-robot-bridge.sh
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/robot_bridge.py"
N8N_URL="${N8N_URL:-http://42.112.26.67:5678/webhook/jarvis-bot}"

echo "==> Tai provider robot_bridge.py ..."
curl -fsSL "$RAW" -o /tmp/robot_bridge.py
docker exec "$C" mkdir -p /opt/xiaozhi-esp32-server/core/providers/llm/robot_bridge
# package marker (an toan neu da co)
docker exec "$C" sh -c 'touch /opt/xiaozhi-esp32-server/core/providers/llm/robot_bridge/__init__.py'
docker cp /tmp/robot_bridge.py "$C":/opt/xiaozhi-esp32-server/core/providers/llm/robot_bridge/robot_bridge.py

echo "==> Cap nhat config (LLM = RobotBridge, dung lai key+model cua GeminiLLM) ..."
docker exec -i -e N8N_URL="$N8N_URL" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
g = (d.get("LLM", {}) or {}).get("GeminiLLM", {}) or {}
key = g.get("api_key", "")
model = g.get("model_name", "gemini-2.5-flash")
d.setdefault("selected_module", {})["LLM"] = "RobotBridge"
d.setdefault("LLM", {})["RobotBridge"] = {
    "type": "robot_bridge",
    "api_key": key,
    "model_name": model,
    "n8n_url": os.environ.get("N8N_URL"),
}
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  LLM=RobotBridge  model=%s  n8n=%s" % (model, os.environ.get("N8N_URL")))
print("  gemini key:", "OK" if key else "!!! THIEU (chat thuong se loi)")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG."
echo "    - Chat thuong: van tra loi nhu cu (qua Gemini)."
echo "    - Noi 'lỗi robot 10' -> Jarvis doc cau tra loi tu bot n8n."
echo "    - Noi 'kết thúc robot' -> thoat che do."
echo "    Xem log:  docker logs -f $C"
