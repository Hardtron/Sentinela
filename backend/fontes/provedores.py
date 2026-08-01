"""Adaptadores finos para contratos oficiais; recortes nunca são presumidos."""

import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contrato import (ConfiguracaoAusente, ConteudoNormalizado, ContratoInvalido,
                       Estacao, Feicao, Observacao, Requisicao)

CEMADEN_BASE = "https://sws.cemaden.gov.br/PED/rest"
ANA_BASE = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
SGB_URL = ("https://geoportal.sgb.gov.br/server/rest/services/"
           "gestaoterritorial/risco/FeatureServer/0/query")
PROVEDORES_ARQUIVO = {
    "INPE_MERGE", "INPE_WRF", "NOAA_GFS", "INMET",
    "NASA_IMERG", "CHIRPS", "NOAA_GOES",
}
INTERVALOS_ANA = {
    "MINUTO_5", "MINUTO_10", "MINUTO_15", "MINUTO_30",
    *(f"HORA_{n}" for n in range(1, 25)),
    "DIAS_2", "DIAS_7", "DIAS_14", "DIAS_21", "DIAS_30",
}


def _exige(ambiente, *chaves):
    faltam = [chave for chave in chaves if not ambiente.get(chave)]
    if faltam:
        raise ConfiguracaoAusente("faltam: " + ", ".join(faltam))


def _urls(ambiente, chave):
    _exige(ambiente, chave)
    return [u.strip() for u in ambiente[chave].split(",") if u.strip()]


def requisicoes(provedor, ambiente=None, buscar=None):
    """Constrói requisições somente depois de validar credencial e recorte."""
    ambiente = os.environ if ambiente is None else ambiente
    if provedor == "CEMADEN":
        return _cemaden(ambiente)
    if provedor == "ANA":
        return _ana(ambiente, buscar)
    if provedor == "SGB":
        return _sgb(ambiente)
    if provedor == "REDEMET":
        return _redemet(ambiente)
    if provedor in PROVEDORES_ARQUIVO:
        cabecalhos = {}
        if ambiente.get(f"{provedor}_AUTHORIZATION"):
            cabecalhos["Authorization"] = ambiente[f"{provedor}_AUTHORIZATION"]
        return [Requisicao(provedor, _conjunto(provedor), url,
                           cabecalhos=cabecalhos)
                for url in _urls(ambiente, f"{provedor}_URLS")]
    raise ConfiguracaoAusente(f"provedor desconhecido: {provedor}")


def _cemaden(ambiente):
    _exige(ambiente, "CEMADEN_PED_TOKEN")
    parametros = {"formato": "JSON"}
    if ambiente.get("CEMADEN_CODIBGE"):
        parametros["codibge"] = ambiente["CEMADEN_CODIBGE"]
    elif ambiente.get("CEMADEN_CODESTACAO"):
        parametros["codestacao"] = ambiente["CEMADEN_CODESTACAO"]
    else:
        raise ConfiguracaoAusente(
            "falta CEMADEN_CODIBGE ou CEMADEN_CODESTACAO (recorte obrigatório)")
    return [Requisicao(
        "CEMADEN", "acumulados-recentes",
        f"{CEMADEN_BASE}/pcds-acum/acumulados-recentes",
        parametros, {"token": ambiente["CEMADEN_PED_TOKEN"]})]


def _ana(ambiente, buscar):
    _exige(ambiente, "ANA_IDENTIFICADOR", "ANA_SENHA", "ANA_ESTACOES",
           "ANA_INTERVALO")
    if ambiente["ANA_INTERVALO"] not in INTERVALOS_ANA:
        raise ConfiguracaoAusente("ANA_INTERVALO não pertence ao enum oficial")
    if buscar is None:
        # Planejamento seco: as credenciais e o recorte foram validados, mas
        # nenhum token é solicitado. O valor nunca será usado em uma coleta.
        token = "[OBTIDO_SOMENTE_DURANTE_A_COLETA]"
    else:
        autenticacao = Requisicao(
            "ANA", "telemetria-adotada", f"{ANA_BASE}/OAUth/v1",
            cabecalhos={"Identificador": ambiente["ANA_IDENTIFICADOR"],
                        "Senha": ambiente["ANA_SENHA"]})
        token = _token_ana(buscar(autenticacao).dados)
    parametros = {
        "Codigos_Estacoes": ambiente["ANA_ESTACOES"],
        "Tipo Filtro Data": ambiente.get("ANA_TIPO_FILTRO", "DATA_LEITURA"),
        "Range Intervalo de busca": ambiente["ANA_INTERVALO"],
    }
    if ambiente.get("ANA_DATA_BUSCA"):
        parametros["Data de Busca (yyyy-MM-dd)"] = ambiente["ANA_DATA_BUSCA"]
    return [Requisicao(
        "ANA", "telemetria-adotada",
        f"{ANA_BASE}/HidroinfoanaSerieTelemetricaAdotada/v2",
        parametros, {"Authorization": f"Bearer {token}"})]


def _token_ana(dados):
    try:
        objeto = json.loads(dados)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContratoInvalido("autenticação ANA não retornou JSON") from erro
    for item in _objetos_token(objeto):
        if not isinstance(item, dict):
            continue
        for chave in ("access_token", "accessToken", "token", "Token"):
            if item.get(chave):
                return str(item[chave])
    raise ContratoInvalido("resposta de autenticação ANA sem token reconhecível")


