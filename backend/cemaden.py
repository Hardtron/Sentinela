#!/usr/bin/env python3
"""Sentinela — importa CSV de chuva da rede oficial (ADR-009).

Este é o caminho manual/legado para exportações CSV. A API PED oficial do
CEMADEN foi confirmada e sua aquisição auditável vive em
``backend/fontes_externas.py``. O importador continua útil para arquivos
históricos e contingência, mas não registra o bruto, a execução e a revisão
completos da migração 011; preferir a nova esteira em operação contínua.

O importador é idempotente: reimportar o mesmo arquivo não duplica acumulado —
e duplicata aqui inflaria justamente o preditor de risco.

Uso:
    python3 backend/cemaden.py --estacoes estacoes.csv
    python3 backend/cemaden.py --chuva leituras.csv
    python3 backend/cemaden.py --chuva leituras.csv --seco

Autoria: Matheus Marassi
"""

import argparse
import csv
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from ingestor import carrega_env

RAIZ = Path(__file__).resolve().parent

# Nomes de coluna aceitos. O Cemaden já mudou rótulo entre exportações, então
# em vez de exigir um cabeçalho exato aceita-se um conjunto de sinônimos — e
# falha-se explicitamente se nenhum aparecer, em vez de gravar coluna errada.
COLUNAS = {
    "codigo": ("codestacao", "cod_estacao", "codigo", "id_estacao"),
    "nome": ("nomeestacao", "nome", "estacao"),
    "municipio": ("municipio", "cidade"),
    "uf": ("uf", "estado", "sigla_uf"),
    "lat": ("latitude", "lat"),
    "lon": ("longitude", "lon", "lng"),
    "altitude": ("altitude", "alt", "altitude_m"),
    "instante": ("datahora", "data_hora", "datamedicao", "horario", "data"),
    "valor": ("valormedida", "valor", "chuva", "acumulado", "precipitacao"),
}


class FormatoDesconhecido(Exception):
    """Cabeçalho não reconhecido — erro explícito, nunca palpite.

    RC-07 aplicado à ingestão: importar uma coluna errada como se fosse chuva
    é pior do que não importar. O acumulado errado vira limiar errado.
    """


def _acha(cabecalho, chave, obrigatorio=True):
    normal = {c.strip().lower().replace(" ", "").replace("_", ""): c
              for c in cabecalho}
    for cand in COLUNAS[chave]:
        alvo = cand.replace("_", "")
        if alvo in normal:
            return normal[alvo]
    if obrigatorio:
        raise FormatoDesconhecido(
            f"coluna '{chave}' não encontrada; cabeçalho: {list(cabecalho)}")
    return None


def _numero(txt):
    if txt is None or str(txt).strip() == "":
        return None
    try:
        return float(str(txt).strip().replace(",", "."))
    except ValueError:
        return None


def _instante(txt):
    """Formatos vistos nas exportações do Cemaden. Sem fuso explícito assume-se
    UTC — e isso fica documentado, não implícito."""
    txt = str(txt).strip()
    for formato in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S",
                    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%Y-%m-%d %H:%M"):
        try:
            return datetime.strptime(txt, formato).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


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
        password=senha)


SQL_ESTACAO = """
INSERT INTO estacao_externa (codigo, nome, municipio, uf, rede, altitude_m, geom)
VALUES (%s, %s, %s, %s, %s, %s,
        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography)
ON CONFLICT (codigo) DO UPDATE SET
    nome = EXCLUDED.nome, municipio = EXCLUDED.municipio,
    uf = EXCLUDED.uf, altitude_m = EXCLUDED.altitude_m, geom = EXCLUDED.geom
"""

SQL_CHUVA = """
INSERT INTO chuva_oficial (medido_em, codigo, chuva_mm, intervalo_min)
VALUES (%s, %s, %s, %s)
ON CONFLICT (codigo, medido_em) DO NOTHING
"""


def le_estacoes(caminho, rede):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, delimiter=_delimitador(caminho))
        cab = leitor.fieldnames or []
        cols = {k: _acha(cab, k) for k in
                ("codigo", "nome", "municipio", "lat", "lon")}
        uf = _acha(cab, "uf", obrigatorio=False)
        alt = _acha(cab, "altitude", obrigatorio=False)
        for linha in leitor:
            lat, lon = _numero(linha[cols["lat"]]), _numero(linha[cols["lon"]])
            if lat is None or lon is None:
                continue     # estação sem coordenada não serve: a associação é geométrica
            yield (str(linha[cols["codigo"]]).strip(), linha[cols["nome"]],
                   linha[cols["municipio"]], (linha.get(uf) or "")[:2] or None,
                   rede, _numero(linha.get(alt)), lon, lat)


def le_chuva(caminho, intervalo):
    with open(caminho, encoding="utf-8-sig", newline="") as f:
        leitor = csv.DictReader(f, delimiter=_delimitador(caminho))
        cab = leitor.fieldnames or []
        c_cod = _acha(cab, "codigo")
        c_ts = _acha(cab, "instante")
        c_val = _acha(cab, "valor")
        for linha in leitor:
            ts, val = _instante(linha[c_ts]), _numero(linha[c_val])
            if ts is None or val is None:
                continue     # RC-07: linha ilegível é descartada, não vira zero
            yield (ts, str(linha[c_cod]).strip(), val, intervalo)


def _delimitador(caminho):
    with open(caminho, encoding="utf-8-sig") as f:
        amostra = f.readline()
    return ";" if amostra.count(";") > amostra.count(",") else ","


def importa(caminho, tipo, rede, intervalo, seco):
    linhas = list(le_estacoes(caminho, rede) if tipo == "estacoes"
                  else le_chuva(caminho, intervalo))
    print(f"{len(linhas)} linha(s) legível(is) em {Path(caminho).name}")
    if seco or not linhas:
        return len(linhas)
    with conecta() as con:
        with con.cursor() as cur:
            cur.executemany(SQL_ESTACAO if tipo == "estacoes" else SQL_CHUVA,
                            linhas)
        con.commit()
    print(f"importado ({tipo})")
    return len(linhas)


def main():
    ap = argparse.ArgumentParser(description="Importa chuva oficial (CEMADEN/INMET)")
    ap.add_argument("--estacoes", help="CSV de estações (código, nome, lat, lon)")
    ap.add_argument("--chuva", help="CSV de leituras (código, data/hora, valor)")
    ap.add_argument("--rede", default="CEMADEN")
    ap.add_argument("--intervalo", type=int, default=10,
                    help="minutos que o acumulado de cada linha representa")
    ap.add_argument("--seco", action="store_true")
    args = ap.parse_args()

    if not args.estacoes and not args.chuva:
        ap.error("informe --estacoes e/ou --chuva")
    try:
        if args.estacoes:
            importa(args.estacoes, "estacoes", args.rede, args.intervalo, args.seco)
        if args.chuva:
            importa(args.chuva, "chuva", args.rede, args.intervalo, args.seco)
    except FormatoDesconhecido as e:
        sys.exit(f"formato não reconhecido: {e}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
