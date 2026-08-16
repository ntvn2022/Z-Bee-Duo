#!/usr/bin/env bash
# Giam ao giac Whisper tieng Viet (vd "Ghien Mi Go / subscribe..."):
#   - Va provider openai.py: temperature=0, gui 'language', LOC cac cau ao giac.
#   - Dam bao config: model whisper-large-v3, language: vi.
#   - Restart container.
set -uo pipefail
C="xiaozhi-esp32-server"
CFG="/opt/xiaozhi-server/data/.config.yaml"

echo "==> Va provider openai.py (temperature + language + loc ao giac) ..."
cat > /tmp/patch_asr_halluc.py <<'PY'
import pathlib
p = pathlib.Path("/opt/xiaozhi-esp32-server/core/providers/asr/openai.py")
s = p.read_text()
if '"temperature"' not in s:
    s = s.replace('                "model": self.model\n            }',
                  '                "model": self.model,\n                "temperature": 0\n            }', 1)
if "self.language" not in s:
    s = s.replace('self.model = config.get("model_name")',
                  'self.model = config.get("model_name")\n        self.language = config.get("language")', 1)
if 'data["language"]' not in s:
    s = s.replace('                "temperature": 0\n            }',
                  '                "temperature": 0\n            }\n            if getattr(self, "language", None):\n                data["language"] = self.language', 1)
if "_HALLUC" not in s:
    s = s.replace('                text = response.json().get("text", "")\n',
                  '                text = response.json().get("text", "")\n'
                  '                _HALLUC = ["ghiền mì gõ","ghien mi go","subscribe","đăng ký kênh","dang ky kenh","video hấp dẫn","video hap dan","không bỏ lỡ","khong bo lo","cảm ơn các bạn đã theo dõi","cảm ơn đã xem","hẹn gặp lại"]\n'
                  '                if text and any(h in text.lower() for h in _HALLUC):\n'
                  '                    logger.bind(tag=TAG).warning(f"Bo qua ao giac Whisper: {text}")\n'
                  '                    text = ""\n', 1)
p.write_text(s)
print("  openai.py da va")
PY
docker cp /tmp/patch_asr_halluc.py "$C":/tmp/patch_asr_halluc.py
docker exec "$C" python3 /tmp/patch_asr_halluc.py

echo "==> Dam bao config (model + language) ..."
sed -i 's|whisper-large-v3-turbo|whisper-large-v3|' "$CFG" || true
grep -q "language: vi" "$CFG" || sed -i '/model_name: whisper-large-v3/a\    language: vi' "$CFG"

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. (Luu y: neu TTS con loi thi van chua nghe/thay cau tra loi -> sua TTS truoc.)"
