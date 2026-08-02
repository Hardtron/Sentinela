"""Adaptadores finos para contratos oficiais; recortes nunca são presumidos."""

import io
import json
import math
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .contrato import (ConfiguracaoAusente, ConteudoNormalizado, ContratoInvalido,
                       Estacao, Feicao, Observacao, Requisicao)

CEMADEN_BASE = "https://sws.cemaden.gov.br/PED/rest"
CEMADEN_TOKEN_URL = ("https://sgaa.cemaden.gov.br/SGAA/rest/"
                     "controle-token/tokens")
ANA_BASE = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
SGB_URL = ("https://geoportal.sgb.gov.br/server/rest/services/"
           "gestaoterritorial/risco/FeatureServer/0/query")
NASA_IMERG_CMR = "https://cmr.earthdata.nasa.gov/search/granules.json"
NASA_IMERG_COLECAO = "GPM_3IMERGHHE"
NASA_IMERG_VERSAO = "07"
RAIZ_BACKEND = Path(__file__).resolve().parents[1]
PROVEDORES_ARQUIVO = {
    "INPE_MERGE", "INPE_WRF", "NOAA_GFS", "INMET",
    "CHIRPS", "NOAA_GOES",
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
        return _cemaden(ambiente, buscar)
    if provedor == "ANA":
        return _ana(ambiente, buscar)
    if provedor == "SGB":
        return _sgb(ambiente)
    if provedor == "REDEMET":
        return _redemet(ambiente)
    if provedor == "NASA_IMERG":
        return _nasa_imerg(ambiente, buscar)
    if provedor in PROVEDORES_ARQUIVO:
        cabecalhos = {}
        if ambiente.get(f"{provedor}_AUTHORIZATION"):
            cabecalhos["Authorization"] = ambiente[f"{provedor}_AUTHORIZATION"]
        return [Requisicao(provedor, _conjunto(provedor), url,
                           cabecalhos=cabecalhos)
                for url in _urls(ambiente, f"{provedor}_URLS")]
    raise ConfiguracaoAusente(f"provedor desconhecido: {provedor}")


def _cemaden(ambiente, buscar):
    token = ambiente.get("CEMADEN_PED_TOKEN")
    email = ambiente.get("CEMADEN_PED_EMAIL")
    senha = ambiente.get("CEMADEN_PED_PASSWORD")
    if email or senha:
        _exige(ambiente, "CEMADEN_PED_EMAIL", "CEMADEN_PED_PASSWORD")
        if buscar is None:
            token = "[OBTIDO_SOMENTE_DURANTE_A_COLETA]"
        else:
            corpo = json.dumps({"email": email, "password": senha}).encode()
            autenticacao = Requisicao(
                "CEMADEN", "acumulados-recentes", CEMADEN_TOKEN_URL,
                cabecalhos={"Content-Type": "application/json"},
                metodo="POST", corpo=corpo)
            token = _token_cemaden(buscar(autenticacao).dados)
    if not token:
        raise ConfiguracaoAusente(
            "falta CEMADEN_PED_TOKEN ou o par "
            "CEMADEN_PED_EMAIL/CEMADEN_PED_PASSWORD")
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
        parametros, {"token": token})]


def _token_cemaden(dados):
    try:
        objeto = json.loads(dados)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContratoInvalido("autenticação CEMADEN não retornou JSON") from erro
    if not isinstance(objeto, dict) or not objeto.get("token"):
        raise ContratoInvalido(
            "resposta de autenticação CEMADEN sem token reconhecível")
    return str(objeto["token"])


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
    return [Requisicao(
                "REDEMET", "radar-satelite", url,
                cabecalhos={"X-Api-Key": ambiente["REDEMET_API_KEY"]})
            for url in _urls(ambiente, "REDEMET_URLS")]


