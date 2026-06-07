# 🌿 Hệ Thống Truy Xuất Nguồn Gốc Rau Sạch — IoT + Custom Proof-of-Work Blockchain

> **Môn học**: Mật Mã và Độ Phức Tạp Thuật Toán — Đại học Bách Khoa Hà Nội (HUST)
>
> **Mô tả**: Hệ thống thu thập dữ liệu môi trường tự động từ cảm biến IoT (ESP32), bảo toàn dữ liệu bằng **mạng lưới Blockchain phân tán tự xây dựng (3 Nodes)** chạy thuật toán đồng thuận **Proof of Work (PoW)** dùng mã băm SHA-256, và tích hợp giao diện **Block Explorer** khám phá chuỗi khối cùng trang truy xuất QR cho người tiêu dùng.

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

## 🔐 Kiến Trúc Blockchain & Thuật Toán Proof of Work (PoW)

Hệ thống hoạt động như một Blockchain thực tế với các thành phần:
- **Cấu trúc Khối (Block)**: Mỗi bản ghi dữ liệu (Lô hàng, Sự kiện, Chỉ số cảm biến) đều được đóng gói thành một giao dịch và đào vào một **Block** riêng biệt.
- **Proof of Work (PoW)**: Khi một khối mới được ghi nhận, server sẽ chạy vòng lặp tìm giá trị **Nonce** sao cho mã băm SHA-256 của khối bắt đầu bằng các chữ số không:
  `SHA-256(index | timestamp | previous_hash | difficulty | data_type | data_id | data_content | nonce)`
  * Độ khó mặc định được cấu hình là **4** (mã băm bắt đầu bằng `0000`), thời gian đào khối trên CPU dao động từ **50ms - 200ms**, tạo ra trải nghiệm khai thác thực tế khi demo.
- **Lưu trữ Phân tán (Replicated Nodes)**: 3 Database hoạt động song song (`node_a.db`, `node_b.db`, `node_c.db`). Khi ghi dữ liệu, khối sẽ được sao chép đến tất cả các node đang hoạt động.
- **Failover (Phòng vệ)**: Nếu một node offline, client tự động chuyển sang đọc/ghi dữ liệu từ node trực tuyến khác.
- **Đồng bộ hóa (Consensus Sync)**: Khi một node online trở lại, quản trị viên có thể nhấn nút "Đồng bộ" để kéo toàn bộ các khối bị thiếu và kiểm tra tính toàn vẹn của chuỗi băm PoW.

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
│   │   │   ├── base.html       # Layout chung (Hiển thị kết nối Node)
│   │   │   ├── dashboard.html  # Điều phối node mạng và danh sách lô hàng
│   │   │   ├── batch_detail.html # Chi tiết và Form đào sự kiện
│   │   │   ├── blockchain.html # [NEW] Trình khám phá Chuỗi khối (Explorer)
│   │   │   └── trace.html      # Trang QR công khai cho khách hàng
│   │   └── static/             # CSS + QR Images (sinh lúc runtime)
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

### BƯỚC 2 — Khởi Tạo Cơ Sở Dữ Liệu & Dữ Liệu Mẫu (Chạy Đào Blockchain)

```bash
# Chạy 1 lần duy nhất để tạo cơ sở dữ liệu cho cả 3 node và tiến hành đào khối mẫu
python -m app.seed_data
```

Kết quả tạo ra:
- ✅ `node_a.db`, `node_b.db`, `node_c.db` — 3 database SQLite độc lập của 3 node.
- ✅ **Hơn 700 Khối (Blocks)** được đào thành công với độ khó PoW (Difficulty = 2) tương ứng cho từng lô hàng, sự kiện và chỉ số cảm biến mẫu.
- ✅ **5 QR code PNG** trong `app/static/qr/` trỏ trực tiếp đến trang truy xuất nguồn gốc.

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
| `GET` | `/` | Dashboard điều khiển mạng lưới và lô hàng |
| `GET` | `/blockchain` | Trình khám phá Chuỗi khối (Block Explorer) |
| `GET` | `/batches/new` | Form tạo lô sản phẩm mới |
| `POST` | `/batches` | Tạo lô mới + đào Genesis Block cho lô hàng |
| `GET` | `/batches/{id}` | Chi tiết lô hàng (hiển thị số khối bảo vệ) |
| `POST` | `/batches/{id}/events` | Thêm sự kiện + đào Block sự kiện |
| `GET` | `/trace/{id}` | Trang QR truy xuất công khai dành cho khách hàng |
| `POST` | `/api/iot/sensor-data` | ESP32 gửi dữ liệu cảm biến + đào Block cảm biến |
| `GET` | `/api/blockchain/blocks` | Raw JSON blockchain blocks |
| `POST` | `/demo/tamper-reading/{id}` | **Demo**: Giả mạo dữ liệu để kiểm thử phát hiện lỗi hash |
| `POST` | `/demo/seed` | **Demo**: Bấm nút nạp lại dữ liệu mẫu từ giao diện web |

---

## 🔐 Cơ Chế Xác Minh Tính Toàn Vẹn

### Cấu Trúc Khối (Block Structure)
Mỗi bản ghi được lưu trữ an toàn trong khối có cấu trúc:
```json
{
  "index": 12,
  "timestamp": "2026-06-07T15:20:00Z",
  "previous_hash": "0000abc789...",
  "nonce": 48210,
  "hash": "0000def123...",
  "difficulty": 4,
  "data_type": "event",
  "data_id": "5",
  "data_content": "{...}"
}
```
* **Lưu ý**: Chỉ khi băm của Block bắt đầu bằng số lượng số `0` bằng đúng `difficulty` thì khối mới được chấp nhận ghi sổ cái.

### Demo Phát Hiện Giả Mạo (Tamper Detection)
1. Mở Dashboard → truy cập Lô hàng `VEG-001`.
2. Bấm nút **"Sửa giả lập"** ở bảng cảm biến.
3. Hệ thống sửa đổi trực tiếp nhiệt độ trong database mà **không** đào lại khối.
4. Mở trang QR `/trace/VEG-001` (hoặc tải lại trang chi tiết), hệ thống tính toán lại hash và so sánh thấy không khớp với Hash của khối tương ứng &rarr; hiển thị cảnh báo đỏ **Cảnh báo: dữ liệu có thể đã bị chỉnh sửa**.

---

## 🛠️ Scripts Tiện Ích

```bash
# Tái tạo QR khi đổi URL server
python regen_qr.py <base_url>
python regen_qr.py https://rausach-hust.loca.lt

# Reset và seed lại từ đầu (xóa 3 database cũ của 3 node)
# Windows (PowerShell):
Remove-Item node_a.db, node_b.db, node_c.db -ErrorAction SilentlyContinue
# macOS / Linux:
rm node_a.db node_b.db node_c.db

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
