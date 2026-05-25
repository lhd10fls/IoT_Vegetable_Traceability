# 🌿 Hệ Thống Truy Xuất Nguồn Gốc Rau Sạch IoT

Hệ thống **truy xuất nguồn gốc thực phẩm** sử dụng IoT (ESP32) + Python FastAPI + SQLite + cơ chế toàn vẹn dữ liệu SHA-256 + QR Code.

> **Định hướng thiết kế**: Hệ thống áp dụng nguyên lý từ kiến trúc blockchain (hash chain, tamper detection, audit trail) vào nền tảng tập trung SQLite, phù hợp với môi trường triển khai thực tế tại các nông trại vừa và nhỏ — nơi không đủ hạ tầng chạy mạng blockchain phân tán.

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌──────────────────────────────────────────────────────────────────┐
│                     ESP32 (IoT Device)                           │
│   DHT22 (Nhiệt độ / Độ ẩm KK)                                   │
│   Cảm biến độ ẩm đất (Analog)                                    │
│   Cảm biến ánh sáng (Analog)                                     │
│   → HTTP POST JSON mỗi 10 giây                                   │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
┌──────────────────────────────────────────────────────────────────┐
│                   FastAPI Backend (Python)                        │
│                                                                  │
│  Nhận dữ liệu IoT                                                │
│       ↓                                                          │
│  Tính SHA-256 hash của toàn bộ payload                           │
│       ↓                                                          │
│  Lưu data + hash vào SQLite                                      │
│       ↓                                                          │
│  Khi verify: recompute hash, so sánh với hash đã lưu            │
│  → Phát hiện nếu data bị sửa mà hash không được cập nhật        │
│                                                                  │
│  Tạo QR Code → link /trace/{batch_id}                           │
└──────────────────────────┬───────────────────────────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   📱 Người dùng     │
                │   Quét QR           │
                │   Xem nguồn gốc     │
                │   Xem trạng thái    │
                │   xác minh dữ liệu  │
                └─────────────────────┘
```

---

## 📐 Giới Hạn Kỹ Thuật (Trung Thực)

| Đặc điểm | Hệ thống này | Blockchain thật |
|---|---|---|
| **Lưu trữ** | Tập trung (1 file SQLite) | Phân tán (nhiều node) |
| **Toàn vẹn dữ liệu** | SHA-256 hash (phát hiện sửa nửa vời) | Bất biến hoàn toàn |
| **Ai kiểm soát** | Người sở hữu server | Phi tập trung |
| **Tốc độ** | Rất nhanh (ms) | Chậm hơn (vài giây) |
| **Chi phí** | Miễn phí | Gas fee (Ethereum) |
| **Phù hợp với** | Demo, MVP, trang trại nhỏ | Chuỗi cung ứng lớn, nhiều bên |

> ⚠️ **Lưu ý**: Cơ chế SHA-256 phát hiện được việc sửa dữ liệu **mà không cập nhật hash**. Nếu người có quyền truy cập DB sửa cả data lẫn hash đồng thời thì hệ thống không phát hiện được — đây là giới hạn của lưu trữ tập trung.

---

## 📁 Cấu Trúc Thư Mục

```
vegetable-traceability/
├── backend/                    # Hệ thống chính — FastAPI + SQLite
│   ├── app/
│   │   ├── main.py             # API routes + web pages
│   │   ├── models.py           # SQLAlchemy models
│   │   ├── schemas.py          # Pydantic schema cho IoT API
│   │   ├── database.py         # SQLite connection
│   │   ├── seed_data.py        # Tạo sẵn 5 lô sản phẩm demo
│   │   ├── services/
│   │   │   ├── hash_service.py     # SHA-256 hash + verify
│   │   │   ├── qr_service.py       # Tạo QR code PNG
│   │   │   └── sensor_service.py   # Phân loại trạng thái cảm biến
│   │   ├── templates/          # Jinja2 HTML templates
│   │   └── static/             # CSS + QR images (generated at runtime)
│   ├── regen_qr.py             # Tiện ích tái tạo QR khi đổi URL
│   ├── requirements.txt
│   ├── render.yaml             # Deploy config cho Render.com
│   └── .env.example
├── iot-firmware/               # ESP32 PlatformIO firmware
│   ├── src/main.cpp
│   ├── include/
│   │   ├── config.h            # Pin mapping, device ID, interval
│   │   └── secrets.example.h  # Template WiFi + Server URL
│   └── platformio.ini
└── docs/
    ├── api_design.md
    └── wiring.md
