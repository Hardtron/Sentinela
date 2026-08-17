#!/usr/bin/env python3
"""Sentinela — decodificador Python dos quadros de `lib/proto/`.

Espelho exato de `firmware/lib/proto/proto.h`. Os dois **têm** de concordar:
se divergirem, o servidor grava número errado sem qualquer sinal de erro, que
é o pior modo de falha possível num sistema de alerta.

Por isso as constantes estão repetidas aqui em vez de importadas de algum
lugar — C++ e Python não compartilham cabeçalho — e há um teste que compara os
tamanhos contra os do C++ (`tools/testa_proto.py` cobre o lado C++;
`tools/testa_decodifica.py` cobre este lado com vetores gerados pelo C++).

Autoria: Luiz Matheus Marassi de Paula
"""

import struct

MAGIC = 0x53
VERSAO = 1

TIPO_SENSOR = 0x01
TIPO_SAUDE = 0x02

TAM_CABECALHO = 3
TAM_SENSOR = TAM_CABECALHO + 17   # 20
TAM_SAUDE = TAM_CABECALHO + 29    # 32

BATERIA_BASE_MV = 2500
BATERIA_PASSO_MV = 10

# Bits de `flags` — mesma ordem do enum Flag em proto.h.
FLAG_CHUVA_OK = 1 << 0
FLAG_INCLIN_OK = 1 << 1
FLAG_SOLO_OK = 1 << 2
FLAG_BATERIA_OK = 1 << 3
FLAG_ALERTA_LOCAL = 1 << 4
FLAG_WATCHDOG = 1 << 5
FLAG_VEDACAO = 1 << 6
FLAG_CALIBRANDO = 1 << 7

# '<' = little-endian sem alinhamento, igual à serialização byte a byte do C++.
_SENSOR = struct.Struct("<HHIhhhBBB")
_SAUDE = struct.Struct("<HHIHHHHHHBbBBBHBB")


class QuadroInvalido(Exception):
    """Erro explícito, não retorno vazio.

    RC-07: quadro corrompido não pode virar leitura com campos zerados. Quem
    chama precisa decidir o que fazer — descartar e contar — em vez de gravar
    silenciosamente um zero que parece medição.
    """


def _cabecalho(dados, tipo_esperado, tam_esperado):
    if len(dados) < tam_esperado:
        raise QuadroInvalido(
            f"quadro curto: {len(dados)} B, esperado {tam_esperado}")
    if dados[0] != MAGIC:
        raise QuadroInvalido(f"magic {dados[0]:#04x} != {MAGIC:#04x}")
    versao = dados[1] >> 4
    tipo = dados[1] & 0x0F
    if versao != VERSAO:
        raise QuadroInvalido(f"versão {versao} incompatível (esperado {VERSAO})")
    if tipo != tipo_esperado:
        raise QuadroInvalido(f"tipo {tipo} != {tipo_esperado}")


def tipo_do_quadro(dados):
    """Devolve o tipo, ou None se nem o cabeçalho confere."""
    if len(dados) < TAM_CABECALHO or dados[0] != MAGIC:
        return None
    if (dados[1] >> 4) != VERSAO:
        return None
    tipo = dados[1] & 0x0F
    return tipo if tipo in (TIPO_SENSOR, TIPO_SAUDE) else None


def decodifica_sensor(dados):
    """Converte para unidades de engenharia já na borda.

    O banco guarda mm e graus, não os inteiros escalados do ar — consulta em
    SQL não deve precisar saber que chuva viaja em 0,1 mm/lsb.
    """
    _cabecalho(dados, TIPO_SENSOR, TAM_SENSOR)
    (node_id, seq, instante, chuva, pitch, roll,
     solo, bateria, flags) = _SENSOR.unpack_from(dados, TAM_CABECALHO)
    return {
        "node_id": node_id,
        "seq": seq,
        "medido_em": instante,
        "chuva_1h_mm": chuva / 10.0,
        "pitch_graus": pitch / 100.0,
        "roll_graus": roll / 100.0,
        "umidade_solo": solo / 2.0,
        "bateria_mv": BATERIA_BASE_MV + bateria * BATERIA_PASSO_MV,
        "flags": flags,
        # RC-07: o bit diz se a grandeza foi medida. Sem isto, 0,0 mm seria
        # ambíguo entre "não choveu" e "pluviômetro morto".
        "chuva_valida": bool(flags & FLAG_CHUVA_OK),
        "inclin_valida": bool(flags & FLAG_INCLIN_OK),
        "solo_valido": bool(flags & FLAG_SOLO_OK),
    }


def decodifica_saude(dados):
    _cabecalho(dados, TIPO_SAUDE, TAM_SAUDE)
    (node_id, seq, instante, energia, t_ini, t_fim, pico, v_min, v_fim,
     dod, temp, umid, reinicios, watchdogs, heap,
     validos, versao_fw) = _SAUDE.unpack_from(dados, TAM_CABECALHO)
    return {
        "node_id": node_id,
        "seq": seq,
        "medido_em": instante,
        "energia_dia_wh": energia / 10.0,
        "t_ini": t_ini,
        "t_fim": t_fim,
        "corrente_pico_ma": pico,
        "v_min_mv": v_min,
        "v_fim_mv": v_fim,
        "dod_pct": dod,
        "temp_interna_c": temp,
        "umidade_interna": umid,
        "reinicios": reinicios,
        "watchdogs": watchdogs,
        "heap_livre_kb": heap,
        "sensores_validos": validos,
        "versao_firmware": versao_fw,
    }
