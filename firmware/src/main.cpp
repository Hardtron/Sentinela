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
// Um terceiro papel, ROLE_BENCH, existe para placas SEM antena conectada:
// inicializa o rádio e escuta passivamente, mas nunca chama radio.transmit()
// — transmitir sem antena degrada o PA (armadilha A-003). Com 6 placas e
// apenas 2 antenas no inventário (HARDWARE.md), é o que permite validar as
// demais 4 placas — flash, OLED, I2C dos sensores, ADC — sem risco.
//
// O display é a interface de campo (ver ui_dev.h) e o botão PRG alterna entre
// as páginas. A saída serial é CSV, para registro do ensaio.
//
// Autoria: Luiz Matheus Marassi de Paula

#include <Arduino.h>
#include <RadioLib.h>
#include <SPI.h>
#include <Wire.h>

#include "board_heltec_v2.h"
#include "ui_dev.h"

#if !defined(ROLE_PINGER) && !defined(ROLE_PONGER) && !defined(ROLE_BENCH)
#error "Defina ROLE_PINGER, ROLE_PONGER ou ROLE_BENCH no platformio.ini"
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

#if defined(ROLE_PINGER)
// Piso de 1500 ms bastava com o toa medido em SF9 (~170 ms), mas encolhe
// demais em SF11/12 — la o toa sozinho ja se aproxima do teto, e o pong
// simplesmente nao cabe na janela. Isso gera "perda" que e do software
// esperando de menos, nao do radio: contaminaria justamente o dado que a
// varredura SF7-SF12 existe para medir. Recalculado em setup() a partir do
// toa real da placa (ver LOG.md).
static uint32_t timeoutPongMs = 1500;
#endif

IRAM_ATTR void onPacketEvent() { packetReady = true; }

// -------------------------------------------------------------- auxiliares --

/// Leitura aproximada da bateria. O divisor da Heltec V2 não foi caracterizado,
/// então o valor é exibido rotulado como não calibrado (RC-07). Calibrar antes
/// de qualquer decisão baseada em tensão.
static float readBattery() {
  int bruto = analogRead(PIN_VBAT_ADC);
  return bruto * (3.3f / 4095.0f) * VBAT_FATOR_DIVISOR * VBAT_CALIBRACAO;
}

/// Sensor de temperatura interno do ESP32 (nao e o mesmo circuito da bateria).
/// Estimativa de fabrica, sem calibracao propria — serve para acompanhar
/// tendencia (aquecendo/esfriando), nao como medicao de precisao.
static float readTempChip() { return temperatureRead(); }

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
      uiRegistrarAtividade();
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

#if defined(ROLE_BENCH)
/// Varre o barramento I2C dos sensores externos (Wire1, GPIO 22/23) e guarda
/// os primeiros endereços encontrados. Roda uma vez no boot — é teste de
/// bancada, não precisa repetir a cada quadro.
static void escaneiaI2C() {
  ui.i2cCount = 0;
  for (uint8_t addr = 1; addr < 127 && ui.i2cCount < 4; addr++) {
    Wire1.beginTransmission(addr);
    if (Wire1.endTransmission() == 0) {
      ui.i2cAddr[ui.i2cCount++] = addr;
    }
  }
}
#endif  // ROLE_BENCH