```

---

## ⚡ Khởi Động Nhanh

### Yêu cầu
- Python 3.10+

### Bước 1 — Clone & Cài đặt

```bash
git clone https://github.com/lhd10fls/IoT_Vegetable_Traceability.git
cd IoT_Vegetable_Traceability/backend

# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows PowerShell — lần đầu cần chạy lệnh này)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.venv\Scripts\activate

# Kích hoạt (macOS/Linux)
source .venv/bin/activate

# Cài thư viện
pip install -r requirements.txt
```

### Bước 2 — Tạo dữ liệu demo

```bash
python -m app.seed_data
```

Tạo ra:
- ✅ `traceability.db` — SQLite database
- ✅ **5 lô sản phẩm** với dữ liệu cảm biến mô phỏng thực tế
- ✅ **705 sensor readings** + **42 trace events** — tất cả có SHA-256 hash
- ✅ **5 QR code PNG**

| Lô | Sản phẩm | Địa điểm | Số ngày |
|---|---|---|---|
| VEG-001 | Rau cải xanh | Đông Anh, Hà Nội | 15 |
| VEG-002 | Cà chua bi VietGAP | Đức Trọng, Lâm Đồng | 30 |
| VEG-003 | Dưa leo baby hữu cơ | Củ Chi, TP.HCM | 20 |
| VEG-004 | Cải bắp Đà Lạt sạch | Lạc Dương, Lâm Đồng | 51 |
| VEG-005 | Xà lách thủy canh NFT | Gia Lâm, Hà Nội | 25 |

### Bước 3 — Chạy server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở trình duyệt: **http://localhost:8000**

---

## 📱 Để Điện Thoại Quét QR Được

### Cách 1 — Cùng mạng WiFi

```bash
# Tìm IP WiFi (Windows)
ipconfig
# → Tìm dòng IPv4, ví dụ: 192.168.1.100

# Cập nhật QR
python regen_qr.py http://192.168.1.100:8000
```

### Cách 2 — Ngrok (bất kỳ mạng nào, dùng khi demo)

```bash
# Terminal 1: Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Mở ngrok tunnel
ngrok http 8000
# → Nhận URL: https://xxxx.ngrok-free.dev

# Terminal 3: Cập nhật QR
python regen_qr.py https://xxxx.ngrok-free.dev
```

> ⚠️ URL ngrok thay đổi mỗi lần khởi động lại. Chạy lại `regen_qr.py` sau khi đổi URL.

---

## 🔌 ESP32 Firmware

### Sơ đồ kết nối

| Cảm biến | Chân ESP32 |
|---|---|
| DHT22 (Data) | GPIO 4 |
| Soil Moisture (AO) | GPIO 34 |
| Light Sensor (AO) | GPIO 35 |

Chi tiết: [docs/wiring.md](docs/wiring.md)

### Cài đặt

```bash
# 1. Mở thư mục iot-firmware/ bằng VS Code + PlatformIO
# 2. Copy file credentials
cp iot-firmware/include/secrets.example.h iot-firmware/include/secrets.h

# 3. Sửa secrets.h
#define WIFI_SSID     "Ten_WiFi"
#define WIFI_PASSWORD "Mat_Khau"
#define SERVER_URL    "http://192.168.1.100:8000/api/iot/sensor-data"

# 4. Upload lên ESP32 qua PlatformIO
```

---

## 🔌 API Endpoints

### Nhận dữ liệu từ ESP32

```http
POST /api/iot/sensor-data
Content-Type: application/json

