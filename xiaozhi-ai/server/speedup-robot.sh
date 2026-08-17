#!/usr/bin/env bash
# Tang toc bot tra loi loi robot + het loi 429 (GitHub raw chan IP VPS).
#
# Chay TU BAN CLONE (khong dung curl raw vi bi 429):
#   git clone --depth 1 -b claude/esp32-s3-touch-screen-wwelt1 \
#     https://github.com/ntvn2022/z-bee-duo /tmp/zbd && \
#   bash /tmp/zbd/xiaozhi-ai/server/speedup-robot.sh
#
# Script se:
#  - Nap robot_bridge.py moi (tra cuu LOCAL + stream Gemini, bo n8n).
#  - Copy registry.json + tables vao container (data/robot/) -> runtime KHONG
#    con goi GitHub -> het 429, het loi "Expecting value: line 1 column 1".
#  - Bo tra cuu IP cham (whois.pconline) gay loi SSL tu VN.
set -uo pipefail
C="xiaozhi-esp32-server"
RD="/opt/xiaozhi-esp32-server/data/robot"

HERE="$(cd "$(dirname "$0")" && pwd)"     # .../xiaozhi-ai/server
ROOT="$(cd "$HERE/../.." && pwd)"         # repo root
REG="$ROOT/xiaozhi-ai/machines/registry.json"
BRIDGE="$ROOT/xiaozhi-ai/server/providers/robot_bridge.py"

if [ ! -f "$REG" ] || [ ! -f "$BRIDGE" ]; then
  echo "LOI: khong tim thay file trong ban clone."
  echo "Hay chay dung cach (clone truoc):"
  echo "  git clone --depth 1 -b claude/esp32-s3-touch-screen-wwelt1 https://github.com/ntvn2022/z-bee-duo /tmp/zbd"
  echo "  bash /tmp/zbd/xiaozhi-ai/server/speedup-robot.sh"
  exit 1
fi

echo "==> Nap robot_bridge.py (local lookup + stream, bo n8n) ..."
D="/opt/xiaozhi-esp32-server/core/providers/llm/robot_bridge"
docker exec "$C" mkdir -p "$D"
docker exec "$C" sh -c "test -f '$D/__init__.py' || touch '$D/__init__.py'"
docker cp "$BRIDGE" "$C":"$D/robot_bridge.py"

echo "==> Copy du lieu (registry + tables) vao container ($RD) ..."
docker exec "$C" mkdir -p "$RD/tables"
docker cp "$REG" "$C":"$RD/registry.json"
# Copy bang tra cuu cua tung may (suy ra duong dan repo tu tables_url).
python3 - "$ROOT" "$C" "$RD" <<'PY'
import json, os, subprocess, sys
root, C, RD = sys.argv[1], sys.argv[2], sys.argv[3]
reg = json.load(open(os.path.join(root, "xiaozhi-ai/machines/registry.json")))
for m in reg:
    tu = m.get("tables_url", "")
    mid = m.get("id", "")
    if "/xiaozhi-ai/" not in tu or not mid:
        continue
    rel = "xiaozhi-ai/" + tu.split("/xiaozhi-ai/", 1)[1]
    local = os.path.join(root, rel)
    if os.path.exists(local):
        subprocess.run(["docker", "cp", local, f"{C}:{RD}/tables/{mid}.json"], check=False)
        print(f"  tables: {mid}")
    else:
        print(f"  (thieu file local cho {mid}: {rel})")
PY

echo "==> Doi model sang gemini-2.5-flash-lite (nhanh hon, khong 'thinking') ..."
docker exec -i "$C" python3 - <<'PY'
import yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
llm = d.setdefault("LLM", {}).setdefault("RobotBridge", {})
llm["model_name"] = "gemini-2.5-flash-lite"
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  LLM.RobotBridge.model_name = gemini-2.5-flash-lite")
PY

echo "==> Tat plugin thoi tiet (khong co API key -> chi spam loi) ..."
docker exec -i "$C" python3 - <<'PY'
p = "/opt/xiaozhi-esp32-server/plugins_func/functions/get_weather.py"
try:
    s = open(p).read()
    a = "async def fetch_city_info(location, api_key, api_host):\n"
    if "WEATHER_DISABLED" not in s and a in s:
        s = s.replace(a, a + "    return None  # WEATHER_DISABLED: tat tra cuu thoi tiet\n", 1)
        open(p, "w").write(s)
        print("  get_weather: da tat")
    else:
        print("  get_weather: bo qua (da tat hoac khong thay)")
except Exception as e:
    print("  get_weather: loi", e)
PY

echo "==> Bo tra cuu IP cham (whois.pconline) ..."
docker exec -i "$C" python3 - <<'PY'
p = "/opt/xiaozhi-esp32-server/core/utils/util.py"
try:
    s = open(p).read()
    a = "def get_ip_info(ip_addr, logger):\n"
    if "SKIP_IP_GEO" not in s and a in s:
        s = s.replace(a, a + '    return {"city": None}  # SKIP_IP_GEO: bo whois.pconline cham\n', 1)
        open(p, "w").write(s)
        print("  util.py: da bo IP geo lookup")
    else:
        print("  util.py: bo qua (da va hoac khong thay)")
except Exception as e:
    print("  util.py: loi", e)
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lỗi robot 11'. Nhanh hon, khong con 429/n8n error."
echo "    Xem log: docker logs -f $C"
