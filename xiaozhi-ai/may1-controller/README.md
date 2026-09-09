# Máy 1 — bộ điều khiển 3 output (ESP32-S3 thứ 2)

Con ESP32-S3 thứ 2 nối Wi-Fi, kết nối MQTT tới VPS, và:
- Bật/tắt **3 output** (relay) theo lệnh giọng nói của bot.
- Giữ **lịch hẹn giờ** bật/tắt cho từng output và tự thực hiện.
- Tự **đếm thời gian** mỗi output đang bật/tắt; khi bot hỏi thì trả về.

Bot không nói chuyện trực tiếp với con này — mọi lệnh đi qua **server** (robot_bridge) rồi qua **MQTT**.

## Đấu dây (mặc định, sửa trong `main/may1_config.h`)
| Output | GPIO |
|-------|------|
| OUT1  | 4    |
| OUT2  | 5    |
| OUT3  | 6    |

- `RELAY_ACTIVE_HIGH = 1`: HIGH = bật. Nếu module relay của bạn kích mức thấp (LOW = bật), đổi thành `0`.
- Nối GND của ESP32 với GND module relay; cấp nguồn relay phù hợp (thường 5V).

## Các bước cài đặt
1. **Cài MQTT broker trên VPS** (một lần):
   ```bash
   bash xiaozhi-ai/server/install-mqtt.sh <mqtt_user> <mqtt_pass>
   ```
   Mở port **1883** trên tường lửa/nhà cung cấp VPS.

2. **Báo cho server biết MQTT** + nạp lại bridge:
   ```bash
   bash xiaozhi-ai/server/set-mqtt-key.sh <mqtt_user> <mqtt_pass>
   # hoặc chạy lại speedup-robot.sh (đã cài paho-mqtt sẵn)
   ```

3. **Build firmware con S3 thứ 2** trên GitHub Actions:
   - Actions → **Build May1 Controller** → *Run workflow*.
   - Nhập: Wi-Fi SSID/mật khẩu, MQTT host (IP VPS), port 1883, mqtt user/pass (giống bước 1).
   - Tải artifact `may1-controller-firmware` → `merged-binary.bin` → nạp tại offset **0x0**.
   - *Lưu ý:* thông tin Wi-Fi/MQTT được nhúng vào file bin — đừng chia sẻ file bin công khai.

## Dùng bằng giọng nói
- `"Alexa"` → `"lệnh máy 1"` để vào chế độ điều khiển máy 1.
- Trong chế độ:
  - `"bật đầu ra 1"`, `"tắt đầu ra 2"`, `"mở output 3"`
  - `"bật tất cả"`, `"tắt hết"`
  - `"trạng thái"`, `"đầu ra 1 thế nào"`, `"đầu ra 2 đang bật bao lâu"`
  - `"hẹn giờ đầu ra 1 bật 18 giờ tắt 22 giờ"`, `"hủy hẹn giờ đầu ra 3"`
- `"kết thúc máy 1"` để thoát chế độ.

Hỗ trợ cả tiếng Anh / tiếng Trung theo ngôn ngữ đang chọn trong Settings.
