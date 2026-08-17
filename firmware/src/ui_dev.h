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
// Autoria: Luiz Matheus Marassi de Paula

#pragma once

#include <stddef.h>
#include <stdint.h>

/// Instantâneo do estado do nó, montado pelo laço principal a cada desenho.
struct UiState {
  uint8_t nodeId;
  const char *papel;  // "PING", "PONG" ou "BENCH" — rótulo curto do cabeçalho

  uint16_t ponto;  // ponto de medição corrente no ensaio de campo

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
  float tempChipC;      // °C — sensor interno do ESP32, aproximado

  // --- modo bancada (ROLE_BENCH) — placa sem antena, ver A-003/HARDWARE.md ---
  uint8_t i2cCount;      // sensores encontrados no barramento externo
  uint8_t i2cAddr[4];    // primeiros endereços encontrados
};

void uiBegin();

/// Alimenta o histórico do gráfico. Chamar uma vez por pacote recebido.
void uiPushRssi(float rssi);

/// Avança para a próxima página (toque curto no botão PRG).
void uiNextPage();

/// Zera o histórico do gráfico. Chamado ao iniciar um novo ponto de medição,
/// para que as estatísticas exibidas sejam só daquele ponto.
void uiResetHist();

/// Estatísticas do histórico corrente. Devolve false se não há amostras.
bool uiHistStats(int16_t &menor, int16_t &media, int16_t &maior, uint8_t &n);

/// Redesenha a página corrente.
void uiDraw(const UiState &s);

/// Tela de abertura, usada durante a inicialização.
void uiSplash(const char *linha1, const char *linha2);

/// Falha terminal: ocupa a tela inteira, sem ambiguidade.
void uiFatal(const char *titulo, const char *detalhe);

/// Sensibilidade teórica do SX1276 para o spreading factor em uso (dBm).
/// Usada para calcular a margem de enlace — o número que importa em campo.
float uiSensitivityDbm(uint8_t sf);

// --- Critérios de aprovação de um ponto de instalação ---------------------
// Ficam aqui, e não espalhados pelo código de desenho, porque são a regra do
// ensaio: mudá-los muda o que o campo considera aprovado. Justificativa em
// docs/ROTEIRO_CAMPO.md §7.

/// Amostras mínimas antes de emitir veredito. Abaixo disso não se distingue
/// sinal ruim de desvanecimento momentâneo.
#define PONTO_MIN_AMOSTRAS 20

/// Margem confortável: suporta chuva, vegetação úmida e variação sazonal.
#define PONTO_MARGEM_BOA_DB 20

/// Abaixo disto o enlace cai na primeira chuva forte — justamente o evento que
/// o sistema existe para monitorar.
#define PONTO_MARGEM_MIN_DB 10

/// Perda acima disto desqualifica o local mesmo com RSSI aparentemente bom:
/// indica interferência ou desvanecimento profundo.
#define PONTO_PERDA_MAX_PCT 5.0f

/// Diferença entre o que cada lado ouve. Acima disto há antena, obstrução
/// próxima ou ruído local em um dos nós.
#define PONTO_ASSIMETRIA_MAX_DB 10

enum VereditoPonto : uint8_t {
  PONTO_COLETANDO = 0,
  PONTO_APROVADO,
  PONTO_LIMITE,
  PONTO_REPROVADO
};

/// Avalia o ponto corrente contra os critérios acima e devolve o veredito,
/// preenchendo `motivo` com o fator dominante. Permite ao operador decidir em
/// campo, sem interpretar números.
VereditoPonto uiAvaliarPonto(const UiState &s, char *motivo, size_t tam);

// --- Economia de energia ---------------------------------------------------
// Em campo, o painel OLED é o maior consumidor de corrente do circuito de
// diagnóstico. Ele apaga sozinho após inatividade e liga de novo a qualquer
// toque no botão — ver docs/ROTEIRO_CAMPO.md.
//
// 60 s cobre a folga entre pontos de medição sem interromper uma coleta em
// andamento na maioria dos casos (ROTEIRO_CAMPO.md §5: ~20 pacotes a 3 s).
// Se apagar no meio de uma coleta, um toque reacende com o estado real —
// nada é perdido, só deixa de ser mostrado por alguns segundos.
#define TELA_INATIVIDADE_MS 60000

/// Chamar a cada iteração do laço principal. Apaga a tela se passou o tempo
/// de inatividade; não faz nada se ela já estiver apagada.
void uiChecaInatividade();

/// Chamar sempre que houver interação do usuário (botão). Liga a tela se
/// estava apagada e reinicia a contagem de inatividade.
void uiRegistrarAtividade();
