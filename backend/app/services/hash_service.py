import hashlib
from typing import Dict, Any


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def make_sensor_hash(payload: Dict[str, Any]) -> str:
    """Create a deterministic hash for one IoT sensor reading."""
    raw = "|".join(
        [
            str(payload["batch_id"]),
            str(payload["device_id"]),
            str(payload["temperature"]),
            str(payload["air_humidity"]),
            str(payload["soil_moisture"]),
            str(payload["light"]),
            str(payload["status"]),
            str(payload["created_at"]),
        ]
    )
    return sha256_text(raw)


def verify_sensor_reading(reading) -> bool:
    payload = {
        "batch_id": reading.batch_id,
        "device_id": reading.device_id,
        "temperature": reading.temperature,
        "air_humidity": reading.air_humidity,
        "soil_moisture": reading.soil_moisture,
        "light": reading.light,
        "status": reading.status,
        "created_at": reading.created_at,
    }
    return make_sensor_hash(payload) == reading.data_hash


def make_event_hash(payload: Dict[str, Any]) -> str:
    raw = "|".join(
        [
            str(payload["batch_id"]),
            str(payload["event_type"]),
            str(payload["description"]),
            str(payload["actor"]),
            str(payload["location"]),
            str(payload["event_time"]),
        ]
    )
    return sha256_text(raw)


def verify_trace_event(event) -> bool:
    payload = {
        "batch_id": event.batch_id,
        "event_type": event.event_type,
        "description": event.description,
        "actor": event.actor,
        "location": event.location,
        "event_time": event.event_time,
    }
    return make_event_hash(payload) == event.event_hash
