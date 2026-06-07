# pyrefly: ignore [missing-import]
from sqlalchemy import Column, Float, Integer, String, Text
# pyrefly: ignore [missing-import]
from app.database import Base

class Block(Base):
    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    index = Column(Integer, unique=True, index=True, nullable=False)
    timestamp = Column(String(64), nullable=False)
    previous_hash = Column(String(128), nullable=False)
    nonce = Column(Integer, nullable=False)
    hash = Column(String(128), nullable=False)
    difficulty = Column(Integer, nullable=False)
    data_type = Column(String(64), nullable=False)  # "batch", "event", "sensor"
    data_id = Column(String(64), nullable=False)    # ID or batch_id of the record
    data_content = Column(Text, nullable=False)     # JSON content of the transaction


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
    block_index = Column(Integer, nullable=True)     # Link to block index securing this batch


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
    block_index = Column(Integer, nullable=True)     # Link to block index securing this reading


class TraceEvent(Base):
    __tablename__ = "trace_events"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(String(64), index=True, nullable=False)
    event_type = Column(String(64), nullable=False)
    description = Column(Text, nullable=False)
    actor = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    event_time = Column(String(64), nullable=False)
    previous_hash = Column(String(128), nullable=False)
    event_hash = Column(String(128), nullable=False)
    block_index = Column(Integer, nullable=True)     # Link to block index securing this event


