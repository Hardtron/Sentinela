// Sentinela — interface de diagnóstico no OLED
// Ver ui_dev.h para o racional. Autoria: Matheus Marassi

#include "ui_dev.h"

#include <Arduino.h>
#include <U8g2lib.h>

#include "board_heltec_v2.h"

static U8G2_SSD1306_128X64_NONAME_F_HW_I2C oled(U8G2_R0, OLED_RST, OLED_SCL,
                                                OLED_SDA);

// --- histórico de RSSI para o gráfico -----------------------------------
static const uint8_t HIST_LEN = 128;  // uma amostra por coluna do display
static int16_t hist[HIST_LEN];
static uint8_t histCount = 0;
static uint8_t histHead = 0;

// Faixa vertical do gráfico, em dBm. Cobre desde o limite de sensibilidade
// até um sinal forte de bancada.
static const int16_t RSSI_PIOR = -140;
static const int16_t RSSI_MELHOR = -30;

enum Page : uint8_t {
  PAGE_LINK = 0,
  PAGE_GRAPH,
  PAGE_RADIO,
  PAGE_SYS,
  PAGE_COUNT
};

static uint8_t page = PAGE_LINK;

// -------------------------------------------------------------- auxiliares --

float uiSensitivityDbm(uint8_t sf) {
  // Valores típicos do SX1276 em BW 125 kHz (datasheet).
  switch (sf) {
    case 7: return -123.0f;
    case 8: return -126.0f;
    case 9: return -129.0f;
    case 10: return -132.0f;
    case 11: return -134.5f;
    case 12: return -137.0f;
    default: return -129.0f;
  }
}

static int mapRssiToY(int16_t rssi, int yTopo, int yBase) {
  if (rssi > RSSI_MELHOR) rssi = RSSI_MELHOR;
  if (rssi < RSSI_PIOR) rssi = RSSI_PIOR;
  long faixa = RSSI_MELHOR - RSSI_PIOR;
  long pos = (long)(rssi - RSSI_PIOR) * (yBase - yTopo) / faixa;
  return yBase - (int)pos;
}

static void cabecalho(const char *titulo, const UiState &s) {
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawStr(0, 6, titulo);

  char dir[20];
  snprintf(dir, sizeof(dir), "n%u %s", (unsigned)s.nodeId,
           s.isPinger ? "PING" : "PONG");
  int w = oled.getStrWidth(dir);
  oled.drawStr(128 - w, 6, dir);

  oled.drawHLine(0, 8, 128);
}

/// Rodapé com o indicador de página — mostra onde se está sem ocupar espaço.
static void indicadorPagina() {
  for (uint8_t i = 0; i < PAGE_COUNT; i++) {
    int x = 100 + i * 7;
    if (i == page) {
      oled.drawBox(x, 60, 5, 3);
    } else {
      oled.drawPixel(x + 2, 61);
    }
  }
}

// ------------------------------------------------------------------ páginas --

// Página 1 — o enlace. É a que fica na tela durante o teste de alcance:
// o número grande é o RSSI, e a barra é a margem até perder o link.
static void pagLink(const UiState &s) {
  cabecalho("ENLACE", s);

  char buf[24];

  if (s.received == 0) {
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(0, 30, "aguardando pacote");
  } else {
    oled.setFont(u8g2_font_10x20_tf);
    snprintf(buf, sizeof(buf), "%d", (int)s.rssiLocal);
    oled.drawStr(0, 28, buf);
    int w = oled.getStrWidth(buf);
    oled.setFont(u8g2_font_5x7_tf);
    oled.drawStr(w + 3, 28, "dBm");

    // SNR à direita, no mesmo bloco
    oled.setFont(u8g2_font_6x10_tf);
    snprintf(buf, sizeof(buf), "SNR %+.0f", (double)s.snrLocal);
    oled.drawStr(78, 27, buf);
  }

  // Barra de margem de enlace: quanto ainda sobra acima da sensibilidade.
  float margem = s.rssiLocal - uiSensitivityDbm(LORA_SF);
  if (s.received == 0) margem = 0;
  if (margem < 0) margem = 0;
  if (margem > 50) margem = 50;  // 50 dB de margem já é sinal muito forte
  int larg = (int)(margem * 126.0f / 50.0f);

  oled.drawFrame(0, 32, 128, 9);
  if (larg > 0) oled.drawBox(1, 33, larg, 7);

  oled.setFont(u8g2_font_5x7_tf);
  snprintf(buf, sizeof(buf), "margem %d dB", (int)(s.rssiLocal - uiSensitivityDbm(LORA_SF)));
  if (s.received == 0) snprintf(buf, sizeof(buf), "margem --");
  oled.drawStr(0, 50, buf);

  // Eco: como o outro lado nos ouve. Link assimétrico aparece aqui.
  if (s.received > 0) {
    snprintf(buf, sizeof(buf), "remoto %d dBm", s.rssiRemote);
    oled.drawStr(0, 58, buf);
  }

  // Perda — o indicador que condena um ponto de instalação.
  uint32_t perdidos = s.sent - s.received;
  if (s.sent > 0) {
    snprintf(buf, sizeof(buf), "%lu/%lu", (unsigned long)perdidos,
             (unsigned long)s.sent);
    int w = oled.getStrWidth(buf);
    oled.drawStr(96 - w, 50, buf);
  }

  indicadorPagina();
}

