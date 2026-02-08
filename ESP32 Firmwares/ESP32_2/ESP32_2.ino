/*
 * FIRMWARE FOR: ESP32-2 (Security Hub)
 * Project: Attacks Against Smart Home
 * Components: Button 2 (GPIO 17), Buzzer (GPIO 18)
 */

#include <WiFi.h>
#include <PubSubClient.h>

// --- START: CONFIGURE YOUR SETTINGS ---
const char* WIFI_SSID = "Smart_Home";
const char* WIFI_PASS = "123456789";
const char* MQTT_BROKER_IP = "192.168.88.10"; // Your RPi 5's Static IP
const int   MQTT_PORT = 1883;
const char* MQTT_CLIENT_ID = "esp32-security-hub"; // <-- Changed Client ID
// --- END: CONFIGURE YOUR SETTINGS ---

// --- Pin Definitions ---
const int BUTTON_2_PIN = 17;
const int BUZZER_PIN = 18;

// --- MQTT Topics ---
const char* BUTTON_2_TOPIC = "home/livingroom/button_disarm";
const char* BUZZER_TOPIC_SET = "home/livingroom/buzzer/set";

// --- Global Variables ---
WiFiClient espClient;
PubSubClient client(espClient);
long lastReconnectAttempt = 0;

// Button Debounce
int lastButton2State = HIGH; // Assuming INPUT_PULLUP
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;

// Actuator States (for non-blocking logic)
String buzzerState = "OFF";
unsigned long lastBuzzerToggle = 0;

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

  // --- Buzzer Logic ---
  if (String(topic) == BUZZER_TOPIC_SET) {
    buzzerState = payloadStr; // Store the desired state
    
    // Handle simple OFF state
    if (buzzerState == "OFF") {
      digitalWrite(BUZZER_PIN, LOW);
    }
    // Handle short, blocking chirps
    else if (buzzerState == "ARM_CHIRP") {
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100);
      digitalWrite(BUZZER_PIN, LOW);
      buzzerState = "OFF"; // Reset state
    }
    else if (buzzerState == "DISARM_CHIRP") {
      digitalWrite(BUZZER_PIN, HIGH); delay(100); digitalWrite(BUZZER_PIN, LOW);
      delay(100);
      digitalWrite(BUZZER_PIN, HIGH); delay(100); digitalWrite(BUZZER_PIN, LOW);
      buzzerState = "OFF"; // Reset state
    }
    // "ALARM" and "ENTRY_BEEP" are handled in the main loop()
  }
}

// --- SETUP: Runs once on boot ---
void setup() {
  Serial.begin(115200);
  pinMode(BUTTON_2_PIN, INPUT_PULLUP);
  pinMode(BUZZER_PIN, OUTPUT);

  digitalWrite(BUZZER_PIN, LOW);

  setup_wifi();
  client.setServer(MQTT_BROKER_IP, MQTT_PORT);
  client.setCallback(callback); // Set the function to run on incoming messages
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
    // Subscribe to command topics
    client.subscribe(BUZZER_TOPIC_SET);
    Serial.println("Subscribed to command topics");
  } else {
    Serial.print("failed, rc=");
    Serial.print(client.state());
  }
  return client.connected();
}

// --- Handle Button 2 (Disarm) ---
void handleButton2() {
  int reading = digitalRead(BUTTON_2_PIN);

  if (reading != lastButton2State) {
    lastDebounceTime = millis();
  }

  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading == LOW) {
      Serial.println("Button 2 Pressed");
      client.publish(BUTTON_2_TOPIC, "PRESSED");
      lastButton2State = LOW;
    } else {
      lastButton2State = HIGH;
    }
  }
  
  if (reading != lastButton2State) {
      lastButton2State = reading;
  }
}

// --- Handle Non-Blocking Actuator States ---
void handleActuators() {
  unsigned long currentMillis = millis();

  // 1. Buzzer State Machine
  if (buzzerState == "ALARM") {
     // UPDATED: Toggle every 1ms (500Hz) for a loud, high-pitched alarm
     // (Was 50ms, which is a slow 10Hz click)
     if (currentMillis - lastBuzzerToggle > 1) { 
       digitalWrite(BUZZER_PIN, !digitalRead(BUZZER_PIN));
       lastBuzzerToggle = currentMillis;
     }
  }
  else if (buzzerState == "ENTRY_BEEP") {
    if (currentMillis - lastBuzzerToggle > 1000) { // 1-second interval
      // Beep for 100ms
      digitalWrite(BUZZER_PIN, HIGH);
      delay(100); // Small delay here is acceptable for a beep
      digitalWrite(BUZZER_PIN, LOW);
      lastBuzzerToggle = currentMillis;
    }
  }
  // Note: "OFF" and "CHIRP" are handled by the callback
}


// --- MAIN LOOP: Runs forever ---
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
    client.loop(); // THIS IS CRITICAL - it processes incoming messages
    
    handleButton2();
    handleActuators(); // Handle flashing/beeping patterns
  }
}