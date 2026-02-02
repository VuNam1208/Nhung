#include <WiFi.h>
#include <FirebaseESP32.h>
#include <time.h>
#include <SPI.h>
#include <LoRa.h>

#define WIFI_SSID     "nam"
#define WIFI_PASSWORD "12345678"

#define API_KEY       "AIzaSyCszb18BsaqZ2nUtPRiq96HT5zcdGLtnHg"
#define DATABASE_URL  "https://iott-eddfb-default-rtdb.asia-southeast1.firebasedatabase.app"

// ====== HW ======
#define LED_PIN   2
#define SEND_MS   600
#define CMD_MS    20

// ====== LORA (ESP32) ======
static const int LORA_SS   = 27;
static const int LORA_RST  = 32;
static const int LORA_DIO0 = 26;  // DIO0
// VSPI: SCK=18, MISO=19, MOSI=23

FirebaseData fbdo;       // gửi data
FirebaseData fbdoCmd;    // đọc cmd
FirebaseAuth auth;
FirebaseConfig config;

// ====== Data nhận từ STM32 ======
// giữ adc nếu cần debug (không bắt buộc)
static volatile int latestAdc = -1;
static volatile uint32_t latestAdcRxMs = 0;

// dùng D0 để hiển thị sáng/tối
static volatile int latestD0 = -1;            // -1 = chưa nhận được, 0/1 = hợp lệ
static volatile uint32_t latestD0RxMs = 0;

static bool syncTime() {
  configTime(0, 0, "pool.ntp.org", "time.nist.gov");
  Serial.print("[TIME] Sync");
  time_t now = time(nullptr);

  for (int i = 0; i < 40; i++) {
    now = time(nullptr);
    if (now > 1700000000) {
      Serial.printf("\n[TIME] OK epoch=%ld\n", (long)now);
      return true;
    }
    Serial.print(".");
    delay(200);
  }
  Serial.printf("\n[TIME] FAIL epoch=%ld\n", (long)time(nullptr));
  return false;
}

static bool connectWiFi(uint32_t timeoutMs = 15000) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  Serial.print("[WIFI] Connecting");
  uint32_t t0 = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - t0 < timeoutMs) {
    Serial.print(".");
    delay(200);
  }
  Serial.println();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("[WIFI] OK");
    Serial.printf("[WIFI] IP: %s\n", WiFi.localIP().toString().c_str());
    return true;
  }
  Serial.println("[WIFI] FAIL");
  return false;
}

static void initLoRa() {
  SPI.begin(18, 19, 23, LORA_SS);
  LoRa.setPins(LORA_SS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("[LORA] BEGIN_FAIL");
    while (1) delay(500);
  }

  // MUST match STM32
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.enableCrc();
  LoRa.setSyncWord(0x12);

  LoRa.receive();
  Serial.println("[LORA] RX_READY");
}

static void sendLoRa(const String& s) {
  LoRa.idle();
  LoRa.beginPacket();
  LoRa.print(s);
  LoRa.endPacket();
  LoRa.receive();
}

