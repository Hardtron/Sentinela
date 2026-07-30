// Sentinela — firmware de bring-up (Fase 0)
//
// Objetivo desta etapa: provar que o rádio, o display e o enlace funcionam, e
// medir o alcance real em campo. Não há sensor nem sono ainda — isso é a
// Fase 1 (docs/PLANO.md).
//
// O nó PINGER transmite periodicamente e espera resposta. O nó PONGER responde
// devolvendo o RSSI/SNR com que ouviu o ping. Assim cada troca mede o enlace
// nos DOIS sentidos, que é o que interessa no teste de alcance: o link pode ser
// assimétrico, e descobrir isso em campo custa caro depois.
//
// A saída serial do PINGER é CSV, para registro direto do ensaio de campo.
//
// Autoria: Matheus Marassi

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <U8g2lib.h>

#include "board_heltec_v2.h"

#if !defined(ROLE_PINGER) && !defined(ROLE_PONGER)
#error "Defina ROLE_PINGER ou ROLE_PONGER no platformio.ini"
#endif

// ---------------------------------------------------------------- protocolo --
// Formato provisório da Fase 0. O protocolo definitivo vive em lib/proto/ e
// reserva espaço para autenticação desde o início (RC-11).

static const uint8_t PKT_MAGIC = 0x53;  // 'S' de Sentinela
static const uint8_t PKT_VERSION = 1;

enum PacketKind : uint8_t { KIND_PING = 0, KIND_PONG = 1 };

struct __attribute__((packed)) Packet {
  uint8_t magic;
  uint8_t version;
  uint8_t srcId;
  uint8_t kind;
  uint32_t seq;
  int16_t rssiEcho;  // RSSI com que o remetente ouviu o pacote anterior (dBm)
  int8_t snrEcho;    // SNR idem (dB, arredondado)
};

// ------------------------------------------------------------------ globais --

SX1276 radio = new Module(LORA_NSS, LORA_DIO0, LORA_RST, LORA_DIO1);
U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, OLED_RST, OLED_SCL, OLED_SDA);

volatile bool packetReady = false;
uint32_t seqCounter = 0;
uint32_t sent = 0;
uint32_t received = 0;
float lastRssiLocal = 0;
float lastSnrLocal = 0;
int16_t lastRssiRemote = 0;
int8_t lastSnrRemote = 0;

IRAM_ATTR void onPacketEvent() { packetReady = true; }

// -------------------------------------------------------------------- OLED --

static void drawStatus(const char *state) {
  oled.clearBuffer();
  oled.setFont(u8g2_font_6x10_tf);

  char line[32];
  snprintf(line, sizeof(line), "Sentinela  no %d", NODE_ID);
  oled.drawStr(0, 9, line);
  oled.drawHLine(0, 12, 128);

#if defined(ROLE_PINGER)
  oled.drawStr(0, 24, "papel: PINGER");
#else
  oled.drawStr(0, 24, "papel: PONGER");
#endif

  snprintf(line, sizeof(line), "%.1f MHz SF%d", (double)LORA_FREQ_MHZ, LORA_SF);
  oled.drawStr(0, 35, line);

  snprintf(line, sizeof(line), "rx %ld dBm  %.0f dB", (long)lastRssiLocal,
           (double)lastSnrLocal);
  oled.drawStr(0, 46, line);

  snprintf(line, sizeof(line), "remoto %d dBm", lastRssiRemote);
  oled.drawStr(0, 57, line);

  oled.drawStr(96, 24, state);
  oled.sendBuffer();
}

// -------------------------------------------------------------------- setup --

