import math
import os
import random
from datetime import datetime, timedelta

from app.database import Base, SessionLocals, engines, init_db, get_active_node, sync_node_data
from app.models import Batch, SensorReading, TraceEvent
from app.services.hash_service import make_event_hash, make_sensor_hash
from app.services.qr_service import generate_qr
from app.services.sensor_service import calculate_status


def to_iso(dt) -> str:
    """Chuyển datetime → ISO string, hoặc giữ nguyên nếu đã là string."""
    if isinstance(dt, datetime):
        return dt.isoformat(timespec="seconds")
    return str(dt)


def get_base_url() -> str:
    return os.getenv("APP_BASE_URL", "http://localhost:8000").rstrip("/")


# ─── CẤU HÌNH 5 LÔ SẢN PHẨM ──────────────────────────────────────────────────
BATCHES = [
    {
        "batch_id": "VEG-001",
        "product_name": "Rau cải xanh",
        "farm_name": "HUST Smart Farm",
        "farm_location": "Đông Anh, Hà Nội",
        "planting_date": "2026-05-01",
        "harvest_date": "2026-05-15",
        "device_id": "ESP32_FARM_01",
        "total_days": 15,
        "start_date": datetime(2026, 5, 1, 6, 0),
        "temp_base": 27, "temp_amplitude": 5,
        "humidity_base": 70, "humidity_amplitude": 8,
        "soil_base": 68, "soil_decay": 1.5,
        "watering_days": [4, 8, 12], "watering_boost": 12,
        "light_base": 600, "light_range": 300,
        "events": [
            {"event_type": "GIEO_TRONG",    "description": "Gieo trồng rau cải xanh tại khu nhà lưới số 1.",            "actor": "HUST Smart Farm",             "location": "Đông Anh, Hà Nội",          "offset_days": 0,  "offset_hours": 7},
            {"event_type": "KIEM_TRA_DAT",  "description": "Kiểm tra độ ẩm đất và điều kiện sinh trưởng ban đầu.",      "actor": "Kỹ thuật viên nông trại",      "location": "HUST Smart Farm",           "offset_days": 1,  "offset_hours": 8},
            {"event_type": "TUOI_NUOC",     "description": "Tưới nước định kỳ, độ ẩm đất đạt mức phù hợp.",            "actor": "Hệ thống tưới tự động",        "location": "HUST Smart Farm",           "offset_days": 5,  "offset_hours": 6},
            {"event_type": "CHAM_SOC",      "description": "Theo dõi sinh trưởng, không phát hiện sâu bệnh bất thường.","actor": "Nhân viên nông trại",           "location": "HUST Smart Farm",           "offset_days": 10, "offset_hours": 9},
            {"event_type": "THU_HOACH",     "description": "Thu hoạch rau cải xanh, phân loại theo lô VEG-001.",        "actor": "HUST Smart Farm",             "location": "Đông Anh, Hà Nội",          "offset_days": 14, "offset_hours": 6},
            {"event_type": "DONG_GOI",      "description": "Đóng gói sản phẩm, dán mã QR truy xuất nguồn gốc.",         "actor": "Bộ phận đóng gói",             "location": "Kho đóng gói HUST",         "offset_days": 14, "offset_hours": 8},
            {"event_type": "VAN_CHUYEN",    "description": "Vận chuyển lô rau tới cửa hàng, điều kiện bảo quản ổn định.","actor": "GreenExpress Logistics",       "location": "Hà Nội",                    "offset_days": 14, "offset_hours": 10},
            {"event_type": "NHAP_CUA_HANG", "description": "Cửa hàng nhận lô rau, kiểm tra QR và trạng thái sản phẩm.", "actor": "Cửa hàng rau sạch Cầu Giấy",  "location": "Cầu Giấy, Hà Nội",         "offset_days": 14, "offset_hours": 12},
        ],
    },
    {
        "batch_id": "VEG-002",
        "product_name": "Cà chua bi VietGAP",
        "farm_name": "Nông trại xanh Đà Lạt",
        "farm_location": "Đức Trọng, Lâm Đồng",
        "planting_date": "2026-04-10",
        "harvest_date": "2026-05-10",
        "device_id": "ESP32_FARM_02",
        "total_days": 30,
        "start_date": datetime(2026, 4, 10, 6, 0),
        "temp_base": 20, "temp_amplitude": 6,
        "humidity_base": 75, "humidity_amplitude": 6,
        "soil_base": 72, "soil_decay": 1.2,
        "watering_days": [3, 7, 11, 15, 19, 23, 27], "watering_boost": 15,
        "light_base": 700, "light_range": 250,
        "events": [
            {"event_type": "GIEO_TRONG",    "description": "Gieo hạt cà chua bi trong nhà kính tại Đức Trọng.",          "actor": "Nông trại xanh Đà Lạt",       "location": "Đức Trọng, Lâm Đồng",      "offset_days": 0,  "offset_hours": 7},
            {"event_type": "KIEM_TRA_DAT",  "description": "Kiểm tra pH đất 6.2-6.8, bón phân hữu cơ cân bằng.",        "actor": "Kỹ sư nông nghiệp",           "location": "Nông trại xanh Đà Lạt",    "offset_days": 2,  "offset_hours": 8},
            {"event_type": "TUOI_NUOC",     "description": "Hệ thống nhỏ giọt tưới tự động, tiết kiệm 40% nước.",        "actor": "Hệ thống tưới nhỏ giọt",      "location": "Nông trại xanh Đà Lạt",    "offset_days": 7,  "offset_hours": 6},
            {"event_type": "KIEM_TRA_BENH", "description": "Phát hiện rệp muội — xử lý bằng thuốc sinh học.",            "actor": "Kỹ thuật viên IPM",            "location": "Nông trại xanh Đà Lạt",    "offset_days": 15, "offset_hours": 9},
            {"event_type": "CHAM_SOC",      "description": "Cắt tỉa nhánh, tăng thông khí, hỗ trợ đậu quả đều.",        "actor": "Nhân viên nông trại",          "location": "Nông trại xanh Đà Lạt",    "offset_days": 20, "offset_hours": 8},
            {"event_type": "THU_HOACH",     "description": "Thu hoạch cà chua chín đỏ 85%, đạt chuẩn VietGAP.",          "actor": "Nông trại xanh Đà Lạt",       "location": "Đức Trọng, Lâm Đồng",      "offset_days": 29, "offset_hours": 6},
            {"event_type": "DONG_GOI",      "description": "Rửa sạch, phân loại kích cỡ, đóng hộp 500g, dán QR.",       "actor": "Bộ phận đóng gói",             "location": "Kho lạnh Lâm Đồng",        "offset_days": 29, "offset_hours": 9},
            {"event_type": "VAN_CHUYEN",    "description": "Xe lạnh vận chuyển Đà Lạt → TP.HCM, nhiệt độ 8-12°C.",     "actor": "FreshShip Logistics",          "location": "QL20, Lâm Đồng → TP.HCM", "offset_days": 29, "offset_hours": 14},
            {"event_type": "NHAP_CUA_HANG", "description": "Co.opmart nhận hàng, kiểm tra QR và cảm quan sản phẩm.",     "actor": "Co.opmart Quận 7",             "location": "Quận 7, TP.HCM",           "offset_days": 30, "offset_hours": 8},
        ],
    },
    {
        "batch_id": "VEG-003",
        "product_name": "Dưa leo baby hữu cơ",
        "farm_name": "HTX Rau sạch Củ Chi",
        "farm_location": "Củ Chi, TP.HCM",
        "planting_date": "2026-04-25",
        "harvest_date": "2026-05-15",
        "device_id": "ESP32_FARM_03",
        "total_days": 20,
        "start_date": datetime(2026, 4, 25, 6, 0),
        "temp_base": 32, "temp_amplitude": 4,
        "humidity_base": 78, "humidity_amplitude": 5,
        "soil_base": 75, "soil_decay": 2.0,
        "watering_days": [2, 5, 8, 11, 14, 17], "watering_boost": 18,
        "light_base": 750, "light_range": 200,
        "events": [
            {"event_type": "GIEO_TRONG",    "description": "Gieo dưa leo baby theo phương pháp hữu cơ, không hóa chất.",  "actor": "HTX Rau sạch Củ Chi",         "location": "Củ Chi, TP.HCM",           "offset_days": 0,  "offset_hours": 6},
            {"event_type": "TUOI_NUOC",     "description": "Tưới phun sương buổi sáng và chiều mát, 2 lần/ngày.",          "actor": "Hệ thống tưới phun sương",    "location": "HTX Rau sạch Củ Chi",      "offset_days": 3,  "offset_hours": 6},
            {"event_type": "KIEM_TRA_BENH", "description": "Kiểm tra bọ trĩ và nhện đỏ — không phát hiện bất thường.",    "actor": "Kỹ thuật viên nông nghiệp",   "location": "HTX Rau sạch Củ Chi",      "offset_days": 8,  "offset_hours": 9},
            {"event_type": "CHAM_SOC",      "description": "Cắm cọc leo, định hướng dây leo, tăng năng suất thu hoạch.",   "actor": "Nhân viên HTX",               "location": "HTX Rau sạch Củ Chi",      "offset_days": 12, "offset_hours": 7},
            {"event_type": "THU_HOACH",     "description": "Thu hoạch dưa leo baby khi dài 8-10cm, vỏ xanh bóng.",         "actor": "HTX Rau sạch Củ Chi",         "location": "Củ Chi, TP.HCM",           "offset_days": 19, "offset_hours": 5},
            {"event_type": "DONG_GOI",      "description": "Đóng gói túi zip 300g, in nhãn hữu cơ, dán mã QR.",            "actor": "Bộ phận đóng gói HTX",        "location": "Kho HTX Củ Chi",           "offset_days": 19, "offset_hours": 8},
            {"event_type": "VAN_CHUYEN",    "description": "Xe lạnh vận chuyển đến siêu thị, nhiệt độ duy trì 10°C.",      "actor": "CoolChain Express",            "location": "TP.HCM",                   "offset_days": 19, "offset_hours": 11},
            {"event_type": "NHAP_CUA_HANG", "description": "Winmart nhận hàng, xác minh QR, bày bán ngay trong ngày.",     "actor": "Winmart Bình Thạnh",          "location": "Bình Thạnh, TP.HCM",       "offset_days": 20, "offset_hours": 7},
        ],
    },
    {
        "batch_id": "VEG-004",
        "product_name": "Cải bắp Đà Lạt sạch",
        "farm_name": "Langbiang Farm",
        "farm_location": "Lạc Dương, Lâm Đồng",
        "planting_date": "2026-03-20",
        "harvest_date": "2026-05-10",
        "device_id": "ESP32_FARM_04",
        "total_days": 51,
        "start_date": datetime(2026, 3, 20, 6, 0),
        "temp_base": 17, "temp_amplitude": 7,
        "humidity_base": 80, "humidity_amplitude": 7,
        "soil_base": 70, "soil_decay": 0.8,
        "watering_days": [5, 10, 15, 20, 25, 30, 35, 40, 45, 50], "watering_boost": 12,
        "light_base": 550, "light_range": 300,
        "events": [
            {"event_type": "GIEO_TRONG",         "description": "Gieo cây con cải bắp từ hạt, ươm 2 tuần trước khi trồng.",          "actor": "Langbiang Farm",              "location": "Lạc Dương, Lâm Đồng",      "offset_days": 0,  "offset_hours": 7},
            {"event_type": "KIEM_TRA_DAT",       "description": "Phân tích đất: pH 6.0-6.5, bổ sung vôi nông nghiệp.",               "actor": "Kỹ sư đất Langbiang",         "location": "Langbiang Farm",            "offset_days": 3,  "offset_hours": 8},
            {"event_type": "TUOI_NUOC",          "description": "Tưới rãnh 2 lần/tuần, kiểm soát độ ẩm 65-75%.",                     "actor": "Hệ thống tưới rãnh",          "location": "Langbiang Farm",            "offset_days": 10, "offset_hours": 6},
            {"event_type": "BON_PHAN",           "description": "Bón phân hữu cơ vi sinh theo quy trình VietGAP.",                   "actor": "Kỹ thuật viên canh tác",      "location": "Langbiang Farm",            "offset_days": 20, "offset_hours": 8},
            {"event_type": "KIEM_TRA_BENH",      "description": "Phun thuốc sinh học ngăn nấm mốc do thời tiết ẩm cao.",             "actor": "Đội IPM Langbiang",           "location": "Langbiang Farm",            "offset_days": 35, "offset_hours": 9},
            {"event_type": "THU_HOACH",          "description": "Thu hoạch bắp cải 1.2-1.5kg/bắp, đạt chuẩn xuất bán.",             "actor": "Langbiang Farm",              "location": "Lạc Dương, Lâm Đồng",      "offset_days": 50, "offset_hours": 6},
            {"event_type": "DONG_GOI",           "description": "Bó lưới bảo vệ, dán mã QR, đóng thùng carton.",                    "actor": "Bộ phận đóng gói Langbiang",  "location": "Kho lạnh Langbiang",       "offset_days": 50, "offset_hours": 10},
            {"event_type": "VAN_CHUYEN",         "description": "Xe tải lạnh vận chuyển lên Hà Nội, 1500km, 24h.",                  "actor": "VietFresh Transport",         "location": "QL1, Lâm Đồng → Hà Nội",  "offset_days": 50, "offset_hours": 14},
            {"event_type": "NHAP_CUA_HANG",      "description": "BigC nhận hàng, kiểm tra chất lượng và QR, lên kệ.",               "actor": "BigC Royal City Hà Nội",      "location": "Thanh Xuân, Hà Nội",       "offset_days": 51, "offset_hours": 10},
        ],
    },
    {
        "batch_id": "VEG-005",
        "product_name": "Xà lách thủy canh NFT",
        "farm_name": "GreenHouse Hà Nội",
        "farm_location": "Gia Lâm, Hà Nội",
        "planting_date": "2026-04-20",
        "harvest_date": "2026-05-15",
        "device_id": "ESP32_FARM_05",
        "total_days": 25,
        "start_date": datetime(2026, 4, 20, 6, 0),
        # Thủy canh: nhiệt độ rất ổn định, độ ẩm cao, không cần tưới thêm
        "temp_base": 25, "temp_amplitude": 2,
        "humidity_base": 85, "humidity_amplitude": 3,
        "soil_base": 92, "soil_decay": 0.0,
        "watering_days": [], "watering_boost": 0,
        "light_base": 420, "light_range": 100,
        "events": [
            {"event_type": "GIEO_TRONG",          "description": "Gieo hạt xà lách vào giá thể rockwool, đặt vào hệ NFT.",       "actor": "GreenHouse Hà Nội",           "location": "Gia Lâm, Hà Nội",          "offset_days": 0,  "offset_hours": 8},
            {"event_type": "KIEM_TRA_DD",         "description": "Kiểm tra EC dung dịch dinh dưỡng: 1.2 mS/cm, pH 5.8-6.2.",   "actor": "Kỹ sư thủy canh",             "location": "GreenHouse Hà Nội",         "offset_days": 3,  "offset_hours": 9},
            {"event_type": "DIEU_CHINH_DD",       "description": "Bổ sung dung dịch dinh dưỡng A+B, EC điều chỉnh lên 1.5.",   "actor": "Hệ thống tự động GreenHouse", "location": "GreenHouse Hà Nội",         "offset_days": 10, "offset_hours": 8},
            {"event_type": "KIEM_TRA_CHAT_LUONG", "description": "Lá xanh đồng đều, không vàng lá, sinh trưởng đúng tiến độ.", "actor": "QC GreenHouse",               "location": "GreenHouse Hà Nội",         "offset_days": 18, "offset_hours": 10},
            {"event_type": "THU_HOACH",           "description": "Thu hoạch xà lách 150g/bụi, cắt cả cây, giữ rễ tươi.",       "actor": "GreenHouse Hà Nội",           "location": "Gia Lâm, Hà Nội",          "offset_days": 24, "offset_hours": 6},
            {"event_type": "DONG_GOI",            "description": "Đóng hộp nhựa thoáng khí 200g, dán QR truy xuất nguồn gốc.", "actor": "Bộ phận đóng gói GreenHouse", "location": "Gia Lâm, Hà Nội",          "offset_days": 24, "offset_hours": 8},
            {"event_type": "VAN_CHUYEN",          "description": "Giao hàng trong ngày bằng xe điện lạnh nội thành Hà Nội.",   "actor": "EcoDelivery Hà Nội",          "location": "Hà Nội",                   "offset_days": 24, "offset_hours": 10},
            {"event_type": "NHAP_CUA_HANG",       "description": "Organica nhận hàng, xác minh QR, bày bán ngay trong ngày.",  "actor": "Organica Tây Hồ",             "location": "Tây Hồ, Hà Nội",           "offset_days": 25, "offset_hours": 7},
        ],
    },
]


