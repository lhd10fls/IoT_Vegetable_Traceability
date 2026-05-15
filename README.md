# 🌿 Vegetable Traceability IoT System

Hệ thống **truy xuất nguồn gốc rau sạch** sử dụng IoT (ESP32) + Python FastAPI + SQLite + SHA-256 hash integrity + QR Code.

Người tiêu dùng **quét mã QR** trên bao bì để xem toàn bộ hành trình của lô rau: từ gieo trồng, chăm sóc, thu hoạch, đóng gói đến cửa hàng — cùng với dữ liệu cảm biến môi trường thực tế từ thiết bị IoT ESP32.

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌──────────────────────────────────────────────────────────────────┐
│                        ESP32 (IoT Device)                        │
│  DHT22 (Temp/Humidity) + Soil Moisture + Light Sensor            │
│  → HTTP POST JSON → FastAPI /api/iot/sensor-data                 │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                     FastAPI Backend (Python)                      │
│  • Nhận dữ liệu IoT → tính SHA-256 hash → lưu SQLite            │
│  • Quản lý lô sản phẩm (Batch) và sự kiện truy xuất             │
│  • Tạo QR Code cho từng lô → link /trace/{batch_id}             │
│  • Verify hash để phát hiện dữ liệu bị chỉnh sửa                │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
                    ┌──────────────────┐
                    │  📱 Người dùng   │
                    │  Quét QR → mở   │
                    │  trang truy xuất │
                    └──────────────────┘
```

---

## 📁 Cấu Trúc Thư Mục

```
vegetable-traceability/
├── backend/                    # Python FastAPI server
│   ├── app/
│   │   ├── main.py             # API routes + web pages
│   │   ├── models.py           # SQLAlchemy models (Batch, SensorReading, TraceEvent)
│   │   ├── schemas.py          # Pydantic input schema cho IoT API
│   │   ├── database.py         # SQLite connection
│   │   ├── seed_data.py        # Tạo sẵn 5 lô sản phẩm demo
│   │   ├── services/
│   │   │   ├── hash_service.py     # SHA-256 hash + verify
│   │   │   ├── qr_service.py       # Tạo QR code PNG
│   │   │   └── sensor_service.py   # Phân loại trạng thái cảm biến
│   │   ├── templates/          # Jinja2 HTML templates
│   │   └── static/             # CSS + QR images (generated)
│   ├── regen_qr.py             # Tiện ích tái tạo QR khi đổi URL
│   ├── requirements.txt
│   ├── render.yaml             # Deploy config cho Render.com
│   └── .env.example
├── iot-firmware/               # ESP32 PlatformIO firmware
│   ├── src/main.cpp
│   ├── include/
│   │   ├── config.h            # Pin mapping, device ID, interval
│   │   └── secrets.example.h  # Template WiFi credentials (copy → secrets.h)
│   └── platformio.ini
├── docs/
│   ├── api_design.md
│   └── wiring.md
└── .gitignore
```

---

## ⚡ Khởi Động Nhanh (Local)

### Yêu cầu
- Python 3.10+
- Git

### Bước 1 — Clone & Cài đặt

```bash
git clone https://github.com/lhd10fls/IoT_Vegetable_Traceability.git
cd IoT_Vegetable_Traceability/backend

# Tạo virtual environment
python -m venv .venv

# Kích hoạt (Windows)
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

Lệnh này sẽ tạo:
- ✅ File `traceability.db` (SQLite)
- ✅ **5 lô sản phẩm** với dữ liệu sensor đầy đủ
- ✅ **705 sensor readings** + **42 trace events**
- ✅ **5 QR code** PNG trong `app/static/qr/`

| Lô | Sản phẩm | Địa điểm | Số ngày |
|---|---|---|---|
| VEG-001 | Rau cải xanh | Đông Anh, Hà Nội | 15 ngày |
| VEG-002 | Cà chua bi VietGAP | Đức Trọng, Lâm Đồng | 30 ngày |
| VEG-003 | Dưa leo baby hữu cơ | Củ Chi, TP.HCM | 20 ngày |
| VEG-004 | Cải bắp Đà Lạt sạch | Lạc Dương, Lâm Đồng | 51 ngày |
| VEG-005 | Xà lách thủy canh NFT | Gia Lâm, Hà Nội | 25 ngày |

### Bước 3 — Chạy server

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Mở trình duyệt: **http://localhost:8000**

---

## 📱 Cho Điện Thoại Quét QR

### Cách 1 — Cùng mạng WiFi

Tìm IP máy tính trên WiFi:

```powershell
# Windows
ipconfig
# Tìm dòng "IPv4 Address" của WiFi adapter, ví dụ: 192.168.1.100
```

```bash
# macOS/Linux
hostname -I
```

Tái tạo QR với IP thực:

```bash
python regen_qr.py http://192.168.1.100:8000
```

Điện thoại và máy tính cùng WiFi → quét QR → truy xuất ngay.

### Cách 2 — Ngrok (bất kỳ mạng nào)

Dùng khi demo với giảng viên hoặc người dùng ở mạng khác.

```bash
# Terminal 1: Chạy server
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Terminal 2: Mở tunnel
ngrok http 8000
# → Nhận URL dạng: https://abc123.ngrok-free.dev

# Cập nhật QR với URL ngrok
python regen_qr.py https://abc123.ngrok-free.dev
```

> ⚠️ **Lưu ý**: URL ngrok thay đổi mỗi lần khởi động lại. Sau khi đổi URL, chạy lại `regen_qr.py`.

---

## 🌐 Deploy Lên Render.com (Vĩnh Viễn, Miễn Phí)

