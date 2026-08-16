#!/usr/bin/env bash
# Doi duong dan OTA cua server tu /xiaozhi/ota/ -> /ruanqinghe/ota/
# LUU Y: va code ben trong container -> mat neu tao lai container (docker compose down/up
#        hoac doi image). Khi do chay lai script nay.
# Sau khi chay: nho doi dia chi OTA tren THIET BI (192.168.4.1) thanh
#   http://42.112.26.67:8003/ruanqinghe/ota/
set -euo pipefail

CONTAINER="xiaozhi-esp32-server"

echo "==> Va route OTA trong container ..."
cat > /tmp/patch_ota_path.py <<'PY'
import pathlib
files = ["core/http_server.py", "core/api/ota_handler.py", "app.py"]
for rel in files:
    p = pathlib.Path("/opt/xiaozhi-esp32-server/" + rel)
    if not p.exists():
        print("  bo qua (khong thay):", rel); continue
    s = p.read_text()
    if "/xiaozhi/ota/" in s:
        s = s.replace("/xiaozhi/ota/", "/ruanqinghe/ota/")
        p.write_text(s)
        print("  da va:", rel)
    else:
        print("  khong doi / da va truoc do:", rel)
PY
docker cp /tmp/patch_ota_path.py "$CONTAINER":/tmp/patch_ota_path.py
docker exec "$CONTAINER" python3 /tmp/patch_ota_path.py

echo "==> Khoi dong lai container ..."
docker restart "$CONTAINER"

echo
echo "==> XONG. Kiem tra:"
echo "    Mo tren dien thoai: http://42.112.26.67:8003/ruanqinghe/ota/"
echo "    (phai tra ve 'OTA接口运行正常...'); con /xiaozhi/ota/ se thanh 404."
echo "==> Nho: tren THIET BI (192.168.4.1 -> tab nang cao) doi dia chi OTA thanh:"
echo "    http://42.112.26.67:8003/ruanqinghe/ota/"