def _objetos_token(objeto):
    """Percorre somente o envelope `items` documentado pela ANA."""
    yield objeto
    if isinstance(objeto, dict) and "items" in objeto:
        yield from _objetos_token(objeto["items"])
    elif isinstance(objeto, list):
        for item in objeto:
            yield from _objetos_token(item)


def _sgb(ambiente):
    _exige(ambiente, "SGB_WHERE")
    where = ambiente["SGB_WHERE"].strip()
    if where.lower().replace(" ", "") in {"1=1", "true"}:
        raise ConfiguracaoAusente("SGB_WHERE precisa ser um recorte, não toda a base")
    return [Requisicao("SGB", "setorizacao-risco", SGB_URL, {
        "where": where, "outFields": "*", "returnGeometry": "true",
        "outSR": "4326", "f": "geojson",
    })]


def _redemet(ambiente):
    _exige(ambiente, "REDEMET_API_KEY", "REDEMET_URLS")
    return [Requisicao("REDEMET", "radar-satelite", url,
                       {"api_key": ambiente["REDEMET_API_KEY"]})
            for url in _urls(ambiente, "REDEMET_URLS")]


def _conjunto(provedor):
    return {
        "INPE_MERGE": "gpm-merge", "INPE_WRF": "ams-07km",
        "NOAA_GFS": "gfs", "INMET": "arquivos-oficiais",
        "NASA_IMERG": "imerg", "CHIRPS": "chirps",
        "NOAA_GOES": "goes-glm",
    }[provedor]


def normaliza(requisicao, resposta, ambiente=None):
    """Normaliza apenas contratos cujo significado foi confirmado oficialmente."""
    ambiente = os.environ if ambiente is None else ambiente
    if requisicao.provedor == "CEMADEN":
        return _normaliza_cemaden(resposta.dados, ambiente)
    if requisicao.provedor == "SGB":
        return _normaliza_geojson(resposta.dados)
    # ANA e grades ficam brutas até um mapeamento de campos/produto ser
    # validado com resposta real. Isso é ausência explícita, não dado perdido.
    return ConteudoNormalizado(metadados={"normalizado": False})


def _normaliza_cemaden(dados, ambiente):
    _exige(ambiente, "CEMADEN_FUSO")
    try:
        fuso = ZoneInfo(ambiente["CEMADEN_FUSO"])
    except ZoneInfoNotFoundError as erro:
        raise ConfiguracaoAusente("CEMADEN_FUSO não é um fuso IANA válido") from erro
    try:
        linhas = json.loads(dados)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContratoInvalido("CEMADEN não retornou JSON válido") from erro
    if not isinstance(linhas, list):
        raise ContratoInvalido("CEMADEN: raiz JSON não é lista")
    saida = ConteudoNormalizado(metadados={"normalizado": True})
    periodos = {"acc1hr": 3600, "acc3hr": 10800, "acc6hr": 21600,
                "acc12hr": 43200, "acc24hr": 86400, "acc48hr": 172800,
                "acc72hr": 259200, "acc96hr": 345600,
                "acc120hr": 432000}
    for indice, linha in enumerate(linhas):
        if not isinstance(linha, dict) or not linha.get("codestacao"):
            raise ContratoInvalido(f"CEMADEN: item {indice} sem codestacao")
        codigo = str(linha["codestacao"])
        saida.estacoes.append(Estacao("CEMADEN", codigo,
                                      metadados={"codibge": linha.get("codibge")}))
        instante = _instante_cemaden(linha.get("datahora"), fuso)
        for campo, periodo in periodos.items():
            if linha.get(campo) is None:
                continue
            try:
                valor = float(linha[campo])
            except (TypeError, ValueError) as erro:
                raise ContratoInvalido(
                    f"CEMADEN: {campo} não numérico no item {indice}") from erro
            saida.observacoes.append(Observacao(
                codigo, instante, "precipitacao_acumulada", valor, "mm",
                periodo_s=periodo, metadados={"campo_origem": campo}))
    return saida


def _instante_cemaden(valor, fuso):
    if not valor:
        raise ContratoInvalido("CEMADEN: datahora ausente")
    texto = str(valor).strip()
    try:
        instante = datetime.fromisoformat(texto.replace("Z", "+00:00"))
    except ValueError as erro:
        raise ContratoInvalido(f"CEMADEN: datahora inválida: {texto}") from erro
    if instante.tzinfo is None:
        instante = instante.replace(tzinfo=fuso)
    return instante


def _normaliza_geojson(dados):
    try:
        objeto = json.loads(dados)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContratoInvalido("SGB não retornou GeoJSON válido") from erro
    if objeto.get("type") != "FeatureCollection" or not isinstance(
            objeto.get("features"), list):
        raise ContratoInvalido("SGB: resposta não é FeatureCollection")
    saida = ConteudoNormalizado(metadados={
        "normalizado": False,
        "tipo": "FeatureCollection",
        "feicoes": len(objeto["features"]),
    })
    for indice, item in enumerate(objeto["features"]):
        if not isinstance(item, dict) or item.get("type") != "Feature":
            raise ContratoInvalido(f"SGB: item {indice} não é Feature")
        propriedades = item.get("properties") or {}
        identificador = item.get("id") or propriedades.get("objectid") or indice
        saida.feicoes.append(Feicao(str(identificador), item.get("geometry"),
                                    propriedades))
    return saida
