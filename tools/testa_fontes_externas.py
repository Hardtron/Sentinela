#!/usr/bin/env python3
"""Testes locais do contrato de fontes; não usam rede, banco ou credenciais."""

import json
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "backend"))

from fontes.contrato import ConfiguracaoAusente, Requisicao, Resposta  # noqa: E402
from fontes.provedores import (_granulo_imerg, _token_ana, _token_cemaden, normaliza,
                               requisicoes)  # noqa: E402
from fontes.repositorio import _revisao  # noqa: E402
from fontes.contrato import Observacao  # noqa: E402
from fontes.cli import coleta_requisicao  # noqa: E402
from fontes.transporte import guarda_bruto, uri_publica  # noqa: E402
from configura_cemaden import atualiza as atualiza_cemaden  # noqa: E402


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


def testa_configurador_cemaden_preserva_env_e_modo():
    with tempfile.TemporaryDirectory() as pasta:
        caminho = Path(pasta) / "fontes.env"
        caminho.write_text("OUTRA_CHAVE=preservada\nCEMADEN_PED_TOKEN=antigo\n",
                           encoding="utf-8")
        atualiza_cemaden(caminho, {
            "CEMADEN_PED_EMAIL": "conta@example.test",
            "CEMADEN_PED_PASSWORD": "segredo",
            "CEMADEN_PED_TOKEN": "",
        })
        texto = caminho.read_text(encoding="utf-8")
        verifica("OUTRA_CHAVE=preservada" in texto, "configuração foi perdida")
        verifica("CEMADEN_PED_TOKEN=\n" in texto, "token manual não foi removido")
        verifica("CEMADEN_PED_PASSWORD=segredo" in texto, "senha não foi gravada")
        verifica(caminho.stat().st_mode & 0o777 == 0o600, "modo não ficou 600")


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


def testa_cemaden_renova_token_sem_vazar_credenciais():
    ambiente = {
        "CEMADEN_PED_EMAIL": "conta@example.test",
        "CEMADEN_PED_PASSWORD": "segredo-de-teste",
        "CEMADEN_CODIBGE": "3510500",
    }
    recebida = {}

    def buscar(req):
        recebida["req"] = req
        return Resposta(req.url, 201, "application/json",
                        b'{"timeToExp":"14400","token":"jwt-teste"}')

    req = requisicoes("CEMADEN", ambiente, buscar=buscar)[0]
    autenticacao = recebida["req"]
    verifica(autenticacao.metodo == "POST", "SGAA não recebeu POST")
    verifica(autenticacao.url.endswith("/controle-token/tokens"),
             "endpoint SGAA incorreto")
    verifica(req.cabecalhos.get("token") == "jwt-teste",
             "token SGAA não chegou à requisição PED")
    verifica("segredo-de-teste" not in repr(autenticacao),
             "senha CEMADEN vazou na representação da requisição")


def testa_cemaden_seco_nao_autentica():
    ambiente = {
        "CEMADEN_PED_EMAIL": "conta@example.test",
        "CEMADEN_PED_PASSWORD": "segredo-de-teste",
        "CEMADEN_CODIBGE": "3510500",
    }
    req = requisicoes("CEMADEN", ambiente, buscar=None)[0]
    verifica("segredo-de-teste" not in repr(req),
             "senha CEMADEN vazou no planejamento seco")


def testa_token_cemaden_no_contrato_oficial():
    token = _token_cemaden(b'{"timeToExp":"14400","token":"abc"}')
    verifica(token == "abc", "token CEMADEN não foi encontrado")


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


def testa_redemet_usa_header():
    req = requisicoes("REDEMET", {
        "REDEMET_API_KEY": "segredo-de-teste",
        "REDEMET_URLS": "https://api-redemet.decea.mil.br/produtos/stsc",
    })[0]
    verifica(req.cabecalhos.get("X-Api-Key") == "segredo-de-teste",
             "REDEMET não usou X-Api-Key")
    verifica("api_key" not in req.parametros and "segredo-de-teste" not in repr(req),
             "chave REDEMET ficou na query/repr")


