from sqlalchemy import Column, Float, Integer, String, Text
from app.database import Base


class Batch(Base):
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), unique=True, index=True, nullable=False)
    product_name = Column(String(255), nullable=False)
    farm_name = Column(String(255), nullable=False)
    farm_location = Column(String(255), nullable=False)
    planting_date = Column(String(32), nullable=False)
    harvest_date = Column(String(32), nullable=False)
    qr_path = Column(String(255), nullable=True)
    created_at = Column(String(64), nullable=False)


class SensorReading(Base):
    __tablename__ = "sensor_readings"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    device_id = Column(String(128), nullable=False)
    temperature = Column(Float, nullable=False)
    air_humidity = Column(Float, nullable=False)
    soil_moisture = Column(Float, nullable=False)
    light = Column(Float, nullable=False)
    status = Column(String(64), nullable=False)
    data_hash = Column(String(128), nullable=False)
    created_at = Column(String(64), nullable=False)


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    actor = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    event_time = Column(String(64), nullable=False)
    event_hash = Column(String(128), nullable=False)
