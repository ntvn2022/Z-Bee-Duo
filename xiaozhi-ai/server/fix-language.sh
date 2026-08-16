#!/usr/bin/env bash
# Bo tieng Hoa: dat ngon ngu tra loi (bien {{language}} lay tu TTS.<module>.language,
# mac dinh la 中文) + doi cac cau phan hoi mac dinh sang tieng Viet.
# Chay tren VPS: bash fix-language.sh
set -uo pipefail
C="xiaozhi-esp32-server"

echo "==> Cap nhat ngon ngu tra loi + cau loi mac dinh ..."
docker exec -i "$C" python3 - <<'PY'
import yaml
p = "/opt/xiaozhi-esp32-server/data/.config.yaml"
d = yaml.safe_load(open(p)) or {}

# 1) Ngon ngu tra loi cua LLM: nhet vao TTS.<selected>.language (bien {{language}})
tts_name = (d.get("selected_module", {}) or {}).get("TTS", "GeminiTTS")
d.setdefault("TTS", {}).setdefault(tts_name, {})["language"] = (
    "tiếng Việt (hoặc tiếng Anh nếu người dùng nói tiếng Anh); TUYỆT ĐỐI KHÔNG dùng tiếng Trung"
)

# 2) Persona (ten + phong cach) bang tieng Viet
d["prompt"] = (
    "Bạn tên là ruanqinghe, một trợ lý AI thân thiện, nói chuyện tự nhiên, ngắn gọn, ấm áp. "
    "Luôn trả lời bằng tiếng Việt (hoặc tiếng Anh nếu người dùng dùng tiếng Anh). "
    "Tuyệt đối không trả lời bằng tiếng Trung."
)

# 3) Cau bao loi / ket thuc bang tieng Viet (thay defaults tieng Hoa)
d["system_error_response"] = "Xin lỗi, mình đang hơi bận một chút, bạn thử lại sau nhé."
d["end_prompt"] = {
    "enable": True,
    "prompt": "Hãy kết thúc cuộc trò chuyện một cách nhẹ nhàng, thân thiện, bằng tiếng Việt.",
}

yaml.safe_dump(d, open(p, "w"), allow_unicode=True, sort_keys=False)
print("  language =", d["TTS"][tts_name]["language"])
print("  system_error_response =", d["system_error_response"])
PY

echo "==> Restart ..."
docker restart "$C" >/dev/null
echo "==> XONG. Noi thu tieng Viet -> tra loi tieng Viet; het cau tieng Hoa."
