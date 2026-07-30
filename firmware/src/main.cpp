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
// O display é a interface de campo (ver ui_dev.h) e o botão PRG alterna entre
// as páginas. A saída serial é CSV, para registro do ensaio.
//
// Autoria: Matheus Marassi

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>

#include "board_heltec_v2.h"
#include "ui_dev.h"

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

volatile bool packetReady = false;
static UiState ui;
RTC_DATA_ATTR static uint32_t bootCount = 0;

IRAM_ATTR void onPacketEvent() { packetReady = true; }

// -------------------------------------------------------------- auxiliares --

/// Leitura aproximada da bateria. O divisor da Heltec V2 não foi caracterizado,
/// então o valor é exibido rotulado como não calibrado (RC-07). Calibrar antes
/// de qualquer decisão baseada em tensão.
static float readBattery() {
  int bruto = analogRead(PIN_VBAT_ADC);
  return bruto * (3.3f / 4095.0f) * VBAT_FATOR_DIVISOR * VBAT_CALIBRACAO;
}

/// Inicia um novo ponto de medição: zera as estatísticas para que o resumo na
/// tela descreva apenas este ponto, e marca a transição no CSV.
static void novoPonto() {
  ui.ponto++;
  ui.sent = 0;
  ui.received = 0;
  uiResetHist();
  Serial.printf("# ===== PONTO %u =====\n", (unsigned)ui.ponto);
}

/// Toque curto muda de página; toque longo (>1 s) marca um novo ponto de
/// medição. Um botão só, duas funções — é o único disponível na placa.
static void pollButton() {
  static int anterior = HIGH;
  static uint32_t ultimaMudanca = 0;
  static uint32_t instantePressao = 0;

  int agora = digitalRead(PIN_PRG);
  if (agora != anterior && (millis() - ultimaMudanca) > 50) {
    ultimaMudanca = millis();
    anterior = agora;
    if (agora == LOW) {
      instantePressao = millis();
    } else {
      uint32_t duracao = millis() - instantePressao;
      if (duracao >= 1000) {
        novoPonto();
        // Pisca longo confirma a marcação sem exigir olhar para a tela.
        digitalWrite(PIN_LED, HIGH);
        delay(250);
        digitalWrite(PIN_LED, LOW);
      } else {
        uiNextPage();
      }
    }
  }
}

#if defined(ROLE_PINGER)
/// Espera mantendo a interface viva. Um laço com delay() cego deixaria o botão
/// sem resposta justamente durante o intervalo entre pings, que é quando o
/// operador está olhando para a tela.
static void idleWithUi(uint32_t ms) {
  uint32_t fim = millis() + ms;
  uint32_t proximoDesenho = 0;
  while ((int32_t)(millis() - fim) < 0) {
    pollButton();
    if ((int32_t)(millis() - proximoDesenho) >= 0) {
      ui.vbat = readBattery();
      uiDraw(ui);
      proximoDesenho = millis() + 150;
    }
    delay(5);
  }
}
#endif  // ROLE_PINGER

static bool readPacket(Packet &pkt) {
  uint8_t buf[sizeof(Packet)];
  int estado = radio.readData(buf, sizeof(buf));
  if (estado != RADIOLIB_ERR_NONE) return false;

  memcpy(&pkt, buf, sizeof(pkt));
  if (pkt.magic != PKT_MAGIC || pkt.version != PKT_VERSION) return false;

  ui.rssiLocal = radio.getRSSI();
  ui.snrLocal = radio.getSNR();
  uiPushRssi(ui.rssiLocal);
  return true;
}

static void sendPacket(uint8_t kind, uint32_t seq) {
  Packet pkt;
  pkt.magic = PKT_MAGIC;
  pkt.version = PKT_VERSION;
  pkt.srcId = NODE_ID;
  pkt.kind = kind;
  pkt.seq = seq;
  pkt.rssiEcho = (int16_t)ui.rssiLocal;
  pkt.snrEcho = (int8_t)ui.snrLocal;

  digitalWrite(PIN_LED, HIGH);
  radio.transmit((uint8_t *)&pkt, sizeof(pkt));
  digitalWrite(PIN_LED, LOW);
  radio.startReceive();
}

// -------------------------------------------------------------------- setup --

