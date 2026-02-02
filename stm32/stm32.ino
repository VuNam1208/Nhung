#include <SPI.h>
#include <LoRa.h>

#include <Wire.h>
#include <LiquidCrystal_I2C.h>


#define LCD_COLS 16
#define LCD_ROWS 2
LiquidCrystal_I2C lcd(0x27, LCD_COLS, LCD_ROWS);

#define D0_DARK_LEVEL 1

#define LORA_CS   PA4
#define LORA_RST  PB1
#define LORA_DIO0 PB0

#define LDR_PIN   PA1
#define ADC_SAMPLES 1
#define ADC_SEND_MS 500
#define LDR_D0_PIN PA3

static void loraConfig() {
  LoRa.setSpreadingFactor(7);
  LoRa.setSignalBandwidth(125E3);
  LoRa.setCodingRate4(5);
  LoRa.setPreambleLength(8);
  LoRa.enableCrc();
  LoRa.setSyncWord(0x12);
}

static void sendText(const String& s) {
  LoRa.idle();
  LoRa.beginPacket();
  LoRa.print(s);
  LoRa.endPacket();
  LoRa.receive();
}

static int readLdrAdcAvg(uint8_t samples = ADC_SAMPLES) {
  long sum = 0;
  for (uint8_t i = 0; i < samples; i++) {
    sum += analogRead(LDR_PIN);
    delay(2);
  }
  return (int)(sum / samples);
}

// ===== LCD helpers =====
static void lcdClearRow(uint8_t row) {
  lcd.setCursor(0, row);
  for (uint8_t i = 0; i < LCD_COLS; i++) lcd.print(' ');
}

static void lcdPrintClean(uint8_t col, uint8_t row, const String &s) {
  lcdClearRow(row);
  // In nội dung mới
  lcd.setCursor(col, row);
  String out = s;
  if (out.length() > LCD_COLS) out = out.substring(0, LCD_COLS);
  lcd.print(out);
}

static void updateLcd() {
  int d0 = digitalRead(LDR_D0_PIN);
  bool isDark = (d0 == D0_DARK_LEVEL);

  bool lampOn = (digitalRead(PB9) == HIGH);

  lcdPrintClean(0, 0, String("Troi: ") + (isDark ? "TOI" : "SANG"));
  lcdPrintClean(0, 1, String("Den : ") + (lampOn ? "BAT" : "TAT"));
}
// =======================

void setup() {
  Serial.begin(115200);
  delay(300);

  pinMode(PB9, OUTPUT);
  digitalWrite(PB9, LOW);

  pinMode(LDR_PIN, INPUT_ANALOG);
  pinMode(LDR_D0_PIN, INPUT_PULLUP);

  // ===== LCD init (STM32F1) =====
  Wire.begin();              // I2C1 default PB7/PB6
  Wire.setClock(100000);
  delay(50);

  lcd.init();                
  lcd.backlight();
  lcd.clear();
  lcdPrintClean(0, 0, "STM32_LoRa");
  lcdPrintClean(0, 1, "LCD Ready");
  delay(500);
  // =============================

  LoRa.setPins(LORA_CS, LORA_RST, LORA_DIO0);

  if (!LoRa.begin(433E6)) {
    Serial.println("BEGIN_FAIL");
    lcd.clear();
    lcdPrintClean(0, 0, "LoRa FAIL");
    while (1) delay(1000);
  }

  loraConfig();
  Serial.println("STM32 READY (RX + ACK + ADC=REAL)");
  LoRa.receive();
}

void loop() {
  // ===== 1) RX + điều khiển + ACK =====
  int sz = LoRa.parsePacket();
  if (sz) {
    String rx;
    while (LoRa.available()) rx += (char)LoRa.read();
    rx.trim();

    Serial.print("RX:");
    Serial.println(rx);

    if (rx == "1") {
      digitalWrite(PB9, HIGH);
    } else if (rx == "2") {
      digitalWrite(PB9, LOW);
    }

    String ack = "ACK:" + rx;
    sendText(ack);
    Serial.print("TX:");
    Serial.println(ack);
  }

  // ===== TX D0 =====
  static uint32_t lastAdcSend = 0;
  if (millis() - lastAdcSend >= ADC_SEND_MS) {
    lastAdcSend = millis();

    int d0 = digitalRead(LDR_D0_PIN);
    String adcMsg = "D0:" + String(d0);

    sendText(adcMsg);

    Serial.print("TX:");
    Serial.println(adcMsg);
  }

  // ===== 3) LCD update =====
  static uint32_t lastLcd = 0;
  if (millis() - lastLcd >= 300) {
    lastLcd = millis();
    updateLcd();
  }
}
