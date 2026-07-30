// Sentinela — mapa de pinos da Heltec WiFi LoRa 32 V2
//
// Fonte: docs/HARDWARE.md. Ver as armadilhas A-001, A-002 e A-004 em ERROS.md
// antes de alocar qualquer GPIO novo.
//
// Autoria: Matheus Marassi

#pragma once

// --- Rádio SX1276 (SPI) ---
#define LORA_SCK 5
#define LORA_MISO 19
#define LORA_MOSI 27
#define LORA_NSS 18
#define LORA_RST 14
#define LORA_DIO0 26
#define LORA_DIO1 35
#define LORA_DIO2 34

// --- Display OLED SSD1306 (I2C dedicado) ---
#define OLED_SDA 4
#define OLED_SCL 15
#define OLED_RST 16

// --- Energia e sinalização ---
#define PIN_VEXT 21  // ATENCAO: ativo em nivel BAIXO (armadilha A-004)
#define PIN_LED 25
#define PIN_PRG 0
#define PIN_VBAT_ADC 37

// --- Barramento I2C dos sensores externos ---
// Separado do OLED de proposito: sensor travado em campo nao pode derrubar o
// display de diagnostico (armadilha A-008).
#define SENSOR_SDA 22
#define SENSOR_SCL 23

// --- Parametros de radio (ADR-003) ---
// 916,8 MHz = canal 8 do plano AU915, dentro da faixa 915-928 MHz permitida
// pela Anatel. A janela 907,5-915 MHz NAO e permitida (armadilha A-006).
#define LORA_FREQ_MHZ 916.8
#define LORA_BW_KHZ 125.0
#define LORA_SF 9
#define LORA_CR 7
#define LORA_SYNC_WORD 0x12  // rede privada
#define LORA_TX_POWER_DBM 17
#define LORA_PREAMBLE_LEN 8

inline void vextOn() {
  pinMode(PIN_VEXT, OUTPUT);
  digitalWrite(PIN_VEXT, LOW);  // LOW liga
}

inline void vextOff() {
  pinMode(PIN_VEXT, OUTPUT);
  digitalWrite(PIN_VEXT, HIGH);
}
