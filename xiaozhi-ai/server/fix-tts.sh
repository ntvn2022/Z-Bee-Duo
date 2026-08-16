#!/usr/bin/env bash
# Chan doan + sua loi TTS (EdgeTTS "No audio received").
#   - Nang cap edge-tts trong container.
#   - Test tao audio -> bao TTS_OK hay TTS_FAIL.
#   - Restart container.
# Chay tren VPS:  bash fix-tts.sh
set -uo pipefail
C="xiaozhi-esp32-server"

echo "==> edge-tts version (truoc):"
docker exec "$C" pip show edge-tts 2>/dev/null | grep -i version || echo "  (khong doc duoc)"

echo "==> Nang cap edge-tts ..."
docker exec "$C" pip install -U --break-system-packages edge-tts >/dev/null 2>&1 \
  || docker exec "$C" pip install -U edge-tts >/dev/null 2>&1 || true

echo "==> edge-tts version (sau):"
docker exec "$C" pip show edge-tts 2>/dev/null | grep -i version || true

echo "==> Test tao audio tieng Viet ..."
docker exec "$C" sh -c 'edge-tts --voice vi-VN-HoaiMyNeural --text "xin chao ban" --write-media /tmp/tts_test.mp3 >/tmp/tts_err.txt 2>&1; if [ -s /tmp/tts_test.mp3 ]; then echo "  ==> TTS_OK  (size=$(stat -c%s /tmp/tts_test.mp3) bytes)"; else echo "  ==> TTS_FAIL"; echo "  --- loi ---"; cat /tmp/tts_err.txt; fi'

echo "==> Khoi dong lai container ..."
docker restart "$C" >/dev/null
echo
echo "==> KET LUAN:"
echo "  - Neu tren hien TTS_OK  -> EdgeTTS da chay lai. Noi thu, cau tra loi se hien tren icon + co tieng."
echo "  - Neu hien TTS_FAIL     -> EdgeTTS bi chan tu VPS nay. Can doi sang TTS tra phi (OpenAI). Bao lai de minh cau hinh."
