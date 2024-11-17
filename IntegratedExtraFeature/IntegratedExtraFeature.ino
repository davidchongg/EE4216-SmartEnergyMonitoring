#include <WiFi.h>
#include <HTTPClient.h>
#include <ESPAsyncWebServer.h>
#include <Adafruit_INA260.h>
#include <Wire.h>
#include <Adafruit_NeoPixel.h>
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

// Network credentials
const char* ssid = "ssid";
const char* password = "password";
const char* serverAddress = "http://172.20.10.2:5001";  // Flask server IP address and port

// Define GPIO pins and I2C addresses
#define I2C_SDA       GPIO_NUM_35
#define I2C_SCL       GPIO_NUM_36

#define INA260_ADDR1  0x40
#define INA260_ADDR2  0x41
#define INA260_ADDR3  0x44
#define INA260_ADDR4  0x45

#define RELAY_PIN1    GPIO_NUM_12   // Fan
#define RELAY_PIN2    GPIO_NUM_13   // Light
#define RELAY_PIN3    GPIO_NUM_14   // Washing machine
#define RELAY_ON      LOW
#define RELAY_OFF     HIGH

#define LEDSTRIP_PIN  GPIO_NUM_9

#define BUTTON_PIN1   GPIO_NUM_15   // Fan
#define BUTTON_PIN2   GPIO_NUM_16   // Light

#define TRIG_PIN1     GPIO_NUM_4    // Left
#define ECHO_PIN1     GPIO_NUM_5
#define TRIG_PIN2     GPIO_NUM_17    // Right
#define ECHO_PIN2     GPIO_NUM_18
#define SOUND_SPEED   0.034

// ************************************
// Instantiate
// ************************************
Adafruit_INA260 ina260_1 = Adafruit_INA260();
Adafruit_INA260 ina260_2 = Adafruit_INA260();
Adafruit_INA260 ina260_3 = Adafruit_INA260();
Adafruit_INA260 ina260_4 = Adafruit_INA260();
Adafruit_NeoPixel strip = Adafruit_NeoPixel(8, LEDSTRIP_PIN, NEO_GRB + NEO_KHZ800);

// Create HTTP client and server
AsyncWebServer server(80);
WiFiClient client;

// ************************************
// Variables
// ************************************
unsigned long previousMillis = 0;
const long interval = 1000;                   // Upload interval (1 second)
bool motorFanOn = false;
bool ledStripOn = false;
bool washingOn = false;
volatile bool fanButtonPressed = false;
volatile bool lightButtonPressed = false;
unsigned long lastFanButtonTime = 0;
unsigned long lastLightButtonTime = 0;
unsigned long washingStartTime = 0;
unsigned long lastMovementTime = 0;
bool offByNoMovement = false;

// ************************************
// Setup functions
// ************************************
// Setup INA260 sensors
void INABegin(Adafruit_INA260 &ina, int addr, int num) {
  if (!ina.begin(addr)) {
    Serial.print("Couldn't find INA260 chip ");
    Serial.println(num);
  } else {
    Serial.print("Found INA260 chip ");
    Serial.println(num);
  }
}

// Function keep trying to connect wifi until wifi is connected
void connectWifi() {
  WiFi.begin(ssid, password);
  Serial.print("Connecting to WiFi...");
  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.print(".");
  }
  Serial.println("\nConnected to WiFi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
}

// ************************************
// Appliance control functions
// ************************************
// Turn on LED strip
void onLight() {
  digitalWrite(RELAY_PIN2, RELAY_ON);     
  delay(200);                                           // Introduce delay to overcome hardware delay of relays
  for (int i = 0; i < 8; i++) {
    strip.setPixelColor(i, strip.Color(64, 64, 64));    // White color
  }
  strip.show();                                         // Update and show on LED strip
  ledStripOn = true;                                    // Update state of LED strip
  lastMovementTime = millis();                          // Update last time of detecting movement (action of turning on light counts as movement)
}

// Turn off LED strip
void offLight() {
  digitalWrite(RELAY_PIN2, RELAY_OFF);
  ledStripOn = false;
}

