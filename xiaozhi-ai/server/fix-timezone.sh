#!/usr/bin/env bash
# Sua mui gio: server tra loi dung gio Viet Nam (UTC+7).
# - Van de: core/utils/current_time.py dung datetime.now() KHONG co timezone,
#   nen container chay UTC -> tra loi lech 7 tieng (2:21 thay vi 9:21).
# - Sua: nap current_time.py ban vá (UTC+7) + dat timezone_offset=+7 (dong ho
#   tren man hinh thiet bi) + dat /etc/localtime cua container = Asia/Ho_Chi_Minh.
# Chay tren VPS:  bash fix-timezone.sh
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/current_time.py"

echo "==> Kiem tra gio hien tai trong container (truoc khi sua) ..."
docker exec "$C" python3 -c "from datetime import datetime; print('  now() =', datetime.now())" 2>/dev/null || true

echo "==> Nap current_time.py (UTC+7) ..."
curl -fsSL "$RAW" -o /tmp/current_time.py
docker cp /tmp/current_time.py "$C":/opt/xiaozhi-esp32-server/core/utils/current_time.py

echo "==> Dat /etc/localtime = Asia/Ho_Chi_Minh (neu co tzdata) ..."
docker exec "$C" sh -c 'ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime 2>/dev/null; echo Asia/Ho_Chi_Minh > /etc/timezone 2>/dev/null' || true

echo "==> Dat server.timezone_offset = +7 (dong ho man hinh thiet bi qua OTA) ..."
docker exec -i "$C" python3 - <<'PY'
import yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
d.setdefault("server",{})["timezone_offset"]="+7"
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("  server.timezone_offset = +7")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null

echo "==> Kiem tra lai gio (sau khi sua) ..."
sleep 2
docker exec "$C" python3 -c "from core.utils.current_time import get_current_time_info as f; import os; os.chdir('/opt/xiaozhi-esp32-server'); print('  ', f())" 2>/dev/null \
  || docker exec "$C" sh -c 'cd /opt/xiaozhi-esp32-server && python3 -c "from core.utils.current_time import get_current_time_info as f; print(\"  \", f())"' 2>/dev/null \
  || docker exec "$C" python3 -c "from datetime import datetime,timezone,timedelta; print('  VN =', datetime.now(timezone(timedelta(hours=7))).strftime('%H:%M'))"

echo "==> XONG. Noi thu: 'Alexa' -> 'bay gio la may gio roi?'  (phai ra dung gio VN)"
