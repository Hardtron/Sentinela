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
  PAGE_PONTO,
  PAGE_GRAPH,
  PAGE_RADIO,
  PAGE_SYS,
  PAGE_BENCH,
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

bool uiHistStats(int16_t &menor, int16_t &media, int16_t &maior, uint8_t &n) {
  if (histCount == 0) return false;
  menor = 32767;
  maior = -32768;
  long soma = 0;
  for (uint8_t i = 0; i < histCount; i++) {
    uint8_t idx = (uint8_t)((histHead + HIST_LEN - histCount + i) % HIST_LEN);
    int16_t v = hist[idx];
    if (v < menor) menor = v;
    if (v > maior) maior = v;
    soma += v;
  }
  media = (int16_t)(soma / histCount);
  n = histCount;
  return true;
}

VereditoPonto uiAvaliarPonto(const UiState &s, char *motivo, size_t tam) {
  int16_t menor, media, maior;
  uint8_t n;

  if (!uiHistStats(menor, media, maior, n) || s.received < PONTO_MIN_AMOSTRAS) {
    snprintf(motivo, tam, "COLETANDO %lu/%d", (unsigned long)s.received,
             PONTO_MIN_AMOSTRAS);
    return PONTO_COLETANDO;
  }

  int margem = (int)(media - uiSensitivityDbm(LORA_SF));
  float perda =
      s.sent > 0 ? 100.0f * (float)(s.sent - s.received) / (float)s.sent : 0.0f;
  int assimetria = abs((int)media - (int)s.rssiRemote);

  // Reprovações primeiro: basta uma para condenar o ponto.
  if (perda > PONTO_PERDA_MAX_PCT) {
    snprintf(motivo, tam, "REPROVA perda %.0f%%", (double)perda);
    return PONTO_REPROVADO;
  }
  if (margem < PONTO_MARGEM_MIN_DB) {
    snprintf(motivo, tam, "REPROVA margem %d", margem);
    return PONTO_REPROVADO;
  }
  if (margem < PONTO_MARGEM_BOA_DB) {
    snprintf(motivo, tam, "LIMITE margem %d", margem);
    return PONTO_LIMITE;
  }
  if (assimetria > PONTO_ASSIMETRIA_MAX_DB) {
    snprintf(motivo, tam, "LIMITE assim %d", assimetria);
    return PONTO_LIMITE;
  }

  snprintf(motivo, tam, "APROVADO margem %d", margem);
  return PONTO_APROVADO;
}

static void cabecalho(const char *titulo, const UiState &s) {
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawStr(0, 6, titulo);

  char dir[20];
  snprintf(dir, sizeof(dir), "P%u n%u %s", (unsigned)s.ponto, (unsigned)s.nodeId,
           s.papel);
  int w = oled.getStrWidth(dir);
  oled.drawStr(128 - w, 6, dir);

  oled.drawHLine(0, 8, 128);
}

/// Rodapé com o indicador de página — mostra onde se está sem ocupar espaço.
static void indicadorPagina() {
  for (uint8_t i = 0; i < PAGE_COUNT; i++) {
    int x = 128 - PAGE_COUNT * 7 + i * 7;
    if (i == page) {
      oled.drawBox(x, 60, 5, 3);
    } else {
      oled.drawPixel(x + 2, 61);
    }
  }
}

// ------------------------------------------------------------------ páginas --

// --- blocos da página de enlace ------------------------------------------
// Divididos por complexidade ciclomática (docs/QUALIDADE_CODIGO.md): a versão
// monolítica desta página chegava a CC 12, acima do limite do projeto.

/// Bloco superior: RSSI em fonte grande e SNR.
static void blocoRssi(const UiState &s) {
  char buf[24];
  if (s.received == 0) {
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(0, 30, "aguardando pacote");
    return;
  }
  oled.setFont(u8g2_font_10x20_tf);
  snprintf(buf, sizeof(buf), "%d", (int)s.rssiLocal);
  oled.drawStr(0, 28, buf);
  int w = oled.getStrWidth(buf);
  oled.setFont(u8g2_font_5x7_tf);
  oled.drawStr(w + 3, 28, "dBm");

  oled.setFont(u8g2_font_6x10_tf);
  snprintf(buf, sizeof(buf), "SNR %+.0f", (double)s.snrLocal);
  oled.drawStr(78, 27, buf);
}