{
  "device_id": "ESP32_FARM_01",
  "batch_id":  "VEG-001",
  "temperature":   27.5,
  "air_humidity":  72.0,
  "soil_moisture": 63.4,
  "light":         820
}
```

Response:
```json
{
  "message":    "Sensor data received successfully",
  "reading_id": 76,
  "status":     "NORMAL",
  "hash":       "a3f8c2d1...",
  "created_at": "2026-05-15T14:30:00Z"
}
```

### Các endpoint khác

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Dashboard quản lý |
| `GET` | `/trace/{batch_id}` | Trang truy xuất công khai (người dùng quét QR) |
| `GET` | `/api/batches/{batch_id}/sensor-data` | Raw sensor data JSON |
| `POST` | `/batches` | Tạo lô mới |
| `POST` | `/batches/{batch_id}/events` | Thêm sự kiện truy xuất |

### Test bằng curl

```bash
curl -X POST http://localhost:8000/api/iot/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_FARM_01","batch_id":"VEG-001","temperature":27.5,"air_humidity":72,"soil_moisture":63,"light":820}'
```

---

## 🔐 Cơ Chế Toàn Vẹn Dữ Liệu

Mỗi sensor reading và trace event được gắn một **SHA-256 hash** tại thời điểm tạo:

```
hash = SHA256(batch_id | device_id | temperature | air_humidity |
              soil_moisture | light | status | created_at)
```

**Khi verify**: tính lại hash từ data hiện tại, so sánh với hash đã lưu:
- ✅ Khớp → dữ liệu nguyên vẹn
- ⚠️ Không khớp → dữ liệu đã bị chỉnh sửa (mà không cập nhật hash)

**Demo tamper detection**: Dashboard có nút *"Sửa giả lập"* — thay đổi `temperature + 10` mà không cập nhật hash → trang `/trace` hiển thị cảnh báo ngay.

---

## 🛠️ Scripts Tiện Ích

```bash
# Tái tạo QR khi đổi URL
python regen_qr.py <base_url>
python regen_qr.py http://192.168.1.100:8000
python regen_qr.py https://xxxx.ngrok-free.dev

# Reset và seed lại từ đầu
del traceability.db          # Windows
rm traceability.db           # macOS/Linux
python -m app.seed_data
```

---

## 🌐 Deploy Lên Render.com (Miễn Phí)

1. Push code lên GitHub
2. Vào [render.com](https://render.com) → New Web Service → Connect repo
3. Render tự đọc `render.yaml`, deploy tự động
4. Vào Environment Variables, thêm:
   ```
   APP_BASE_URL = https://ten-app.onrender.com
   ```
5. Trong Render Shell chạy: `python -m app.seed_data`
6. Cập nhật QR: `python regen_qr.py https://ten-app.onrender.com`

---

## 📊 Kịch Bản Demo

1. Mở dashboard → thấy 5 lô sản phẩm, mỗi lô có QR
2. Click vào VEG-002 (Cà chua) → xem timeline 9 sự kiện, 150 readings
3. Quét QR bằng điện thoại → trang truy xuất mở ngay, badge **✅ Dữ liệu hợp lệ**
4. Bấm *"Sửa giả lập"* trên một reading
5. Quét lại QR → badge chuyển **⚠️ Cảnh báo: dữ liệu có thể đã bị chỉnh sửa**
6. ESP32 cắm vào → dữ liệu cảm biến thực hiện lên realtime

---

## 📦 Dependencies

```
fastapi==0.115.6
uvicorn[standard]==0.34.0
sqlalchemy==2.0.36
jinja2==3.1.4
python-multipart==0.0.20
qrcode[pil]==8.0
pillow==11.0.0
```

---

## 👤 Tác Giả

- **Sinh viên**: Lê Hoàng Dương
- **Trường**: Đại học Bách khoa Hà Nội (HUST)
- **Năm học**: 2025–2026
