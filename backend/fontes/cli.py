"""Orquestra coleta por provedor com falha isolada e rastreável."""

import argparse
import os
import sys
from dataclasses import replace
from pathlib import Path

from .contrato import ConfiguracaoAusente, Requisicao, Resposta
from .provedores import requisicoes, normaliza
from .repositorio import Repositorio, conecta, configuracao_publica
from .transporte import busca, guarda_bruto

PROVEDORES = (
    "CEMADEN", "ANA", "SGB", "INPE_MERGE", "INPE_WRF", "NOAA_GFS",
    "REDEMET", "INMET", "NASA_IMERG", "CHIRPS", "NOAA_GOES",
)


def coleta_requisicao(requisicao, repositorio, buscar=busca, guardar=guarda_bruto):
    conjunto_id, execucao_id = repositorio.inicia(
        requisicao.provedor, requisicao.conjunto,
        configuracao_publica(requisicao))
    resposta = None
    sha256 = None
    try:
        condicionais = repositorio.condicionais_http(conjunto_id)
        if condicionais:
            requisicao = replace(
                requisicao,
                cabecalhos={**requisicao.cabecalhos, **condicionais})
        resposta = buscar(requisicao)
        if resposta.status == 304:
            repositorio.termina(execucao_id, "SEM_NOVIDADE", http_status=304)
            return "SEM_NOVIDADE", 0
        caminho, sha256 = guardar(resposta, requisicao.provedor,
                                   requisicao.conjunto)
        ativo_id, novo, processado = repositorio.registra_ativo(
            conjunto_id, execucao_id, resposta, caminho, sha256, {
                "http": {"etag": resposta.etag,
                         "ultima_modificacao": resposta.ultima_modificacao}})
        if not novo and processado:
            repositorio.termina(execucao_id, "SEM_NOVIDADE", http_status=resposta.status)
            return "SEM_NOVIDADE", 0
        conteudo = normaliza(requisicao, resposta)
        aceitos = repositorio.normaliza(conjunto_id, ativo_id, conteudo)
        recebidos = _itens_recebidos(conteudo)
        # Reimportação normalizada idempotente não é rejeição de contrato.
        repositorio.termina(execucao_id, "SUCESSO", recebidos, aceitos,
                            0, resposta.status)
        return "SUCESSO", aceitos
    except Exception as erro:  # noqa: BLE001 - isolamento entre provedores
        repositorio.reverte()
        uri = resposta.url_publica if resposta else None
        repositorio.quarentena(conjunto_id, execucao_id, "AQUISICAO_OU_PARSE",
                               erro, uri, sha256)
        repositorio.termina(execucao_id, "QUARENTENA", rejeitados=1,
                            http_status=resposta.status if resposta else None,
                            erro=erro)
        return "QUARENTENA", 0


def planeja(provedores, ambiente=None, buscar=busca):
    ambiente = os.environ if ambiente is None else ambiente
    plano, ausentes = [], {}
    for provedor in provedores:
        try:
            plano.extend(requisicoes(provedor, ambiente, buscar))
        except ConfiguracaoAusente as erro:
            ausentes[provedor] = str(erro)
        except Exception as erro:  # uma autenticação não bloqueia outra fonte
            ausentes[provedor] = "falha de preparação: " + str(erro).splitlines()[0]
    return plano, ausentes


def _argumentos(argv):
    ap = argparse.ArgumentParser(
        description="Aquisição auditável de fontes ambientais externas")
    ap.add_argument("--provedor", action="append", choices=PROVEDORES,
                    help="pode ser repetido; sem a opção avalia todos")
    ap.add_argument("--listar", action="store_true",
                    help="mostra prontidão de configuração sem rede ou banco")
    ap.add_argument("--seco", action="store_true",
                    help="planeja sem baixar nem gravar")
    ap.add_argument("--reprocessar-brutos", action="store_true",
                    help=("reinterpreta brutos do --provedor com versão antiga; "
                          "não acessa a rede nem substitui o arquivo"))
    return ap.parse_args(argv)


def _mostra_plano(selecionados, plano, ausentes):
    for provedor in selecionados:
        reqs = [r for r in plano if r.provedor == provedor]
        estado = f"PRONTO ({len(reqs)} requisição(ões))" if reqs else (
            "AGUARDA_CONFIGURACAO: " + ausentes.get(provedor, "sem requisição"))
        print(f"{provedor}: {estado}")


