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
N8N_C="n8n"
NET="jarvisnet"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/robot_bridge.py"
# Reach n8n by container name over a shared Docker network (works from inside
# the container, unlike the host public IP which fails via NAT hairpin).
N8N_URL="${N8N_URL:-http://n8n:5678/webhook/jarvis-bot}"

echo "==> Noi 2 container qua mang Docker chung ($NET) ..."
docker network create "$NET" >/dev/null 2>&1 || true
docker network connect "$NET" "$C" 2>/dev/null || true
docker network connect "$NET" "$N8N_C" 2>/dev/null || true

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

echo "==> Test ket noi tu trong container xiaozhi toi n8n ..."
sleep 6
docker exec "$C" python3 - <<'PY' || echo "  !!! Container CHUA goi duoc n8n. Kiem tra workflow n8n da Active chua."
import json, urllib.request
req=urllib.request.Request("http://n8n:5678/webhook/jarvis-bot",
    data=json.dumps({"text":"robot T23 la gi"}).encode(),
    headers={"Content-Type":"application/json"})
try:
    r=urllib.request.urlopen(req, timeout=15)
    d=json.loads(r.read().decode())
    print("  OK n8n tra loi:", (d.get("reply","") or "")[:80])
except Exception as e:
    print("  LOI:", e); raise SystemExit(1)
PY

echo "==> XONG."
echo "    - Chat thuong: van tra loi nhu cu (qua Gemini)."
echo "    - Noi 'lỗi robot 10' -> Jarvis doc cau tra loi tu bot n8n."
echo "    - Noi 'kết thúc robot' -> thoat che do."
echo "    Xem log:  docker logs -f $C"
