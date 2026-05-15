# API Design

## POST /api/iot/sensor-data

ESP32 gửi dữ liệu cảm biến.

Request:

```json
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
  "reading_id": 1,
  "batch_id": "VEG-001",
  "status": "NORMAL",
  "hash": "...",
  "created_at": "2026-05-15T...Z"
}
```

## GET /trace/{batch_id}

Trang public cho người tiêu dùng quét QR.

## GET /api/batches/{batch_id}/sensor-data

Lấy dữ liệu cảm biến dạng JSON.
