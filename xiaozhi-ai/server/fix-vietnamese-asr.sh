#!/usr/bin/env bash
# Cai thien nhan dien tieng Viet cho ASR (Groq/OpenAI Whisper):
#  1) Va provider openai.py de gui tham so 'language' len API Whisper.
#  2) Sua .config.yaml dang co: model -> whisper-large-v3, them language: vi.
#  3) Khoi dong lai container.
# Chay tren VPS:  bash fix-vietnamese-asr.sh
set -euo pipefail

CONTAINER="xiaozhi-esp32-server"
CFG="/opt/xiaozhi-server/data/.config.yaml"

echo "==> 1/3 Va provider openai.py (ho tro language) ..."
cat > /tmp/patch_openai_asr.py <<'PY'
import pathlib
p = pathlib.Path("/opt/xiaozhi-esp32-server/core/providers/asr/openai.py")
s = p.read_text()
a1 = 'self.model = config.get("model_name")'
a2 = '            data = {\n                "model": self.model\n            }'
changed = False
if "self.language" not in s:
    s = s.replace(a1, a1 + '\n        self.language = config.get("language")', 1); changed = True
if 'data["language"]' not in s:
    s = s.replace(a2, a2 + '\n            if getattr(self, "language", None):\n                data["language"] = self.language', 1); changed = True
p.write_text(s)
print("  provider patched" if changed else "  provider already patched")
PY
docker cp /tmp/patch_openai_asr.py "$CONTAINER":/tmp/patch_openai_asr.py
docker exec "$CONTAINER" python3 /tmp/patch_openai_asr.py

echo "==> 2/3 Cap nhat config (model + language: vi) ..."
sed -i 's|whisper-large-v3-turbo|whisper-large-v3|' "$CFG" || true
if ! grep -q "language: vi" "$CFG"; then
    sed -i '/model_name: whisper-large-v3/a\    language: vi' "$CFG"
fi
echo "   -- ASR config hien tai --"
grep -nE "GroqASR|model_name|language" "$CFG" || true

echo "==> 3/3 Khoi dong lai container ..."
docker restart "$CONTAINER"
echo "==> XONG. Test: noi tieng Viet, xem 'docker logs -f $CONTAINER' -> dong '识别文本' co dung khong."
