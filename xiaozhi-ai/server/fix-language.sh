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

# 2) Persona (ten + phong cach) bang tieng Viet.
#    QUY TAC NGON NGU dat o CA DAU va CUOI prompt de model yeu (vd gemini-3.7-flash)
#    khong the bo qua. Day la enforcement chinh (khong phu thuoc bien {{language}}).
d["prompt"] = (
    "[QUY TẮC BẮT BUỘC] Chỉ được trả lời bằng ĐÚNG ngôn ngữ mà người dùng vừa dùng: "
    "nếu người dùng nói tiếng Việt -> trả lời 100% tiếng Việt; nếu nói tiếng Anh -> trả lời tiếng Anh. "
    "TUYỆT ĐỐI KHÔNG dùng tiếng Trung (Hoa) hay bất kỳ chữ Hán nào trong mọi trường hợp.\n\n"
    "Bạn tên là ruanqinghe, một trợ lý AI thân thiện, nói chuyện tự nhiên, ngắn gọn, ấm áp.\n\n"
    "[NHẮC LẠI] Người dùng đang nói tiếng Việt thì bạn PHẢI trả lời bằng tiếng Việt. "
    "Không được chèn tiếng Trung. Nếu lỡ nghĩ bằng tiếng khác, hãy dịch sang tiếng Việt trước khi trả lời."
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
