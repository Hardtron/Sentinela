#!/usr/bin/env python3
"""Sentinela — leitura do banco para o painel (sensor, frota e GIS).

Separado de `coletor.py` de propósito: aquele lê o **repositório** (documentos,
git, builds) e não depende de nada externo; este lê o **banco**, que pode estar
fora do ar. Misturar os dois faria uma falha do PostgreSQL derrubar abas que
não têm nada a ver com ele.

Toda função devolve estrutura vazia — e o motivo em `erro` — quando o banco não
responde. Nunca inventa dado (RC-07): aba sem dado diz que está sem dado.

Autoria: Matheus Marassi
"""

import os
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

try:
    import psycopg
except ImportError:                                   # pragma: no cover
    psycopg = None

_estado = {"erro": None}


def _dsn():
    env = RAIZ / "backend" / ".env"
    if env.exists():
        for linha in env.read_text(encoding="utf-8").splitlines():
            linha = linha.strip()
            if linha and not linha.startswith("#") and "=" in linha:
                chave, valor = linha.split("=", 1)
                os.environ.setdefault(chave.strip(), valor.strip())
    return {
        "host": os.environ.get("POSTGRES_HOST", "localhost"),
        "port": int(os.environ.get("POSTGRES_PORT", "5432")),
        "dbname": os.environ.get("POSTGRES_DB", "sentinela"),
        "user": os.environ.get("POSTGRES_USER", "sentinela"),
        "password": os.environ.get("POSTGRES_PASSWORD", ""),
    }


def consulta(sql, params=None):
    """Devolve lista de dicionários, ou [] com o motivo em `_estado['erro']`.

    Erro de banco não sobe como exceção para o servidor HTTP: derrubaria o
    painel inteiro por causa de uma aba. Fica registrado e visível.
    """
    if psycopg is None:
        _estado["erro"] = "psycopg não instalado"
        return []
    try:
        with psycopg.connect(**_dsn(), connect_timeout=5) as con:
            with con.cursor() as cur:
                cur.execute(sql, params or ())
                if cur.description is None:
                    return []
                colunas = [d[0] for d in cur.description]
                linhas = [dict(zip(colunas, l)) for l in cur.fetchall()]
        _estado["erro"] = None
        return linhas
    except Exception as e:                            # noqa: BLE001
        _estado["erro"] = str(e).strip().split("\n")[0]
        return []


def _texto(valor):
    """Datas e Decimals viram texto/float — JSON não serializa os tipos do
    psycopg direto, e converter aqui evita espalhar `default=str` pelo servidor."""
    if valor is None:
        return None
    if isinstance(valor, (int, float, str, bool, list, dict)):
        return valor
    return str(valor)


def _limpa(linhas):
    return [{k: _texto(v) for k, v in linha.items()} for linha in linhas]


# ------------------------------------------------------------------ sensor --

def sensor():
    """Estado corrente de cada nó: última leitura + chuva acumulada."""
    ultimas = consulta("""
        SELECT DISTINCT ON (l.node_id)
               l.node_id, n.placa, l.recebido_em, l.medido_em,
               l.chuva_1h_mm, l.pitch_graus, l.roll_graus, l.umidade_solo,
               l.bateria_mv, l.flags,
               l.chuva_valida, l.inclin_valida, l.solo_valido, l.fonte
          FROM leitura l LEFT JOIN no n ON n.node_id = l.node_id
         ORDER BY l.node_id, l.recebido_em DESC
    """)
    acumulada = consulta("SELECT * FROM chuva_acumulada")
    silencio = consulta("SELECT * FROM no_silencioso ORDER BY node_id")
    return {
        "leituras": _limpa(ultimas),
        "chuva": _limpa(acumulada),
        "silencio": _limpa(silencio),
        "erro": _estado["erro"],
    }


def historico(node_id, horas=72):
    """Série horária para o gráfico — vem da agregação contínua, não da tabela
    bruta, para não trazer milhares de linhas ao navegador."""
    return {
        "pontos": _limpa(consulta("""
            SELECT hora, amostras, chuva_mm, pitch_med, roll_med,
                   solo_med, bateria_min_mv
              FROM leitura_hora
             WHERE node_id = %s AND hora > now() - (%s || ' hours')::interval
             ORDER BY hora
        """, (node_id, str(horas)))),
        "erro": _estado["erro"],
    }


# ------------------------------------------------------------------- frota --

