# xiaozhi AI cho board DIYMORE ESP32-S3 2.8" Touch

Project cấu hình để chạy trợ lý AI giọng nói **xiaozhi (小智)**
([78/xiaozhi-esp32](https://github.com/78/xiaozhi-esp32)) trên board
**DIYMORE ESP32-S3 2.8" cảm ứng điện dung**.

> ⚠️ **Việc nạp firmware phải làm trên máy tính của bạn** (nơi cắm board qua
> USB-C). Repo này chỉ chứa cấu hình board + script chuẩn bị mã nguồn.

---

## 1. Phần cứng

| Thành phần | Chi tiết |
|-----------|----------|
| MCU | ESP32-S3 |
| Màn hình | 2.8" IPS 240×320, driver **ILI9341V**, SPI 4 dây |
| Cảm ứng | **FT6336G** điện dung, I2C (địa chỉ `0x38`) |
| Âm thanh | Codec **ES8311** — mic tích hợp + cổng loa |
| Khác | MicroSD, RGB LED, cổng pin, USB Type-C |

Board này cùng thiết kế với dòng **Freenove / LCDwiki ES3C28P** ("Cheap Yellow
Display S3"), nên dùng lại được sơ đồ chân đã kiểm chứng.

---

## 2. Có gì trong project

```
xiaozhi-ai/
├── README.md                         # file này
├── setup.sh                          # clone xiaozhi-esp32 + đăng ký board
└── boards/
    └── diymore-esp32s3-2p8-touch/    # cấu hình board tùy chỉnh
        ├── config.h                  # sơ đồ chân
        ├── config.json               # target build (esp32s3)
        ├── diymore-esp32s3-2p8-touch.cc  # class board (LCD + touch + audio)
        └── README.md
```

---

## 3. Chuẩn bị môi trường (trên máy của bạn)

1. Cài **ESP-IDF v5.4+** (khuyến nghị): làm theo
   [hướng dẫn cài ESP-IDF](https://docs.espressif.com/projects/esp-idf/en/stable/esp32s3/get-started/index.html)
   hoặc dùng extension **ESP-IDF** trong VSCode.
2. Cài `git` và `python3`.
3. Cắm board vào máy bằng cáp USB-C (cổng TYPE-C trên board).

---

## 4. Build firmware

```bash
# Lấy project này về (hoặc copy thư mục xiaozhi-ai/ ra ngoài)
git clone https://github.com/ntvn2022/z-bee-duo.git
cd z-bee-duo/xiaozhi-ai

# Clone xiaozhi-esp32 và tự động đăng ký board DIYMORE
chmod +x setup.sh
./setup.sh

# Build
cd xiaozhi-esp32
. $IDF_PATH/export.sh            # nạp môi trường ESP-IDF
idf.py set-target esp32s3
idf.py menuconfig                # Xiaozhi Assistant → Board Type
                                 #   → "DIYMORE ESP32-S3 2.8-inch ..."
idf.py build
```

---

## 5. Nạp (flash) vào board

```bash
# Thay /dev/ttyACM0 bằng cổng serial thật của board bạn
#   Linux:   /dev/ttyACM0 hoặc /dev/ttyUSB0
#   macOS:   /dev/cu.usbmodem*  hoặc /dev/cu.usbserial-*
#   Windows: COM3, COM4, ...
idf.py -p /dev/ttyACM0 flash monitor
```

Nếu nạp lỗi: giữ nút **BOOT**, nhấn **RESET** rồi thả BOOT để vào chế độ nạp,
sau đó chạy lại lệnh flash.

---

## 6. Cấu hình sau khi nạp

1. Lần đầu bật, board phát WiFi cấu hình (captive portal) → kết nối và chọn
   WiFi nhà bạn.
2. Firmware mặc định kết nối server chính thức **xiaozhi.me** (miễn phí cho
   người dùng cá nhân) — đăng ký tài khoản và thêm thiết bị theo mã hiển thị
   trên màn hình.

---

## 7. Lưu ý về chân (pin)

Sơ đồ chân trong `boards/diymore-esp32s3-2p8-touch/config.h` lấy theo thiết kế
Freenove/ES3C28P. Nếu **màn hình không hiện** hoặc **không có tiếng / không thu
được mic**, hãy đối chiếu lại các chân SPI (LCD), I2C (touch + codec) và I2S
(audio) với sơ đồ chân board của bạn rồi sửa trong `config.h`.

## 8. Cách nhanh (không cần custom board)

Vì phần cứng trùng với Freenove, bạn có thể bỏ qua bước custom board và chọn
thẳng target có sẵn **"Freenove ESP32-S3 Display 2.8-inch LCD"** trong
`idf.py menuconfig`. Custom board ở đây cho bạn một *kênh OTA / định danh riêng*
và chỗ để tinh chỉnh chân nếu cần.
