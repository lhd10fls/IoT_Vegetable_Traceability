# 🌿 Hệ Thống Truy Xuất Nguồn Gốc Rau Sạch — IoT + Blockchain

> **Môn học**: Mật Mã và Độ Phức Tạp Thuật Toán — Đại học Bách Khoa Hà Nội (HUST)
>
> **Mô tả**: Hệ thống thu thập dữ liệu môi trường tự động từ cảm biến IoT (ESP32), bảo toàn tính toàn vẹn dữ liệu bằng chuỗi liên kết băm SHA-256 (Hash Chain) theo triết lý Blockchain, và cho phép người tiêu dùng tra cứu nguồn gốc sản phẩm bằng cách quét mã QR.

---

## 📐 Kiến Trúc Hệ Thống

```
┌─────────────────────────────┐
│     ESP32 (IoT Device)      │
│  DHT22 · Soil · Light       │
│  → HTTP POST JSON / 10 giây │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│    FastAPI Backend (Python) │
│                             │
│  Nhận dữ liệu IoT           │
│       ↓                     │
│  Tính SHA-256 Hash          │
│       ↓                     │
│  Lưu SQLite + Hash Chain    │
│       ↓                     │
│  Xác minh chuỗi liên kết   │
│       ↓                     │
│  Sinh mã QR → /trace/{id}  │
└────────────┬────────────────┘
             │
             ▼
      ┌──────────────┐
      │ 📱 Người dùng│
      │   Quét QR    │
      │  Xem nguồn   │
      │  gốc & Hash  │
      └──────────────┘
```

---

## 🔐 Cơ Chế Bảo Toàn Dữ Liệu (Hash Chain)

Mỗi sự kiện truy xuất (TraceEvent) được liên kết mật mã học với sự kiện trước đó:

```
GENESIS   →  GIEO_TRONG  →  THU_HOACH  →  VAN_CHUYEN  →  ...
Hash: 000000  →  a3f2b91c  →  7e84c2d1  →  5b91f3a2   →  ...
```

- **Event Hash** = SHA-256(batch_id | event_type | ... | **previous_hash**)
- Nếu ai sửa dữ liệu của 1 sự kiện → hash bị vỡ → toàn bộ chuỗi phía sau mất hiệu lực

---

## 📁 Cấu Trúc Thư Mục

```
vegetable-traceability/
├── backend/                    # FastAPI Backend
│   ├── app/
│   │   ├── main.py             # API Routes + Web Dashboard
│   │   ├── models.py           # SQLAlchemy ORM Models
│   │   ├── schemas.py          # Pydantic Schema (IoT Input)
│   │   ├── database.py         # SQLite Connection
│   │   ├── seed_data.py        # Khởi tạo 5 lô mẫu + dữ liệu cảm biến
│   │   ├── services/
│   │   │   ├── hash_service.py    # SHA-256 Hash Chain
│   │   │   ├── qr_service.py      # Sinh mã QR PNG
│   │   │   └── sensor_service.py  # Phân loại trạng thái cảm biến
│   │   ├── templates/          # Jinja2 HTML Templates
│   │   └── static/             # CSS + QR Images (sinh lúc runtime)
│   ├── regen_qr.py             # Cập nhật lại QR khi đổi URL
│   ├── requirements.txt        # Thư viện Python
│   ├── render.yaml             # Deploy config cho Render.com
│   └── .env.example
├── iot-firmware/               # ESP32 PlatformIO Firmware
│   ├── src/main.cpp            # Firmware chính (C++ / Arduino)
│   ├── include/
│   │   ├── config.h            # Pin mapping + cấu hình
│   │   └── secrets.example.h  # Mẫu cấu hình WiFi (copy → secrets.h)
│   └── platformio.ini
└── docs/
    ├── api_design.md
    └── wiring.md
```

---

## ⚡ Chạy Nhanh (Trên Máy Tính)