void setup() {
  Serial.begin(115200);
  delay(200);

  vextOn();  // LOW liga os periféricos (armadilha A-004)
  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);

  oled.begin();
  drawStatus("init");

  Serial.println();
  Serial.println(F("# Sentinela - bring-up Fase 0"));
  Serial.printf("# no=%d papel=%s\n", NODE_ID,
#if defined(ROLE_PINGER)
                "PINGER"
#else
                "PONGER"
#endif
  );

  // A Heltec V2 não usa os pinos VSPI padrão do ESP32: o SPI precisa ser
  // inicializado explicitamente antes do rádio.
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  int state = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR,
                          LORA_SYNC_WORD, LORA_TX_POWER_DBM, LORA_PREAMBLE_LEN);
  if (state != RADIOLIB_ERR_NONE) {
    Serial.printf("# ERRO: radio.begin falhou, codigo %d\n", state);
    oled.clearBuffer();
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(0, 20, "FALHA NO RADIO");
    char line[32];
    snprintf(line, sizeof(line), "codigo %d", state);
    oled.drawStr(0, 34, line);
    oled.sendBuffer();
    while (true) {  // falha de rádio é terminal: piscar e parar
      digitalWrite(PIN_LED, HIGH);
      delay(120);
      digitalWrite(PIN_LED, LOW);
      delay(880);
    }
  }

  Serial.println(F("# radio ok"));
  Serial.println(F("# seq,rssi_local_dbm,snr_local_db,rssi_remoto_dbm,snr_remoto_db,enviados,recebidos"));

  radio.setPacketReceivedAction(onPacketEvent);
  radio.startReceive();
  drawStatus("rx");
}

// --------------------------------------------------------------- utilitário --

static bool readPacket(Packet &pkt) {
  uint8_t buf[sizeof(Packet)];
  int state = radio.readData(buf, sizeof(buf));
  if (state != RADIOLIB_ERR_NONE) return false;

  memcpy(&pkt, buf, sizeof(pkt));
  if (pkt.magic != PKT_MAGIC || pkt.version != PKT_VERSION) return false;

  lastRssiLocal = radio.getRSSI();
  lastSnrLocal = radio.getSNR();
  return true;
}

static void sendPacket(uint8_t kind, uint32_t seq) {
  Packet pkt;
  pkt.magic = PKT_MAGIC;
  pkt.version = PKT_VERSION;
  pkt.srcId = NODE_ID;
  pkt.kind = kind;
  pkt.seq = seq;
  pkt.rssiEcho = (int16_t)lastRssiLocal;
  pkt.snrEcho = (int8_t)lastSnrLocal;

  digitalWrite(PIN_LED, HIGH);
  radio.transmit((uint8_t *)&pkt, sizeof(pkt));
  digitalWrite(PIN_LED, LOW);
  radio.startReceive();
}

// ---------------------------------------------------------------- principal --

#if defined(ROLE_PINGER)

static const uint32_t PING_INTERVAL_MS = 3000;
static const uint32_t PONG_TIMEOUT_MS = 1500;

void loop() {
  seqCounter++;
  sent++;
  drawStatus("tx");
  packetReady = false;
  sendPacket(KIND_PING, seqCounter);

  bool gotPong = false;
  uint32_t deadline = millis() + PONG_TIMEOUT_MS;
  while (millis() < deadline) {
    if (packetReady) {
      packetReady = false;
      Packet pkt;
      if (readPacket(pkt) && pkt.kind == KIND_PONG && pkt.seq == seqCounter) {
        lastRssiRemote = pkt.rssiEcho;
        lastSnrRemote = pkt.snrEcho;
        received++;
        gotPong = true;
        break;
      }
    }
    delay(5);
  }

  if (gotPong) {
    // CSV para registro do ensaio de campo
    Serial.printf("%lu,%.1f,%.1f,%d,%d,%lu,%lu\n", (unsigned long)seqCounter,
                  (double)lastRssiLocal, (double)lastSnrLocal, lastRssiRemote,
                  lastSnrRemote, (unsigned long)sent, (unsigned long)received);
    drawStatus("ok");
  } else {
    Serial.printf("%lu,,,,,%lu,%lu\n", (unsigned long)seqCounter,
                  (unsigned long)sent, (unsigned long)received);
    drawStatus("--");
  }

  delay(PING_INTERVAL_MS);
}

#else  // ROLE_PONGER

void loop() {
  if (!packetReady) {
    delay(5);
    return;
  }
  packetReady = false;

  Packet pkt;
  if (!readPacket(pkt) || pkt.kind != KIND_PING) {
    radio.startReceive();
    return;
  }

  received++;
  drawStatus("tx");
  sendPacket(KIND_PONG, pkt.seq);
  sent++;

  Serial.printf("%lu,%.1f,%.1f,,,%lu,%lu\n", (unsigned long)pkt.seq,
                (double)lastRssiLocal, (double)lastSnrLocal,
                (unsigned long)sent, (unsigned long)received);
  drawStatus("rx");
}

#endif
