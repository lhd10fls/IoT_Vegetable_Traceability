#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WiFiClient.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <DHT.h>

#include "config.h"
#include "secrets.h"

DHT dht(DHT_PIN, DHT_TYPE);

unsigned long lastSendTime = 0;

float clampFloat(float value, float minValue, float maxValue) {
  if (value < minValue) return minValue;
  if (value > maxValue) return maxValue;
  return value;
}

float soilRawToPercent(int rawValue) {
  float percent = ((float)(SOIL_DRY_RAW - rawValue) / (float)(SOIL_DRY_RAW - SOIL_WET_RAW)) * 100.0;
  return clampFloat(percent, 0.0, 100.0);
}

void connectWiFi() {
  Serial.print("Connecting to WiFi: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int retry = 0;
  while (WiFi.status() != WL_CONNECTED && retry < 30) {
    delay(500);
    Serial.print(".");
    retry++;
  }

  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected");
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
  } else {
    Serial.println("WiFi connection failed. ESP32 will retry in loop.");
  }
}

bool sendSensorData(float temperature, float airHumidity, float soilMoisture, int lightValue) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("WiFi disconnected. Reconnecting...");
    connectWiFi();
    if (WiFi.status() != WL_CONNECTED) return false;
  }

  StaticJsonDocument<256> doc;
  doc["device_id"] = DEVICE_ID;
  doc["batch_id"] = BATCH_ID;
  doc["temperature"] = temperature;
  doc["air_humidity"] = airHumidity;
  doc["soil_moisture"] = soilMoisture;
  doc["light"] = lightValue;

  String payload;
  serializeJson(doc, payload);

  Serial.print("Sending payload: ");
  Serial.println(payload);

  HTTPClient http;
  int httpResponseCode = -1;

  String url = String(SERVER_URL);
  if (url.startsWith("https://")) {
    WiFiClientSecure secureClient;
    secureClient.setInsecure(); // Demo only. Use certificates in production.
    http.begin(secureClient, url);
    http.addHeader("Content-Type", "application/json");
    httpResponseCode = http.POST(payload);
  } else {
    WiFiClient client;
    http.begin(client, url);
    http.addHeader("Content-Type", "application/json");
    httpResponseCode = http.POST(payload);
  }

  if (httpResponseCode > 0) {
    Serial.print("HTTP Response code: ");
    Serial.println(httpResponseCode);
    Serial.println(http.getString());
  } else {
    Serial.print("HTTP POST failed. Error: ");
    Serial.println(http.errorToString(httpResponseCode));
  }

  http.end();
  return httpResponseCode >= 200 && httpResponseCode < 300;
}

void setup() {
  Serial.begin(115200);
  delay(1000);

  Serial.println("=== Vegetable Traceability IoT Firmware ===");
  Serial.print("Device ID: ");
  Serial.println(DEVICE_ID);
  Serial.print("Batch ID: ");
  Serial.println(BATCH_ID);

  dht.begin();
  pinMode(SOIL_MOISTURE_PIN, INPUT);
  pinMode(LIGHT_SENSOR_PIN, INPUT);

  connectWiFi();
}

void loop() {
  unsigned long now = millis();
  if (now - lastSendTime < SEND_INTERVAL_MS) {
    return;
  }
  lastSendTime = now;

  float temperature = dht.readTemperature();
  float airHumidity = dht.readHumidity();
  int soilRaw = analogRead(SOIL_MOISTURE_PIN);
  int lightValue = analogRead(LIGHT_SENSOR_PIN);
  float soilMoisture = soilRawToPercent(soilRaw);

  if (isnan(temperature) || isnan(airHumidity)) {
    Serial.println("Failed to read from DHT sensor. Check wiring.");
    return;
  }

  Serial.println("--- Sensor reading ---");
  Serial.print("Temperature: ");
  Serial.print(temperature);
  Serial.println(" °C");

  Serial.print("Air humidity: ");
  Serial.print(airHumidity);
  Serial.println(" %");

  Serial.print("Soil raw: ");
  Serial.print(soilRaw);
  Serial.print(" -> ");
  Serial.print(soilMoisture);
  Serial.println(" %");

  Serial.print("Light raw: ");
  Serial.println(lightValue);

  bool ok = sendSensorData(temperature, airHumidity, soilMoisture, lightValue);
  if (ok) {
    Serial.println("Upload success");
  } else {
    Serial.println("Upload failed");
  }
}
