#include <Arduino.h>
#include <ArduinoJson.h>

// Pinconfiguratie
const int motorEn = 9;     // ENA (PWM)
const int motorIn1 = 2;    // IN1
const int motorIn2 = 3;    // IN2
const int startStopBtn = 5;
const int reverseBtn = 4;
const int potPin = A0;

bool motorRunning = false;
bool reverse = false;
int speedValue = 0;

void setup() {
  pinMode(motorEn, OUTPUT);
  pinMode(motorIn1, OUTPUT);
  pinMode(motorIn2, OUTPUT);
  pinMode(startStopBtn, INPUT);
  pinMode(reverseBtn, INPUT);
  digitalWrite(motorEn, LOW);
  digitalWrite(motorIn1, LOW);
  digitalWrite(motorIn2, LOW);

  Serial.begin(9600);
}

void updateMotor() {
  if (reverse) {
    digitalWrite(motorIn1, LOW);
    digitalWrite(motorIn2, HIGH);
  } else {
    digitalWrite(motorIn1, HIGH);
    digitalWrite(motorIn2, LOW);
  }

  if (motorRunning) {
    analogWrite(motorEn, speedValue);
  } else {
    analogWrite(motorEn, 0);
  }
}

void handleButtons() {
  static bool lastStartStop = LOW;
  static bool lastReverse = LOW;

  bool currentStartStop = digitalRead(startStopBtn);
  bool currentReverse = digitalRead(reverseBtn);

  if (lastStartStop == LOW && currentStartStop == HIGH) {
    motorRunning = !motorRunning;
  }
  if (lastReverse == LOW && currentReverse == HIGH) {
    reverse = !reverse;
  }

  lastStartStop = currentStartStop;
  lastReverse = currentReverse;
}

void handleSerial() {
  static String inputBuffer = "";

  while (Serial.available()) {
    char ch = Serial.read();

    if (ch == '\r') continue;

    if (ch == '\n') {
      inputBuffer.trim();
      if (inputBuffer.length() > 0) {
        StaticJsonDocument<128> doc;
        DeserializationError error = deserializeJson(doc, inputBuffer);

        StaticJsonDocument<64> response;
        if (error) {
          response["status"] = "error";
          response["message"] = "Invalid JSON";
          serializeJson(response, Serial);
          Serial.println();
        } else {
          const char* cmd = doc["command"];
          if (strcmp(cmd, "start") == 0) {
            motorRunning = true;
          } else if (strcmp(cmd, "stop") == 0) {
            motorRunning = false;
          } else if (strcmp(cmd, "reverse") == 0) {
            reverse = !reverse;
          } else if (strcmp(cmd, "set_speed") == 0) {
            int val = doc["value"] | 0;
            speedValue = constrain(val, 0, 255);
          } else {
            response["status"] = "error";
            response["message"] = "Unknown command";
            serializeJson(response, Serial);
            Serial.println();
            inputBuffer = "";
            return;
          }

          updateMotor();
          response["status"] = "done";
          serializeJson(response, Serial);
          Serial.println();
        }
      }
      inputBuffer = "";  // reset na newline
    } else {
      inputBuffer += ch;
    }
  }
}


void loop() {
  handleSerial();

  // Stand-alone mode na 2s zonder seriële activiteit
  static unsigned long lastSerial = 0;
  if (Serial.available()) {
    lastSerial = millis();
  }

  if (millis() - lastSerial > 2000) {
    handleButtons();
    speedValue = map(analogRead(potPin), 0, 1023, 0, 255);
    updateMotor();
  }
}
