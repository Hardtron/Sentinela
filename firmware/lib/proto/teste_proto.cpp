// Sentinela — testes do protocolo, executados no host (sem placa).
//
// Rodar com `./tools/venv/bin/python tools/testa_proto.py`.
//
// Por que testar isto no host e não na placa: o valor do `lib/proto/` é
// justamente ser independente de chip. Um teste que só roda no ESP32 não
// provaria portabilidade — e portabilidade é o requisito (ADR-004: o alvo de
// campo é STM32WLE5, não ESP32).
//
// Autoria: Luiz Matheus Marassi de Paula

#include <cstdio>
#include <cstring>

#include "proto.h"

static int falhas = 0;
static int testes = 0;

static void verifica(bool ok, const char *nome) {
  testes++;
  if (!ok) {
    falhas++;
    std::printf("  FALHOU: %s\n", nome);
  }
}

// --- ida e volta preserva todos os campos ----------------------------------

static void teste_sensor_ida_volta() {
  proto::Sensor origem;
  origem.node_id = 4097;
  origem.seq = 65535;
  origem.instante = 1785540000u;
  origem.chuva_1h = 1234;     // 123,4 mm
  origem.pitch = -1250;       // −12,50°
  origem.roll = 875;          // +8,75°
  origem.umidade_solo = 174;   // 87,0 %
  origem.bateria = proto::bateria_para_byte(3710);
  origem.flags = proto::FLAG_CHUVA_OK | proto::FLAG_INCLIN_OK |
                 proto::FLAG_ALERTA_LOCAL;

  uint8_t buf[64];
  size_t n = proto::codifica_sensor(origem, buf, sizeof(buf));
  verifica(n == proto::TAM_SENSOR, "sensor: tamanho codificado");
  verifica(n <= 20, "sensor: cabe no teto de 20 bytes (PLANO.md fase 1)");

  proto::Sensor volta;
  std::memset(&volta, 0, sizeof(volta));
  verifica(proto::decodifica_sensor(buf, n, volta), "sensor: decodifica");

  verifica(volta.node_id == origem.node_id, "sensor: node_id");
  verifica(volta.seq == origem.seq, "sensor: seq");
  verifica(volta.instante == origem.instante, "sensor: instante");
  verifica(volta.chuva_1h == origem.chuva_1h, "sensor: chuva");
  verifica(volta.pitch == origem.pitch, "sensor: pitch negativo preservado");
  verifica(volta.roll == origem.roll, "sensor: roll");
  verifica(volta.umidade_solo == origem.umidade_solo, "sensor: umidade");
  verifica(volta.bateria == origem.bateria, "sensor: bateria");
  verifica(proto::byte_para_bateria(volta.bateria) == 3710,
           "sensor: bateria volta a mV com passo de 10 mV");
  verifica(volta.flags == origem.flags, "sensor: flags");
}

static void teste_saude_ida_volta() {
  proto::Saude origem;
  origem.node_id = 14;
  origem.seq = 7;
  origem.instante = 1785540000u;
  origem.energia_dia = 1500;  // 150,0 Wh
  origem.t_ini = 400;
  origem.t_fim = 1050;
  origem.corrente_pico = 820;
  origem.v_min = 3400;
  origem.v_fim = 4050;
  origem.dod = 35;
  origem.temp_interna = -8;  // negativo: serra à noite
  origem.umidade_interna = 62;
  origem.reinicios = 2;
  origem.watchdogs = 1;
  origem.heap_livre_kb = 180;
  origem.sensores_validos = 0x0F;
  origem.versao_firmware = 3;

  uint8_t buf[64];
  size_t n = proto::codifica_saude(origem, buf, sizeof(buf));
  verifica(n == proto::TAM_SAUDE, "saude: tamanho codificado");

  proto::Saude volta;
  std::memset(&volta, 0, sizeof(volta));
  verifica(proto::decodifica_saude(buf, n, volta), "saude: decodifica");

  verifica(volta.energia_dia == origem.energia_dia, "saude: E_dia");
  verifica(volta.v_min == origem.v_min, "saude: V_min");
  verifica(volta.dod == origem.dod, "saude: DoD");
  verifica(volta.temp_interna == origem.temp_interna,
           "saude: temperatura negativa preservada");
  verifica(volta.umidade_interna == origem.umidade_interna,
           "saude: umidade interna (RC-14)");
  verifica(volta.heap_livre_kb == origem.heap_livre_kb, "saude: heap");
  verifica(volta.sensores_validos == origem.sensores_validos,
           "saude: bitmap de sensores validos");
}

// --- recusas: o que o decodificador precisa rejeitar ------------------------

