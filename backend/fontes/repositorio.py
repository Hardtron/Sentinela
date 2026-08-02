"""Persistência transacional do contrato de fontes externas."""

import json
import os
import hashlib
from datetime import datetime, timezone
from pathlib import Path

from . import VERSAO_COLETOR

RAIZ_BACKEND = Path(__file__).resolve().parents[1]


def _carrega_env(caminho):
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip())


def conecta():
    _carrega_env(RAIZ_BACKEND / ".env")
    try:
        import psycopg
    except ImportError as erro:
        raise RuntimeError("psycopg não instalado no ambiente do backend") from erro
    senha = os.environ.get("POSTGRES_PASSWORD")
    if not senha:
        raise RuntimeError("POSTGRES_PASSWORD ausente em backend/.env")
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "sentinela"),
        user=os.environ.get("POSTGRES_USER", "sentinela"), password=senha)


class Repositorio:
    def __init__(self, conexao):
        self.conexao = conexao

    def conjunto_id(self, provedor, conjunto):
        with self.conexao.cursor() as cur:
            cur.execute("""
                SELECT id FROM fonte_conjunto
                 WHERE provedor_codigo=%s AND codigo=%s
            """, (provedor, conjunto))
            linha = cur.fetchone()
        if not linha:
            raise RuntimeError(f"conjunto não migrado: {provedor}/{conjunto}")
        return linha[0]

    def reverte(self):
        self.conexao.rollback()

    def condicionais_http(self, conjunto_id):
        with self.conexao.cursor() as cur:
            cur.execute("""
                SELECT metadados->'http'->>'etag',
                       metadados->'http'->>'ultima_modificacao'
                  FROM fonte_ativo_bruto
                 WHERE conjunto_id=%s
                 ORDER BY adquirido_em DESC, id DESC LIMIT 1
            """, (conjunto_id,))
            linha = cur.fetchone()
        if not linha:
            return {}
        cabecalhos = {}
        if linha[0]:
            cabecalhos["If-None-Match"] = linha[0]
        if linha[1]:
            cabecalhos["If-Modified-Since"] = linha[1]
        return cabecalhos

    def inicia(self, provedor, conjunto, configuracao):
        conjunto_id = self.conjunto_id(provedor, conjunto)
        with self.conexao.cursor() as cur:
            cur.execute("""
                UPDATE fonte_conjunto SET estado='ATIVO' WHERE id=%s
            """, (conjunto_id,))
            cur.execute("""
                INSERT INTO fonte_execucao
                    (conjunto_id, estado, versao_coletor, configuracao)
                VALUES (%s, 'INICIADA', %s, %s::jsonb) RETURNING id
            """, (conjunto_id, VERSAO_COLETOR,
                  json.dumps(configuracao, ensure_ascii=False)))
            execucao_id = cur.fetchone()[0]
        self.conexao.commit()
        return conjunto_id, execucao_id

    def registra_ativo(self, conjunto_id, execucao_id, resposta, caminho, sha256,
                       metadados=None):
        with self.conexao.cursor() as cur:
            cur.execute("""
                WITH novo AS (
                    INSERT INTO fonte_ativo_bruto
                        (conjunto_id, execucao_id, fonte_uri, tipo_conteudo,
                         tamanho_bytes, sha256, caminho, metadados)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (conjunto_id, sha256) DO NOTHING
                    RETURNING id
                )
                SELECT id, TRUE, FALSE FROM novo
                UNION ALL
                SELECT id, FALSE, processado_em IS NOT NULL FROM fonte_ativo_bruto
                 WHERE conjunto_id=%s AND sha256=%s
                   AND NOT EXISTS (SELECT 1 FROM novo)
                LIMIT 1
            """, (conjunto_id, execucao_id, resposta.url_publica,
                  resposta.tipo_conteudo, len(resposta.dados), sha256,
                  str(caminho), json.dumps(metadados or {}, ensure_ascii=False),
                  conjunto_id, sha256))
            resultado = cur.fetchone()
        self.conexao.commit()
        return resultado[0], bool(resultado[1]), bool(resultado[2])

    def normaliza(self, conjunto_id, ativo_id, conteudo):
        aceitos = 0
        estacoes = {}
        with self.conexao.cursor() as cur:
            for estacao in conteudo.estacoes:
                cur.execute("""
                    INSERT INTO fonte_estacao
                        (provedor_codigo, codigo_externo, nome, municipio, uf,
                         altitude_m, geom, metadados)
                    VALUES (%s,%s,%s,%s,%s,%s,
                            CASE WHEN %s::double precision IS NULL
                                      OR %s::double precision IS NULL THEN NULL ELSE
                              ST_SetSRID(ST_MakePoint(%s::double precision,
                                                     %s::double precision),4326)::geography END,
                            %s::jsonb)
                    ON CONFLICT (provedor_codigo, codigo_externo) DO UPDATE SET
                        nome=coalesce(EXCLUDED.nome, fonte_estacao.nome),
                        municipio=coalesce(EXCLUDED.municipio, fonte_estacao.municipio),
                        uf=coalesce(EXCLUDED.uf, fonte_estacao.uf),
                        altitude_m=coalesce(EXCLUDED.altitude_m, fonte_estacao.altitude_m),
                        geom=coalesce(EXCLUDED.geom, fonte_estacao.geom),
                        metadados=fonte_estacao.metadados || EXCLUDED.metadados,
                        vista_ultimo_em=now()
                    RETURNING id
                """, (estacao.provedor, estacao.codigo, estacao.nome,
                      estacao.municipio, estacao.uf, estacao.altitude_m,
                      estacao.longitude, estacao.latitude, estacao.longitude,
                      estacao.latitude,
                      json.dumps(estacao.metadados, ensure_ascii=False)))
                estacoes[estacao.codigo] = cur.fetchone()[0]
            for obs in conteudo.observacoes:
                estacao_id = estacoes.get(obs.estacao_codigo)
                if estacao_id is None:
                    raise RuntimeError(
                        f"observação sem estação: {obs.estacao_codigo}")
                revisao = _revisao(obs)
                cur.execute("""
                    INSERT INTO fonte_observacao_pontual
                        (conjunto_id, estacao_id, medido_em, variavel, valor,
                         unidade, periodo_s, qualificacao_origem, revisao,
                         ativo_bruto_id, metadados)
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                    ON CONFLICT (conjunto_id, estacao_id, medido_em, variavel,
                                 (coalesce(periodo_s, -1)), revisao) DO NOTHING
                """, (conjunto_id, estacao_id, obs.medido_em, obs.variavel,
                      obs.valor, obs.unidade, obs.periodo_s, obs.qualificacao,
                      revisao, ativo_id,
                      json.dumps(obs.metadados, ensure_ascii=False)))
                aceitos += cur.rowcount
            _atualiza_periodo(cur, ativo_id, conteudo)
            if conteudo.feicoes:
                for feicao in conteudo.feicoes:
                    geometria = (json.dumps(feicao.geometria, ensure_ascii=False)
                                 if feicao.geometria else None)
                    cur.execute("""
                        INSERT INTO fonte_feicao
                            (conjunto_id, ativo_bruto_id, identificador, geom,
                             propriedades)
                        VALUES (%s,%s,%s,
                                CASE WHEN %s::text IS NULL THEN NULL ELSE
                                  ST_SetSRID(ST_GeomFromGeoJSON(%s::text),4326) END,
                                %s::jsonb)
                        ON CONFLICT (conjunto_id, ativo_bruto_id, identificador)
                        DO NOTHING
                    """, (conjunto_id, ativo_id, feicao.identificador,
                          geometria, geometria,
                          json.dumps(feicao.propriedades, ensure_ascii=False)))
                    aceitos += cur.rowcount
            if not conteudo.observacoes:
                cur.execute("""
                    INSERT INTO fonte_camada
                        (conjunto_id, ativo_bruto_id, identificador, metadados)
                    VALUES (%s,%s,%s,%s::jsonb)
                    ON CONFLICT (conjunto_id, ativo_bruto_id, identificador)
                    DO NOTHING
                """, (conjunto_id, ativo_id,
                      conteudo.metadados.get("identificador", "ATIVO_BRUTO"),
                      json.dumps(conteudo.metadados, ensure_ascii=False)))
            cur.execute("""
                UPDATE fonte_ativo_bruto SET processado_em=now() WHERE id=%s
            """, (ativo_id,))
        self.conexao.commit()
        return aceitos

    def termina(self, execucao_id, estado, recebidos=0, aceitos=0, rejeitados=0,
                http_status=None, erro=None):
        with self.conexao.cursor() as cur:
            cur.execute("""
                UPDATE fonte_execucao SET terminado_em=now(), estado=%s,
                       http_status=%s, itens_recebidos=%s, itens_aceitos=%s,
                       itens_rejeitados=%s, erro_resumo=%s
                 WHERE id=%s
            """, (estado, http_status, recebidos, aceitos, rejeitados,
                  _resumo(erro), execucao_id))
        self.conexao.commit()

    def quarentena(self, conjunto_id, execucao_id, etapa, motivo, uri=None,
                   sha256=None, detalhe=None):
        with self.conexao.cursor() as cur:
            cur.execute("""
                INSERT INTO fonte_quarentena
                    (conjunto_id, execucao_id, etapa, motivo, fonte_uri,
                     sha256, detalhe)
                VALUES (%s,%s,%s,%s,%s,%s,%s::jsonb)
            """, (conjunto_id, execucao_id, etapa, _resumo(motivo), uri,
                  sha256, json.dumps(detalhe or {}, ensure_ascii=False)))
        self.conexao.commit()


