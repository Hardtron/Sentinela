// Sentinela — implementação do protocolo binário. Ver proto.h para o racional.
// Autoria: Matheus Marassi

#include "proto.h"

namespace proto {
namespace {

// Serialização explícita em little-endian. Escrita byte a byte de propósito:
// `memcpy` de struct carregaria o padding e o endianness do alvo, e o quadro
// precisa ser idêntico no ESP32, no STM32WLE5 e no decodificador do servidor.

void p8(uint8_t *b, size_t &i, uint8_t v) { b[i++] = v; }

void p16(uint8_t *b, size_t &i, uint16_t v) {
  b[i++] = (uint8_t)(v & 0xFF);
  b[i++] = (uint8_t)(v >> 8);
}

void p32(uint8_t *b, size_t &i, uint32_t v) {
  b[i++] = (uint8_t)(v & 0xFF);
  b[i++] = (uint8_t)((v >> 8) & 0xFF);
  b[i++] = (uint8_t)((v >> 16) & 0xFF);
  b[i++] = (uint8_t)((v >> 24) & 0xFF);
}

uint8_t g8(const uint8_t *b, size_t &i) { return b[i++]; }

uint16_t g16(const uint8_t *b, size_t &i) {
  uint16_t v = (uint16_t)b[i] | (uint16_t)((uint16_t)b[i + 1] << 8);
  i += 2;
  return v;
}

uint32_t g32(const uint8_t *b, size_t &i) {
  uint32_t v = (uint32_t)b[i] | ((uint32_t)b[i + 1] << 8) |
               ((uint32_t)b[i + 2] << 16) | ((uint32_t)b[i + 3] << 24);
  i += 4;
  return v;
}

void cabecalho(uint8_t *b, size_t &i, uint8_t tipo) {
  p8(b, i, MAGIC);
  p8(b, i, (uint8_t)((VERSAO << 4) | (tipo & 0x0F)));
  p8(b, i, AUTH_AUSENTE);  // RC-11: reservado, ver proto.h
}

/// Confere magic/versão/tipo/tamanho de uma vez. Quadro que não passa aqui é
/// descartado inteiro — decodificar parcialmente um quadro suspeito é como
/// um sistema de alerta começa a inventar dado.
bool cabecalho_valido(const uint8_t *b, size_t tam, uint8_t esperado,
                      size_t minimo) {
  if (b == 0 || tam < minimo) return false;
  if (b[0] != MAGIC) return false;
  if ((uint8_t)(b[1] >> 4) != VERSAO) return false;
  return (uint8_t)(b[1] & 0x0F) == esperado;
}

}  // namespace

// ------------------------------------------------------------------ sensor --

size_t codifica_sensor(const Sensor &s, uint8_t *buf, size_t tam) {
  if (buf == 0 || tam < TAM_SENSOR) return 0;
  size_t i = 0;
  cabecalho(buf, i, TIPO_SENSOR);
  p16(buf, i, s.node_id);
  p16(buf, i, s.seq);
  p32(buf, i, s.instante);
  p16(buf, i, s.chuva_1h);
  p16(buf, i, (uint16_t)s.pitch);
  p16(buf, i, (uint16_t)s.roll);
  p8(buf, i, s.umidade_solo);
  p8(buf, i, s.bateria);
  p8(buf, i, s.flags);
  return i;
}

bool decodifica_sensor(const uint8_t *buf, size_t tam, Sensor &saida) {
  if (!cabecalho_valido(buf, tam, TIPO_SENSOR, TAM_SENSOR)) return false;
  size_t i = TAM_CABECALHO;
  saida.node_id = g16(buf, i);
  saida.seq = g16(buf, i);
  saida.instante = g32(buf, i);
  saida.chuva_1h = g16(buf, i);
  saida.pitch = (int16_t)g16(buf, i);
  saida.roll = (int16_t)g16(buf, i);
  saida.umidade_solo = g8(buf, i);
  saida.bateria = g8(buf, i);
  saida.flags = g8(buf, i);
  return true;
}

// ------------------------------------------------------------------- saúde --

size_t codifica_saude(const Saude &s, uint8_t *buf, size_t tam) {
  if (buf == 0 || tam < TAM_SAUDE) return 0;
  size_t i = 0;
  cabecalho(buf, i, TIPO_SAUDE);
  p16(buf, i, s.node_id);
  p16(buf, i, s.seq);
  p32(buf, i, s.instante);
  p16(buf, i, s.energia_dia);
  p16(buf, i, s.t_ini);
  p16(buf, i, s.t_fim);
  p16(buf, i, s.corrente_pico);
  p16(buf, i, s.v_min);
  p16(buf, i, s.v_fim);
  p8(buf, i, s.dod);
  p8(buf, i, (uint8_t)s.temp_interna);
  p8(buf, i, s.umidade_interna);
  p8(buf, i, s.reinicios);
  p8(buf, i, s.watchdogs);
  p16(buf, i, s.heap_livre_kb);
  p8(buf, i, s.sensores_validos);
  p8(buf, i, s.versao_firmware);
  return i;
}

bool decodifica_saude(const uint8_t *buf, size_t tam, Saude &saida) {
  if (!cabecalho_valido(buf, tam, TIPO_SAUDE, TAM_SAUDE)) return false;
  size_t i = TAM_CABECALHO;
  saida.node_id = g16(buf, i);
  saida.seq = g16(buf, i);
  saida.instante = g32(buf, i);
  saida.energia_dia = g16(buf, i);
  saida.t_ini = g16(buf, i);
  saida.t_fim = g16(buf, i);
  saida.corrente_pico = g16(buf, i);
  saida.v_min = g16(buf, i);
  saida.v_fim = g16(buf, i);
  saida.dod = g8(buf, i);
  saida.temp_interna = (int8_t)g8(buf, i);
  saida.umidade_interna = g8(buf, i);
  saida.reinicios = g8(buf, i);
  saida.watchdogs = g8(buf, i);
  saida.heap_livre_kb = g16(buf, i);
  saida.sensores_validos = g8(buf, i);
  saida.versao_firmware = g8(buf, i);
  return true;
}

// ------------------------------------------------------------------- comum --

bool tipo_do_quadro(const uint8_t *buf, size_t tam, uint8_t &tipo) {
  if (buf == 0 || tam < TAM_CABECALHO) return false;
  if (buf[0] != MAGIC || (uint8_t)(buf[1] >> 4) != VERSAO) return false;
  tipo = (uint8_t)(buf[1] & 0x0F);
  return tipo == TIPO_SENSOR || tipo == TIPO_SAUDE;
}

}  // namespace proto