# ─── HÀM SEED CHUNG ────────────────────────────────────────────────────────────
def seed_batch(db, cfg: dict, base_url: str) -> None:
    batch_id = cfg["batch_id"]

    # ── 1. Tạo Batch ──────────────────────────────────────────────────────────
    existing = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not existing:
        qr_path = generate_qr(batch_id=batch_id, base_url=base_url)
        batch = Batch(
            batch_id=batch_id,
            product_name=cfg["product_name"],
            farm_name=cfg["farm_name"],
            farm_location=cfg["farm_location"],
            planting_date=cfg["planting_date"],
            harvest_date=cfg["harvest_date"],
            qr_path=qr_path,
            created_at=to_iso(cfg["start_date"]),
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)

        # Đào khối cho Batch
        import json
        from app.database import mine_block
        block = mine_block(
            db_session=db,
            data_type="batch",
            data_id=batch.batch_id,
            data_content=json.dumps({
                "batch_id": batch.batch_id,
                "product_name": batch.product_name,
                "farm_name": batch.farm_name,
                "farm_location": batch.farm_location,
                "planting_date": batch.planting_date,
                "harvest_date": batch.harvest_date
            }),
            difficulty=2  # Độ khó thấp khi gieo dữ liệu để chạy nhanh
        )
        batch.block_index = block.index
        db.commit()
        print(f"  ✅ Batch {batch_id} — QR: {qr_path}")
    else:
        print(f"  ⏭  Batch {batch_id} đã tồn tại, bỏ qua.")

    # ── 2. Trace Events ───────────────────────────────────────────────────────
    if db.query(TraceEvent).filter(TraceEvent.batch_id == batch_id).count() == 0:
        for item in cfg["events"]:
            event_time = cfg["start_date"] + timedelta(
                days=item["offset_days"], hours=item["offset_hours"]
            )
            event_time_str = to_iso(event_time)
            
            # Retrieve the last event for this batch to get previous_hash
            last_event = (
                db.query(TraceEvent)
                .filter(TraceEvent.batch_id == batch_id)
                .order_by(TraceEvent.id.desc())
                .first()
            )
            previous_hash = last_event.event_hash if last_event else "0" * 64

            payload = {
                "batch_id":    batch_id,
                "event_type":  item["event_type"],
                "description": item["description"],
                "actor":       item["actor"],
                "location":    item["location"],
                "event_time":  event_time_str,
                "previous_hash": previous_hash,
            }
            event = TraceEvent(**payload, event_hash=make_event_hash(payload))
            db.add(event)
            db.commit()
            db.refresh(event)

            # Đào khối cho Event
            import json
            from app.database import mine_block
            block = mine_block(
                db_session=db,
                data_type="event",
                data_id=str(event.id),
                data_content=json.dumps({
                    "batch_id": event.batch_id,
                    "event_type": event.event_type,
                    "description": event.description,
                    "actor": event.actor,
                    "location": event.location,
                    "event_time": event.event_time,
                    "previous_hash": event.previous_hash,
                    "event_hash": event.event_hash
                }),
                difficulty=2
            )
            event.block_index = block.index
            db.commit()
        print(f"  ✅ {len(cfg['events'])} trace events cho {batch_id}")


    # ── 3. Sensor Readings ────────────────────────────────────────────────────
    if db.query(SensorReading).filter(SensorReading.batch_id == batch_id).count() == 0:
        random.seed(hash(batch_id) % (2**32))  # seed khác nhau mỗi lô

        readings_added = 0
        for day in range(cfg["total_days"]):
            for hour in [6, 10, 14, 18, 22]:
                current_time = cfg["start_date"] + timedelta(days=day, hours=hour - 6)
                day_ratio = hour / 24

                temperature = round(
                    cfg["temp_base"]
                    + cfg["temp_amplitude"] * math.sin(day_ratio * 2 * math.pi)
                    + random.uniform(-0.8, 0.8),
                    2,
                )
                air_humidity = round(
                    cfg["humidity_base"]
                    - cfg["humidity_amplitude"] * math.sin(day_ratio * 2 * math.pi)
                    + random.uniform(-2, 2),
                    2,
                )

                base_soil = cfg["soil_base"] - cfg["soil_decay"] * day
                if day in cfg["watering_days"]:
                    base_soil += cfg["watering_boost"]
                soil_moisture = round(max(20, min(95, base_soil + random.uniform(-2, 2))), 2)

                if 6 <= hour <= 18:
                    light = round(
                        cfg["light_base"]
                        + cfg["light_range"] * math.sin(day_ratio * math.pi)
                        + random.uniform(-40, 40),
                        2,
                    )
                else:
                    light = round(random.uniform(10, 60), 2)
                light = round(max(0, light), 2)

                status = calculate_status(temperature, air_humidity, soil_moisture)
                created_at_str = to_iso(current_time)

                payload = {
                    "batch_id":     batch_id,
                    "device_id":    cfg["device_id"],
                    "temperature":  temperature,
                    "air_humidity": air_humidity,
                    "soil_moisture":soil_moisture,
                    "light":        light,
                    "status":       status,
                    "created_at":   created_at_str,
                }
                reading = SensorReading(**payload, data_hash=make_sensor_hash(payload))
                db.add(reading)
                db.commit()
                db.refresh(reading)

                # Đào khối cho SensorReading
                import json
                from app.database import mine_block
                block = mine_block(
                    db_session=db,
                    data_type="sensor",
                    data_id=str(reading.id),
                    data_content=json.dumps({
                        "batch_id": reading.batch_id,
                        "device_id": reading.device_id,
                        "temperature": reading.temperature,
                        "air_humidity": reading.air_humidity,
                        "soil_moisture": reading.soil_moisture,
                        "light": reading.light,
                        "status": reading.status,
                        "created_at": reading.created_at,
                        "data_hash": reading.data_hash
                    }),
                    difficulty=2
                )
                reading.block_index = block.index
                db.commit()
                readings_added += 1

        print(f"  ✅ {readings_added} sensor readings cho {batch_id}")


