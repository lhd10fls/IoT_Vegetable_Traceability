# Vegetable Traceability IoT MVP

Project demo truy xuất nguồn gốc rau sạch:

- ESP32 đọc cảm biến DHT22, độ ẩm đất, ánh sáng.
- ESP32 gửi dữ liệu JSON về Python FastAPI.
- Backend lưu dữ liệu vào SQLite.
- Backend tạo QR code cho từng lô rau.
- Người dùng quét QR để mở trang `/trace/{batch_id}`.
- Hệ thống tạo SHA-256 hash để kiểm tra dữ liệu có bị chỉnh sửa hay không.

## 1. Cấu trúc thư mục

```text
vegetable-traceability/
├── backend/          # Python FastAPI web + API + QR + hash
├── iot-firmware/     # ESP32 PlatformIO firmware
└── docs/             # Tài liệu mô tả demo
```

## 2. Chạy backend local

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn app.main:app --reload
```

Mở trình duyệt:

```text
http://localhost:8000
```

Bấm `Tạo demo VEG-001` hoặc tạo lô rau mới.

## 3. Test API IoT bằng curl

```bash
curl -X POST http://localhost:8000/api/iot/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_FARM_01","batch_id":"VEG-001","temperature":27.5,"air_humidity":72,"soil_moisture":63,"light":820}'
```

## 4. Chạy ESP32 firmware

1. Mở thư mục `iot-firmware` bằng VS Code + PlatformIO.
2. Copy `include/secrets.example.h` thành `include/secrets.h`.
3. Sửa WiFi và `SERVER_URL`.
4. Upload code lên ESP32.

Ví dụ `SERVER_URL` khi chạy local trong cùng mạng WiFi:

```cpp
#define SERVER_URL "http://192.168.1.10:8000/api/iot/sensor-data"
```

Không dùng `localhost` trong ESP32, vì `localhost` là chính ESP32, không phải laptop.

## 5. Quét QR

QR code chứa đường link:

```text
http://your-domain/trace/VEG-001
```

Khi deploy thật hoặc dùng ngrok, đặt biến môi trường:

```bash
APP_BASE_URL=https://your-domain.com
```

Sau đó tạo lại batch để QR sinh ra link public đúng.

## 6. Deploy nhanh

### Cách 1: Ngrok cho demo lớp học

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
ngrok http 8000
```

Đặt `APP_BASE_URL` theo link ngrok, tạo lại QR.

### Cách 2: Render

Thư mục `backend` đã có `render.yaml`.

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

## 7. Kịch bản demo

1. Tạo lô rau `VEG-001`.
2. ESP32 gửi dữ liệu cảm biến.
3. Dashboard hiển thị dữ liệu IoT.
4. In QR hoặc mở ảnh QR.
5. Người dùng quét QR bằng camera điện thoại.
6. Trang truy xuất hiển thị nguồn gốc, timeline, dữ liệu môi trường.
7. Bấm `Sửa giả lập` trong dashboard để thay đổi dữ liệu mà không cập nhật hash.
8. Trang truy xuất báo dữ liệu có thể đã bị chỉnh sửa.