#if defined(ROLE_PINGER)
/// Espera mantendo a interface viva. Um laço com delay() cego deixaria o botão
/// sem resposta justamente durante o intervalo entre pings, que é quando o
/// operador está olhando para a tela.
static void idleWithUi(uint32_t ms) {
  uint32_t fim = millis() + ms;
  uint32_t proximoDesenho = 0;
  while ((int32_t)(millis() - fim) < 0) {
    pollButton();
    uiChecaInatividade();
    if ((int32_t)(millis() - proximoDesenho) >= 0) {
      ui.vbat = readBattery();
      ui.tempChipC = readTempChip();
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

#if defined(ROLE_PINGER) || defined(ROLE_PONGER)
/// Só existe nos papéis que transmitem. Em ROLE_BENCH nem é compilada — é o
/// compilador confirmando, em tempo de build, que não há caminho de TX.
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
#endif  // ROLE_PINGER || ROLE_PONGER

// -------------------------------------------------------------------- setup --

void setup() {
  Serial.begin(115200);
  delay(200);

  bootCount++;

  memset(&ui, 0, sizeof(ui));
  ui.nodeId = NODE_ID;
#if defined(ROLE_PINGER)
  ui.papel = "PING";
#elif defined(ROLE_PONGER)
  ui.papel = "PONG";
#else
  ui.papel = "BENCH";
#endif
  ui.bootCount = bootCount;

  pinMode(PIN_LED, OUTPUT);
  digitalWrite(PIN_LED, LOW);
  pinMode(PIN_PRG, INPUT_PULLUP);

  uiBegin();
  uiSplash("Fase 0 - bring-up", "iniciando radio...");

  Serial.println();
  Serial.println(F("# Sentinela - bring-up Fase 0"));
  Serial.printf("# no=%d papel=%s boots=%lu\n", NODE_ID, ui.papel,
                (unsigned long)bootCount);

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
#if defined(ROLE_PINGER)
  // 3x o toa do pong + folga fixa: cobre o tempo no ar mais a incerteza de
  // deteccao de preambulo, sem exigir que o operador calcule isso por SF.
  timeoutPongMs = (uint32_t)(ui.toaMs * 3 + 200);
#endif

  Serial.println(F("# radio ok"));
  Serial.printf("# freq=%.1fMHz sf=%d bw=%.0fkHz cr=4/%d pot=%ddBm toa=%lums\n",
                (double)LORA_FREQ_MHZ, LORA_SF, (double)LORA_BW_KHZ, LORA_CR,
                LORA_TX_POWER_DBM, (unsigned long)ui.toaMs);
  Serial.println(
      F("# seq,rssi_local_dbm,snr_local_db,rssi_remoto_dbm,snr_remoto_db,"
        "enviados,recebidos"));

  radio.setPacketReceivedAction(onPacketEvent);
  radio.startReceive();

#if defined(ROLE_BENCH)
  Wire1.begin(SENSOR_SDA, SENSOR_SCL);
  escaneiaI2C();
  Serial.printf("# bancada: %u sensor(es) no barramento I2C externo\n",
                (unsigned)ui.i2cCount);
#endif

  ui.vbat = readBattery();
  ui.tempChipC = readTempChip();
  uiRegistrarAtividade();
  uiDraw(ui);
}

// ---------------------------------------------------------------- principal --

#if defined(ROLE_PINGER)

static const uint32_t INTERVALO_PING_MS = 3000;

void loop() {
  ui.seq++;
  ui.sent++;
  packetReady = false;
  sendPacket(KIND_PING, ui.seq);

  bool recebeuPong = false;
  uint32_t limite = millis() + timeoutPongMs;
  uint32_t proximoDesenho = 0;

  while ((int32_t)(millis() - limite) < 0) {
    pollButton();
    uiChecaInatividade();
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

#elif defined(ROLE_PONGER)

void loop() {
  static uint32_t proximoDesenho = 0;
  static uint32_t proximoHeartbeat = 0;

  pollButton();
  uiChecaInatividade();

  // Silêncio no receptor é ambíguo: pode ser transmissor desligado, pode ser
  // rádio que não entrou em recepção. O piso de ruído do canal desfaz a
  // ambiguidade — se ele varia, o receptor está de fato escutando.
  if ((int32_t)(millis() - proximoHeartbeat) >= 0) {
    // O `sf=` repetido aqui não é redundância: a bridge pode ser reiniciada
    // com a placa já rodando, e nesse caso ela nunca veria o banner de boot.
    // Reanunciar o parâmetro faz a telemetria se autodescrever mesmo assim —
    // e é o SF que define a sensibilidade contra a qual a margem é medida.
    Serial.printf("# rx ativo | ruido %.0f dBm | recebidos %lu | sf=%d\n",
                  (double)radio.getRSSI(false, false),
                  (unsigned long)ui.received, LORA_SF);
    proximoHeartbeat = millis() + 5000;
  }

  if (!packetReady) {
    if ((int32_t)(millis() - proximoDesenho) >= 0) {
      ui.vbat = readBattery();
      ui.tempChipC = readTempChip();
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

#else  // ROLE_BENCH

/// Só recebe. `sendPacket()` nunca é chamado neste papel — é essa ausência
/// que torna seguro rodar sem antena (A-003).
void loop() {
  static uint32_t proximoDesenho = 0;

  pollButton();
  uiChecaInatividade();

  if (packetReady) {
    packetReady = false;
    Packet pkt;
    if (readPacket(pkt)) ui.received++;
    radio.startReceive();
  }

  if ((int32_t)(millis() - proximoDesenho) >= 0) {
    ui.vbat = readBattery();
    ui.tempChipC = readTempChip();
    uiDraw(ui);
    proximoDesenho = millis() + 150;
  }
  delay(5);
}

#endif
