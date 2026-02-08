/*
 * FIRMWARE FOR: ESP32-1 (Entryway Hub)
 * Project: Attacks Against Smart Home
 * Components: Motion Sensor (GPIO 13), Button 1 (GPIO 12)
 */

#include <WiFi.h>
#include <PubSubClient.h>

// --- START: CONFIGURE YOUR SETTINGS ---
const char* WIFI_SSID = "Smart_Home";
const char* WIFI_PASS = "123456789";
const char* MQTT_BROKER_IP = "192.168.88.10"; // Your RPi 5's Static IP
const int   MQTT_PORT = 1883;
const char* MQTT_CLIENT_ID = "esp32-entryway";
// --- END: CONFIGURE YOUR SETTINGS ---

// --- Pin Definitions ---
const int MOTION_PIN = 13;
const int BUTTON_1_PIN = 12;

// --- MQTT Topics ---
const char* MOTION_TOPIC = "home/entryway/motion";
const char* BUTTON_1_TOPIC = "home/entryway/button_arm";

// --- Global Variables ---
WiFiClient espClient;
PubSubClient client(espClient);
long lastReconnectAttempt = 0;

// Button Debounce
int lastButton1State = HIGH; // Assuming INPUT_PULLUP, HIGH is unpressed
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

// Motion State
int lastMotionState = LOW;

// --- SETUP: Runs once on boot ---
void setup() {
  Serial.begin(115200);
  pinMode(MOTION_PIN, INPUT);
  pinMode(BUTTON_1_PIN, INPUT_PULLUP); // Use internal pull-up resistor

  setup_wifi();
  client.setServer(MQTT_BROKER_IP, MQTT_PORT);
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

  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println("IP address: ");
  Serial.println(WiFi.localIP());
}

// --- Reconnect to MQTT ---
boolean reconnect_mqtt() {
  if (client.connect(MQTT_CLIENT_ID)) {
    Serial.println("MQTT Connected");
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
  }
  return client.connected();
}

// --- Handle Button 1 (Arm) ---
void handleButton1() {
  int reading = digitalRead(BUTTON_1_PIN);

  // If the switch changed, due to noise or pressing:
  if (reading != lastButton1State) {
    lastDebounceTime = millis(); // reset the debouncing timer
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    // If the button state has been stable for long enough
    if (reading == LOW) { // Button is pressed (LOW due to INPUT_PULLUP)
      Serial.println("Button 1 Pressed");
      client.publish(BUTTON_1_TOPIC, "PRESSED");
      lastButton1State = LOW; // Update the state
    } else {
      lastButton1State = HIGH; // Button is released
    }
  }

  // Save the reading for next time
  if (reading != lastButton1State) {
      lastButton1State = reading;
  }
}

// --- Handle Motion Sensor ---
void handleMotion() {
  int motionState = digitalRead(MOTION_PIN);

  if (motionState != lastMotionState) {
    if (motionState == HIGH) {
      Serial.println("Motion ON");
      client.publish(MOTION_TOPIC, "ON");
    } else {
      Serial.println("Motion OFF");
      client.publish(MOTION_TOPIC, "OFF");
    }
    lastMotionState = motionState;
  }
}

// --- MAIN LOOP: Runs forever ---
void loop() {
  if (WiFi.status() != WL_CONNECTED) {
    setup_wifi();
    return; // Skip the rest of the loop until WiFi is back
  }

  if (!client.connected()) {
    long now = millis();
    // Try to reconnect every 5 seconds
    if (now - lastReconnectAttempt > 5000) {
      lastReconnectAttempt = now;
      if (reconnect_mqtt()) {
        lastReconnectAttempt = 0;
      }
    }
  } else {
    // Client is connected
    client.loop(); // Process MQTT messages (if any)
    
    handleButton1();
    handleMotion();
  }
}