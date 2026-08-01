#!/usr/bin/env python3
"""Executa a verificação local reprodutível que não exige hardware ou banco."""

import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TESTES = (
    "testa_proto.py",
    "testa_decodifica.py",
    "testa_reconhecimento_alarme.py",
    "testa_fluxo_robusto.py",
    "testa_painel_operacional.py",
    "testa_fontes_externas.py",
)


def main():
    for teste in TESTES:
        caminho = RAIZ / "tools" / teste
        print(f"\n== {teste} ==", flush=True)
        resultado = subprocess.run([sys.executable, str(caminho)], cwd=RAIZ)
        if resultado.returncode:
            return resultado.returncode
    print("\n== complexidade ==", flush=True)
    return subprocess.run([
        sys.executable, str(RAIZ / "tools" / "complexidade.py"),
        "--limite", "10"], cwd=RAIZ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
