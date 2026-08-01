#!/usr/bin/env python3
"""Sentinela — compila e roda os testes do protocolo no host.

O `lib/proto/` é C++ puro justamente para poder ser testado sem placa. Este
script existe para que isso seja um comando só, igual em qualquer estação
(MacBook ou homeserver), sem depender de instalar o platform `native` do
PlatformIO.

Uso:
    ./tools/venv/bin/python tools/testa_proto.py

Autoria: Matheus Marassi
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
PROTO = RAIZ / "firmware" / "lib" / "proto"


def acha_compilador():
    """c++ no macOS é clang, no Linux é g++ — os dois servem."""
    for nome in ("c++", "g++", "clang++"):
        achado = shutil.which(nome)
        if achado:
            return achado
    sys.exit("nenhum compilador C++ encontrado (c++, g++ ou clang++)")


def main():
    compilador = acha_compilador()
    fontes = [PROTO / "proto.cpp", PROTO / "teste_proto.cpp"]
    for f in fontes:
        if not f.exists():
            sys.exit(f"fonte ausente: {f}")

    with tempfile.TemporaryDirectory() as tmp:
        binario = Path(tmp) / "teste_proto"
        # -Wall -Wextra -Werror: o protocolo é o contrato entre firmware e
        # servidor; aviso de compilador aqui é defeito, não ruído.
        cmd = [compilador, "-std=c++11", "-Wall", "-Wextra", "-Werror",
               "-I", str(PROTO), *[str(f) for f in fontes], "-o", str(binario)]
        print(f"$ {' '.join(cmd)}", flush=True)
        if subprocess.run(cmd).returncode != 0:
            sys.exit("falha de compilação")
        return subprocess.run([str(binario)]).returncode


if __name__ == "__main__":
    sys.exit(main())