# ─── ENTRY POINT ───────────────────────────────────────────────────────────────
def seed_all():
    os.makedirs("app/static/qr", exist_ok=True)
    init_db()

    base_url = get_base_url()
    print(f"\n{'='*55}")
    print(f"  SEEDING {len(BATCHES)} lô sản phẩm | base_url={base_url}")
    print(f"{'='*55}\n")

    # Xác định node đang hoạt động (thường là node_a)
    active_node = get_active_node() or "node_a"
    print(f"--- Gieo dữ liệu cho Node chính: {active_node} ---")
    
    db = SessionLocals[active_node]()
    try:
        for cfg in BATCHES:
            print(f"[{cfg['batch_id']}] {cfg['product_name']}")
            seed_batch(db, cfg, base_url)
            print()
        print(f"✅ Gieo dữ liệu hoàn tất cho Node chính ({active_node})!")
    finally:
        db.close()

    # Đồng bộ dữ liệu sang các node khác
    print("\n--- Đồng bộ dữ liệu sang các node phụ ---")
    for node_name in SessionLocals.keys():
        if node_name == active_node:
            continue
        print(f"Đang đồng bộ {node_name}...")
        res = sync_node_data(node_name)
        print(f"Kết quả {node_name}: {res['status']} - {res.get('message', '')}")


if __name__ == "__main__":
    seed_all()