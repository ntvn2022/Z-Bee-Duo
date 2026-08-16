#!/usr/bin/env bash
# Cai TTS lai: Gemini TTS (chinh) + tu dong chuyen EdgeTTS khi het quota ngay,
# hom sau tu mo lai Gemini. Chay tren VPS: bash setup-tts-fallback.sh
#   Tuy chon: TTS_MODEL=... TTS_VOICE=... EDGE_VOICE=... bash setup-tts-fallback.sh
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/gemini_edge.py"
TTS_MODEL="${TTS_MODEL:-gemini-2.5-flash-preview-tts}"
TTS_VOICE="${TTS_VOICE:-Kore}"
EDGE_VOICE="${EDGE_VOICE:-vi-VN-HoaiMyNeural}"

echo "==> Tai provider gemini_edge.py ..."
curl -fsSL "$RAW" -o /tmp/gemini_edge.py
docker cp /tmp/gemini_edge.py "$C":/opt/xiaozhi-esp32-server/core/providers/tts/gemini_edge.py

echo "==> Dam bao edge-tts co san (cho fallback) ..."
docker exec "$C" pip install -q -U edge-tts >/dev/null 2>&1 || \
  docker exec "$C" pip3 install -q -U edge-tts >/dev/null 2>&1 || true

echo "==> Cap nhat config (TTS = GeminiEdge) ..."
docker exec -i -e M="$TTS_MODEL" -e V="$TTS_VOICE" -e EV="$EDGE_VOICE" "$C" python3 - <<'PY'
import os, yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
# reuse existing Gemini key (from GeminiTTS or GeminiLLM)
tts=(d.get("TTS",{}) or {})
key=((tts.get("GeminiTTS",{}) or {}).get("api_key")
     or (tts.get("GeminiEdge",{}) or {}).get("api_key")
     or ((d.get("LLM",{}) or {}).get("GeminiLLM",{}) or {}).get("api_key","") )
d.setdefault("selected_module",{})["TTS"]="GeminiEdge"
d.setdefault("TTS",{})["GeminiEdge"]={
    "type":"gemini_edge",
    "api_key":key,
    "model_name":os.environ["M"],
    "voice":os.environ["V"],
    "edge_voice":os.environ["EV"],
    "output_dir":"tmp/",
}
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("  TTS=GeminiEdge  gemini_model=%s  gemini_voice=%s  edge_voice=%s"
      % (os.environ["M"], os.environ["V"], os.environ["EV"]))
print("  gemini key:", "OK" if key else "!!! THIEU (se luon dung EdgeTTS)")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG."
echo "    - Uu tien Gemini TTS. Het quota ngay (429) -> tu chuyen EdgeTTS."
echo "    - Sang ngay moi tu thu lai Gemini."
echo "    Xem log:  docker logs -f $C   (tim 'chuyen EdgeTTS' khi het quota)"
