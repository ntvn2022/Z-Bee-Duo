#!/usr/bin/env bash
# Tang toc bot tra loi loi robot:
#  - Bo n8n khoi duong di: bridge tra cuu NGAY trong container (bang du lieu
#    tai 1 lan roi cache), goi Gemini truc tiep va STREAM -> thiet bi bat dau
#    doc gan nhu ngay, khong con loi "Expecting value: line 1 column 1".
#  - Bo lenh tra cuu vi tri IP (whois.pconline.com.cn) bi loi SSL tu VN, gay
#    cham + spam loi moi lan ket noi.
# Chay tren VPS:  bash speedup-robot.sh
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/robot_bridge.py"

echo "==> Nap robot_bridge.py moi (tra cuu local + stream, bo n8n) ..."
curl -fsSL "$RAW" -o /tmp/robot_bridge.py
D="/opt/xiaozhi-esp32-server/core/providers/llm/robot_bridge"
docker exec "$C" mkdir -p "$D"
docker exec "$C" sh -c "test -f '$D/__init__.py' || touch '$D/__init__.py'"
docker cp /tmp/robot_bridge.py "$C":"$D/robot_bridge.py"

echo "==> Bo lenh tra cuu IP cham (whois.pconline) ..."
docker exec -i "$C" python3 - <<'PY'
import glob
targets = glob.glob("/opt/xiaozhi-esp32-server/core/utils/util.py")
for p in targets:
    s = open(p).read()
    anchor = "def get_ip_info(ip_addr, logger):\n"
    if "SKIP_IP_GEO" not in s and anchor in s:
        s = s.replace(
            anchor,
            anchor + '    return {"city": None}  # SKIP_IP_GEO: bo whois.pconline cham\n',
            1,
        )
        open(p, "w").write(s)
        print("  util.py: da bo IP geo lookup")
    else:
        print("  util.py: bo qua (da vá hoac khong tim thay)")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lỗi robot 11'. Se tra loi nhanh hon nhieu."
echo "    Xem log: docker logs -f $C   (khong con dong 'n8n bridge error')"
