#!/usr/bin/env bash
# Cai n8n (Docker) len VPS de lam bo tra cuu loi robot cho Jarvis.
#   - Chay canh xiaozhi-esp32-server, cong 5678.
#   - Truy cap: http://42.112.26.67:5678  (lan dau tao tai khoan chu so huu).
# Chay tren VPS: bash install-n8n.sh
set -uo pipefail

C="n8n"
IP="42.112.26.67"
PORT="5678"

echo "==> Kiem tra Docker ..."
if ! command -v docker >/dev/null 2>&1; then
  echo "!!! Chua co Docker. Cai xiaozhi-server truoc (da co Docker) roi chay lai." >&2
  exit 1
fi

echo "==> Go container n8n cu (neu co) ..."
docker rm -f "$C" >/dev/null 2>&1 || true

echo "==> Tao volume du lieu (giu workflow qua cac lan restart) ..."
docker volume create n8n_data >/dev/null

echo "==> Khoi dong n8n ..."
# Tuy chon: truyen Gemini key de workflow goi Gemini duoc:
#   GEMINI_API_KEY=xxxx bash install-n8n.sh
GEMINI_API_KEY="${GEMINI_API_KEY:-}"
if [ -z "$GEMINI_API_KEY" ]; then
  echo "  (Chua co GEMINI_API_KEY -> bot se tra loi tho. Chay lai voi GEMINI_API_KEY=... de bat Gemini.)"
fi
docker run -d --name "$C" --restart unless-stopped \
  -p ${PORT}:5678 \
  -e N8N_SECURE_COOKIE=false \
  -e N8N_HOST="${IP}" \
  -e N8N_PORT=5678 \
  -e N8N_PROTOCOL=http \
  -e WEBHOOK_URL="http://${IP}:${PORT}/" \
  -e GENERIC_TIMEZONE="Asia/Ho_Chi_Minh" \
  -e TZ="Asia/Ho_Chi_Minh" \
  -e GEMINI_API_KEY="$GEMINI_API_KEY" \
  -e N8N_RUNNERS_ENABLED=true \
  -v n8n_data:/home/node/.n8n \
  docker.n8n.io/n8nio/n8n >/dev/null

echo "==> Cho n8n khoi dong ..."
for i in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/healthz" >/dev/null 2>&1; then
    echo "  n8n da san sang."
    break
  fi
  sleep 2
done

echo ""
echo "==> XONG."
echo "    Mo trinh duyet:  http://${IP}:${PORT}"
echo "    Lan dau: tao tai khoan chu so huu (email + mat khau tu dat)."
echo "    Xem log:         docker logs -f ${C}"
echo ""
echo "    LUU Y BAO MAT: n8n dang chay HTTP tren IP cong khai."
echo "    - Dat mat khau manh khi tao tai khoan."
echo "    - Neu co the, gioi han cong ${PORT} qua firewall (chi IP cua ban)."