### Yêu Cầu Cài Đặt
| Phần mềm | Phiên bản | Ghi chú |
|---|---|---|
| Python | 3.10+ | Tải tại [python.org](https://python.org), tick "Add to PATH" |
| Node.js | 18+ | Tải tại [nodejs.org](https://nodejs.org) — cần để chạy `localtunnel` |

---

### BƯỚC 1 — Clone & Cài Đặt Môi Trường

```bash
# 1. Clone repo về máy
git clone https://github.com/lhd10fls/IoT_Vegetable_Traceability.git
cd IoT_Vegetable_Traceability/backend

# 2. Tạo môi trường ảo Python
python -m venv .venv

# 3. Kích hoạt môi trường ảo
# Windows (CMD):
.venv\Scripts\activate
# Windows (PowerShell — chạy lần đầu nếu bị báo lỗi execution policy):
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# 4. Cài thư viện
pip install -r requirements.txt
```

---

### BƯỚC 2 — Khởi Tạo Cơ Sở Dữ Liệu & Dữ Liệu Mẫu

```bash
# Chạy 1 lần duy nhất để tạo traceability.db + 5 lô mẫu + QR codes
python -m app.seed_data
```

Kết quả tạo ra:
- ✅ `traceability.db` — SQLite database
- ✅ **5 lô sản phẩm** với dữ liệu cảm biến mô phỏng thực tế (sóng sine theo chu kỳ ngày/đêm)
- ✅ **705 sensor readings** đều có SHA-256 hash
- ✅ **42 trace events** được liên kết thành chuỗi Hash Chain
- ✅ **5 QR code PNG** trong `app/static/qr/`

---

### BƯỚC 3 — Chạy Server

> ⚠️ **Lưu ý trên Windows**: Không dùng tham số `--reload` nếu đường dẫn project có ký tự tiếng Việt hoặc dấu cách (gây lỗi WatchFiles không đọc được đường dẫn).

```bash
# Không dùng --reload khi đường dẫn có tiếng Việt
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Hoặc nếu chưa kích hoạt .venv:
.venv\Scripts\uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Mở trình duyệt: **http://localhost:8000**

---

## 📱 Quét QR Bằng Điện Thoại (Ở Bất Kỳ Mạng Nào)

Để điện thoại (dùng 3G/4G hoặc WiFi khác) quét được mã QR và truy cập trang web, bạn cần tạo một đường dẫn internet công khai bằng **Localtunnel** (miễn phí, không cần đăng ký tài khoản).

### Mở thêm một cửa sổ Terminal MỚI:

```bash
# Tạo đường dẫn internet (thay 'rausach-hust' bằng tên tùy ý viết liền không dấu)
npx localtunnel --port 8000 --subdomain rausach-hust
```

Terminal sẽ hiển thị:
```
your url is: https://rausach-hust.loca.lt
```

### Mở thêm một cửa sổ Terminal thứ 3:

```bash
# Di chuyển vào thư mục backend (Windows CMD)
cd /d "đường-dẫn-tới-dự-án/backend"

# Cập nhật tất cả QR codes trỏ về URL mới (dán link thực tế bạn nhận được vào đây)
python regen_qr.py https://rausach-hust.loca.lt
```

### Kết quả:
- 🖥️ Truy cập Dashboard trên máy tính: `http://localhost:8000`
- 📱 Điện thoại quét QR trên Dashboard → mở thẳng trang truy xuất nguồn gốc!

---

## 🌐 Deploy Lên Internet Vĩnh Viễn (Render.com — Miễn Phí)

Để hệ thống hoạt động 24/7 mà không cần máy tính luôn bật, deploy lên Render.com:

1. Push code lên GitHub
2. Đăng nhập [render.com](https://render.com) → **New Web Service** → Kết nối repo GitHub
3. Render tự đọc `render.yaml` và deploy tự động
4. Vào **Environment Variables** trên Render Dashboard, thêm:
   ```
   APP_BASE_URL = https://ten-app-cua-ban.onrender.com
   ```
5. Vào **Shell** của Render chạy: `python -m app.seed_data`
6. Không cần chạy `regen_qr.py` thêm vì URL đã cố định

---

## 🔌 Kết Nối Thiết Bị IoT (ESP32)

### Sơ Đồ Kết Nối Cảm Biến

| Cảm biến | Chân ESP32 | Ghi chú |
|---|---|---|
| DHT22 — Data | GPIO 4 | Nhiệt độ & Độ ẩm không khí |
| Soil Moisture — AO | GPIO 34 | Cần hiệu chỉnh `SOIL_DRY_RAW` / `SOIL_WET_RAW` trong `config.h` |
| LDR Light — AO | GPIO 35 | Cường độ ánh sáng |

### Nạp Firmware

```bash
# 1. Mở thư mục iot-firmware/ bằng VS Code + PlatformIO extension
# 2. Tạo file credentials từ template
cp iot-firmware/include/secrets.example.h iot-firmware/include/secrets.h

# 3. Sửa secrets.h với thông tin WiFi và địa chỉ server
```

Nội dung file `secrets.h`:
```cpp
#define WIFI_SSID     "Ten_WiFi_Cua_Ban"
#define WIFI_PASSWORD "Mat_Khau_WiFi"

// Địa chỉ server — dùng link Localtunnel / Render.com:
#define SERVER_URL    "https://rausach-hust.loca.lt/api/iot/sensor-data"
```

```bash
# 4. Upload lên ESP32 qua PlatformIO (nhấn nút mũi tên → Upload)
```

---

## 🧪 Giả Lập IoT (Không Cần Phần Cứng)

Dùng `curl` để giả lập gói tin dữ liệu cảm biến từ ESP32:

```bash
# Windows PowerShell
Invoke-WebRequest -Method POST http://localhost:8000/api/iot/sensor-data `
  -ContentType "application/json" `
  -Body '{"device_id":"ESP32_DEMO","batch_id":"VEG-001","temperature":27.5,"air_humidity":72.0,"soil_moisture":63.4,"light":820}'

# macOS / Linux / Git Bash
curl -X POST http://localhost:8000/api/iot/sensor-data \
  -H "Content-Type: application/json" \
  -d '{"device_id":"ESP32_DEMO","batch_id":"VEG-001","temperature":27.5,"air_humidity":72.0,"soil_moisture":63.4,"light":820}'
```

---

## 📊 API Endpoints

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/` | Dashboard quản lý |
| `GET` | `/batches/new` | Form tạo lô sản phẩm mới |
| `POST` | `/batches` | Tạo lô mới + sinh QR |
| `GET` | `/batches/{id}` | Chi tiết lô: cảm biến + Hash Chain |
| `POST` | `/batches/{id}/events` | Thêm sự kiện truy xuất |
| `GET` | `/trace/{id}` | Trang công khai người dùng quét QR |
| `POST` | `/api/iot/sensor-data` | ESP32 gửi dữ liệu cảm biến |
| `GET` | `/api/batches/{id}/sensor-data` | Raw sensor data JSON |
| `POST` | `/demo/tamper-reading/{id}` | **Demo**: Giả mạo dữ liệu để test phát hiện |

---

## 🔐 Cơ Chế Xác Minh Tính Toàn Vẹn

### Sensor Reading Hash
```
hash = SHA256(batch_id | device_id | temperature | air_humidity |
              soil_moisture | light | status | created_at)
```

### Trace Event Hash Chain
```
event_hash = SHA256(batch_id | event_type | description |
                    actor | location | event_time | previous_hash)
```

- Sự kiện đầu tiên (Genesis): `previous_hash = "000...000"` (64 ký tự 0)
- Mỗi sự kiện tiếp theo: `previous_hash = event_hash của sự kiện trước đó`
- **Kết quả**: Sửa 1 sự kiện → hash vỡ → toàn chuỗi phía sau mất hiệu lực

### Demo Phát Hiện Giả Mạo (Tamper Detection)
1. Mở Dashboard → vào chi tiết lô VEG-001
2. Nhấn nút **"Sửa giả lập"** trên một bản ghi cảm biến bất kỳ
3. Hệ thống tăng nhiệt độ +10°C mà **không** cập nhật hash
4. Trang `/trace/VEG-001` ngay lập tức hiển thị banner đỏ: ⚠️ **Dữ liệu có thể đã bị chỉnh sửa**

---

## 🛠️ Scripts Tiện Ích

```bash
# Tái tạo QR khi đổi URL server
python regen_qr.py <base_url>
python regen_qr.py http://192.168.1.10:8000
python regen_qr.py https://rausach-hust.loca.lt
python regen_qr.py https://ten-app.onrender.com

# Reset và seed lại từ đầu (xóa database cũ)
# Windows:
del traceability.db
# macOS/Linux:
rm traceability.db

python -m app.seed_data
```

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

## ❓ Xử Lý Sự Cố Thường Gặp

| Triệu chứng | Nguyên nhân | Cách khắc phục |
|---|---|---|
| `ModuleNotFoundError` | Chưa kích hoạt `.venv` hoặc chạy sai thư mục | Chắc chắn đang ở thư mục `backend/` và đã chạy `.venv\Scripts\activate` |
| Server tự tắt ngay | Dùng `--reload` với đường dẫn tiếng Việt | Bỏ `--reload` khi khởi động uvicorn |
| Điện thoại không quét được | QR trỏ về `localhost` | Chạy localtunnel + `python regen_qr.py <url-mới>` |
| `WinError 10013` (Port in use) | Cổng 8000 bị chiếm bởi tiến trình cũ | Đóng cửa sổ Terminal cũ hoặc dùng cổng khác: `--port 8001` |
| `npx: command not found` | Chưa cài Node.js | Tải Node.js tại [nodejs.org](https://nodejs.org) (bản LTS) |

---

## 👤 Tác Giả

- **Sinh viên**: Lê Hoàng Dương
- **Trường**: Đại học Bách Khoa Hà Nội (HUST) — Khoa Toán Tin
- **Môn học**: Mật Mã và Độ Phức Tạp Thuật Toán — Năm học 2025–2026
