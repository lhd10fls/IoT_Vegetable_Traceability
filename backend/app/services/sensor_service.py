def calculate_status(temperature: float, air_humidity: float, soil_moisture: float) -> str:
    """Simple demo rules for clean vegetable monitoring."""
    if temperature > 35:
        return "WARNING_TEMPERATURE_HIGH"
    if temperature < 10:
        return "WARNING_TEMPERATURE_LOW"
    if soil_moisture < 30:
        return "WARNING_SOIL_DRY"
    if air_humidity < 40:
        return "WARNING_AIR_DRY"
    return "NORMAL"


def status_label(status: str) -> str:
    labels = {
        "NORMAL": "Bình thường",
        "WARNING_TEMPERATURE_HIGH": "Cảnh báo: nhiệt độ cao",
        "WARNING_TEMPERATURE_LOW": "Cảnh báo: nhiệt độ thấp",
        "WARNING_SOIL_DRY": "Cảnh báo: đất khô",
        "WARNING_AIR_DRY": "Cảnh báo: độ ẩm không khí thấp",
    }
    return labels.get(status, status)
