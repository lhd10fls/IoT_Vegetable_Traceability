from pydantic import BaseModel, Field


class SensorDataIn(BaseModel):
    device_id: str = Field(..., examples=["ESP32_FARM_01"])
    batch_id: str = Field(..., examples=["VEG-001"])
    temperature: float = Field(..., examples=[27.5])
    air_humidity: float = Field(..., examples=[72.0])
    soil_moisture: float = Field(..., examples=[63.4])
    light: float = Field(..., examples=[820])