def frota_saude():
    """Manutenção por condição (Frente 7): fila priorizada e alarmes abertos."""
    return {
        "fila": _limpa(consulta("SELECT * FROM fila_manutencao")),
        "referencia": _limpa(consulta(
            "SELECT * FROM referencia_distribuida ORDER BY node_id")),
        "alarmes": _limpa(consulta("""
            SELECT id, node_id, nome, grupo, severidade, gatilho, acao,
                   aberto_em, fechado_em
              FROM alarme WHERE fechado_em IS NULL
             ORDER BY CASE severidade
                        WHEN 'CRITICO' THEN 1 WHEN 'URGENTE' THEN 2
                        WHEN 'ATENCAO' THEN 3 ELSE 4 END, aberto_em DESC
        """)),
        "erro": _estado["erro"],
    }


# --------------------------------------------------------------------- GIS --

def _geojson(linhas, campo="geojson"):
    """Monta FeatureCollection. O PostGIS já devolve a geometria em GeoJSON;
    aqui só se separa geometria de propriedades."""
    import json
    feicoes = []
    for linha in linhas:
        geo = linha.pop(campo, None)
        if not geo:
            continue
        feicoes.append({
            "type": "Feature",
            "geometry": json.loads(geo),
            "properties": {k: _texto(v) for k, v in linha.items()},
        })
    return {"type": "FeatureCollection", "features": feicoes}


def gis_atalaias():
    linhas = consulta("""
        SELECT n.node_id, n.placa, n.papel, n.antena,
               ST_AsGeoJSON(n.posicao::geometry) AS geojson,
               f.indice, f.faixa, f.alarmes_abertos,
               s.estado AS estado_comunicacao
          FROM no n
          LEFT JOIN fila_manutencao f ON f.node_id = n.node_id
          LEFT JOIN no_silencioso   s ON s.node_id = n.node_id
         WHERE n.posicao IS NOT NULL
    """)
    saida = _geojson(linhas)
    saida["erro"] = _estado["erro"]
    return saida


def gis_estacoes():
    """Rede oficial de pluviômetros, com o acumulado corrente."""
    linhas = consulta("""
        SELECT e.codigo, e.nome, e.municipio, e.rede, e.altitude_m,
               round(a.mm_24h::numeric, 1) AS mm_24h,
               round(a.mm_72h::numeric, 1) AS mm_72h,
               round(a.mm_84h::numeric, 1) AS mm_84h,
               ST_AsGeoJSON(e.geom::geometry) AS geojson
          FROM estacao_externa e
          LEFT JOIN chuva_oficial_acumulada a ON a.codigo = e.codigo
         WHERE e.ativa
    """)
    saida = _geojson(linhas)
    saida["erro"] = _estado["erro"]
    return saida


def situacao():
    """Visão combinada: chuva regional oficial + sensores locais da Atalaia.

    É a materialização do ADR-009 — cada fonte na escala em que é confiável, e
    a distância até a estação viajando junto com o número.
    """
    return {
        "atalaias": _limpa(consulta(
            "SELECT * FROM situacao_atalaia ORDER BY node_id")),
        "estacoes": _limpa(consulta("""
            SELECT e.codigo, e.nome, e.municipio, e.rede,
                   round(a.mm_1h::numeric,1)  AS mm_1h,
                   round(a.mm_24h::numeric,1) AS mm_24h,
                   round(a.mm_72h::numeric,1) AS mm_72h,
                   round(a.mm_84h::numeric,1) AS mm_84h,
                   a.ate
              FROM estacao_externa e
              LEFT JOIN chuva_oficial_acumulada a ON a.codigo = e.codigo
             WHERE e.ativa ORDER BY e.nome
        """)),
        "limiares": _limpa(consulta("SELECT * FROM limiar_municipio")),
        "erro": _estado["erro"],
    }


def gis_suscetibilidade():
    linhas = consulta("""
        SELECT id, municipio, classe, fonte, referencia,
               ST_AsGeoJSON(geom::geometry) AS geojson
          FROM suscetibilidade
    """)
    saida = _geojson(linhas)
    saida["erro"] = _estado["erro"]
    return saida


def gis_ensaios():
    """Pontos do ensaio 02, já no PostGIS — dá contexto de alcance ao mapa."""
    linhas = consulta("""
        SELECT ensaio, ponto, veredito, distancia_m, rssi_med, margem_db,
               ST_AsGeoJSON(posicao::geometry) AS geojson
          FROM ponto_ensaio
    """)
    saida = _geojson(linhas)
    saida["erro"] = _estado["erro"]
    return saida
