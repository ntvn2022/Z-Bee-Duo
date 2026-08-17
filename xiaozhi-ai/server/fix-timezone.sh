#!/usr/bin/env bash
# Sua mui gio: server tra loi dung gio Viet Nam (UTC+7).
#
# Nguyen nhan that su: nhieu cho trong server goi datetime.now() KHONG co
# timezone (vd core/utils/dialogue.py thay {{current_time}} bang gio UTC) ->
# tra loi lech 7 tieng (2:28 thay vi 9:28). Sua tung file rat de sot, nen ta
# ep CA TIEN TRINH Python chay theo gio VN bang sitecustomize.py (Python tu
# dong import luc khoi dong) dat TZ=ICT-7 (dang POSIX cua UTC+7, KHONG can
# tzdata). Nho vay MOI datetime.now() deu ra gio VN.
#
# Chay TU BAN CLONE (tranh loi 429 cua GitHub raw):
#   git clone --depth 1 -b claude/esp32-s3-touch-screen-wwelt1 \
#     https://github.com/ntvn2022/z-bee-duo /tmp/zbd && \
#   bash /tmp/zbd/xiaozhi-ai/server/fix-timezone.sh
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server"
HERE="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
# Lay file: uu tien ban clone (local), neu khong co thi tai qua curl.
get() {  # get <ten_file> <dich_tmp>
  if [ -n "$HERE" ] && [ -f "$HERE/$1" ]; then
    cp "$HERE/$1" "$2"
  else
    curl -fsSL "$RAW/$1" -o "$2"
  fi
}

echo "==> Gio hien tai trong container TRUOC khi sua:"
docker exec "$C" python3 -c "from datetime import datetime; print('   now() =', datetime.now().strftime('%Y-%m-%d %H:%M'))" 2>/dev/null || true

echo "==> Tim thu muc site-packages ..."
SP="$(docker exec "$C" python3 -c 'import site; print(site.getsitepackages()[0])' 2>/dev/null | tr -d '\r')"
[ -z "$SP" ] && SP="$(docker exec "$C" python3 -c 'import sysconfig; print(sysconfig.get_paths()[\"purelib\"])' 2>/dev/null | tr -d '\r')"
echo "   site-packages = ${SP:-<khong tim thay>}"

echo "==> Nap sitecustomize.py (ep TZ=ICT-7 cho toan tien trinh) ..."
get sitecustomize.py /tmp/sitecustomize.py
if [ -n "$SP" ]; then
  docker cp /tmp/sitecustomize.py "$C":"$SP/sitecustomize.py"
fi
# Du phong: dat them vao thu muc app (neu chay voi cwd = app va site khong tat)
docker cp /tmp/sitecustomize.py "$C":/opt/xiaozhi-esp32-server/sitecustomize.py 2>/dev/null || true

echo "==> Nap current_time.py (UTC+7 tuong minh, du phong) ..."
get current_time.py /tmp/current_time.py
docker cp /tmp/current_time.py "$C":/opt/xiaozhi-esp32-server/core/utils/current_time.py 2>/dev/null || true

echo "==> Dat /etc/localtime = Asia/Ho_Chi_Minh (neu co tzdata) ..."
docker exec "$C" sh -c 'ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime 2>/dev/null; echo Asia/Ho_Chi_Minh > /etc/timezone 2>/dev/null' || true

echo "==> Dat server.timezone_offset = +7 (dong ho tren man hinh thiet bi qua OTA) ..."
docker exec -i "$C" python3 - <<'PY'
import yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
d.setdefault("server",{})["timezone_offset"]="+7"
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("   server.timezone_offset = +7")
PY

echo "==> Restart container ..."
docker restart "$C" >/dev/null
sleep 3

echo "==> Gio trong container SAU khi sua (phai la gio VN):"
docker exec "$C" python3 -c "from datetime import datetime; print('   now() =', datetime.now().strftime('%Y-%m-%d %H:%M'))" 2>/dev/null || true

echo "==> XONG. Noi thu: 'Alexa' -> 'bay gio la may gio roi?' (phai ra dung gio VN)."
echo "    Neu van sai, gui minh dong 'now() =' o tren."
