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
from datetime import datetime, timezone
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
    """Atalaias no mapa, com tudo que decide olhar para ela (§I.3 do plano).

    O marcador junta três escalas que só fazem sentido lidas juntas: o estado
    do ciclo de vida (Atalaia em comissionamento não é ponto de dado confiável),
    a chuva **regional** oficial da estação mais próxima com a distância — que
    é o limitador da representatividade (ADR-009) — e o enlace **local**
    corrente. Chuva de 84 h sem a distância da estação é número solto: célula
    convectiva de 1–5 km na Serra do Mar não cabe numa estação a 8 km.
    """
    linhas = consulta("""
        SELECT n.node_id, n.placa, n.papel, n.antena, n.estado,
               ST_AsGeoJSON(n.posicao::geometry) AS geojson,
               f.indice, f.faixa, f.alarmes_abertos,
               s.estado AS estado_comunicacao,
               ae.estacao, ae.distancia_m AS distancia_estacao_m,
               round(ca.mm_24h::numeric, 1) AS mm_24h,
               round(ca.mm_72h::numeric, 1) AS mm_72h,
               round(ca.mm_84h::numeric, 1) AS mm_84h,
               u.rssi_dbm, u.snr_db, u.recebido_em AS enlace_em,
               sa.v_fim_mv, sa.umidade_interna, sa.temp_interna_c,
               ci.foto_oficial_path
          FROM no n
          LEFT JOIN fila_manutencao f ON f.node_id = n.node_id
          LEFT JOIN no_silencioso   s ON s.node_id = n.node_id
          LEFT JOIN atalaia_estacao ae ON ae.node_id = n.node_id
          LEFT JOIN chuva_oficial_acumulada ca ON ca.codigo = ae.codigo
          LEFT JOIN LATERAL (
              SELECT e.rssi_dbm, e.snr_db, e.recebido_em FROM enlace e
               WHERE e.node_id = n.node_id
               ORDER BY e.recebido_em DESC LIMIT 1) u ON true
          LEFT JOIN LATERAL (
              SELECT h.v_fim_mv, h.umidade_interna, h.temp_interna_c
                FROM saude_atalaia h
               WHERE h.node_id = n.node_id
               ORDER BY h.recebido_em DESC LIMIT 1) sa ON true
          LEFT JOIN LATERAL (
              SELECT c.foto_oficial_path FROM checklist_instalacao c
               WHERE c.node_id = n.node_id AND c.foto_oficial_path IS NOT NULL
               ORDER BY c.submetido_em DESC LIMIT 1) ci ON true
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


def operacao():
    """Evidências de funcionamento persistidas, sem inferir serviço online.

    Os quatro ``max`` respondem somente qual foi o registro mais recente de
    cada etapa no banco. Em particular, dado recente em ``enlace`` é evidência
    de que a cadeia escreveu no passado, não prova que bridge ou ingestor
    continuam executando neste instante.
    """
    consultado_em = datetime.now(timezone.utc).isoformat()
    linhas = consulta("""
        SELECT (SELECT max(recebido_em) FROM enlace)       AS enlace_em,
               (SELECT max(gerado_em) FROM saude_bridge)  AS bridge_em,
               (SELECT max(recebido_em) FROM leitura)     AS leitura_em,
               (SELECT max(recebido_em) FROM saude_atalaia) AS atalaia_em
    """)
    erro = _estado["erro"]
    return {
        "disponivel": erro is None,
        "consultado_em": consultado_em,
        "evidencias": _limpa(linhas)[0] if linhas else {},
        "erro": erro,
        "fonte": "PostgreSQL/TimescaleDB",
        "qualidade": "observado no banco; não confirma processo em execução",
    }


def fontes_externas():
    """Catálogo e última aquisição, sem converter fonte em alerta.

    A view é criada pela migração 011. Em banco ainda não migrado, ``consulta``
    devolve a ausência explicitamente e o restante do painel permanece ativo.
    """
    fontes = consulta("""
        SELECT s.provedor_codigo, s.provedor, s.orgao, s.acesso,
               s.exige_cadastro,
               conjunto_codigo, titulo, classe, variavel, unidade, uso,
               configuracao_estado, limitacao, ultima_execucao_em,
               ultima_conclusao_em, ultima_execucao_estado,
               itens_recebidos, itens_aceitos, itens_rejeitados, erro_resumo,
               ultimo_ativo_em, ultimo_processado_em, ultimo_observado_em,
               ultimo_sha256,
               (SELECT fc.metadados
                  FROM fonte_camada fc
                 WHERE fc.conjunto_id=s.conjunto_id
                 ORDER BY fc.id DESC LIMIT 1) AS camada_metadados
          FROM fonte_estado s
         ORDER BY provedor, titulo
    """)
    erro = _estado["erro"]
    quarentena = []
    if erro is None:
        quarentena = consulta("""
            SELECT count(*) AS total, max(registrado_em) AS ultima_em
              FROM fonte_quarentena
             WHERE registrado_em > now() - interval '7 days'
        """)
        erro = _estado["erro"]
    return {
        "fontes": _limpa(fontes),
        "quarentena_7d": _limpa(quarentena)[0] if quarentena else {},
        "consultado_em": datetime.now(timezone.utc).isoformat(),
        "erro": erro,
        "escopo": (
            "Dados externos são evidência contextual; não participam de "
            "alertas automáticos nesta versão."),
    }


def fontes_observacoes():
    """Última revisão de cada observação externa, sem agregar provedores."""
    linhas = consulta("""
        SELECT DISTINCT ON (p.codigo, e.codigo_externo, o.variavel,
                            coalesce(o.periodo_s, -1))
               p.codigo AS provedor_codigo, p.nome AS provedor,
               c.codigo AS conjunto_codigo, c.classe, c.uso,
               e.codigo_externo, e.nome AS estacao, e.municipio, e.uf,
               o.medido_em, o.recebido_em, o.variavel, o.valor, o.unidade,
               o.periodo_s, o.qualificacao_origem, o.revisao,
               o.metadados, b.sha256, b.fonte_uri
          FROM fonte_observacao_atual o
          JOIN fonte_conjunto c ON c.id=o.conjunto_id
          JOIN fonte_provedor p ON p.codigo=c.provedor_codigo
          JOIN fonte_estacao e ON e.id=o.estacao_id
          LEFT JOIN fonte_ativo_bruto b ON b.id=o.ativo_bruto_id
         ORDER BY p.codigo, e.codigo_externo, o.variavel,
                  coalesce(o.periodo_s, -1), o.recebido_em DESC,
                  o.medido_em DESC
    """)
    return {
        "observacoes": _limpa(linhas),
        "erro": _estado["erro"],
        "escopo": "observações por estação e período; sem soma entre provedores",
    }


def gis_fontes_contexto():
    """Feições oficiais externas mais recentes, com proveniência explícita."""
    linhas = consulta("""
        SELECT p.codigo AS provedor_codigo, p.nome AS provedor,
               c.codigo AS conjunto_codigo, c.titulo, c.classe, c.uso,
               f.identificador, f.propriedades,
               b.adquirido_em, b.sha256, b.fonte_uri,
               ST_AsGeoJSON(f.geom) AS geojson
          FROM fonte_feicao_atual f
          JOIN fonte_conjunto c ON c.id=f.conjunto_id
          JOIN fonte_provedor p ON p.codigo=c.provedor_codigo
          JOIN fonte_ativo_bruto b ON b.id=f.ativo_bruto_id
         WHERE f.geom IS NOT NULL
    """)
    saida = _geojson(linhas)
    saida["erro"] = _estado["erro"]
    saida["escopo"] = "contexto oficial externo; não é classificação do Sentinela"
    return saida


def comissionamento():
    """Estado do ciclo de vida de cada Atalaia (Frente 9)."""
    return {
        "atalaias": _limpa(consulta("SELECT * FROM comissionamento_estado")),
        "criterios": _limpa(consulta(
            "SELECT chave, valor, unidade, fonte, descricao, "
            "to_jsonb(c)->>'status' AS status, "
            "to_jsonb(c)->>'referencia' AS referencia, "
            "to_jsonb(c)->>'vigente_desde' AS vigente_desde, "
            "to_jsonb(c)->>'atualizado_por' AS atualizado_por "
            "FROM criterio_comissionamento c ORDER BY chave")),
        "transicoes": _limpa(consulta("""
            SELECT t.node_id, n.placa, t.de, t.para, t.ocorrida_em, t.autor, t.motivo
              FROM transicao_estado t JOIN no n ON n.node_id = t.node_id
             ORDER BY t.ocorrida_em DESC LIMIT 40""")),
        "erro": _estado["erro"],
    }


def laudo(node_id):
    """Ficha técnica de homologação — tudo o que sustenta a ativação."""
    checklist = consulta("""
        SELECT c.*, ST_Y(c.posicao_exif::geometry) AS lat,
               ST_X(c.posicao_exif::geometry) AS lon
          FROM checklist_instalacao c
         WHERE c.node_id = %s ORDER BY c.submetido_em DESC LIMIT 1""", (node_id,))
    return {
        "no": _limpa(consulta(
            "SELECT * FROM comissionamento_estado WHERE node_id = %s", (node_id,))),
        "checklist": _limpa(checklist),
        "transicoes": _limpa(consulta(
            "SELECT de, para, ocorrida_em, autor, motivo FROM transicao_estado "
            "WHERE node_id = %s ORDER BY ocorrida_em", (node_id,))),
        # Para checklists novos, o snapshot é a fonte histórica. O catálogo
        # corrente segue separado para não fingir que era o vigente em laudos
        # antigos, anteriores à migração 010.
        "criterios": _limpa(consulta(
            "SELECT chave, valor, unidade, fonte, "
            "to_jsonb(c)->>'status' AS status, "
            "to_jsonb(c)->>'referencia' AS referencia, "
            "to_jsonb(c)->>'vigente_desde' AS vigente_desde "
            "FROM criterio_comissionamento c")),
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


def reconhece_alarme(payload):
    """Executa a chamada da procedure SQL 009 de reconhecimento de alarme."""
    alarme_id = payload.get("alarme_id")
    operador = str(payload.get("operador") or "").strip()
    acao = str(payload.get("acao_tomada") or "RECONHECIDO").strip()
    despacho = bool(payload.get("despacho_equipe", False))
    nota = payload.get("nota_operador")

    if not alarme_id:
        return {"erro": "alarme_id é obrigatório"}
    if not operador:
        return {"erro": "operador é obrigatório"}
    if not acao:
        return {"erro": "ação tomada é obrigatória"}

    sql = "SELECT reconhecer_alarme(%s, %s, %s, %s, %s)"
    if psycopg is None:
        return {"erro": "psycopg não instalado"}
    try:
        with psycopg.connect(**_dsn(), connect_timeout=5) as con:
            with con.cursor() as cur:
                cur.execute(sql, (int(alarme_id), operador, acao, despacho, nota))
                con.commit()
        return {"ok": True, "alarme_id": alarme_id, "reconhecido_por": operador}
    except Exception as e:                            # noqa: BLE001
        return {"erro": str(e).strip().split("\n")[0]}