static void teste_recusa_quadro_invalido() {
  proto::Sensor s;
  std::memset(&s, 0, sizeof(s));
  uint8_t buf[64];
  size_t n = proto::codifica_sensor(s, buf, sizeof(buf));

  proto::Sensor saida;

  uint8_t magic_ruim[64];
  std::memcpy(magic_ruim, buf, n);
  magic_ruim[0] = 0x00;
  verifica(!proto::decodifica_sensor(magic_ruim, n, saida),
           "recusa: magic errado");

  uint8_t versao_ruim[64];
  std::memcpy(versao_ruim, buf, n);
  versao_ruim[1] = (uint8_t)((9 << 4) | proto::TIPO_SENSOR);
  verifica(!proto::decodifica_sensor(versao_ruim, n, saida),
           "recusa: versao futura nao e interpretada como atual");

  verifica(!proto::decodifica_sensor(buf, n - 1, saida),
           "recusa: quadro truncado");

  // Um quadro de sensor não pode ser lido como quadro de saúde: os campos
  // ocupam posições diferentes e a interpretação cruzada geraria número
  // plausível e errado — o pior modo de falha aqui.
  proto::Saude como_saude;
  std::memset(&como_saude, 0, sizeof(como_saude));
  verifica(!proto::decodifica_saude(buf, n, como_saude),
           "recusa: sensor nao decodifica como saude");
}

static void teste_buffer_pequeno() {
  proto::Sensor s;
  std::memset(&s, 0, sizeof(s));
  uint8_t curto[4];
  verifica(proto::codifica_sensor(s, curto, sizeof(curto)) == 0,
           "buffer pequeno devolve 0, nao estoura");
}

static void teste_identificacao_de_tipo() {
  proto::Sensor s;
  std::memset(&s, 0, sizeof(s));
  uint8_t buf[64];
  size_t n = proto::codifica_sensor(s, buf, sizeof(buf));

  uint8_t tipo = 0;
  verifica(proto::tipo_do_quadro(buf, n, tipo), "tipo: identifica");
  verifica(tipo == proto::TIPO_SENSOR, "tipo: e sensor");

  proto::Saude h;
  std::memset(&h, 0, sizeof(h));
  n = proto::codifica_saude(h, buf, sizeof(buf));
  verifica(proto::tipo_do_quadro(buf, n, tipo) && tipo == proto::TIPO_SAUDE,
           "tipo: e saude");
}

/// O byte de autenticação (RC-11) precisa existir no quadro desde já, senão
/// ligá-lo depois quebra compatibilidade com nós já em campo.
static void teste_reserva_de_autenticacao() {
  proto::Sensor s;
  std::memset(&s, 0, sizeof(s));
  uint8_t buf[64];
  proto::codifica_sensor(s, buf, sizeof(buf));
  verifica(buf[2] == proto::AUTH_AUSENTE,
           "RC-11: byte de autenticacao reservado no cabecalho");
}

/// Emite quadros conhecidos em hexadecimal, para o decodificador Python do
/// servidor conferir contra a MESMA fonte de bytes. É o que impede o C++ e o
/// Python de divergirem silenciosamente — divergência aqui grava número errado
/// no banco sem levantar erro nenhum.
static void emite_vetores() {
  proto::Sensor s;
  s.node_id = 4097;
  s.seq = 65535;
  s.instante = 1785540000u;
  s.chuva_1h = 1234;
  s.pitch = -1250;
  s.roll = 875;
  s.umidade_solo = 174;
  s.bateria = proto::bateria_para_byte(3710);
  s.flags = proto::FLAG_CHUVA_OK | proto::FLAG_INCLIN_OK | proto::FLAG_SOLO_OK;

  uint8_t buf[64];
  size_t n = proto::codifica_sensor(s, buf, sizeof(buf));
  std::printf("SENSOR ");
  for (size_t i = 0; i < n; i++) std::printf("%02x", buf[i]);
  std::printf("\n");

  proto::Saude h;
  h.node_id = 14;
  h.seq = 7;
  h.instante = 1785540000u;
  h.energia_dia = 1500;
  h.t_ini = 400;
  h.t_fim = 1050;
  h.corrente_pico = 820;
  h.v_min = 3400;
  h.v_fim = 4050;
  h.dod = 35;
  h.temp_interna = -8;
  h.umidade_interna = 62;
  h.reinicios = 2;
  h.watchdogs = 1;
  h.heap_livre_kb = 180;
  h.sensores_validos = 0x0F;
  h.versao_firmware = 3;

  n = proto::codifica_saude(h, buf, sizeof(buf));
  std::printf("SAUDE ");
  for (size_t i = 0; i < n; i++) std::printf("%02x", buf[i]);
  std::printf("\n");
}

int main(int argc, char **argv) {
  if (argc > 1 && std::strcmp(argv[1], "--vetores") == 0) {
    emite_vetores();
    return 0;
  }
  std::printf("Sentinela — testes do protocolo (host)\n");
  teste_sensor_ida_volta();
  teste_saude_ida_volta();
  teste_recusa_quadro_invalido();
  teste_buffer_pequeno();
  teste_identificacao_de_tipo();
  teste_reserva_de_autenticacao();

  std::printf("%d testes, %d falha(s)\n", testes, falhas);
  return falhas == 0 ? 0 : 1;
}
