#!/usr/bin/env bash
# Sua loi Gemini LLM: generate_content() got an unexpected keyword argument 'timeout'
# -> bo tham so timeout khong tuong thich trong provider gemini.
# Chay tren VPS: bash fix-gemini-llm.sh
set -uo pipefail
C="xiaozhi-esp32-server"

echo "==> Va provider Gemini LLM (bo 'timeout=self.timeout') ..."
cat > /tmp/patch_gllm.py <<'PY'
import pathlib
p = pathlib.Path("/opt/xiaozhi-esp32-server/core/providers/llm/gemini/gemini.py")
s = p.read_text()
if "timeout=self.timeout," in s:
    s = s.replace("            timeout=self.timeout,\n", "", 1)
    p.write_text(s)
    print("  da bo timeout=self.timeout")
else:
    print("  khong tim thay (co the da sua roi)")
PY
docker cp /tmp/patch_gllm.py "$C":/tmp/patch_gllm.py
docker exec "$C" python3 /tmp/patch_gllm.py

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu -> LLM se tra loi (tieng Viet theo prompt), TTS Gemini doc ra."
