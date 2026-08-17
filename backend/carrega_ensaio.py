#!/usr/bin/env python3
"""Sentinela — carrega a campanha de campo (GeoJSON) no PostGIS.

Põe os pontos do ensaio 02 no banco, e não apenas no arquivo, para que a
medição de campo possa ser cruzada com a telemetria corrente e com as bases
geoespaciais (carta de suscetibilidade, edificações) direto no QGIS — que é o
ponto do ADR-005.

Idempotente: reexecutar atualiza os pontos em vez de duplicar.

Uso:
    python3 carrega_ensaio.py                      # dados/ensaio02.geojson
    python3 carrega_ensaio.py --arquivo outro.geojson --ensaio ensaio03

Autoria: Luiz Matheus Marassi de Paula
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import psycopg

from ingestor import carrega_env

RAIZ = Path(__file__).resolve().parents[1]

SQL = """
INSERT INTO ponto_ensaio (ensaio, ponto, posicao, altitude_m, distancia_m,
    rssi_med, rssi_min, rssi_max, margem_db, assimetria_db, perda_pct,
    veredito, motivo, ambiente, quando)
VALUES (%(ensaio)s, %(ponto)s,
        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
        %(altitude_m)s, %(distancia_m)s, %(rssi_med)s, %(rssi_min)s,
        %(rssi_max)s, %(margem_db)s, %(assimetria_db)s, %(perda_pct)s,
        %(veredito)s, %(motivo)s, %(ambiente)s, %(quando)s)
ON CONFLICT (ensaio, ponto) DO UPDATE SET
    posicao = EXCLUDED.posicao, altitude_m = EXCLUDED.altitude_m,
    distancia_m = EXCLUDED.distancia_m, rssi_med = EXCLUDED.rssi_med,
    rssi_min = EXCLUDED.rssi_min, rssi_max = EXCLUDED.rssi_max,
    margem_db = EXCLUDED.margem_db, assimetria_db = EXCLUDED.assimetria_db,
    perda_pct = EXCLUDED.perda_pct, veredito = EXCLUDED.veredito,
    motivo = EXCLUDED.motivo, ambiente = EXCLUDED.ambiente,
    quando = EXCLUDED.quando
"""


def _quando(valor):
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def monta(feicao, ensaio):
    p = feicao["properties"]
    lon, lat = feicao["geometry"]["coordinates"][:2]
    return {
        "ensaio": ensaio, "ponto": p.get("ponto"), "lon": lon, "lat": lat,
        "altitude_m": p.get("altitude_m"), "distancia_m": p.get("distancia_m"),
        "rssi_med": p.get("rssi_med"), "rssi_min": p.get("rssi_min"),
        "rssi_max": p.get("rssi_max"), "margem_db": p.get("margem_db"),
        "assimetria_db": p.get("assimetria_db"), "perda_pct": p.get("perda_pct"),
        "veredito": p.get("veredito"), "motivo": p.get("motivo"),
        "ambiente": p.get("ambiente"), "quando": _quando(p.get("quando")),
    }


def main():
    ap = argparse.ArgumentParser(description="Carrega pontos de ensaio no PostGIS")
    ap.add_argument("--arquivo", default=str(RAIZ / "dados" / "ensaio02.geojson"))
    ap.add_argument("--ensaio", default="ensaio02")
    ap.add_argument("--banco-host", dest="banco_host",
                    default=os.environ.get("POSTGRES_HOST", "localhost"))
    args = ap.parse_args()

    carrega_env(Path(__file__).resolve().parent / ".env")
    senha = os.environ.get("POSTGRES_PASSWORD")
    if not senha:
        sys.exit("POSTGRES_PASSWORD ausente — defina em backend/.env")

    dados = json.loads(Path(args.arquivo).read_text(encoding="utf-8"))
    linhas = [monta(f, args.ensaio) for f in dados["features"]
              if f.get("geometry")]

    with psycopg.connect(host=args.banco_host,
                         dbname=os.environ.get("POSTGRES_DB", "sentinela"),
                         user=os.environ.get("POSTGRES_USER", "sentinela"),
                         password=senha) as con:
        with con.cursor() as cur:
            cur.executemany(SQL, linhas)
        con.commit()
    print(f"{len(linhas)} ponto(s) de {args.ensaio} carregado(s)")


if __name__ == "__main__":
    main()
