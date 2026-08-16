#!/usr/bin/env bash
# Ghi cau hinh xiaozhi-server (Gemini + GroqASR + EdgeTTS vi-VN + nointent)
# roi khoi dong lai container. Doc key tu bien moi truong.
#   GEMINI_API_KEY=... GROQ_API_KEY=... bash apply-config.sh
set -euo pipefail

: "${GEMINI_API_KEY:?Thieu GEMINI_API_KEY}"
: "${GROQ_API_KEY:?Thieu GROQ_API_KEY}"

DEST="/opt/xiaozhi-server/data/.config.yaml"
URL="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/config.template.yaml"

echo "==> Tai config template ..."
curl -fsSL "$URL" -o "$DEST"

echo "==> Dien API key ..."
sed -i "s|__GEMINI_KEY__|${GEMINI_API_KEY}|" "$DEST"
sed -i "s|__GROQ_KEY__|${GROQ_API_KEY}|" "$DEST"

echo "==> Kiem tra config:"
grep -nE 'Intent:|ASR:|voice:|api_key|__' "$DEST" || true

echo "==> Khoi dong lai container ..."
docker restart xiaozhi-esp32-server

echo "==> XONG. Xem log bang: docker logs -f xiaozhi-esp32-server"
