#!/usr/bin/env bash
# Cai module Gemini TTS cho xiaozhi-server (dung lai key Gemini dang co).
#   - Copy provider gemini.py vao container.
#   - Doi config: TTS = GeminiTTS.
#   - Restart.
# Tuy chon: TTS_MODEL=... TTS_VOICE=... bash setup-gemini-tts.sh
# LUU Y: file provider nam trong container -> mat neu tao lai container. Khi do chay lai.
set -uo pipefail
C="xiaozhi-esp32-server"
RAW="https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/providers/gemini_tts.py"
TTS_MODEL="${TTS_MODEL:-gemini-3.1-flash-tts}"
TTS_VOICE="${TTS_VOICE:-Kore}"

echo "==> Tai provider Gemini TTS ..."
curl -fsSL "$RAW" -o /tmp/gemini_tts.py
docker cp /tmp/gemini_tts.py "$C":/opt/xiaozhi-esp32-server/core/providers/tts/gemini.py

echo "==> Cap nhat config (TTS = GeminiTTS, dung lai key Gemini cua LLM) ..."
docker exec -i -e TTS_MODEL="$TTS_MODEL" -e TTS_VOICE="$TTS_VOICE" "$C" python3 - <<'PY'
import os, yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}
key = ((d.get("LLM", {}) or {}).get("GeminiLLM", {}) or {}).get("api_key", "") \
      or os.environ.get("GEMINI_API_KEY", "")
d.setdefault("selected_module", {})["TTS"] = "GeminiTTS"
d.setdefault("TTS", {})["GeminiTTS"] = {
    "type": "gemini",
    "api_key": key,
    "model_name": os.environ.get("TTS_MODEL"),
    "voice": os.environ.get("TTS_VOICE"),
    "output_dir": "tmp/",
}
yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  TTS=GeminiTTS  model=%s  voice=%s" % (os.environ.get("TTS_MODEL"), os.environ.get("TTS_VOICE")))
print("  api_key:", "OK" if key else "!!! THIEU KEY GEMINI")
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu + xem: docker logs -f $C"
echo "    - Neu loi 'model not found' -> chay lai voi TTS_MODEL khac, vd:"
echo "        TTS_MODEL=gemini-2.5-pro-preview-tts bash setup-gemini-tts.sh"