void setup() {
  Serial.begin(115200);
  delay(200);

  bootCount++;

  memset(&ui, 0, sizeof(ui));
  ui.nodeId = NODE_ID;
#if defined(ROLE_PINGER)
  ui.isPinger = true;
#else
  ui.isPinger = false;
#endif
  ui.bootCount = bootCount;

  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  pinMode(PIN_PRG, INPUT_PULLUP);

  uiBegin();
  uiSplash("Fase 0 - bring-up", "iniciando radio...");

  Serial.println();
  Serial.println(F("# Sentinela - bring-up Fase 0"));
  Serial.printf("# no=%d papel=%s boots=%lu\n", NODE_ID,
                ui.isPinger ? "PINGER" : "PONGER", (unsigned long)bootCount);

  // A Heltec V2 não usa os pinos VSPI padrão do ESP32: o SPI precisa ser
  // inicializado explicitamente antes do rádio.
  SPI.begin(LORA_SCK, LORA_MISO, LORA_MOSI, LORA_NSS);

  int estado = radio.begin(LORA_FREQ_MHZ, LORA_BW_KHZ, LORA_SF, LORA_CR,
                           LORA_SYNC_WORD, LORA_TX_POWER_DBM, LORA_PREAMBLE_LEN);
  if (estado != RADIOLIB_ERR_NONE) {
    Serial.printf("# ERRO: radio.begin falhou, codigo %d\n", estado);
    char detalhe[24];
    snprintf(detalhe, sizeof(detalhe), "codigo %d", estado);
    uiFatal("FALHA NO RADIO", detalhe);
    while (true) {  // falha de rádio é terminal: piscar e parar
      digitalWrite(PIN_LED, HIGH);
      delay(120);
      digitalWrite(PIN_LED, LOW);
      delay(880);
    }
  }

  ui.toaMs = radio.getTimeOnAir(sizeof(Packet)) / 1000;

  Serial.println(F("# radio ok"));
  Serial.printf("# freq=%.1fMHz sf=%d bw=%.0fkHz cr=4/%d pot=%ddBm toa=%lums\n",
                (double)LORA_FREQ_MHZ, LORA_SF, (double)LORA_BW_KHZ, LORA_CR,
                LORA_TX_POWER_DBM, (unsigned long)ui.toaMs);
  Serial.println(
      F("# seq,rssi_local_dbm,snr_local_db,rssi_remoto_dbm,snr_remoto_db,"
        "enviados,recebidos"));

  radio.setPacketReceivedAction(onPacketEvent);
  radio.startReceive();

  ui.vbat = readBattery();
  uiDraw(ui);
}

// ---------------------------------------------------------------- principal --

#if defined(ROLE_PINGER)

static const uint32_t INTERVALO_PING_MS = 3000;
static const uint32_t TIMEOUT_PONG_MS = 1500;

void loop() {
  ui.seq++;
  ui.sent++;
  packetReady = false;
  sendPacket(KIND_PING, ui.seq);

  bool recebeuPong = false;
  uint32_t limite = millis() + TIMEOUT_PONG_MS;
  uint32_t proximoDesenho = 0;

  while ((int32_t)(millis() - limite) < 0) {
    pollButton();
    if (packetReady) {
      packetReady = false;
      Packet pkt;
      if (readPacket(pkt) && pkt.kind == KIND_PONG && pkt.seq == ui.seq) {
        ui.rssiRemote = pkt.rssiEcho;
        ui.snrRemote = pkt.snrEcho;
        ui.received++;
        recebeuPong = true;
        break;
      }
    }
    if ((int32_t)(millis() - proximoDesenho) >= 0) {
      uiDraw(ui);
      proximoDesenho = millis() + 150;
    }
    delay(5);
  }

  ui.lastOk = recebeuPong;

  if (recebeuPong) {
    Serial.printf("%lu,%.1f,%.1f,%d,%d,%lu,%lu\n", (unsigned long)ui.seq,
                  (double)ui.rssiLocal, (double)ui.snrLocal, ui.rssiRemote,
                  ui.snrRemote, (unsigned long)ui.sent,
                  (unsigned long)ui.received);
  } else {
    Serial.printf("%lu,,,,,%lu,%lu\n", (unsigned long)ui.seq,
                  (unsigned long)ui.sent, (unsigned long)ui.received);
  }

  idleWithUi(INTERVALO_PING_MS);
}

#else  // ROLE_PONGER

void loop() {
  static uint32_t proximoDesenho = 0;
  static uint32_t proximoHeartbeat = 0;

  pollButton();

  // Silêncio no receptor é ambíguo: pode ser transmissor desligado, pode ser
  // rádio que não entrou em recepção. O piso de ruído do canal desfaz a
  // ambiguidade — se ele varia, o receptor está de fato escutando.
  if ((int32_t)(millis() - proximoHeartbeat) >= 0) {
    Serial.printf("# rx ativo | ruido %.0f dBm | recebidos %lu\n",
                  (double)radio.getRSSI(false, false),
                  (unsigned long)ui.received);
    proximoHeartbeat = millis() + 5000;
  }

  if (!packetReady) {
    if ((int32_t)(millis() - proximoDesenho) >= 0) {
      ui.vbat = readBattery();
      uiDraw(ui);
      proximoDesenho = millis() + 150;
    }
    delay(5);
    return;
  }
  packetReady = false;

  Packet pkt;
  if (!readPacket(pkt) || pkt.kind != KIND_PING) {
    radio.startReceive();
    return;
  }

  ui.seq = pkt.seq;
  ui.received++;
  ui.rssiRemote = pkt.rssiEcho;
  ui.snrRemote = pkt.snrEcho;

  sendPacket(KIND_PONG, pkt.seq);
  ui.sent++;
  ui.lastOk = true;

  Serial.printf("%lu,%.1f,%.1f,%d,%d,%lu,%lu\n", (unsigned long)pkt.seq,
                (double)ui.rssiLocal, (double)ui.snrLocal, ui.rssiRemote,
                ui.snrRemote, (unsigned long)ui.sent,
                (unsigned long)ui.received);

  uiDraw(ui);
}

#endif