/// Barra de margem: quanto sobra acima da sensibilidade do SF em uso.
static void blocoMargem(const UiState &s) {
  const float MARGEM_CHEIA_DB = 50.0f;  // acima disto a barra satura
  float margem = (s.received == 0) ? 0.0f
                                   : s.rssiLocal - uiSensitivityDbm(LORA_SF);
  if (margem < 0) margem = 0;
  if (margem > MARGEM_CHEIA_DB) margem = MARGEM_CHEIA_DB;

  oled.drawFrame(0, 32, 128, 9);
  int larg = (int)(margem * 126.0f / MARGEM_CHEIA_DB);
  if (larg > 0) oled.drawBox(1, 33, larg, 7);

  char buf[24];
  oled.setFont(u8g2_font_5x7_tf);
  if (s.received == 0) {
    snprintf(buf, sizeof(buf), "margem --");
  } else {
    snprintf(buf, sizeof(buf), "margem %d dB",
             (int)(s.rssiLocal - uiSensitivityDbm(LORA_SF)));
  }
  oled.drawStr(0, 50, buf);
}

/// Eco do outro lado e contagem de perda.
static void blocoEco(const UiState &s) {
  char buf[24];
  if (s.received > 0) {
    snprintf(buf, sizeof(buf), "remoto %d dBm", s.rssiRemote);
    oled.drawStr(0, 58, buf);
  }
  if (s.sent > 0) {
    snprintf(buf, sizeof(buf), "%lu/%lu",
             (unsigned long)(s.sent - s.received), (unsigned long)s.sent);
    oled.drawStr(96 - oled.getStrWidth(buf), 50, buf);
  }
}

static const char *seloDoVeredito(VereditoPonto v) {
  switch (v) {
    case PONTO_APROVADO: return "OK";
    case PONTO_LIMITE: return "LIM";
    case PONTO_REPROVADO: return "REP";
    default: return "...";
  }
}

/// Selo compacto do veredito, em vídeo invertido no canto.
static void blocoSelo(const UiState &s) {
  char motivo[48];
  const char *selo = seloDoVeredito(uiAvaliarPonto(s, motivo, sizeof(motivo)));
  int w = oled.getStrWidth(selo);
  oled.drawBox(126 - w - 2, 51, w + 4, 9);
  oled.setDrawColor(0);
  oled.drawStr(126 - w, 58, selo);
  oled.setDrawColor(1);
}

// Página 1 — o enlace. É a que fica na tela durante o teste de alcance:
// o número grande é o RSSI, e a barra é a margem até perder o link.
static void pagLink(const UiState &s) {
  cabecalho("ENLACE", s);
  blocoRssi(s);
  blocoMargem(s);
  blocoEco(s);
  blocoSelo(s);
  indicadorPagina();
}

// Página 2 — resumo consolidado do ponto de medição. É esta a tela que o
// operador anota ou fotografa antes de caminhar para o próximo ponto: ela
// concentra tudo o que descreve a qualidade do enlace ali.
static void pagPonto(const UiState &s) {
  char titulo[16];
  snprintf(titulo, sizeof(titulo), "PONTO %u", (unsigned)s.ponto);
  cabecalho(titulo, s);

  char buf[48];
  oled.setFont(u8g2_font_6x10_tf);

  float perda =
      s.sent > 0 ? 100.0f * (float)(s.sent - s.received) / (float)s.sent : 0.0f;
  snprintf(buf, sizeof(buf), "pac %lu/%lu  perda %.0f%%",
           (unsigned long)s.received, (unsigned long)s.sent, (double)perda);
  oled.drawStr(0, 19, buf);

  int16_t menor, media, maior;
  uint8_t n;
  if (uiHistStats(menor, media, maior, n)) {
    snprintf(buf, sizeof(buf), "rssi %d (%d..%d)", media, menor, maior);
    oled.drawStr(0, 30, buf);
    snprintf(buf, sizeof(buf), "margem %d  assim %d",
             (int)(media - uiSensitivityDbm(LORA_SF)),
             abs((int)media - (int)s.rssiRemote));
    oled.drawStr(0, 41, buf);
  } else {
    oled.drawStr(0, 30, "sem amostras");
  }

  // Faixa de veredito: o operador decide sem interpretar número. Ocupa o rodapé
  // inteiro em vídeo invertido para ser legível de relance, sob sol.
  VereditoPonto v = uiAvaliarPonto(s, buf, sizeof(buf));

  oled.drawBox(0, 52, 128, 12);
  oled.setDrawColor(0);
  oled.setFont(u8g2_font_6x10_tf);
  oled.drawStr(3, 61, buf);
  oled.setDrawColor(1);

  // Reprovado ganha moldura dupla — não deve ser confundido com aprovado num
  // olhar rápido.
  if (v == PONTO_REPROVADO) {
    oled.drawFrame(0, 50, 128, 14);
  }
}