def _nasa_imerg(ambiente, buscar):
    """Descobre o granulo Early V07 mais recente e fixa o recorte aprovado."""
    _exige(ambiente, "NASA_IMERG_AUTHORIZATION", "NASA_IMERG_CODIBGE")
    codibge = ambiente["NASA_IMERG_CODIBGE"].strip()
    recorte = _recorte_municipal(codibge)
    cabecalhos = {"Authorization": ambiente["NASA_IMERG_AUTHORIZATION"]}
    metadados = {
        "colecao": NASA_IMERG_COLECAO,
        "versao": NASA_IMERG_VERSAO,
        "codibge": codibge,
        "municipio": recorte["properties"].get("municipio"),
        "recorte_fonte": recorte["source"],
    }
    if buscar is None:
        url = ("https://data.gesdisc.earthdata.nasa.gov/"
               "[DESCOBERTO_SOMENTE_DURANTE_A_COLETA]")
    else:
        descoberta = Requisicao(
            "NASA_IMERG", "imerg", NASA_IMERG_CMR,
            {"short_name": NASA_IMERG_COLECAO, "version": NASA_IMERG_VERSAO,
             "sort_key": "-start_date", "page_size": "1",
             "downloadable": "true"}, cabecalhos)
        url, granulo = _granulo_imerg(buscar(descoberta).dados)
        metadados.update(granulo)
    return [Requisicao("NASA_IMERG", "imerg", url,
                       cabecalhos=cabecalhos, metadados=metadados)]


def _granulo_imerg(dados):
    try:
        objeto = json.loads(dados)
        entrada = objeto["feed"]["entry"][0]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError,
            TypeError) as erro:
        raise ContratoInvalido("CMR não retornou granulo IMERG reconhecível") from erro
    candidatos = [
        item.get("href") for item in entrada.get("links", [])
        if item.get("rel", "").endswith("/data#")
        and str(item.get("href", "")).startswith(
            "https://data.gesdisc.earthdata.nasa.gov/data/GPM_L3/")
    ]
    if not candidatos:
        raise ContratoInvalido("CMR não retornou link HTTPS do granulo IMERG")
    return candidatos[0], {
        "granulo_id": entrada.get("id"),
        "granulo_titulo": entrada.get("title"),
        "inicio_cmr": entrada.get("time_start"),
        "fim_cmr": entrada.get("time_end"),
    }


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
    if requisicao.provedor == "NASA_IMERG":
        return _normaliza_imerg(requisicao, resposta.dados, ambiente)
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


def _recorte_municipal(codibge):
    caminho = RAIZ_BACKEND / "recortes" / f"{codibge}.geojson"
    if not caminho.exists():
        raise ConfiguracaoAusente(
            f"recorte municipal oficial ausente: recortes/{codibge}.geojson")
    try:
        objeto = json.loads(caminho.read_text(encoding="utf-8"))
        feicao = objeto["features"][0]
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError,
            IndexError, TypeError) as erro:
        raise ConfiguracaoAusente(f"recorte municipal inválido: {caminho.name}") from erro
    if str(feicao.get("properties", {}).get("codarea")) != codibge:
        raise ConfiguracaoAusente("código IBGE diverge do recorte municipal")
    geometria = feicao.get("geometry") or {}
    if geometria.get("type") != "Polygon" or not geometria.get("coordinates"):
        raise ConfiguracaoAusente("recorte municipal precisa ser Polygon GeoJSON")
    return {**feicao, "source": objeto.get("source", {})}


def _normaliza_imerg(requisicao, dados, ambiente):
    try:
        import h5py
    except ImportError as erro:
        raise ConfiguracaoAusente("h5py não instalado no ambiente do backend") from erro
    codibge = requisicao.metadados.get("codibge") or ambiente.get(
        "NASA_IMERG_CODIBGE")
    recorte = _recorte_municipal(str(codibge or ""))
    try:
        with h5py.File(io.BytesIO(dados), "r") as arquivo:
            grupo = arquivo["Grid"]
            longitudes = [float(x) for x in grupo["lon"][:]]
            latitudes = [float(x) for x in grupo["lat"][:]]
            grade = grupo["precipitation"]
            amostras, unidade = _amostras_grade(
                grade, longitudes, latitudes,
                recorte["geometry"]["coordinates"][0])
    except (KeyError, OSError, TypeError, ValueError) as erro:
        raise ContratoInvalido("IMERG HDF5 não contém a grade esperada") from erro
    inicio, fim = _periodo_granulo(requisicao)
    fonte = recorte.get("source", {})
    return ConteudoNormalizado(metadados={
        "normalizado": True,
        "identificador": "PRECIPITATION_RECORTE_MUNICIPAL",
        "classe": "ESTIMATIVA_GRADE",
        "produto": f"{NASA_IMERG_COLECAO}.{NASA_IMERG_VERSAO}",
        "variavel_origem": "precipitation",
        "unidade_origem": unidade,
        "observado_de": inicio.isoformat(),
        "observado_ate": fim.isoformat(),
        "resolucao": "0,1 grau (coordenadas da grade do arquivo)",
        "itens_recebidos": len(amostras),
        "amostras_grade": amostras,
        "recorte": {
            "codibge": str(codibge),
            "municipio": recorte["properties"].get("municipio"),
            "metodo": "centros de celulas contidos no perimetro municipal",
            "fonte": fonte.get("orgao"),
            "fonte_url": fonte.get("url"),
            "qualidade_malha": fonte.get("qualidade"),
        },
        "limitacao": (
            "estimativa orbital em grade; amostras não são pluviômetros nem "
            "média municipal e não acionam alerta"),
    })


