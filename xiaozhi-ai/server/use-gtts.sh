#!/usr/bin/env bash
# Doi TTS sang gTTS (Google Translate TTS): free, on dinh, khong quota, khong key.
# Dung khi EdgeTTS loi 'No audio' va Gemini TTS het quota.
# Chay tren VPS: bash use-gtts.sh    (tuy chon: GTTS_LANG=vi bash use-gtts.sh)
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/gtts_tts.py"
# LUU Y: dung GTTS_LANG (khong dung $LANG vi trung bien he thong = en_US.UTF-8)
LANG_CODE="${GTTS_LANG:-vi}"

echo "==> Cai gTTS trong container ..."
docker exec "$C" pip install -q -U gTTS >/dev/null 2>&1 || \
  docker exec "$C" pip3 install -q -U gTTS >/dev/null 2>&1 || true

echo "==> Tai provider gtts ..."
curl -fsSL "$RAW" -o /tmp/gtts_tts.py
docker cp /tmp/gtts_tts.py "$C":/opt/xiaozhi-esp32-server/core/providers/tts/gtts.py

echo "==> Test gTTS ..."
if docker exec "$C" python3 - <<'PY'
try:
    from gtts import gTTS
    gTTS(text="xin chào, thử giọng nói", lang="vi").save("/tmp/gtts_test.mp3")
    import os
    print("GTTS_OK" if os.path.getsize("/tmp/gtts_test.mp3")>0 else "GTTS_FAIL")
except Exception as e:
    print("GTTS_FAIL:", e)
PY
then :; fi

echo "==> Cap nhat config (TTS = GTTS) ..."
docker exec -i -e L="$LANG_CODE" "$C" python3 - <<'PY'
import os, yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
d.setdefault("selected_module",{})["TTS"]="GTTS"
d.setdefault("TTS",{})["GTTS"]={"type":"gtts","lang":os.environ["L"],"output_dir":"tmp/"}
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("  TTS=GTTS lang=%s" % os.environ["L"])
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lỗi robot 10'. Xem log: docker logs -f $C"
