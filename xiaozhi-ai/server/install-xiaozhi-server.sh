#!/usr/bin/env bash
# =============================================================================
#  install-xiaozhi-server.sh
#  Cai xiaozhi-esp32-server (ban Docker gon nhe) len VPS, dung Google Gemini
#  lam LLM. ASR = FunASR (local), TTS = EdgeTTS (mien phi).
#
#  CHAY TREN VPS (Ubuntu/Debian) voi quyen root:
#     GEMINI_API_KEY=xxxxx bash install-xiaozhi-server.sh
#  Hoac chay roi nhap key khi duoc hoi.
#
#  Repo goc: https://github.com/xinnan-tech/xiaozhi-esp32-server
# =============================================================================
set -euo pipefail

# ---- Tham so (co the dat qua bien moi truong) ----
INSTALL_DIR="${INSTALL_DIR:-/opt/xiaozhi-server}"
GEMINI_MODEL="${GEMINI_MODEL:-gemini-2.0-flash}"
IMAGE="${IMAGE:-ghcr.io/xinnan-tech/xiaozhi-esp32-server:server_latest}"
MODEL_URL="${MODEL_URL:-https://modelscope.cn/models/iic/SenseVoiceSmall/resolve/master/model.pt}"

echo "==> xiaozhi-esp32-server installer (LLM = Gemini)"

# ---- Lay Gemini API key ----
if [ -z "${GEMINI_API_KEY:-}" ]; then
    read -r -p "Nhap Gemini API key (lay tai https://aistudio.google.com/apikey): " GEMINI_API_KEY
fi
if [ -z "${GEMINI_API_KEY:-}" ]; then
    echo "!! Chua co GEMINI_API_KEY. Dung lai."; exit 1
fi

# ---- ASR: neu co GROQ_API_KEY thi dung GroqASR (nghe tieng Viet), khong thi FunASR ----
GROQ_API_KEY="${GROQ_API_KEY:-}"
if [ -n "$GROQ_API_KEY" ]; then
    ASR_SELECTED="GroqASR"
    echo "==> ASR: GroqASR (Whisper, ho tro tieng Viet)"
else
    ASR_SELECTED="FunASR"
    echo "==> ASR: FunASR (local; KHONG nghe duoc tieng Viet). Dat GROQ_API_KEY de nghe tieng Viet."
fi

# ---- Tu dong lay IP cong khai ----
PUBLIC_IP="${PUBLIC_IP:-$(curl -fsS https://api.ipify.org 2>/dev/null || true)}"
if [ -z "$PUBLIC_IP" ]; then
    read -r -p "Khong tu lay duoc IP cong khai. Nhap IP VPS: " PUBLIC_IP
fi
echo "==> IP cong khai: $PUBLIC_IP"

# ---- Cai Docker neu chua co ----
if ! command -v docker >/dev/null 2>&1; then
    echo "==> Cai Docker ..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable --now docker || true
fi
# Bao dam co 'docker compose' (v2)
if ! docker compose version >/dev/null 2>&1; then
    echo "==> Cai docker compose plugin ..."
    apt-get update -y && apt-get install -y docker-compose-plugin || true
fi

# ---- Tao thu muc ----
echo "==> Tao thu muc tai $INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data" "$INSTALL_DIR/models/SenseVoiceSmall"
cd "$INSTALL_DIR"

# ---- Tai model ASR (FunASR / SenseVoiceSmall, ~900MB) ----
MODEL_PT="$INSTALL_DIR/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PT" ] || [ "$(stat -c%s "$MODEL_PT" 2>/dev/null || echo 0)" -lt 100000000 ]; then
    echo "==> Tai model ASR SenseVoiceSmall (~900MB, co the lau) ..."
    curl -fL --retry 3 -o "$MODEL_PT" "$MODEL_URL"
else
    echo "==> Da co model.pt, bo qua tai."
fi

