// Sentinela — interface de diagnóstico no OLED (apoio ao desenvolvimento)
//
// O display integrado da Heltec é a única fonte de informação disponível no
// campo, longe do computador. Durante o teste de alcance o operador caminha com
// a placa na mão: a tela precisa responder "o enlace ainda está de pé, e com
// quanta margem?" a um olhar, e não exigir interpretação.
//
// Esta UI é ferramenta de desenvolvimento e não vai para o nó de campo
// definitivo (que não tem display). Por isso vive em src/ e não em lib/app/.
//
// Autoria: Matheus Marassi

#pragma once

#include <stdint.h>

/// Instantâneo do estado do nó, montado pelo laço principal a cada desenho.
struct UiState {
  uint8_t nodeId;
  bool isPinger;

  uint32_t seq;
  uint32_t sent;
  uint32_t received;
  bool lastOk;  // o último ciclo fechou (pong recebido / ping respondido)

  float rssiLocal;      // dBm — como ouvimos o outro lado
  float snrLocal;       // dB
  int16_t rssiRemote;   // dBm — como o outro lado nos ouviu (eco)
  int8_t snrRemote;     // dB

  uint32_t toaMs;       // tempo no ar do quadro
  float vbat;           // V — não calibrado, ver pendência no README
  uint32_t bootCount;
};

void uiBegin();

/// Alimenta o histórico do gráfico. Chamar uma vez por pacote recebido.
void uiPushRssi(float rssi);

/// Avança para a próxima página (botão PRG).
void uiNextPage();

/// Redesenha a página corrente.
void uiDraw(const UiState &s);

/// Tela de abertura, usada durante a inicialização.
void uiSplash(const char *linha1, const char *linha2);

/// Falha terminal: ocupa a tela inteira, sem ambiguidade.
void uiFatal(const char *titulo, const char *detalhe);

/// Sensibilidade teórica do SX1276 para o spreading factor em uso (dBm).
/// Usada para calcular a margem de enlace — o número que importa em campo.
float uiSensitivityDbm(uint8_t sf);
