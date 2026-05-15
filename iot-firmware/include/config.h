#ifndef CONFIG_H
#define CONFIG_H

#define DEVICE_ID "ESP32_FARM_01"
#define BATCH_ID "VEG-001"

#define DHT_PIN 4
#define DHT_TYPE DHT22

#define SOIL_MOISTURE_PIN 34
#define LIGHT_SENSOR_PIN 35

#define SEND_INTERVAL_MS 10000

// Soil sensor calibration values. You should calibrate these for your sensor.
// Typical ESP32 ADC range: 0 - 4095.
#define SOIL_DRY_RAW 4095
#define SOIL_WET_RAW 1300

#endif