void onFan() {
  digitalWrite(RELAY_PIN1, RELAY_ON);
  motorFanOn = true;
  lastMovementTime = millis();
}

void offFan() {
  digitalWrite(RELAY_PIN1, RELAY_OFF);
  motorFanOn = false;
}

void startWashing() {
  digitalWrite(RELAY_PIN3, RELAY_ON);
  washingOn = true;
  washingStartTime = millis();
}

void stopWashing() {
  digitalWrite(RELAY_PIN3, RELAY_OFF);
  washingOn = false;
}

void toggleFan() {
  if (!motorFanOn) { 
    onFan();
  } else {           
    offFan();
  }
}

void toggleLight() {
  if (!ledStripOn) { 
    onLight();
  } else {           
    offLight();
  }
}

// INA260 sensor reading functions
float getLightPower() { return ina260_1.readPower(); }
float getLightCurrent() { return ina260_1.readCurrent(); }
float getLightVoltage() {return ina260_1.readBusVoltage(); }

float getFanPower() { return ina260_2.readPower(); }
float getFanCurrent() { return ina260_2.readCurrent(); }
float getFanVoltage() {return ina260_2.readBusVoltage(); }

float getChargerPower() { return ina260_3.readPower(); }
float getChargerCurrent() { return ina260_3.readCurrent(); }
float getChargerVoltage() {return ina260_3.readBusVoltage(); }

float getWashingPower() { return ina260_4.readPower(); }
float getWashingCurrent() { return ina260_4.readCurrent(); }
float getWashingVoltage() {return ina260_4.readBusVoltage(); }

bool checkMovement(int trigPin, int echoPin) {
  long duration;
  float distanceCm;

  digitalWrite(trigPin, LOW);
  delayMicroseconds(2);
  // Sets the trigPin on HIGH state for 10 micro seconds
  digitalWrite(trigPin, HIGH);
  delayMicroseconds(10);
  digitalWrite(trigPin, LOW);
  
  // Reads the echoPin, returns the sound wave travel time in microseconds
  duration = pulseIn(echoPin, HIGH);
  
  // Calculate the distance
  distanceCm = duration * SOUND_SPEED/2;
  // Serial.println(distanceCm);
  return (distanceCm < 12 && distanceCm != 0) ? true : false;
}

void checkUltrasonic() {
  bool movement = checkMovement(TRIG_PIN1, ECHO_PIN1) | checkMovement(TRIG_PIN2, ECHO_PIN2);

  if (!movement && !offByNoMovement) {
    if (millis() - lastMovementTime > 20000) {
      Serial.println("No movement detected for more than 20s, turning off fan and light to conserve electricity");
      offFan();
      offLight();
      offByNoMovement = true;
    }
  } else {
    lastMovementTime = millis();
    offByNoMovement = false;
  }
}

// ************************************
// Server
// ************************************
// Upload data to Flask server
void uploadData(const char* device, float power, float current, float voltage) {
  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    http.begin(String(serverAddress) + "/upload_data");
    http.addHeader("Content-Type", "application/json");

    String jsonData = "{\"device\":\"" + String(device) + "\",\"power\":" + String(power) +
                      ",\"current\":" + String(current) + ",\"voltage\":" + String(voltage) + "}";

    int httpResponseCode = http.POST(jsonData);

    if (httpResponseCode > 0) {
      Serial.printf("Data upload successful, response code: %d\n", httpResponseCode);
    } else {
      Serial.printf("Error on data upload: %s\n", http.errorToString(httpResponseCode).c_str());
    }
    http.end();
  } else {
    Serial.println("WiFi not connected, skipping data upload.");
  }
}

// Handle incoming control requests
void handleControlRequest(AsyncWebServerRequest *request) {
  if (request->hasParam("appliance", true) && request->hasParam("action", true)) {
    String appliance = request->getParam("appliance", true)->value();
    String action = request->getParam("action", true)->value();
    if (action == "turn_off") {
      if (appliance == "Motor Fan") {
        offFan();
      } else if (appliance == "LED Strip") {
        offLight();
      } else if (appliance == "Washing Machine") {
        stopWashing();
      }
      request->send(200, "text/plain", appliance + " turned off");
      Serial.println(appliance + " turned off via server request");
    } else if (action == "turn_on") {
      if (appliance == "Motor Fan") {
        onFan();
      } else if (appliance == "LED Strip") {
        onLight();
      } else if (appliance == "Washing Machine") {
        startWashing();
      }
      request->send(200, "text/plain", appliance + " turned on");
      Serial.println(appliance + " turned off via server request");
    } else {
      request->send(400, "text/plain", "Invalid action");
    }
  } else {
    request->send(400, "text/plain", "Missing parameters");
  }
}