def testa_imerg_descobre_granulo_sem_expor_token():
    cmr = json.dumps({"feed": {"entry": [{
        "id": "G-TESTE", "title": "granulo-teste",
        "time_start": "2026-08-01T19:30:00Z",
        "time_end": "2026-08-01T19:59:59Z",
        "links": [{
            "rel": "http://esipfed.org/ns/fedsearch/1.1/data#",
            "href": ("https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/"
                     "GPM_3IMERGHHE.07/2026/213/granulo.HDF5"),
        }],
    }]}}).encode()
    url, metadados = _granulo_imerg(cmr)
    verifica(url.endswith("granulo.HDF5"), "link HTTPS do granulo não foi usado")
    verifica(metadados["granulo_id"] == "G-TESTE", "id CMR não foi preservado")
    ambiente = {
        "NASA_IMERG_AUTHORIZATION": "Bearer segredo-de-teste",
        "NASA_IMERG_CODIBGE": "3510500",
    }
    req = requisicoes(
        "NASA_IMERG", ambiente,
        buscar=lambda _: Resposta("https://cmr.test", 200,
                                  "application/json", cmr))[0]
    verifica(req.url == url and req.metadados["codibge"] == "3510500",
             "granulo não ficou associado ao recorte aprovado")
    verifica("segredo-de-teste" not in repr(req), "token NASA vazou no plano")


def testa_imerg_recorta_centros_sem_virar_pluviometro():
    class Vetor:
        def __init__(self, valores):
            self.valores = valores

        def __getitem__(self, chave):
            return self.valores[chave]

    class Grade:
        shape = (1, 6, 5)
        attrs = {"units": b"mm/hr", "_FillValue": -9999.9}
        fillvalue = -9999.9

        def __getitem__(self, indice):
            _, ilon, ilat = indice
            return ilon + ilat / 10

    class Arquivo:
        grupo = {
            "lon": Vetor([-45.75, -45.65, -45.55, -45.45, -45.35, -45.25]),
            "lat": Vetor([-23.80, -23.70, -23.60, -23.50, -23.40]),
            "precipitation": Grade(),
        }

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def __getitem__(self, chave):
            return self.grupo if chave == "Grid" else None

    h5py = types.SimpleNamespace(File=lambda *_args, **_kwargs: Arquivo())
    req = Requisicao(
        "NASA_IMERG", "imerg",
        ("https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/"
         "3B-HHR-E.MS.MRG.3IMERG.20260801-S193000-E195959.1170.V07C.HDF5"),
        metadados={"codibge": "3510500"})
    res = Resposta(req.url, 200, "application/x-hdf5", b"hdf5-teste")
    with patch.dict(sys.modules, {"h5py": h5py}):
        conteudo = normaliza(req, res, {})
    verifica(conteudo.metadados["normalizado"] is True,
             "grade IMERG válida não foi reconhecida")
    verifica(conteudo.metadados["observado_de"].startswith("2026-08-01T19:30"),
             "início do granulo foi perdido")
    verifica(conteudo.metadados["amostras_grade"],
             "nenhum centro de célula do município foi preservado")
    verifica(not conteudo.observacoes and not conteudo.estacoes,
             "estimativa IMERG foi convertida em pluviômetro")


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

        def condicionais_http(self, *args):
            return {}

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


def testa_http_304_e_sem_novidade():
    class Repo:
        terminou = None

        def inicia(self, *args):
            return 1, 2

        def condicionais_http(self, *args):
            return {"If-None-Match": '"abc"'}

        def termina(self, execucao, estado, **kwargs):
            self.terminou = (execucao, estado, kwargs.get("http_status"))

        def reverte(self):
            pass

    recebeu = {}

    def buscar(req):
        recebeu.update(req.cabecalhos)
        return Resposta("https://x.test", 304, "", b"")

    repo = Repo()
    req = Requisicao("SGB", "setorizacao-risco", "https://x.test")
    estado, aceitos = coleta_requisicao(
        req, repo, buscar=buscar,
        guardar=lambda *args: (_ for _ in ()).throw(
            AssertionError("HTTP 304 tentou gravar corpo")))
    verifica(recebeu.get("If-None-Match") == '"abc"', "ETag não foi enviado")
    verifica((estado, aceitos) == ("SEM_NOVIDADE", 0), "HTTP 304 mal classificado")
    verifica(repo.terminou == (2, "SEM_NOVIDADE", 304), "execução 304 incompleta")


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