def configuracao_publica(requisicao):
    """Snapshot sem valores: prova quais opções atuaram sem guardar segredo."""
    return {
        "parametros": sorted(requisicao.parametros),
        "cabecalhos": sorted(requisicao.cabecalhos),
        "metodo": requisicao.metodo,
        "metadados": requisicao.metadados,
        "coletado_em": datetime.now(timezone.utc).isoformat(),
    }


def _atualiza_periodo(cur, ativo_id, conteudo):
    if conteudo.observacoes:
        instantes = [obs.medido_em for obs in conteudo.observacoes]
        inicio, fim = min(instantes), max(instantes)
    else:
        inicio = conteudo.metadados.get("observado_de")
        fim = conteudo.metadados.get("observado_ate")
    if inicio and fim:
        cur.execute("""
            UPDATE fonte_ativo_bruto SET observado_de=%s, observado_ate=%s
             WHERE id=%s
        """, (inicio, fim, ativo_id))


def _resumo(valor):
    if valor is None:
        return None
    # Primeira linha, limitada. Nunca incluir corpo de resposta.
    return str(valor).strip().splitlines()[0][:1000]


def _revisao(observacao):
    if observacao.revisao != "ORIGINAL":
        return observacao.revisao
    identidade = json.dumps({
        "valor": observacao.valor, "unidade": observacao.unidade,
        "periodo_s": observacao.periodo_s,
        "qualificacao": observacao.qualificacao,
    }, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "CONTEUDO:" + hashlib.sha256(identidade.encode()).hexdigest()
