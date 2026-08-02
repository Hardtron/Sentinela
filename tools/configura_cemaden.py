#!/usr/bin/env python3
"""Instala credenciais PED localmente, sem eco ou passagem pela linha de comando."""

import getpass
import os
import tempfile
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]
ARQUIVO_PADRAO = RAIZ / "backend" / "fontes.env"


def atualiza(caminho, valores):
    linhas = caminho.read_text(encoding="utf-8").splitlines()
    pendentes = dict(valores)
    novas = []
    for linha in linhas:
        chave = linha.split("=", 1)[0].strip() if "=" in linha else None
        if chave in pendentes:
            novas.append(f"{chave}={pendentes.pop(chave)}")
        else:
            novas.append(linha)
    novas.extend(f"{chave}={valor}" for chave, valor in pendentes.items())

    descritor, temporario = tempfile.mkstemp(
        prefix=".fontes.env.", dir=caminho.parent)
    try:
        os.fchmod(descritor, 0o600)
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            arquivo.write("\n".join(novas) + "\n")
            arquivo.flush()
            os.fsync(arquivo.fileno())
        os.replace(temporario, caminho)
    finally:
        if os.path.exists(temporario):
            os.unlink(temporario)


def main():
    if not ARQUIVO_PADRAO.exists():
        raise SystemExit(f"arquivo ausente: {ARQUIVO_PADRAO}")
    email = input("E-mail da conta PED: ").strip()
    senha = getpass.getpass("Senha PED (não será exibida): ")
    if not email or not senha:
        raise SystemExit("e-mail e senha são obrigatórios; nada foi alterado")
    atualiza(ARQUIVO_PADRAO, {
        "CEMADEN_PED_EMAIL": email,
        "CEMADEN_PED_PASSWORD": senha,
        "CEMADEN_PED_TOKEN": "",
    })
    print("Credenciais PED instaladas; token manual removido; modo 600 aplicado.")


if __name__ == "__main__":
    main()
