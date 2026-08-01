#!/usr/bin/env python3
"""Sentinela — aplica migrações versionadas no banco.

Existe por causa do RT-06: `esquema.sql` só roda na criação do container, então
toda mudança de esquema depois disso era aplicada à mão — e já houve caso real
de o arquivo versionado divergir do banco em produção (a função
`sensibilidade_dbm`, LOG 18). Migração numerada + registro do que já rodou
elimina essa classe de erro.

Cada arquivo em `backend/migracoes/NNN_*.sql` roda **uma vez**, em ordem. O que
já rodou fica em `schema_migracao`. Os arquivos são escritos de forma
idempotente mesmo assim (`IF NOT EXISTS`, `CREATE OR REPLACE`), para que
reaplicar à mão não quebre nada.

Uso:
    python3 backend/migra.py            # aplica o que falta
    python3 backend/migra.py --listar   # só mostra o estado

Autoria: Matheus Marassi
"""

import argparse
import os
import sys
from pathlib import Path

import psycopg

from ingestor import carrega_env

RAIZ = Path(__file__).resolve().parent
MIGRACOES = RAIZ / "migracoes"

SQL_CONTROLE = """
CREATE TABLE IF NOT EXISTS schema_migracao (
    nome       TEXT PRIMARY KEY,
    aplicada_em TIMESTAMPTZ NOT NULL DEFAULT now()
)
"""


def conecta():
    carrega_env(RAIZ / ".env")
    senha = os.environ.get("POSTGRES_PASSWORD")
    if not senha:
        sys.exit("POSTGRES_PASSWORD ausente — defina em backend/.env")
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "sentinela"),
        user=os.environ.get("POSTGRES_USER", "sentinela"),
        password=senha, autocommit=False)


def aplicadas(con):
    with con.cursor() as cur:
        cur.execute(SQL_CONTROLE)
        con.commit()
        cur.execute("SELECT nome FROM schema_migracao")
        return {linha[0] for linha in cur.fetchall()}


def pendentes(con):
    ja = aplicadas(con)
    todas = sorted(p for p in MIGRACOES.glob("*.sql"))
    return [p for p in todas if p.name not in ja]


def aplica(con, caminho):
    """Uma transação por migração: ou o arquivo inteiro entra, ou nada dele.

    Migração aplicada pela metade é pior que migração não aplicada — deixa o
    banco num estado que nenhum arquivo descreve.
    """
    sql = caminho.read_text(encoding="utf-8")
    with con.cursor() as cur:
        cur.execute(sql)
        cur.execute("INSERT INTO schema_migracao (nome) VALUES (%s)",
                    (caminho.name,))
    con.commit()
    print(f"  aplicada: {caminho.name}", flush=True)


def main():
    ap = argparse.ArgumentParser(description="Migrações do banco do Sentinela")
    ap.add_argument("--listar", action="store_true")
    args = ap.parse_args()

    with conecta() as con:
        falta = pendentes(con)
        if args.listar:
            ja = aplicadas(con)
            for p in sorted(MIGRACOES.glob("*.sql")):
                print(f"  [{'x' if p.name in ja else ' '}] {p.name}")
            return 0

        if not falta:
            print("nada a aplicar — banco em dia")
            return 0
        print(f"{len(falta)} migração(ões) pendente(s)")
        for caminho in falta:
            aplica(con, caminho)
    return 0


if __name__ == "__main__":
    sys.exit(main())
