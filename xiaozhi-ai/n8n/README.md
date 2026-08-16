# n8n workflow — Jarvis bot lỗi máy (Leader/Branch)

File: `jarvis-bot.workflow.json` — import thẳng vào n8n.

## 1. Nạp Gemini key cho n8n (một lần)
Workflow gọi Gemini bằng biến môi trường `GEMINI_API_KEY` của container n8n.
Chạy lại script cài kèm key (giữ nguyên dữ liệu cũ vì dùng volume):

```bash
GEMINI_API_KEY='<gemini_key_cua_ban>' bash install-n8n.sh
```

(hoặc tự thêm `-e GEMINI_API_KEY=...` vào container n8n.)

## 2. Import workflow
1. Mở http://42.112.26.67:5678 → đăng nhập.
2. Góc phải trên **⋮ → Import from File** (hoặc **Import from URL**):
   `https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/n8n/jarvis-bot.workflow.json`
3. Bấm **Active** (bật) để webhook chạy thật.

## 3. Địa chỉ webhook
```
http://42.112.26.67:5678/webhook/jarvis-bot
```
(khi đang chỉnh sửa/test dùng: `/webhook-test/jarvis-bot`)

## 4. Test nhanh bằng curl
```bash
curl -s -X POST http://42.112.26.67:5678/webhook/jarvis-bot \
  -H 'Content-Type: application/json' \
  -d '{"text":"lỗi robot 10"}' | jq .
```
Ví dụ khác:
- `{"text":"cảnh báo robot 20"}`  → trả lời nhóm alarm
- `{"text":"robot 10"}`           → nếu mã có ở cả 2 loại → tóm tắt + hỏi lại
- `{"text":"lỗi 10"}`             → hỏi lại "máy nào?" (nếu có nhiều máy)
- `{"text":"kết thúc robot"}`      → thoát chế độ

## Cách hoạt động (khớp yêu cầu)
- **Leader** đọc `registry.json` → chọn máy theo từ khoá; thiếu → hỏi lại.
- **Branch** nạp `tables.json` của máy → tra mã → Gemini soạn: mô tả → nguyên
  nhân → khắc phục.
- Mã có ở cả **error** lẫn **alarm** → tóm tắt cả hai và hỏi lại loại nào.
- Luôn kèm câu nhắc **phân biệt cảnh báo (alarm) và lỗi (error)**.

## Thêm máy mới
Thêm thư mục `machines/<id>/tables/*.csv` + `tables.json`, và một mục trong
`machines/registry.json`. Không cần sửa workflow.
