#!/usr/bin/env bash
# Doi API key Gemini dung trong xiaozhi (LLM + RobotBridge + TTS) sang key MOI
# (vd key cua project 'clawbot' da tra phi de het gioi han 100/ngay).
# Chay tren VPS:  GEMINI_KEY='<key_clawbot>' bash set-gemini-key.sh
set -uo pipefail
C="xiaozhi-esp32-server"
: "${GEMINI_KEY:?Thieu GEMINI_KEY. Chay: GEMINI_KEY='<key>' bash set-gemini-key.sh}"

echo "==> Cap nhat key Gemini trong config (LLM/RobotBridge/TTS) ..."
docker exec -i -e K="$GEMINI_KEY" "$C" python3 - <<'PY'
import os, yaml
p="/opt/xiaozhi-esp32-server/data/.config.yaml"
d=yaml.safe_load(open(p)) or {}
k=os.environ["K"]
n=0
for path in (("LLM","GeminiLLM"),("LLM","RobotBridge"),("TTS","GeminiTTS")):
    a,b=path
    if isinstance(d.get(a,{}).get(b), dict):
        d[a][b]["api_key"]=k; n+=1; print("  set", a, b)
yaml.safe_dump(d, open(p,"w"), allow_unicode=True, sort_keys=False)
print("  updated %d place(s)" % n)
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu: 'Alexa' -> 'lỗi robot 10'. Neu het loi 429 la key clawbot da an."
echo "    (Neu van 429 limit 100 -> key nay VAN thuoc project free, tao lai key trong project clawbot.)"
