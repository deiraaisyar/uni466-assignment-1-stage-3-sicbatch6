#include <Wire.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>
#include <DHT.h>

// --- WiFi ---
const char* ssid = "Yusuf iPhone 13";
const char* password = "kepokamubabi";

// --- Ubidots ---
String ubidotsToken = "BBUS-8rMLXoEFppMoI2rt7r9zFIOEu53CTe";
String deviceLabel = "esp32-sic6-stage3";
String alertLabel = "alert";

// --- Variable Labels (di Ubidots) ---
String tempLabel = "temperature";
String humLabel = "humidity";
String motionLabel = "motion";

// --- OLED ---
#define SCREEN_WIDTH 128
#define SCREEN_HEIGHT 64
#define OLED_RESET     -1
#define SCREEN_ADDRESS 0x3C
#define SCREEN_SDA 21
#define SCREEN_SCL 22

Adafruit_SSD1306 display(SCREEN_WIDTH, SCREEN_HEIGHT, &Wire, OLED_RESET);

// --- Sensor & Aktuator ---
#define DHTPIN 19
#define DHTTYPE DHT11
#define PIRPIN 23
#define BUZZERPIN 5

DHT dht(DHTPIN, DHTTYPE);

void sendToUbidots(String label, float value) {
  HTTPClient http;
  String url = "http://industrial.api.ubidots.com/api/v1.6/devices/" + deviceLabel + "/";
  http.begin(url);
  http.addHeader("X-Auth-Token", ubidotsToken);
  http.addHeader("Content-Type", "application/json");

  String payload = "{\"" + label + "\":" + String(value) + "}";
  int httpCode = http.POST(payload);

  if (httpCode > 0) {
    Serial.println("✅ Data " + label + " terkirim: " + String(value));
  } else {
    Serial.println("❌ Gagal kirim data " + label);
  }

  http.end();
}

int getUbidotsAlert() {
  HTTPClient http;
  String url = "http://industrial.api.ubidots.com/api/v1.6/devices/" + deviceLabel + "/" + alertLabel + "/lv";

  http.begin(url);
  http.addHeader("X-Auth-Token", ubidotsToken);
  int httpCode = http.GET();
  
  if (httpCode == 200) {
    String payload = http.getString();
    http.end();
    return payload.toInt();
  } else {
    Serial.println("❌ Gagal ambil alert dari Ubidots");
    http.end();
    return 0;
  }
}

void setup() {
  Serial.begin(9600);
  delay(1000);

  WiFi.begin(ssid, password);
  Serial.print("🔌 Menghubungkan WiFi");
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n✅ WiFi Tersambung");

  Wire.begin(SCREEN_SDA, SCREEN_SCL);
  if (!display.begin(SSD1306_SWITCHCAPVCC, SCREEN_ADDRESS)) {
    Serial.println(F("❌ Gagal inisialisasi OLED"));
    while (true);
  }

  display.clearDisplay();
  display.setTextColor(SSD1306_WHITE);
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("Warga Naget");
  display.display();
  delay(2000);

  dht.begin();
  pinMode(PIRPIN, INPUT);

  pinMode(PIRPIN, INPUT);
  pinMode(BUZZERPIN, OUTPUT);

  Serial.println("🚀 Sistem siap kirim data ke Ubidots!");
}

void loop() {
  float suhu = dht.readTemperature();
  float kelembapan = dht.readHumidity();
  int gerakan = digitalRead(PIRPIN);

  display.clearDisplay();
  display.setTextSize(1);
  display.setCursor(0, 0);
  display.println("HelmAware");

  // DHT sensor
  if (isnan(suhu) || isnan(kelembapan)) {
    Serial.println("❌ Gagal baca DHT!");
    display.setCursor(0, 12);
    display.println("Sensor DHT Error");
  } else {
    display.setCursor(0, 12);
    display.print("Suhu: ");
    display.print(suhu);
    display.println(" C");

    display.setCursor(0, 24);
    display.print("Lembap: ");
    display.print(kelembapan);
    display.println(" %");

    sendToUbidots(tempLabel, suhu);
    sendToUbidots(humLabel, kelembapan);
  }

  // Gerakan (PIR)
  display.setCursor(0, 36);
  display.print("Gerakan: ");
  display.println(gerakan == HIGH ? "YA" : "Tidak");
  sendToUbidots(motionLabel, gerakan);

  // Ambil alert dari Ubidots
  int alertStatus = getUbidotsAlert();
  Serial.print("📥 Status alert dari Ubidots: ");
  Serial.println(alertStatus);

  // Tampilkan status alert di OLED
  display.setCursor(0, 48);
  display.print("Alert: ");
  if (alertStatus == 1) {
    display.println("BAHAYA!");
  } else {
    display.println("Aman");
  }

bool suhuBahaya = suhu > 50;
bool lembapBahaya = kelembapan > 80;  // kamu bisa sesuaikan threshold ini
bool deteksiGerakan = gerakan == HIGH;
bool alertDariUbidots = alertStatus == 1;

// 🔔 Logika buzzer komprehensif
if (suhuBahaya || lembapBahaya || alertDariUbidots) {
  Serial.println("🚨 Buzzer ON (suhu/lembap/gerakan/kamera)");
  digitalWrite(BUZZERPIN, HIGH);
} else {
  digitalWrite(BUZZERPIN, LOW);
}


  display.display();
  Serial.println("==============================\n");
  delay(10000);
}