static void pollLoRaRx() {
  int packetSize = LoRa.parsePacket();
  if (!packetSize) return;

  String rx;
  while (LoRa.available()) rx += (char)LoRa.read();
  rx.trim();

  Serial.print("[LORA] RX: ");
  Serial.println(rx);
  // ✅ 2) D0:0/1
  if (rx.startsWith("D0:")) {
    String s = rx.substring(3);
    s.trim();
    int d0 = s.toInt();
    latestD0 = (d0 != 0) ? 1 : 0;
    latestD0RxMs = millis();
    return;
  }

  // (tương thích cũ) ADC:<adc>
  if (rx.startsWith("ADC:")) {
    String s = rx.substring(4);
    s.trim();
    int v = s.toInt();
    latestAdc = v;
    latestAdcRxMs = millis();
    // không set latestD0 ở case này vì UI mới dùng d0
  }

  // ACK:1/2 chỉ log thôi (đã log ở trên)
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\n=== BOOT ===");

  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  // LoRa init để nhận SENS/D0 từ STM32
  initLoRa();

  if (!connectWiFi()) {
    Serial.println("[SYS] Restart in 2s...");
    delay(1000);
    ESP.restart();
  }

  syncTime();

  config.api_key = API_KEY;
  config.database_url = DATABASE_URL;

  Serial.println("[FB] signUp (anonymous)...");
  if (!Firebase.signUp(&config, &auth, "", "")) {
    Serial.print("[FB] SignUp error: ");
    Serial.println(config.signer.signupError.message.c_str());
  } else {
    Serial.println("[FB] SignUp OK");
  }

  Firebase.begin(&config, &auth);
  Firebase.reconnectWiFi(true);

  fbdo.setResponseSize(1024);
  fbdoCmd.setResponseSize(512);

  Serial.println("[FB] begin() done");
  Serial.println("[LORA] Type on Serial to send (ex: 1 or 2 then Enter)");
}

void loop() {
  // 0) luôn poll LoRa để nhận data từ STM32
  pollLoRaRx();

  // 0.5) gõ Serial -> gửi LoRa sang STM32 (test)
  if (Serial.available()) {
    String tx = Serial.readStringUntil('\n');
    tx.trim();
    if (tx.length() > 0) {
      sendLoRa(tx);
      Serial.print("[LORA] TX: ");
      Serial.println(tx);
    }
  }

  // WiFi reconnect
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WIFI] lost, reconnect...");
    connectWiFi();
    delay(100);
    return;
  }

  static unsigned long lastNotReadyLog = 0;
  if (!Firebase.ready()) {
    if (millis() - lastNotReadyLog > 3000) {
      lastNotReadyLog = millis();
      Serial.println("[FB] not ready (waiting token/network)");
    }
    delay(10);
    return;
  }

  // 1) Gửi trạng thái sáng/tối (D0) lên /esp32/data
  static unsigned long lastSend = 0;
  if (millis() - lastSend >= SEND_MS) {
    lastSend = millis();

    int d0 = latestD0;
    if (d0 < 0) {
      Serial.println("[FB] skip (no D0 from STM32 yet)");
    } else {
      FirebaseJson json;
      json.set("ts_ms", (uint32_t)millis());
      json.set("d0", d0);
      json.set("light", (d0 == 1) ? "TOI" : "SANG");
      json.set("rx_age_ms", (uint32_t)(millis() - latestD0RxMs));

      // optional debug: vẫn gửi adc nếu bạn đang dùng SENS
      if (latestAdc >= 0) json.set("adc", latestAdc);

      if (Firebase.setJSON(fbdo, "/esp32/data", json)) {
        Serial.printf("[FB] Sent OK | d0=%d (%s) | age=%lu ms\n",
                      d0, (d0 == 1 ? "TOI" : "SANG"),
                      (unsigned long)(millis() - latestD0RxMs));
      } else {
        Serial.print("[FB] Send FAIL: ");
        Serial.println(fbdo.errorReason());
      }
    }
  }
  // 2) Đọc lệnh /esp32/cmd/led để bật/tắt LED ESP32 + gửi LoRa cho STM32
  static unsigned long lastCmd = 0;
  static String lastCmdStr = "";

  if (millis() - lastCmd >= CMD_MS) {
    lastCmd = millis();

    if (Firebase.getString(fbdoCmd, "/esp32/cmd/led")) {
      String cmd = fbdoCmd.stringData();
      cmd.trim();

      if (cmd == "1" || cmd == "2") {
        if (cmd != lastCmdStr) {
          lastCmdStr = cmd;

          sendLoRa(cmd);
          Serial.printf("[CMD] web=%s -> LoRa TX\n", cmd.c_str());

          digitalWrite(LED_PIN, (cmd == "1") ? HIGH : LOW);
        }
      } else {
        Serial.printf("[CMD] invalid value: '%s' (expect '1' or '2')\n", cmd.c_str());
      }
    }
  }
}