# ---- Ghi docker-compose.yml ----
echo "==> Ghi docker-compose.yml"
cat > "$INSTALL_DIR/docker-compose.yml" <<EOF
version: '3'
services:
  xiaozhi-esp32-server:
    image: ${IMAGE}
    container_name: xiaozhi-esp32-server
    restart: always
    security_opt:
      - seccomp:unconfined
    environment:
      - TZ=UTC
    ports:
      - "8000:8000"   # WebSocket (thiet bi ket noi)
      - "8003:8003"   # HTTP / OTA
    volumes:
      - ./data:/opt/xiaozhi-esp32-server/data
      - ./models/SenseVoiceSmall/model.pt:/opt/xiaozhi-esp32-server/models/SenseVoiceSmall/model.pt
EOF

# ---- Ghi cau hinh Gemini + tieng Viet (data/.config.yaml) ----
echo "==> Ghi data/.config.yaml (LLM = Gemini, tra loi tieng Viet)"
cat > "$INSTALL_DIR/data/.config.yaml" <<EOF
server:
  ip: 0.0.0.0
  port: 8000
  http_port: 8003
  # Dia chi WebSocket ma OTA tra ve cho thiet bi (dung IP cong khai VPS)
  websocket: ws://${PUBLIC_IP}:8000/xiaozhi/v1/

# Ten tro ly
assistant_name: "ruanqinghe"

# Prompt: dat ten + tu dong tra loi theo ngon ngu cua nguoi dung
prompt: |
  Ban ten la ruanqinghe, mot tro ly AI than thien, noi chuyen tu nhien, ngan gon.
  QUY TAC NGON NGU (rat quan trong): Tu dong nhan biet ngon ngu cua nguoi dung va
  tra loi DUNG bang chinh ngon ngu do:
  - Nguoi dung noi/viet tieng Viet  -> tra loi hoan toan bang tieng Viet.
  - Nguoi dung noi/viet tieng Anh    -> tra loi hoan toan bang tieng Anh.
  - Nguoi dung noi/viet tieng Trung  -> tra loi bang tieng Trung.
  Khong tu y doi sang ngon ngu khac voi ngon ngu ma nguoi dung dang dung.
  Uu tien ho tro: Tieng Viet va English.

selected_module:
  LLM: GeminiLLM
  TTS: EdgeTTS
  ASR: ${ASR_SELECTED}
  # nointent: tat function_call. Gemini khong ho tro schema function_call
  # (loi "Unknown field for Schema: minimum") nen dung nointent de chat on dinh.
  Intent: nointent

LLM:
  GeminiLLM:
    type: gemini
    api_key: ${GEMINI_API_KEY}
    model_name: "${GEMINI_MODEL}"
    http_proxy: ""
    https_proxy: ""

ASR:
  # GroqASR: Whisper large-v3 tren Groq (mien phi, ho tro TIENG VIET, khong ton RAM).
  # Lay key mien phi tai: https://console.groq.com/keys
  GroqASR:
    type: openai
    api_key: ${GROQ_API_KEY}
    base_url: https://api.groq.com/openai/v1/audio/transcriptions
    model_name: whisper-large-v3-turbo

TTS:
  EdgeTTS:
    type: edge
    voice: vi-VN-HoaiMyNeural   # giong nu tieng Viet; nam: vi-VN-NamMinhNeural
    output_dir: tmp/
EOF

# ---- Mo cong tuong lua (neu dung ufw) ----
if command -v ufw >/dev/null 2>&1; then
    ufw allow 8000/tcp || true
    ufw allow 8003/tcp || true
fi

# ---- Khoi dong ----
echo "==> Keo image va khoi dong container ..."
docker compose pull
docker compose up -d

echo
echo "============================================================"
echo " Cai xong! Container dang chay."
echo
echo "   WebSocket : ws://${PUBLIC_IP}:8000/xiaozhi/v1/"
echo "   OTA/HTTP  : http://${PUBLIC_IP}:8003/xiaozhi/ota/"
echo
echo " Xem log:      docker logs -f xiaozhi-esp32-server"
echo " Sua cau hinh: nano ${INSTALL_DIR}/data/.config.yaml"
echo "               roi: docker compose -f ${INSTALL_DIR}/docker-compose.yml restart"
echo
echo " BUOC TIEP: cau hinh thiet bi ESP32-S3 tro OTA ve:"
echo "   http://${PUBLIC_IP}:8003/xiaozhi/ota/"
echo "============================================================"