// Página 2 — histórico. Caminhando em campo, a forma da curva mostra onde o
// sinal caiu; um degrau denuncia obstrução, não distância.
static void pagGraph(const UiState &s) {
  cabecalho("HISTORICO RSSI", s);

  const int yTopo = 12;
  const int yBase = 52;

  oled.drawHLine(0, yBase, 128);

  if (histCount == 0) {
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(0, 34, "sem amostras");
    indicadorPagina();
    return;
  }

  int16_t menor = 32767, maior = -32768;
  long soma = 0;
  int xInicial = HIST_LEN - histCount;

  for (uint8_t i = 0; i < histCount; i++) {
    uint8_t idx = (uint8_t)((histHead + HIST_LEN - histCount + i) % HIST_LEN);
    int16_t v = hist[idx];
    if (v < menor) menor = v;
    if (v > maior) maior = v;
    soma += v;
    int y = mapRssiToY(v, yTopo, yBase);
    oled.drawVLine(xInicial + i, y, yBase - y);
  }

  char buf[26];
  oled.setFont(u8g2_font_5x7_tf);
  snprintf(buf, sizeof(buf), "min%d med%d max%d", menor,
           (int)(soma / histCount), maior);
  oled.drawStr(0, 62, buf);

  indicadorPagina();
}

// Página 3 — parâmetros de rádio. Confere de imediato se a placa está na
// configuração que se pensa que está, incluindo a frequência legal.
static void pagRadio(const UiState &s) {
  cabecalho("RADIO", s);

  char buf[26];
  oled.setFont(u8g2_font_6x10_tf);

  snprintf(buf, sizeof(buf), "%.1f MHz  SF%d", (double)LORA_FREQ_MHZ, LORA_SF);
  oled.drawStr(0, 20, buf);

  snprintf(buf, sizeof(buf), "BW%d CR4/%d %ddBm", (int)LORA_BW_KHZ, LORA_CR,
           LORA_TX_POWER_DBM);
  oled.drawStr(0, 31, buf);

  snprintf(buf, sizeof(buf), "tempo no ar %lu ms", (unsigned long)s.toaMs);
  oled.drawStr(0, 42, buf);

  snprintf(buf, sizeof(buf), "sensib %.0f dBm", (double)uiSensitivityDbm(LORA_SF));
  oled.drawStr(0, 53, buf);

  indicadorPagina();
}

// Página 4 — saúde do nó. É o embrião da telemetria exigida por RC-03.
static void pagSys(const UiState &s) {
  cabecalho("SISTEMA", s);

  char buf[26];
  oled.setFont(u8g2_font_6x10_tf);

  uint32_t seg = millis() / 1000;
  snprintf(buf, sizeof(buf), "ativo %02lu:%02lu:%02lu",
           (unsigned long)(seg / 3600), (unsigned long)((seg / 60) % 60),
           (unsigned long)(seg % 60));
  oled.drawStr(0, 20, buf);

  snprintf(buf, sizeof(buf), "heap %lu KB",
           (unsigned long)(ESP.getFreeHeap() / 1024));
  oled.drawStr(0, 31, buf);

  snprintf(buf, sizeof(buf), "boots %lu", (unsigned long)s.bootCount);
  oled.drawStr(0, 42, buf);

  // Rotulado como não calibrado de propósito: valor plausível porém errado é
  // pior que valor ausente (RC-07).
  snprintf(buf, sizeof(buf), "vbat ~%.2fV nc", (double)s.vbat);
  oled.drawStr(0, 53, buf);

  indicadorPagina();
}

// -------------------------------------------------------------------- API --

void uiBegin() {
  vextOn();
  oled.begin();
  oled.clearBuffer();
  oled.sendBuffer();
}

void uiPushRssi(float rssi) {
  hist[histHead] = (int16_t)rssi;
  histHead = (uint8_t)((histHead + 1) % HIST_LEN);
  if (histCount < HIST_LEN) histCount++;
}

void uiNextPage() { page = (uint8_t)((page + 1) % PAGE_COUNT); }

void uiDraw(const UiState &s) {
  oled.clearBuffer();
  switch (page) {
    case PAGE_LINK: pagLink(s); break;
    case PAGE_GRAPH: pagGraph(s); break;
    case PAGE_RADIO: pagRadio(s); break;
    default: pagSys(s); break;
  }
  oled.sendBuffer();
}

void uiSplash(const char *linha1, const char *linha2) {
  oled.clearBuffer();
  oled.setFont(u8g2_font_10x20_tf);
  oled.drawStr(0, 22, "Sentinela");
  oled.setFont(u8g2_font_6x10_tf);
  if (linha1) oled.drawStr(0, 40, linha1);
  if (linha2) oled.drawStr(0, 52, linha2);
  oled.sendBuffer();
}

void uiFatal(const char *titulo, const char *detalhe) {
  oled.clearBuffer();
  oled.drawFrame(0, 0, 128, 64);
  oled.setFont(u8g2_font_6x10_tf);
  oled.drawStr(6, 22, titulo);
  if (detalhe) oled.drawStr(6, 38, detalhe);
  oled.sendBuffer();
}
