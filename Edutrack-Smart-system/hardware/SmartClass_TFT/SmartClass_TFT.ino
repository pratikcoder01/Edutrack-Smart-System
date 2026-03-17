#include <ESP8266WiFi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <ArduinoJson.h>
#include <TFT_eSPI.h> // Ensure you install TFT_eSPI library and configure User_Setup.h
#include <SPI.h>

// ==========================================
// CONFIGURATION
// ==========================================
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// Replace with the IP address of the computer running your Flask app (e.g., 192.168.1.x)
const String serverName = "http://192.168.1.100:5000/api/hardware_display";

unsigned long lastTime = 0;
unsigned long timerDelay = 3000; // Poll every 3 seconds

TFT_eSPI tft = TFT_eSPI();

// Memory allocations for previous states to prevent screen flickering
String lastSubject = "";
String lastTeacher = "";
String lastTimeStr = "";
int lastPresentCount = -1;

void setup() {
  Serial.begin(115200);

  // Initialize TFT Screen
  tft.init();
  tft.setRotation(1); // Landscape
  tft.fillScreen(TFT_BLACK);
  tft.setTextColor(TFT_WHITE, TFT_BLACK); // Background is black to overwrite text cleanly

  drawHeader();

  // Connect to Wi-Fi
  tft.setTextSize(2);
  tft.setCursor(10, 50);
  tft.print("Connecting to WiFi...");
  
  WiFi.begin(ssid, password);
  Serial.println("Connecting");
  while(WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  
  // Connected!
  tft.fillScreen(TFT_BLACK);
  drawHeader();
  tft.setCursor(10, 50);
  tft.setTextColor(TFT_GREEN, TFT_BLACK);
  tft.print("WiFi Connected!");
  delay(1000);
  tft.fillScreen(TFT_BLACK);
  drawHeader();
  drawLabels();
}

void loop() {
  // Check if minimum time delay has passed
  if ((millis() - lastTime) > timerDelay) {
    
    // Check WiFi connection status
    if(WiFi.status()== WL_CONNECTED){
      WiFiClient client;
      HTTPClient http;
      
      http.begin(client, serverName.c_str());
      int httpResponseCode = http.GET();
      
      if (httpResponseCode > 0) {
        String payload = http.getString();
        // Parse JSON
        StaticJsonDocument<256> doc;
        DeserializationError error = deserializeJson(doc, payload);

        if (!error) {
          String subject = doc["subject"].as<String>();
          String teacher = doc["teacher"].as<String>();
          String timeStr = doc["time"].as<String>();
          int present_count = doc["present_count"].as<int>();

          updateDisplay(subject, teacher, timeStr, present_count);
        } else {
          Serial.print("deserializeJson() failed: ");
          Serial.println(error.c_str());
        }
      }
      else {
        Serial.print("Error code: ");
        Serial.println(httpResponseCode);
        tft.fillRect(0, 40, 320, 200, TFT_BLACK);
        tft.setCursor(10, 50);
        tft.setTextColor(TFT_RED, TFT_BLACK);
        tft.print("Server Offline.");
      }
      http.end(); // Free resources
    }
    else {
      Serial.println("WiFi Disconnected");
    }
    lastTime = millis();
  }
}

// ==========================================
// TFT RENDER FUNCTIONS
// ==========================================
void drawHeader() {
  tft.fillRect(0, 0, 320, 30, TFT_BLUE);
  tft.setTextColor(TFT_WHITE, TFT_BLUE);
  tft.setTextSize(2);
  tft.setCursor(10, 8);
  tft.print("SmartClass AI Panel");
}

void drawLabels() {
  tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
  tft.setTextSize(2);
  
  tft.setCursor(10, 50);
  tft.print("Subject:");
  
  tft.setCursor(10, 100);
  tft.print("Status:");
  
  tft.setCursor(10, 150);
  tft.print("Present:");
}

void updateDisplay(String subject, String teacher, String timeStr, int present_count) {
  tft.setTextSize(3);

  // Subject Update (Only overwrite if changed)
  if (subject != lastSubject) {
    tft.fillRect(10, 70, 300, 25, TFT_BLACK);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.setCursor(10, 70);
    tft.print(subject.substring(0, 15)); // Truncate
    lastSubject = subject;
  }

  // Status/Teacher Update
  if (teacher != lastTeacher) {
    tft.fillRect(10, 120, 300, 25, TFT_BLACK);
    if(teacher == "Waiting...") tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    else tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.setCursor(10, 120);
    tft.print(teacher);
    lastTeacher = teacher;
  }

  // Count Update
  if (present_count != lastPresentCount) {
    tft.fillRect(130, 145, 100, 35, TFT_BLACK); // Clear slightly offset rect for number
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextSize(4);
    tft.setCursor(130, 145);
    tft.print(present_count);
    lastPresentCount = present_count;
  }

  // Update Time string tiny in bottom right corner
  if (timeStr != lastTimeStr) {
    tft.fillRect(230, 220, 90, 20, TFT_BLACK);
    tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(230, 220);
    tft.print(timeStr);
    lastTimeStr = timeStr;
  }
}
