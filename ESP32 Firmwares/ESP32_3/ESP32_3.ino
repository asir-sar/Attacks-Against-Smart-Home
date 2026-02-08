/*
 * FIRMWARE FOR: ESP32-3 (Actuator Hub) - VULNERABLE EDITION
 * Project: Attacks Against Smart Home
 * Components: LED (GPIO 16), Fan (GPIO 15 via Relay)
 */

#include <WiFi.h>
#include <PubSubClient.h>
// --- VULNERABILITY ADDITION: Libraries for downloading firmware ---
#include <HTTPClient.h>
#include <HTTPUpdate.h> 

// --- START: CONFIGURE YOUR SETTINGS ---
const char* WIFI_SSID = "Smart_Home";
const char* WIFI_PASS = "123456789";
const char* MQTT_BROKER_IP = "192.168.88.10"; // Your RPi 5's Static IP
const int   MQTT_PORT = 1883;
const char* MQTT_CLIENT_ID = "esp32-actuator-hub"; 
// --- END: CONFIGURE YOUR SETTINGS ---

// --- Pin Definitions ---
const int LED_PIN = 16;
const int FAN_PIN = 15; // !! This pin controls a LOW-LEVEL TRIGGER RELAY !!

// --- MQTT Topics ---
const char* LED_TOPIC_SET = "home/livingroom/led/set";
const char* FAN_TOPIC_SET = "home/livingroom/fan/set";
// --- VULNERABILITY ADDITION: The topic triggering the update ---
const char* UPDATE_TOPIC  = "home/update/url";

// --- Global Variables ---
WiFiClient espClient;
PubSubClient client(espClient);
long lastReconnectAttempt = 0;

// Actuator States
String ledState = "OFF";
unsigned long lastLedToggle = 0;

// --- VULNERABILITY ADDITION: Helper function to perform the update ---
// This downloads code from a URL and installs it.
void performOTA(String url) {
  Serial.println("-----------------------------------");
  Serial.println("⚠ CRITICAL: STARTING FIRMWARE UPDATE ⚠");
  Serial.println("Downloading from: " + url);
  
  WiFiClient client;
  // The update function returns ONLY if it fails. 
  // If successful, the ESP32 restarts automatically.
  t_httpUpdate_return ret = httpUpdate.update(client, url);

  switch (ret) {
    case HTTP_UPDATE_FAILED:
      Serial.printf("HTTP_UPDATE_FAILED Error (%d): %s\n", httpUpdate.getLastError(), httpUpdate.getLastErrorString().c_str());
      break;
    case HTTP_UPDATE_NO_UPDATES:
      Serial.println("HTTP_UPDATE_NO_UPDATES");
      break;
    case HTTP_UPDATE_OK:
      Serial.println("HTTP_UPDATE_OK");
      break;
  }
  Serial.println("-----------------------------------");
}

// --- MQTT Callback Function ---
void callback(char* topic, byte* payload, unsigned int length) {
  Serial.print("Message arrived [");
  Serial.print(topic);
  Serial.print("] ");

  String payloadStr = "";
  for (int i = 0; i < length; i++) {
    payloadStr += (char)payload[i];
  }
  Serial.println(payloadStr);

  // --- VULNERABILITY ADDITION: Check for update command ---
  if (String(topic) == UPDATE_TOPIC) {
    payloadStr.trim();
    performOTA(payloadStr);// Immediately try to download and install
  }

  // --- LED Logic ---
  if (String(topic) == LED_TOPIC_SET) {
    ledState = payloadStr;
    if (ledState == "ON") {
      digitalWrite(LED_PIN, HIGH);
    } else if (ledState == "OFF") {
      digitalWrite(LED_PIN, LOW);
    }
  }

  // --- Fan Logic (Low-Level Trigger) ---
  if (String(topic) == FAN_TOPIC_SET) {
    if (payloadStr == "ON") {
      digitalWrite(FAN_PIN, HIGH); // LOW = Relay ON
    } else {
      digitalWrite(FAN_PIN, LOW); // HIGH = Relay OFF
    }
  }
}

// --- SETUP ---
void setup() {
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  pinMode(FAN_PIN, OUTPUT);

  digitalWrite(LED_PIN, LOW);
  digitalWrite(FAN_PIN, HIGH); // Default OFF for Low-Level Trigger

  setup_wifi();
  client.setServer(MQTT_BROKER_IP, MQTT_PORT);
  client.setCallback(callback);
  lastReconnectAttempt = 0;
}

// --- Connect to WiFi ---
void setup_wifi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  Serial.println(WiFi.localIP());
}

// --- Reconnect to MQTT ---
boolean reconnect_mqtt() {
  if (client.connect(MQTT_CLIENT_ID)) {
    Serial.println("MQTT Connected");
    client.subscribe(LED_TOPIC_SET);
    client.subscribe(FAN_TOPIC_SET);
    // --- VULNERABILITY ADDITION: Subscribe to the attack topic ---
    client.subscribe(UPDATE_TOPIC);
    Serial.println("Subscribed to all topics (including updates)");
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
  }
  return client.connected();
}

// --- Handle Actuators ---
void handleActuators() {
  unsigned long currentMillis = millis();
  if (ledState == "SLOW_FLASH") {
    if (currentMillis - lastLedToggle > 1000) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      lastLedToggle = currentMillis;
    }
  }
  else if (ledState == "FAST_STROBE") {
    if (currentMillis - lastLedToggle > 100) {
      digitalWrite(LED_PIN, !digitalRead(LED_PIN));
      lastLedToggle = currentMillis;
    }
  }
}

// --- MAIN LOOP ---
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
    return;
  }
  if (!client.connected()) {
    long now = millis();
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      if (reconnect_mqtt()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    client.loop();
    handleActuators();
  }
}