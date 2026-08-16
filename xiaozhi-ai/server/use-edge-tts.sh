#!/usr/bin/env bash
# Doi TTS sang EdgeTTS (Microsoft, MIEN PHI, khong gioi han 100/ngay nhu Gemini TTS).
# Giong Viet mac dinh: vi-VN-HoaiMyNeural (nu). Nam: vi-VN-NamMinhNeural.
# Chay tren VPS: bash use-edge-tts.sh
#   Tuy chon: VOICE=vi-VN-NamMinhNeural bash use-edge-tts.sh
set -uo pipefail
C="xiaozhi-esp32-server"
VOICE="${VOICE:-vi-VN-HoaiMyNeural}"

echo "==> Nang cap edge-tts trong container (fix loi 'No audio' do lib cu) ..."
docker exec "$C" pip install -q -U edge-tts 2>/dev/null || \
  docker exec "$C" pip3 install -q -U edge-tts 2>/dev/null || true

echo "==> Test EdgeTTS ($VOICE) ..."
if docker exec -e V="$VOICE" "$C" sh -c 'edge-tts --voice "$V" --text "xin chào, đây là bản thử giọng nói" --write-media /tmp/edge_test.mp3 >/dev/null 2>&1 && [ -s /tmp/edge_test.mp3 ]'; then
  echo "  EDGE_OK: tao duoc audio."
else
  echo "  !!! EDGE_FAIL: khong tao duoc audio (co the VPS chan Microsoft). Bao lai de dung cach khac."
fi

echo "==> Cap nhat config (TTS = EdgeTTS, giong $VOICE) ..."
docker exec -i -e VOICE="$VOICE" "$C" python3 - <<'PY'
import os, yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
d.setdefault("selected_module", {})["TTS"]="EdgeTTS"
d.setdefault("TTS", {})["EdgeTTS"]={
    "type":"edge",
    "voice":os.environ.get("VOICE"),
    "output_dir":"tmp/",
}
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("  TTS=EdgeTTS  voice=%s" % os.environ.get("VOICE"))
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lỗi robot 10'. Xem log: docker logs -f $C"
echo "    - Neu van loi TTS, chay: docker logs --tail 20 $C  va bao minh."