def _executa(plano):
    with conecta() as conexao:
        repositorio = Repositorio(conexao)
        falhas = 0
        for requisicao in plano:
            try:
                estado, aceitos = coleta_requisicao(requisicao, repositorio)
            except Exception as erro:  # falha de uma fonte não para as demais
                repositorio.reverte()
                estado, aceitos = "FALHA", 0
                print(f"{requisicao.provedor}/{requisicao.conjunto}: "
                      f"FALHA: {str(erro).splitlines()[0]}", file=sys.stderr)
            print(f"{requisicao.provedor}/{requisicao.conjunto}: "
                  f"{estado}; {aceitos} item(ns) normalizado(s)")
            falhas += estado in {"QUARENTENA", "FALHA"}
    return 1 if falhas else 0


def _reprocessa_brutos(provedores):
    with conecta() as conexao:
        repositorio = Repositorio(conexao)
        ativos = repositorio.brutos_para_reprocessar(provedores)
        falhas = 0
        for ativo in ativos:
            _, execucao_id = repositorio.inicia(
                ativo["provedor"], ativo["conjunto"], {
                    "modo": "REPROCESSAMENTO_BRUTO",
                    "ativo_bruto_id": ativo["id"],
                })
            try:
                caminho = Path(ativo["caminho"])
                dados = caminho.read_bytes()
                requisicao = Requisicao(
                    ativo["provedor"], ativo["conjunto"], ativo["fonte_uri"],
                    metadados=ativo["requisicao_metadados"])
                resposta = Resposta(ativo["fonte_uri"], 200,
                                    ativo["tipo_conteudo"] or "", dados)
                conteudo = normaliza(requisicao, resposta)
                aceitos = repositorio.normaliza(
                    ativo["conjunto_id"], ativo["id"], conteudo)
                repositorio.termina(execucao_id, "SUCESSO",
                                    _itens_recebidos(conteudo), aceitos)
                print(f'{ativo["provedor"]}/{ativo["conjunto"]} ativo '
                      f'{ativo["id"]}: SUCESSO; {aceitos} item(ns)')
            except Exception as erro:  # falha isolada e auditada
                repositorio.reverte()
                repositorio.quarentena(
                    ativo["conjunto_id"], execucao_id, "REPROCESSAMENTO",
                    erro, ativo["fonte_uri"])
                repositorio.termina(execucao_id, "QUARENTENA", rejeitados=1,
                                    erro=erro)
                falhas += 1
                print(f'{ativo["provedor"]}/{ativo["conjunto"]} ativo '
                      f'{ativo["id"]}: QUARENTENA', file=sys.stderr)
    print(f"reprocessamento: {len(ativos)} ativo(s), {falhas} falha(s)")
    return 1 if falhas else 0


def _itens_recebidos(conteudo):
    contagens = (len(conteudo.observacoes), len(conteudo.feicoes),
                 len(conteudo.estacoes),
                 int(conteudo.metadados.get("itens_recebidos", 0)))
    return next((total for total in contagens if total),
                1 if conteudo.metadados else 0)


def main(argv=None):
    _carrega_env(Path(__file__).resolve().parents[1] / "fontes.env")
    args = _argumentos(argv)
    selecionados = args.provedor or list(PROVEDORES)
    if args.reprocessar_brutos:
        if not args.provedor:
            print("--reprocessar-brutos exige ao menos um --provedor",
                  file=sys.stderr)
            return 2
        return _reprocessa_brutos(selecionados)
    sem_rede = args.listar or args.seco
    plano, ausentes = planeja(selecionados, buscar=None if sem_rede else busca)
    _mostra_plano(selecionados, plano, ausentes)
    if args.listar or args.seco:
        return 0
    if not plano:
        print("nenhuma fonte configurada; nada foi alterado", file=sys.stderr)
        return 0
    return _executa(plano)


def _carrega_env(caminho):
    """Carrega configuração local sem sobrepor systemd/shell."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#") and "=" in linha:
            chave, valor = linha.split("=", 1)
            os.environ.setdefault(chave.strip(), valor.strip())
