# Hệ thống bot lỗi máy (Leader → Branch) cho Jarvis

Kiến trúc điều phối nhiều máy, dữ liệu lớn:

```
Jarvis (giọng nói) ─ cầu nối trong xiaozhi ─▶ BOT TRƯỞNG NHÓM (leader, n8n)
                                                 │  đọc registry.yaml
                                                 ▼  định tuyến theo máy
                                        ┌────────┴─────────┐
                                   Bot nhánh:          Bot nhánh:
                                   takeout_robot       (máy khác…)
                                   tables/*.csv        tables/*.csv
```

## Thành phần
- **registry.yaml** — danh bạ máy. Leader đọc file nhỏ này để biết có những
  máy nào, từ khoá nhận diện, và thư mục bảng của từng máy.
- **machines/<id>/tables/*.csv** — dữ liệu lỗi/alarm của một máy (một bot nhánh).
- **machines/<id>/README.md** — mô tả máy đó + quy tắc trả lời.

## Luồng xử lý của Leader
1. **Chọn máy**: so khớp câu hỏi với `aliases` trong registry.
   - Không rõ máy nào → hỏi lại "Bạn hỏi về máy nào?".
2. **Xác định loại + mã**: error hay alarm, và số mã.
   - Thiếu mã → hỏi lại số mã.
   - Cùng một số tồn tại ở cả error lẫn alarm → hỏi "cảnh báo hay lỗi?",
     nếu vẫn không rõ thì **tóm tắt tất cả loại** cho số đó.
3. **Gọi bot nhánh**: nạp bảng của máy đã chọn, tra mã, để Gemini soạn câu trả
   lời: **mô tả → nguyên nhân → khắc phục**, kèm câu nhắc **phân biệt
   cảnh báo (alarm) và lỗi (error)**.

## Kích hoạt bằng giọng nói (Jarvis)
- Vào chế độ: nói ví dụ *"lỗi robot 10"* hoặc *"cảnh báo robot 20"*.
- Thoát: nói *"kết thúc robot"*.

## Thêm một máy mới (một bot nhánh mới)
1. Tạo `machines/<ten-may>/tables/` và bỏ các CSV vào (cột: `code,content`).
2. Thêm một mục vào `registry.yaml` (id, name_vi, aliases, tables_dir,
   error_types, alarm_types).
3. Xong — leader tự thấy máy mới, không phải sửa code.

> Dữ liệu quá lớn cho một máy? Gắn thêm vector-search cho riêng nhánh đó;
> leader và các nhánh khác không đổi.