// Página 3 — histórico. Caminhando em campo, a forma da curva mostra onde o
// sinal caiu; um degrau denuncia obstrução, não distância.
static void pagGraph(const UiState &s) {
  cabecalho("HISTORICO", s);

  const int yTopo = 12;
  const int yBase = 52;

  oled.drawHLine(0, yBase, 128);

  if (histCount == 0) {
    oled.setFont(u8g2_font_6x10_tf);
    oled.drawStr(0, 34, "sem amostras");
    indicadorPagina();
    return;
  }

  int xInicial = HIST_LEN - histCount;
  for (uint8_t i = 0; i < histCount; i++) {
    uint8_t idx = (uint8_t)((histHead + HIST_LEN - histCount + i) % HIST_LEN);
    int y = mapRssiToY(hist[idx], yTopo, yBase);
    oled.drawVLine(xInicial + i, y, yBase - y);
  }

  int16_t menor, media, maior;
  uint8_t n;
  uiHistStats(menor, media, maior, n);

  char buf[48];
  oled.setFont(u8g2_font_5x7_tf);
  snprintf(buf, sizeof(buf), "min%d med%d max%d", menor, media, maior);
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

  // Aviso discreto, não alarme: enquanto a leitura não for calibrada (P-005),
  // um alerta enfático seria enganoso.
  if (s.vbat > 0.5f && s.vbat < VBAT_BAIXA_V) {
    oled.drawStr(84, 53, "BAIXA");
  }

  indicadorPagina();
}

// Página extra — bancada. Confirma o barramento de sensores externos e lembra
// que esta placa não deve transmitir sem antena (A-003). Disponível em
// qualquer papel — em PINGER/PONGER só confirma que não há sensor pendurado.
static void pagBench(const UiState &s) {
  cabecalho("BANCADA", s);

  oled.setFont(u8g2_font_6x10_tf);
  oled.drawStr(0, 20, "SEM TX - so recepcao");

  char buf[26];
  snprintf(buf, sizeof(buf), "I2C sensores: %u", s.i2cCount);
  oled.drawStr(0, 33, buf);

  if (s.i2cCount == 0) {
    oled.drawStr(0, 44, "nenhum encontrado");
  } else {
    char lista[26] = "";
    for (uint8_t i = 0; i < s.i2cCount; i++) {
      char item[6];
      snprintf(item, sizeof(item), "0x%02X ", s.i2cAddr[i]);
      strncat(lista, item, sizeof(lista) - strlen(lista) - 1);
    }
    oled.drawStr(0, 44, lista);
  }

  snprintf(buf, sizeof(buf), "pacotes ouvidos: %lu", (unsigned long)s.received);
  oled.drawStr(0, 55, buf);

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

void uiResetHist() {
  histCount = 0;
  histHead = 0;
}

void uiDraw(const UiState &s) {
  oled.clearBuffer();
  switch (page) {
    case PAGE_LINK: pagLink(s); break;
    case PAGE_PONTO: pagPonto(s); break;
    case PAGE_GRAPH: pagGraph(s); break;
    case PAGE_RADIO: pagRadio(s); break;
    case PAGE_SYS: pagSys(s); break;
    default: pagBench(s); break;
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
