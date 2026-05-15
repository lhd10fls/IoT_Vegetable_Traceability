from datetime import datetime, date, timedelta
import hashlib
import math
import random

from app.database import SessionLocal, engine, Base
from app.models import Batch, SensorReading, TraceEvent


def make_hash(*values) -> str:
    raw = "|".join(str(v) for v in values)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def get_status(temperature: float, air_humidity: float, soil_moisture: float) -> str:
    if temperature > 35:
        return "WARNING_TEMPERATURE_HIGH"
    if soil_moisture < 30:
        return "WARNING_SOIL_DRY"
    if air_humidity < 40:
        return "WARNING_AIR_HUMIDITY_LOW"
    return "NORMAL"


def seed_batch_veg_001(db):
    batch_id = "VEG-001"

    existing_batch = db.query(Batch).filter(Batch.batch_id == batch_id).first()
    if not existing_batch:
        batch = Batch(
            batch_id=batch_id,
            product_name="Rau cải xanh",
            farm_name="HUST Smart Farm",
            farm_location="Hà Nội",
            planting_date=date(2026, 5, 1),
            harvest_date=date(2026, 5, 15),
        )
        db.add(batch)
        db.commit()

    existing_events = db.query(TraceEvent).filter(TraceEvent.batch_id == batch_id).count()
    if existing_events == 0:
        events = [
            {
                "event_type": "GIEO_TRONG",
                "description": "Gieo trồng rau cải xanh tại khu nhà lưới số 1.",
                "actor": "HUST Smart Farm",
                "location": "Hà Nội",
                "event_time": datetime(2026, 5, 1, 7, 30),
            },
            {
                "event_type": "KIEM_TRA_DAT",
                "description": "Kiểm tra độ ẩm đất và điều kiện sinh trưởng ban đầu.",
                "actor": "Kỹ thuật viên nông trại",
                "location": "HUST Smart Farm",
                "event_time": datetime(2026, 5, 2, 8, 0),
            },
            {
                "event_type": "TUOI_NUOC",
                "description": "Tưới nước định kỳ, độ ẩm đất đạt mức phù hợp.",
                "actor": "Hệ thống tưới",
                "location": "HUST Smart Farm",
                "event_time": datetime(2026, 5, 5, 6, 30),
            },
            {
                "event_type": "CHAM_SOC",
                "description": "Theo dõi sinh trưởng, không phát hiện sâu bệnh bất thường.",
                "actor": "Nhân viên nông trại",
                "location": "HUST Smart Farm",
                "event_time": datetime(2026, 5, 10, 9, 0),
            },
            {
                "event_type": "THU_HOACH",
                "description": "Thu hoạch rau cải xanh, phân loại theo lô VEG-001.",
                "actor": "HUST Smart Farm",
                "location": "Hà Nội",
                "event_time": datetime(2026, 5, 15, 6, 45),
            },
            {
                "event_type": "DONG_GOI",
                "description": "Đóng gói sản phẩm, dán mã QR truy xuất nguồn gốc.",
                "actor": "Bộ phận đóng gói",
                "location": "Kho đóng gói HUST Smart Farm",
                "event_time": datetime(2026, 5, 15, 8, 30),
            },
            {
                "event_type": "VAN_CHUYEN",
                "description": "Vận chuyển lô rau tới cửa hàng, điều kiện bảo quản ổn định.",
                "actor": "Đơn vị vận chuyển GreenExpress",
                "location": "Hà Nội",
                "event_time": datetime(2026, 5, 15, 10, 0),
            },
            {
                "event_type": "NHAP_CUA_HANG",
                "description": "Cửa hàng nhận lô rau, kiểm tra QR và trạng thái sản phẩm.",
                "actor": "Cửa hàng rau sạch",
                "location": "Cầu Giấy, Hà Nội",
                "event_time": datetime(2026, 5, 15, 12, 0),
            },
        ]

        for item in events:
            event_hash = make_hash(
                batch_id,
                item["event_type"],
                item["description"],
                item["actor"],
                item["location"],
                item["event_time"],
            )

            event = TraceEvent(
                batch_id=batch_id,
                event_type=item["event_type"],
                description=item["description"],
                actor=item["actor"],
                location=item["location"],
                event_time=item["event_time"],
                event_hash=event_hash,
            )
            db.add(event)

        db.commit()

    existing_readings = db.query(SensorReading).filter(SensorReading.batch_id == batch_id).count()
    if existing_readings == 0:
        random.seed(42)

        start_time = datetime(2026, 5, 1, 6, 0)
        total_days = 15

        for day in range(total_days):
            for hour in [6, 10, 14, 18, 22]:
                current_time = start_time + timedelta(days=day, hours=hour - 6)

                day_ratio = hour / 24

                temperature = 27 + 5 * math.sin(day_ratio * 2 * math.pi) + random.uniform(-0.8, 0.8)
                air_humidity = 70 - 8 * math.sin(day_ratio * 2 * math.pi) + random.uniform(-2, 2)

                base_soil = 68 - day * 1.5
                if day in [4, 8, 12]:
                    base_soil += 12
                soil_moisture = base_soil + random.uniform(-2, 2)

                if 6 <= hour <= 18:
                    light = 600 + 300 * math.sin(day_ratio * math.pi) + random.uniform(-40, 40)
                else:
                    light = random.uniform(20, 80)

                temperature = round(temperature, 2)
                air_humidity = round(air_humidity, 2)
                soil_moisture = round(max(20, min(90, soil_moisture)), 2)
                light = round(max(0, light), 2)

                status = get_status(temperature, air_humidity, soil_moisture)

                data_hash = make_hash(
                    "ESP32_FARM_01",
                    batch_id,
                    temperature,
                    air_humidity,
                    soil_moisture,
                    light,
                    current_time,
                )

                reading = SensorReading(
                    device_id="ESP32_FARM_01",
                    batch_id=batch_id,
                    temperature=temperature,
                    air_humidity=air_humidity,
                    soil_moisture=soil_moisture,
                    light=light,
                    status=status,
                    data_hash=data_hash,
                    created_at=current_time,
                )

                db.add(reading)

        db.commit()


def seed_all():
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        seed_batch_veg_001(db)
        print("Seed data created successfully.")
    finally:
        db.close()


if __name__ == "__main__":
    seed_all()