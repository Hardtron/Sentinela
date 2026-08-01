#!/usr/bin/env python3
"""Testes locais do contrato de fontes; não usam rede, banco ou credenciais."""

import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

from fontes.contrato import ConfiguracaoAusente, Requisicao, Resposta  # noqa: E402
from fontes.provedores import _token_ana, normaliza, requisicoes  # noqa: E402
from fontes.repositorio import _revisao  # noqa: E402
from fontes.contrato import Observacao  # noqa: E402
from fontes.cli import coleta_requisicao  # noqa: E402
from fontes.transporte import guarda_bruto, uri_publica  # noqa: E402


def verifica(condicao, mensagem):
    if not condicao:
        raise AssertionError(mensagem)


def testa_uri_sem_segredo():
    uri = uri_publica("https://exemplo.test/a?token=abc&uf=SP&api_key=xyz")
    verifica("abc" not in uri and "xyz" not in uri, "segredo ficou na URI")
    verifica("uf=SP" in uri, "parâmetro não sensível foi removido")


def testa_bruto_atomico_e_deduplicado():
    resposta = Resposta("https://exemplo.test/dado", 200,
                        "application/json", b'{"x":1}')
    instante = datetime(2026, 8, 1, tzinfo=timezone.utc)
    with tempfile.TemporaryDirectory() as pasta:
        raiz = Path(pasta)
        caminho1, hash1 = guarda_bruto(resposta, "TESTE", "dados", raiz, instante)
        caminho2, hash2 = guarda_bruto(
            resposta, "TESTE", "dados", raiz,
            datetime(2026, 8, 2, tzinfo=timezone.utc))
        verifica(caminho1 == caminho2 and hash1 == hash2, "bruto duplicado")
        verifica(caminho1.read_bytes() == resposta.dados, "bruto alterado")
        verifica(not list(caminho1.parent.glob(".aquisicao-*")), "temporário sobrou")


def testa_cemaden_com_fuso_explicito():
    dados = json.dumps([{
        "codestacao": "ABC", "codibge": 3510500,
        "datahora": "2026-08-01T12:30:00", "acc1hr": 1.5,
        "acc24hr": 8.0, "acc72hr": None,
    }]).encode()
    req = Requisicao("CEMADEN", "acumulados-recentes", "https://x.test")
    res = Resposta("https://x.test", 200, "application/json", dados)
    normal = normaliza(req, res, {"CEMADEN_FUSO": "America/Sao_Paulo"})
    verifica(len(normal.estacoes) == 1, "estação CEMADEN não normalizada")
    verifica(len(normal.observacoes) == 2, "acumulados ausentes/duplicados")
    verifica({o.periodo_s for o in normal.observacoes} == {3600, 86400},
             "períodos oficiais foram alterados")
    verifica(normal.observacoes[0].medido_em.utcoffset() is not None,
             "timestamp continuou sem fuso")


def testa_cemaden_recusa_fuso_ausente():
    req = Requisicao("CEMADEN", "acumulados-recentes", "https://x.test")
    res = Resposta("https://x.test", 200, "application/json", b"[]")
    try:
        normaliza(req, res, {})
    except ConfiguracaoAusente:
        return
    raise AssertionError("CEMADEN aceitou data sem política de fuso")


def testa_sgb_exige_recorte():
    try:
        requisicoes("SGB", {"SGB_WHERE": "1 = 1"})
    except ConfiguracaoAusente:
        return
    raise AssertionError("SGB aceitou download nacional não recortado")


def testa_ana_seco_nao_chama_rede():
    ambiente = {
        "ANA_IDENTIFICADOR": "id", "ANA_SENHA": "segredo",
        "ANA_ESTACOES": "123", "ANA_INTERVALO": "HORA_1",
    }
    reqs = requisicoes("ANA", ambiente, buscar=None)
    verifica(len(reqs) == 1, "planejamento ANA falhou")
    verifica("segredo" not in str(reqs), "senha ANA vazou no plano")


def testa_token_ana_no_envelope_oficial():
    token = _token_ana(b'{"status":"200 OK","items":{"access_token":"abc"}}')
    verifica(token == "abc", "token no envelope items não foi encontrado")


def testa_revisao_por_conteudo():
    instante = datetime(2026, 8, 1, tzinfo=timezone.utc)
    primeira = Observacao("A", instante, "x", 1.0, "mm", periodo_s=3600)
    repetida = Observacao("A", instante, "x", 1.0, "mm", periodo_s=3600)
    corrigida = Observacao("A", instante, "x", 1.1, "mm", periodo_s=3600)
    verifica(_revisao(primeira) == _revisao(repetida), "repetição criou revisão")
    verifica(_revisao(primeira) != _revisao(corrigida), "correção foi perdida")


def testa_geojson_preserva_sem_reinterpretar():
    req = Requisicao("SGB", "setorizacao-risco", "https://x.test")
    bruto = b'{"type":"FeatureCollection","features":[{"type":"Feature","properties":{"grau_risco":"R4"},"geometry":null}]}'
    res = Resposta("https://x.test", 200, "application/geo+json", bruto)
    normal = normaliza(req, res, {})
    verifica(normal.metadados["feicoes"] == 1, "contagem GeoJSON incorreta")
    verifica(len(normal.feicoes) == 1 and normal.feicoes[0].identificador == "0",
             "feição GeoJSON não foi preservada")
    verifica(not normal.estacoes and not normal.observacoes,
             "classificação SGB foi convertida em medição")


def testa_bruto_em_quarentena_e_reprocessado():
    class Repo:
        normalizou = False

        def inicia(self, *args):
            return 1, 2

        def registra_ativo(self, *args):
            return 3, False, False  # já baixado, ainda não processado

        def normaliza(self, *args):
            self.normalizou = True
            return 1

        def termina(self, *args, **kwargs):
            pass

        def reverte(self):
            pass

        def quarentena(self, *args, **kwargs):
            raise AssertionError("resposta válida foi para quarentena")

    repo = Repo()
    req = Requisicao("SGB", "setorizacao-risco", "https://x.test")
    res = Resposta("https://x.test", 200, "application/geo+json",
                   b'{"type":"FeatureCollection","features":[]}')
    estado, aceitos = coleta_requisicao(
        req, repo, buscar=lambda _: res,
        guardar=lambda *args: (Path("/tmp/bruto"), "a" * 64))
    verifica(estado == "SUCESSO" and aceitos == 1 and repo.normalizou,
             "bruto não processado não foi retentado")


def main():
    testes = [valor for nome, valor in globals().items()
              if nome.startswith("testa_") and callable(valor)]
    for teste in sorted(testes, key=lambda f: f.__name__):
        teste()
        print(f"ok: {teste.__name__}")
    print(f"{len(testes)} testes de fontes externas: ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
