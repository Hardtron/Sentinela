#!/usr/bin/env python3
"""Sentinela — verifica que o decodificador Python concorda com o C++.

O firmware codifica; o servidor decodifica. São duas linguagens, dois
compiladores e duas máquinas. Se os layouts divergirem — um campo a mais, uma
ordem trocada, um `int16` virando `uint16` — **o servidor grava número errado
sem levantar erro nenhum**. Num sistema de alerta de risco, esse é o defeito
mais perigoso que existe: silencioso e plausível.

Este teste elimina a classe inteira: compila o C++, pede os bytes reais e
manda o Python interpretá-los. Uma fonte de bytes só.

Uso:
    ./tools/venv/bin/python tools/testa_decodifica.py

Autoria: Luiz Matheus Marassi de Paula
"""

import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

import decodifica  # noqa: E402
from testa_proto import acha_compilador  # noqa: E402

PROTO = RAIZ / "firmware" / "lib" / "proto"

falhas = 0


def verifica(ok, nome):
    global falhas
    if ok:
        print(f"  ok   {nome}")
    else:
        falhas += 1
        print(f"  FALHOU {nome}")


def bytes_do_cpp():
    """Compila o teste do firmware e pede os vetores em hexadecimal."""
    with tempfile.TemporaryDirectory() as tmp:
        binario = Path(tmp) / "vetores"
        cmd = [acha_compilador(), "-std=c++11", "-I", str(PROTO),
               str(PROTO / "proto.cpp"), str(PROTO / "teste_proto.cpp"),
               "-o", str(binario)]
        if subprocess.run(cmd).returncode != 0:
            sys.exit("falha ao compilar os vetores")
        saida = subprocess.run([str(binario), "--vetores"],
                               capture_output=True, text=True, check=True)
    quadros = {}
    for linha in saida.stdout.split("\n"):
        if " " in linha:
            nome, hexa = linha.split(" ", 1)
            quadros[nome] = bytes.fromhex(hexa.strip())
    return quadros


def main():
    quadros = bytes_do_cpp()
    print("Sentinela — C++ codifica, Python decodifica")

    bruto = quadros["SENSOR"]
    verifica(len(bruto) == decodifica.TAM_SENSOR,
             f"sensor: {len(bruto)} B == TAM_SENSOR")
    verifica(len(bruto) <= 20, "sensor: dentro do teto de 20 B")
    verifica(decodifica.tipo_do_quadro(bruto) == decodifica.TIPO_SENSOR,
             "sensor: tipo identificado")

    s = decodifica.decodifica_sensor(bruto)
    verifica(s["node_id"] == 4097, "sensor: node_id")
    verifica(s["seq"] == 65535, "sensor: seq")
    verifica(s["medido_em"] == 1785540000, "sensor: instante")
    verifica(abs(s["chuva_1h_mm"] - 123.4) < 1e-6, "sensor: chuva 123,4 mm")
    verifica(abs(s["pitch_graus"] + 12.5) < 1e-6, "sensor: pitch −12,50°")
    verifica(abs(s["roll_graus"] - 8.75) < 1e-6, "sensor: roll +8,75°")
    verifica(abs(s["umidade_solo"] - 87.0) < 1e-6, "sensor: solo 87,0 %")
    verifica(s["bateria_mv"] == 3710, "sensor: bateria 3710 mV")
    verifica(s["chuva_valida"] and s["inclin_valida"] and s["solo_valido"],
             "sensor: bits de validade (RC-07)")

    bruto = quadros["SAUDE"]
    verifica(len(bruto) == decodifica.TAM_SAUDE,
             f"saude: {len(bruto)} B == TAM_SAUDE")
    h = decodifica.decodifica_saude(bruto)
    verifica(abs(h["energia_dia_wh"] - 150.0) < 1e-6, "saude: E_dia 150,0 Wh")
    verifica(h["v_min_mv"] == 3400, "saude: V_min")
    verifica(h["dod_pct"] == 35, "saude: DoD")
    verifica(h["temp_interna_c"] == -8, "saude: temperatura negativa")
    verifica(h["umidade_interna"] == 62, "saude: umidade interna (RC-14)")
    verifica(h["heap_livre_kb"] == 180, "saude: heap")
    verifica(h["sensores_validos"] == 0x0F, "saude: bitmap")

    # Recusa explícita, não retorno vazio.
    try:
        decodifica.decodifica_sensor(quadros["SAUDE"])
        verifica(False, "recusa: saude nao decodifica como sensor")
    except decodifica.QuadroInvalido:
        verifica(True, "recusa: saude nao decodifica como sensor")

    try:
        decodifica.decodifica_sensor(quadros["SENSOR"][:-1])
        verifica(False, "recusa: quadro truncado")
    except decodifica.QuadroInvalido:
        verifica(True, "recusa: quadro truncado")

    print(f"{falhas} falha(s)")
    return 1 if falhas else 0


if __name__ == "__main__":
    sys.exit(main())