// Function to handle data upload in a separate task
void uploadTask(void *parameter) {
  while (true) {
    // Reconnect WiFi if disconnected
    if (WiFi.status() != WL_CONNECTED) {
      Serial.println("Wi-Fi connection lost. Reconnecting...");
      connectWifi();
    }
    uploadData("Motor Fan", getFanPower(), getFanCurrent(), getFanVoltage());  
    uploadData("LED Strip", getLightPower(), getLightCurrent(), getLightVoltage()); 
    uploadData("USB Charger", getChargerPower(), getChargerCurrent(), getChargerVoltage()); 
    uploadData("Washing Machine", getWashingPower(), getWashingCurrent(), getWashingVoltage()); 
    vTaskDelay(interval / portTICK_PERIOD_MS);  // Delay for the next interval
  }
}

// ************************************
// Interrupt Handlers
// ************************************
void IRAM_ATTR handleButtonPress1() {
  unsigned long interruptTime = millis();
  if (interruptTime - lastFanButtonTime > 300) {
    fanButtonPressed = true;
  }
  lastFanButtonTime = interruptTime;
}

void IRAM_ATTR handleButtonPress2() {
  unsigned long interruptTime = millis();
  if (interruptTime - lastLightButtonTime > 300) {
    lightButtonPressed = true;
  }
  lastLightButtonTime = interruptTime;
}

// ************************************
// Setup
// ************************************
void setup() {
  Serial.begin(115200);

  // Configure I2C and INA260 sensors
  Wire.begin(I2C_SDA, I2C_SCL);
  INABegin(ina260_1, INA260_ADDR1, 1);
  INABegin(ina260_2, INA260_ADDR2, 2);
  INABegin(ina260_3, INA260_ADDR3, 3);
  INABegin(ina260_4, INA260_ADDR4, 4);

  // Setup relays and LED strip
  pinMode(RELAY_PIN1, OUTPUT);
  pinMode(RELAY_PIN2, OUTPUT);
  pinMode(RELAY_PIN3, OUTPUT);
  digitalWrite(RELAY_PIN1, RELAY_OFF);
  digitalWrite(RELAY_PIN2, RELAY_OFF);
  digitalWrite(RELAY_PIN3, RELAY_OFF);
  pinMode(BUTTON_PIN1, INPUT_PULLUP);
  pinMode(BUTTON_PIN2, INPUT);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN1), handleButtonPress1, FALLING);
  attachInterrupt(digitalPinToInterrupt(BUTTON_PIN2), handleButtonPress2, RISING);
  strip.begin();
  pinMode(TRIG_PIN1, OUTPUT);
  pinMode(ECHO_PIN1, INPUT);
  pinMode(TRIG_PIN2, OUTPUT);
  pinMode(ECHO_PIN2, INPUT);

  // Connect to WiFi
  connectWifi();

  // Setup HTTP server
  server.on("/control", HTTP_POST, handleControlRequest);
  server.begin();
  Serial.println("HTTP server started");

  // FreeRTOS
  xTaskCreatePinnedToCore(uploadTask, "Upload Task", 4096, NULL, 1, NULL, 1);
}

// ************************************
// Loop
// ************************************
void loop() {
  if (fanButtonPressed) {
    Serial.println("Fan button");
    toggleFan();
    fanButtonPressed = false;
  }

  if (lightButtonPressed) {
    Serial.println("Light button");
    toggleLight();
    lightButtonPressed = false;
  }

  if (washingOn) {
    if (millis() - washingStartTime > 5000) {  // 5s
      stopWashing();
    }
  }

  checkUltrasonic();
}