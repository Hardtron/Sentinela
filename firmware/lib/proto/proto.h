// Sentinela — protocolo de payload binário (Fase 1)
//
// Codificação compacta para LoRa P2P e, adiante, LoRaWAN. O tempo no ar cresce
// com o tamanho do quadro: em SF12 cada byte custa caro em bateria e em
// ocupação de canal, então o payload é dimensionado em bytes, não em campos
// "que seria bom ter".
//
// **C++ puro, sem Arduino.** Isto é o que permite testar no host
// (`tools/testa_proto.py`) sem placa conectada, e o que vai permitir reusar a
// mesma codificação no STM32WLE5 (ADR-004) sem reescrever.
//
// Dois tipos de quadro, com propósitos e cadências diferentes:
//
//   SENSOR (a cada ciclo de medição) — o dado que decide risco.
//   SAUDE  (1x/dia)                  — o dado que decide manutenção (RC-12).
//
// Separá-los é deliberado: telemetria de manutenção não pode roubar tempo de
// ar do dado de risco. Ver docs/MANUTENCAO.md §8.
//
// Autoria: Matheus Marassi

#pragma once

#include <stddef.h>
#include <stdint.h>

namespace proto {

// --- cabeçalho comum -------------------------------------------------------

/// 'S' de Sentinela. Primeiro descarte de quadro alheio na mesma faixa.
static const uint8_t MAGIC = 0x53;

/// Versão do formato. Incrementar a cada mudança incompatível de layout —
/// receptor antigo precisa poder recusar quadro novo em vez de interpretá-lo
/// errado, que é o modo de falha perigoso num sistema de alerta.
///
/// Vai empacotada com o tipo em **um byte só** (versão nos 4 bits altos, tipo
/// nos 4 baixos). Não é microoptimização gratuita: é o byte que faz o quadro
/// de sensor fechar em 20 bytes — ver §"orçamento de bytes" abaixo. Limita a
/// 15 versões e 15 tipos, o que é folgado para o horizonte do projeto.
static const uint8_t VERSAO = 1;

enum Tipo : uint8_t {
  TIPO_SENSOR = 0x01,
  TIPO_SAUDE = 0x02,
};

/// Bits de `status_flags` do quadro de sensor.
///
/// **RC-07 — sem falha silenciosa.** Sensor ausente ou com leitura inválida
/// não vira zero nem valor plausível: vira bit apagado em `sensores_validos`.
/// Quem lê o quadro sabe distinguir "mediu 0,0 mm" de "não mediu".
enum Flag : uint8_t {
  FLAG_CHUVA_OK = 1 << 0,
  FLAG_INCLIN_OK = 1 << 1,
  FLAG_SOLO_OK = 1 << 2,
  FLAG_BATERIA_OK = 1 << 3,
  FLAG_ALERTA_LOCAL = 1 << 4,  // o nó decidiu sozinho (RC-05/ADR-006)
  FLAG_WATCHDOG = 1 << 5,      // houve reinício por watchdog desde o último
  FLAG_VEDACAO = 1 << 6,       // umidade interna acima do limiar (RC-14)
  FLAG_CALIBRANDO = 1 << 7,    // referência de inclinação ainda assentando
};

// --- quadro de sensor ------------------------------------------------------
// 20 bytes é o teto declarado em PLANO.md (Fase 1). O layout abaixo fecha em
// 19 + 1 de reserva de autenticação truncada = ver `TAM_SENSOR`.

struct Sensor {
  uint16_t node_id;
  uint16_t seq;
  uint32_t instante;      // epoch UNIX (s)
  uint16_t chuva_1h;      // 0,1 mm/lsb  → 0..6553,5 mm
  int16_t pitch;          // 0,01°/lsb   → ±327,67°
  int16_t roll;           // 0,01°/lsb
  uint8_t umidade_solo;   // 0,5 %/lsb   → 0..100 % (ver orçamento)
  uint8_t bateria;        // (mV − 2500)/10 → 2500..5050 mV, passo 10 mV
  uint8_t flags;          // ver enum Flag
};

/// Conversões da bateria. Ficam aqui, e não espalhadas, porque codificador e
/// decodificador têm de concordar — inclusive o decodificador em Python do
/// lado do servidor.
static const uint16_t BATERIA_BASE_MV = 2500;
static const uint16_t BATERIA_PASSO_MV = 10;

inline uint8_t bateria_para_byte(uint16_t mv) {
  if (mv <= BATERIA_BASE_MV) return 0;
  uint32_t passos = (uint32_t)(mv - BATERIA_BASE_MV) / BATERIA_PASSO_MV;
  return passos > 255 ? 255 : (uint8_t)passos;
}

inline uint16_t byte_para_bateria(uint8_t b) {
  return (uint16_t)(BATERIA_BASE_MV + (uint16_t)b * BATERIA_PASSO_MV);
}

// --- quadro de saúde (RC-12) -----------------------------------------------
// Cadência diária. Alimenta a manutenção preditiva (MANUTENCAO.md, Frente 7):
// é com estes campos que se distingue painel sujo de painel sombreado, e
// bateria velha de consumo anômalo.

struct Saude {
  uint16_t node_id;
  uint16_t seq;
  uint32_t instante;
  uint16_t energia_dia;      // 0,1 Wh/lsb — E_dia
  uint16_t t_ini;            // minutos desde 00:00 — início da janela de carga
  uint16_t t_fim;            // minutos desde 00:00 — fim da janela
  uint16_t corrente_pico;    // mA — I_pico
  uint16_t v_min;            // mV — V_min (noite)
  uint16_t v_fim;            // mV — V_fim
  uint8_t dod;               // % de profundidade de descarga
  int8_t temp_interna;       // °C
  uint8_t umidade_interna;   // % — RC-14, o alarme de melhor retorno
  uint8_t reinicios;         // desde o último quadro de saúde
  uint8_t watchdogs;
  uint16_t heap_livre_kb;
  uint8_t sensores_validos;  // bitmap, mesma semântica de Flag
  uint8_t versao_firmware;
};

// --- tamanhos no ar --------------------------------------------------------
// Não são `sizeof(struct)`: a serialização é explícita, little-endian e sem
// padding, para que o quadro seja idêntico entre ESP32, STM32 e o decodificador
// em Python do lado do servidor. Confiar em `sizeof` aqui seria confiar no
// alinhamento do compilador — e é assim que protocolo binário quebra ao trocar
// de alvo.

static const size_t TAM_CABECALHO = 3;  // magic, versao|tipo, reservado_auth
static const size_t TAM_SENSOR = TAM_CABECALHO + 17;   // = 20, no teto exato
static const size_t TAM_SAUDE = TAM_CABECALHO + 29;    // = 32, cadência diária

// --- orçamento de bytes: por que o layout é este --------------------------
//
// O PLANO.md (Fase 1) fixa **≤ 20 bytes** para o quadro de sensor. A lista de
// campos proposta no caderno de planejamento somava 19 B de dados; com um
// cabeçalho convencional de 4 B o quadro fecharia em **23 B — acima do teto**.
// Três decisões trouxeram de volta para 20, e nenhuma custa informação útil:
//
//  1. **Versão e tipo no mesmo byte** (4+4 bits): −1 B.
//  2. **`umidade_solo` de 16 → 8 bits**, a 0,5 %/lsb: −1 B. Resolução de meio
//     ponto percentual está muito além da exatidão de qualquer sensor de
//     umidade de solo de baixo custo; 0,01 % era precisão fictícia.
//  3. **`bateria` de 16 → 8 bits**, passo de 10 mV a partir de 2500 mV: −1 B.
//     Cobre 2,50–5,05 V, que contém toda a faixa útil de uma célula Li-ion.
//     10 mV é folgado num divisor que sequer está calibrado (P-005) — gravar
//     mV exato ali seria precisão que a medição não tem (RC-07).
//
// **Por que não cortar o `instante` (4 B), que era o corte óbvio:** porque o
// nó precisa guardar leitura quando o Farol está fora do ar (RC-06/RC-13) e
// enviá-la depois. Sem carimbo de tempo do nó, a leitura atrasada entraria na
// janela errada de chuva acumulada — e é a chuva acumulada de 24/72 h o
// principal preditor do sistema (SENSORES.md). Trocar 4 B por um erro
// sistemático no preditor central seria péssimo negócio.
//
// **Custo real do que sobrou:** em SF12/125 kHz, 20 B ocupam ~1,2 s de ar; os
// 23 B originais ocupariam ~1,4 s. Cerca de 19 % de bateria e de ocupação de
// canal por transmissão.
//
// **[?] Fase 4 (LoRaWAN):** o quadro de saúde tem 32 B. Convém confirmar o
// tamanho máximo de payload no DR mais baixo de AU915 antes de assumir que
// ele passa em SF12 — se não passar, fragmentar o quadro diário é a saída
// natural, já que ele não é urgente.

/// **RC-11 — espaço reservado para autenticação.** Ainda não há MAC/assinatura
/// no P2P da fase 0-1, mas o byte existe desde já para que ligar autenticação
/// depois **não** seja mudança incompatível de layout. Em LoRaWAN (fase 4) a
/// autenticação vem da própria spec (AES-128 + contador anti-replay); no P2P
/// a injeção de alerta falso é ameaça concreta num sistema de alerta de risco
/// à vida, e trocar o formato do quadro com nós já em campo é caro.
static const uint8_t AUTH_AUSENTE = 0x00;

// --- API -------------------------------------------------------------------
// Devolvem quantos bytes foram escritos, ou 0 se o buffer não comporta. Zero
// como falha (em vez de exceção ou código negativo) mantém o chamador simples
// no firmware, onde não há tratamento de exceção.

size_t codifica_sensor(const Sensor &s, uint8_t *buf, size_t tam);
size_t codifica_saude(const Saude &s, uint8_t *buf, size_t tam);

/// Devolvem false se magic, versão, tipo ou tamanho não conferirem. Quadro
/// suspeito é descartado, nunca interpretado parcialmente.
bool decodifica_sensor(const uint8_t *buf, size_t tam, Sensor &saida);
bool decodifica_saude(const uint8_t *buf, size_t tam, Saude &saida);

/// Identifica o tipo sem decodificar o resto — o receptor precisa disso para
/// escolher o decodificador certo.
bool tipo_do_quadro(const uint8_t *buf, size_t tam, uint8_t &tipo);

}  // namespace proto