def _amostras_grade(grade, longitudes, latitudes, poligono):
    forma = tuple(grade.shape)
    eixo_lon, eixo_lat = _eixos_grade(forma, longitudes, latitudes)
    unidade = _atributo_texto(grade.attrs.get("units"))
    if not unidade:
        raise ContratoInvalido("IMERG sem unidade no dataset precipitation")
    preenchimento = grade.attrs.get("_FillValue")
    if preenchimento is None:
        preenchimento = getattr(grade, "fillvalue", None)
    saida = []
    for ilon, ilat, lon, lat in _centros_no_recorte(
            longitudes, latitudes, poligono):
        indice = [0] * len(forma)
        indice[eixo_lon], indice[eixo_lat] = ilon, ilat
        valor = float(grade[tuple(indice)])
        if _valor_grade_valido(valor, preenchimento):
            saida.append({"longitude": lon, "latitude": lat, "valor": valor})
    return saida, unidade


def _eixos_grade(forma, longitudes, latitudes):
    try:
        eixo_lon = forma.index(len(longitudes))
        eixo_lat = forma.index(len(latitudes))
    except ValueError as erro:
        raise ContratoInvalido(
            "dimensões lon/lat não correspondem à precipitação") from erro
    if eixo_lon == eixo_lat:
        raise ContratoInvalido("eixos lon/lat ambíguos na grade IMERG")
    return eixo_lon, eixo_lat


def _centros_no_recorte(longitudes, latitudes, poligono):
    minx = min(p[0] for p in poligono)
    maxx = max(p[0] for p in poligono)
    miny = min(p[1] for p in poligono)
    maxy = max(p[1] for p in poligono)
    for ilon, lon in enumerate(longitudes):
        if not minx <= lon <= maxx:
            continue
        for ilat, lat in enumerate(latitudes):
            if _centro_pertence(lon, lat, miny, maxy, poligono):
                yield ilon, ilat, lon, lat


def _centro_pertence(lon, lat, miny, maxy, poligono):
    return miny <= lat <= maxy and _ponto_no_poligono(lon, lat, poligono)


def _valor_grade_valido(valor, preenchimento):
    if not math.isfinite(valor):
        return False
    return preenchimento is None or not math.isclose(
        valor, float(preenchimento), rel_tol=0, abs_tol=1e-6)


def _atributo_texto(valor):
    if valor is None:
        return None
    if isinstance(valor, bytes):
        return valor.decode("utf-8", "replace")
    if hasattr(valor, "tolist"):
        valor = valor.tolist()
        if isinstance(valor, bytes):
            return valor.decode("utf-8", "replace")
    return str(valor)


def _ponto_no_poligono(x, y, poligono):
    dentro = False
    anterior = poligono[-1]
    for atual in poligono:
        x1, y1 = anterior[:2]
        x2, y2 = atual[:2]
        cruza = ((y1 > y) != (y2 > y))
        if cruza and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            dentro = not dentro
        anterior = atual
    return dentro


def _periodo_granulo(requisicao):
    inicio = requisicao.metadados.get("inicio_cmr")
    fim = requisicao.metadados.get("fim_cmr")
    if inicio and fim:
        try:
            return (_iso_utc(inicio), _iso_utc(fim))
        except ValueError:
            pass
    nome = Path(urlsplit(requisicao.url).path).name
    achou = re.search(
        r"\.(\d{8})-S(\d{6})-E(\d{6})\.", nome)
    if not achou:
        raise ContratoInvalido("IMERG sem período reconhecível no granulo")
    data, inicio_h, fim_h = achou.groups()
    primeiro = datetime.strptime(data + inicio_h, "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc)
    ultimo = datetime.strptime(data + fim_h, "%Y%m%d%H%M%S").replace(
        tzinfo=timezone.utc)
    if ultimo < primeiro:
        ultimo += timedelta(days=1)
    return primeiro, ultimo


def _iso_utc(valor):
    instante = datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    if instante.tzinfo is None:
        raise ValueError("timestamp sem fuso")
    return instante.astimezone(timezone.utc)