1. **Push code lên GitHub** (đã có sẵn `render.yaml`)

2. **Vào [render.com](https://render.com)** → New Web Service → Connect GitHub repo

3. **Render tự đọc `render.yaml`** và deploy

4. **Sau khi deploy xong**, vào Environment Variables trong Render dashboard:
   ```
   APP_BASE_URL = https://ten-app-cua-ban.onrender.com
   ```

5. **Seed dữ liệu** bằng Render Shell:
   ```bash
   python -m app.seed_data
   ```

6. **Cập nhật QR** trên máy local:
   ```bash
   python regen_qr.py https://ten-app-cua-ban.onrender.com
   ```
   Hoặc dùng Render Shell:
   ```bash
   python regen_qr.py https://ten-app-cua-ban.onrender.com
   ```

---

## 🔌 ESP32 Firmware

### Phần cứng cần có

| Linh kiện | Chân ESP32 |
|---|---|
| DHT22 (Temp + Humidity) | GPIO 4 |
| Soil Moisture Sensor (Analog) | GPIO 34 |
| Light Sensor / LDR (Analog) | GPIO 35 |

Xem chi tiết: [docs/wiring.md](docs/wiring.md)

### Cài đặt

1. Cài [VS Code](https://code.visualstudio.com/) + extension [PlatformIO IDE](https://platformio.org/)
2. Mở thư mục `iot-firmware/` trong VS Code
3. Copy file credentials:
   ```bash
   cp iot-firmware/include/secrets.example.h iot-firmware/include/secrets.h
   ```
4. Chỉnh sửa `secrets.h`:
   ```cpp
   #define WIFI_SSID     "Ten_WiFi_Cua_Ban"
   #define WIFI_PASSWORD "Mat_Khau_WiFi"
   #define SERVER_URL    "http://192.168.1.100:8000/api/iot/sensor-data"
   // hoặc dùng URL Render/ngrok
   ```
5. Chỉnh `include/config.h` nếu cần đổi `DEVICE_ID`, `BATCH_ID`, hoặc calibration cảm biến đất
6. Click **Upload** trong PlatformIO để flash lên ESP32
7. Mở **Serial Monitor** (115200 baud) để theo dõi

---

## 🔌 API Endpoints

### Nhận dữ liệu từ ESP32

```http
POST /api/iot/sensor-data
Content-Type: application/json

{
  "device_id": "ESP32_FARM_01",
  "batch_id": "VEG-001",
  "temperature": 27.5,
  "air_humidity": 72.0,
  "soil_moisture": 63.4,
  "light": 820
}
```

Response:
```json
{
  "message": "Sensor data received successfully",
  "reading_id": 76,
  "status": "NORMAL",
  "hash": "a3f8c2...",
  "created_at": "2026-05-15T14:30:00Z"
}
```

### Xem dữ liệu cảm biến (JSON)

```http
GET /api/batches/{batch_id}/sensor-data
```

### Trang truy xuất (dành cho người tiêu dùng quét QR)

```
GET /trace/{batch_id}
```

### Test bằng curl

```bash
curl -X POST http://localhost:8000/api/iot/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_FARM_01","batch_id":"VEG-001","temperature":27.5,"air_humidity":72,"soil_moisture":63,"light":820}'
```

---

## 🔐 Cơ Chế Toàn Vẹn Dữ Liệu (Hash Integrity)

Mỗi bản ghi cảm biến và sự kiện truy xuất đều có **SHA-256 hash**:

```
SHA256(batch_id | device_id | temperature | air_humidity | soil_moisture | light | status | created_at)
```

Trang `/trace/{batch_id}` tự động kiểm tra và hiển thị:
- ✅ **"Dữ liệu hợp lệ"** — nếu tất cả hash khớp
- ⚠️ **"Cảnh báo: dữ liệu có thể đã bị chỉnh sửa"** — nếu có bất kỳ hash nào không khớp

**Demo tamper detection**: Dashboard có nút "Sửa giả lập" để thay đổi nhiệt độ mà không cập nhật hash → trang trace báo ngay lập tức.

---

## 🛠️ Biến Môi Trường

Tạo file `.env` trong thư mục `backend/` (copy từ `.env.example`):

```env
APP_BASE_URL=http://localhost:8000   # URL public để tạo link QR
DATABASE_URL=sqlite:///./traceability.db
```

---

## 🔧 Scripts Tiện Ích

### Tái tạo QR code khi đổi URL

```bash
# Cú pháp
python regen_qr.py <base_url>

# Ví dụ
python regen_qr.py http://192.168.1.100:8000      # local IP
python regen_qr.py https://abc.ngrok-free.dev     # ngrok
python regen_qr.py https://myapp.onrender.com     # Render
```

### Reset và seed lại dữ liệu

```bash
rm traceability.db         # Linux/macOS
del traceability.db        # Windows
python -m app.seed_data
```

---

## 📊 Kịch Bản Demo

1. Mở `http://localhost:8000` → thấy **5 lô sản phẩm** trên dashboard
2. Click vào **VEG-002 (Cà chua bi)** → xem QR code, timeline, sensor data
3. **Quét QR bằng điện thoại** → trang truy xuất mở ra với badge ✅ xác minh
4. Trong dashboard, bấm **"Sửa giả lập"** trên một reading
5. Quét lại QR → badge chuyển thành ⚠️ cảnh báo bị chỉnh sửa
6. ESP32 cắm vào → dữ liệu thực từ cảm biến hiện lên realtime

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

- **Tên**: Lê Hoàng Dương  
- **Trường**: Đại học Bách khoa Hà Nội (HUST)  
- **Môn học**: Mật mã ứng dụng / IoT  
- **Năm**: 2026
