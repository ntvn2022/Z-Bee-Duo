# xiaozhi AI Server (self-hosted) trên VPS — dùng Gemini

Cài **xiaozhi-esp32-server** ([xinnan-tech/xiaozhi-esp32-server](https://github.com/xinnan-tech/xiaozhi-esp32-server))
lên VPS của bạn, dùng **Google Gemini** làm mô hình ngôn ngữ (LLM). ASR dùng
**FunASR** (chạy local), TTS dùng **EdgeTTS** (miễn phí) — chỉ Gemini cần API key.

> Bản cài này là **Docker gọn nhẹ (server-only)**: chỉ có `xiaozhi-server`, cấu
> hình bằng 1 file `data/.config.yaml`. Nhẹ hơn bản đầy đủ (không cần MySQL/Redis
> và web console).

---

## 1. Yêu cầu VPS
- Ubuntu/Debian, quyền **root**
- **RAM ≥ 2GB** (khuyến nghị 4GB vì ASR FunASR nạp model ~900MB)
- **Ổ đĩa trống ≥ 5GB**
- Mở cổng **8000** (WebSocket) và **8003** (HTTP/OTA)

## 2. Lấy Gemini API key
Vào <https://aistudio.google.com/apikey> → tạo key (miễn phí).

## 3. Cài đặt
SSH vào VPS rồi chạy:

```bash
# Tải script (hoặc copy file install-xiaozhi-server.sh lên VPS)
curl -fsSL https://raw.githubusercontent.com/ntvn2022/z-bee-duo/claude/esp32-s3-touch-screen-wwelt1/xiaozhi-ai/server/install-xiaozhi-server.sh -o install-xiaozhi-server.sh

# Chạy (thay YOUR_KEY bằng Gemini API key của bạn)
GEMINI_API_KEY=YOUR_KEY bash install-xiaozhi-server.sh
```

Script sẽ tự: cài Docker → tạo thư mục `/opt/xiaozhi-server` → tải model ASR →
ghi `docker-compose.yml` + `data/.config.yaml` (đã cắm Gemini) → khởi động.

## 4. Kiểm tra
```bash
docker logs -f xiaozhi-esp32-server      # xem log khởi động
```
Khi thấy dòng in ra địa chỉ WebSocket `ws://<IP>:8000/xiaozhi/v1/` là chạy OK.

Địa chỉ dịch vụ:
- **WebSocket** (thiết bị kết nối): `ws://<IP_VPS>:8000/xiaozhi/v1/`
- **OTA/HTTP**: `http://<IP_VPS>:8003/xiaozhi/ota/`

## 5. Đổi/xem cấu hình
Sửa file `/opt/xiaozhi-server/data/.config.yaml`, ví dụ đổi model Gemini:

```yaml
selected_module:
  LLM: GeminiLLM
LLM:
  GeminiLLM:
    type: gemini
    api_key: "AIza...your key..."
    model_name: "gemini-2.0-flash"   # hoặc gemini-2.5-flash, gemini-1.5-pro, ...
```
Sau khi sửa: `docker compose -f /opt/xiaozhi-server/docker-compose.yml restart`

## 6. Trỏ thiết bị ESP32-S3 về server này
Firmware dựng sẵn mặc định nối `xiaozhi.me`. Để dùng **server riêng của bạn**,
thiết bị phải trỏ địa chỉ **OTA** về VPS:

```
http://<IP_VPS>:8003/xiaozhi/ota/
```

Cách đặt địa chỉ này tùy firmware:
- Khi **build từ nguồn**: đặt trong `menuconfig` → *Xiaozhi Assistant → OTA URL*
  (hoặc sửa mặc định trong code) trước khi flash.
- Một số bản firmware cho phép nhập địa chỉ OTA trong trang cấu hình WiFi
  (`http://192.168.4.1`) sau khi flash.

## 7. ⚠️ Bảo mật sau khi cài
- **Đổi mật khẩu root** ngay: `passwd`
- Nên tắt đăng nhập mật khẩu, chuyển sang **SSH key**.
- Chỉ mở cổng cần thiết (22, 8000, 8003); cân nhắc đặt sau reverse proxy + HTTPS
  nếu chạy công khai lâu dài.

---

Tài liệu triển khai gốc:
<https://github.com/xinnan-tech/xiaozhi-esp32-server/blob/main/docs/Deployment.md>
