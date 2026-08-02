"""Adaptadores finos para contratos oficiais; recortes nunca são presumidos."""

import io
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

from .contrato import (ConfiguracaoAusente, ConteudoNormalizado, ContratoInvalido,
                       Estacao, Feicao, Observacao, Requisicao)

CEMADEN_BASE = "https://sws.cemaden.gov.br/PED/rest"
CEMADEN_TOKEN_URL = ("https://sgaa.cemaden.gov.br/SGAA/rest/"
                     "controle-token/tokens")
ANA_BASE = "https://www.ana.gov.br/hidrowebservice/EstacoesTelemetricas"
SGB_URL = ("https://geoportal.sgb.gov.br/server/rest/services/"
           "gestaoterritorial/risco/FeatureServer/0/query")
NASA_IMERG_SERVICO = ("https://gis.earthdata.nasa.gov/image/rest/services/"
                      "GESDISC/GPM_3IMERGHHE/ImageServer")
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
    """Exporta a grade Early V07 mais recente no recorte municipal aprovado."""
    _exige(ambiente, "NASA_IMERG_CODIBGE")
    codibge = ambiente["NASA_IMERG_CODIBGE"].strip()
    recorte = _recorte_municipal(codibge)
    metadados = {
        "colecao": NASA_IMERG_COLECAO,
        "versao": NASA_IMERG_VERSAO,
        "codibge": codibge,
        "municipio": recorte["properties"].get("municipio"),
        "recorte_fonte": recorte["source"],
    }
    if buscar is None:
        url = ("https://gis.earthdata.nasa.gov/image/rest/directories/"
               "arcgisoutput/[DESCOBERTO_SOMENTE_DURANTE_A_COLETA].tif")
    else:
        item = _item_imerg(buscar(Requisicao(
            "NASA_IMERG", "imerg", NASA_IMERG_SERVICO + "/query",
            {"where": "1=1", "outFields": "objectid,stdtime,name,variable",
             "orderByFields": "stdtime DESC", "resultRecordCount": "1",
             "returnGeometry": "false", "f": "json"})).dados)
        bbox, largura, altura = _grade_exportacao(recorte["geometry"])
        exportacao = Requisicao(
            "NASA_IMERG", "imerg", NASA_IMERG_SERVICO + "/exportImage",
            {"bbox": ",".join(str(x) for x in bbox), "bboxSR": "4326",
             "imageSR": "4326", "size": f"{largura},{altura}",
             "format": "tiff", "pixelType": "F32",
             "interpolation": "RSP_NearestNeighbor",
             "mosaicRule": json.dumps({
                 "mosaicMethod": "esriMosaicLockRaster",
                 "lockRasterIds": [item["objectid"]]}, separators=(",", ":")),
             "f": "json"})
        url, imagem = _imagem_imerg(buscar(exportacao).dados)
        metadados.update(item)
        metadados.update(imagem)
    return [Requisicao("NASA_IMERG", "imerg", url, metadados=metadados)]


def _item_imerg(dados):
    try:
        objeto = json.loads(dados)
        item = objeto["features"][0]["attributes"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, IndexError,
            TypeError) as erro:
        raise ContratoInvalido("ImageServer não retornou item IMERG") from erro
    if not item.get("objectid") or item.get("stdtime") is None:
        raise ContratoInvalido("item IMERG sem objectid ou stdtime")
    observado = datetime.fromtimestamp(
        float(item["stdtime"]) / 1000, timezone.utc).isoformat()
    return {"objectid": int(item["objectid"]), "nome_item": item.get("name"),
            "variavel_item": item.get("variable"),
            "observado_de": observado, "observado_ate": observado}


def _imagem_imerg(dados):
    try:
        objeto = json.loads(dados)
        url = objeto["href"]
        largura, altura = int(objeto["width"]), int(objeto["height"])
        extensao = objeto["extent"]
        bbox = [float(extensao[x]) for x in ("xmin", "ymin", "xmax", "ymax")]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError,
            ValueError) as erro:
        raise ContratoInvalido("ImageServer não retornou exportação IMERG") from erro
    prefixo = ("https://gis.earthdata.nasa.gov/image/rest/directories/"
               "arcgisoutput/")
    if not str(url).startswith(prefixo) or largura <= 0 or altura <= 0:
        raise ContratoInvalido("exportação IMERG retornou URI ou dimensão inválida")
    return url, {"largura": largura, "altura": altura, "bbox_exportado": bbox}


def _grade_exportacao(geometria):
    pontos = geometria["coordinates"][0]
    minx = math.floor(min(p[0] for p in pontos) * 10) / 10
    miny = math.floor(min(p[1] for p in pontos) * 10) / 10
    maxx = math.ceil(max(p[0] for p in pontos) * 10) / 10
    maxy = math.ceil(max(p[1] for p in pontos) * 10) / 10
    largura = round((maxx - minx) / 0.1)
    altura = round((maxy - miny) / 0.1)
    return [minx, miny, maxx, maxy], largura, altura


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
    if requisicao.provedor == "REDEMET":
        return _normaliza_redemet(resposta.dados)
    # ANA e grades ficam brutas até um mapeamento de campos/produto ser
    # validado com resposta real. Isso é ausência explícita, não dado perdido.
    return ConteudoNormalizado(metadados={"normalizado": False})


def _normaliza_redemet(dados):
    """Extrai somente metadados cartográficos declarados pela REDEMET.

    O horário dos produtos chega sem offset no payload. Por isso ele é
    preservado como texto de origem, sem ser convertido em ``TIMESTAMPTZ``.
    Imagens também só são aceitas no host estático oficial; a API nunca faz
    uma URI arbitrária persistida virar recurso carregável pelo painel.
    """
    try:
        objeto = json.loads(dados)
    except (UnicodeDecodeError, json.JSONDecodeError) as erro:
        raise ContratoInvalido("REDEMET não retornou JSON válido") from erro
    if (not isinstance(objeto, dict) or objeto.get("status") is not True
            or not isinstance(objeto.get("data"), dict)):
        raise ContratoInvalido("REDEMET: envelope sem status/data reconhecível")
    payload = objeto["data"]
    if isinstance(payload.get("radar"), list):
        return _normaliza_redemet_radar(payload)
    if isinstance(payload.get("satelite"), list):
        return _normaliza_redemet_satelite(payload)
    if isinstance(payload.get("stsc"), list) and isinstance(
            payload.get("info"), dict):
        return _normaliza_redemet_stsc(payload)
    raise ContratoInvalido("REDEMET: produto não reconhecido no payload")


def _normaliza_redemet_radar(payload):
    quadros = _quadros_redemet(payload["radar"], radar=True)
    if not quadros:
        raise ContratoInvalido("REDEMET: produto radar sem quadro válido")
    produto = str(payload.get("tipo") or "radar")
    return ConteudoNormalizado(metadados={
        "normalizado": True,
        "identificador": f"REDEMET_RADAR_{produto.upper()}",
        "classe": "PRODUTO_RADAR",
        "produto": produto,
        "quadros": quadros,
        "fuso_origem": "não declarado no payload",
        "limitacao": (
            "imagem de radar meteorológico de terceiro; cobertura nominal "
            "não comprova qualidade local nem precipitação na superfície"),
    })


def _normaliza_redemet_satelite(payload):
    quadros = _quadros_redemet(payload["satelite"], radar=False)
    bbox = _bbox_redemet(payload.get("lat_lon"))
    if not quadros or bbox is None:
        raise ContratoInvalido("REDEMET: satélite sem quadro ou extensão válida")
    produto = str(payload.get("tipo") or "satelite")
    for quadro in quadros:
        quadro["bbox"] = bbox
    return ConteudoNormalizado(metadados={
        "normalizado": True,
        "identificador": f"REDEMET_SATELITE_{produto.upper()}",
        "classe": "PRODUTO_SATELITE",
        "produto": produto,
        "quadros": quadros,
        "fuso_origem": "não declarado no payload",
        "limitacao": (
            "imagem meteorológica de satélite; não é medição de chuva na "
            "superfície nem regra de alerta"),
    })


def _normaliza_redemet_stsc(payload):
    pontos = payload["stsc"]
    if not all(isinstance(grupo, list) for grupo in pontos):
        raise ContratoInvalido("REDEMET: STSC sem grupos reconhecíveis")
    quantidade = sum(len(grupo) for grupo in pontos)
    return ConteudoNormalizado(metadados={
        "normalizado": True,
        "identificador": "REDEMET_STSC",
        "classe": "DETECCAO_DESCARGA_ATMOSFERICA",
        "produto": "stsc",
        "instante_origem": payload["info"].get("ultima_ocorrencia"),
        "fuso_origem": "não declarado no payload",
        "quantidade_celulas_payload": quantidade,
        "limitacao": (
            "contagem do payload nacional; ainda não há recorte espacial "
            "versionado para exibir ocorrências no mapa piloto"),
    })


def _quadros_redemet(grupos, radar):
    quadros = []
    for grupo in grupos:
        itens = grupo if isinstance(grupo, list) else [grupo]
        for item in itens:
            if not isinstance(item, dict):
                raise ContratoInvalido("REDEMET: quadro não é objeto")
            caminho = str(item.get("path") or "")
            if not caminho.startswith(
                    "https://estatico-redemet.decea.mil.br/"):
                raise ContratoInvalido("REDEMET: URI de imagem fora do host oficial")
            quadro = {
                "instante_origem": item.get("data"),
                "imagem_url": caminho,
                "tamanho_origem": item.get("tamanho"),
            }
            if radar:
                bbox = _bbox_redemet(item)
                centro = _ponto_redemet(item.get("lat_center"),
                                        item.get("lon_center"))
                if bbox is None or centro is None:
                    raise ContratoInvalido("REDEMET: radar sem geometria válida")
                quadro.update({
                    "bbox": bbox,
                    "centro": centro,
                    "nome": item.get("nome"),
                    "localidade": item.get("localidade"),
                    "raio_km": _numero_redemet(item.get("raio")),
                })
            quadros.append(quadro)
    return quadros


def _numero_redemet(valor):
    try:
        numero = float(valor)
    except (TypeError, ValueError) as erro:
        raise ContratoInvalido("REDEMET: coordenada/medida não numérica") from erro
    if not math.isfinite(numero):
        raise ContratoInvalido("REDEMET: coordenada/medida não finita")
    return numero


def _bbox_redemet(item):
    if not isinstance(item, dict):
        return None
    try:
        bbox = [_numero_redemet(item[chave]) for chave in
                ("lon_min", "lat_min", "lon_max", "lat_max")]
    except (KeyError, ContratoInvalido):
        return None
    if not (-180 <= bbox[0] < bbox[2] <= 180
            and -90 <= bbox[1] < bbox[3] <= 90):
        return None
    return bbox


def _ponto_redemet(lat, lon):
    try:
        ponto = [_numero_redemet(lon), _numero_redemet(lat)]
    except ContratoInvalido:
        return None
    if not (-180 <= ponto[0] <= 180 and -90 <= ponto[1] <= 90):
        return None
    return ponto


def _normaliza_cemaden(dados, ambiente):
    _exige(ambiente, "CEMADEN_FUSO")
    if ambiente["CEMADEN_FUSO"] != "UTC":
        raise ConfiguracaoAusente(
            "CEMADEN_FUSO deve ser UTC conforme a convenção publicada pelo órgão")
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
        instante = _instante_cemaden(linha.get("datahora"), timezone.utc)
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
                periodo_s=periodo,
                metadados={"campo_origem": campo, "fuso_origem": "UTC"}))
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
        import tifffile
    except ImportError as erro:
        raise ConfiguracaoAusente("tifffile não instalado no backend") from erro
    codibge = requisicao.metadados.get("codibge") or ambiente.get(
        "NASA_IMERG_CODIBGE")
    recorte = _recorte_municipal(str(codibge or ""))
    try:
        grade = tifffile.imread(io.BytesIO(dados))
        amostras, resolucao = _amostras_tiff(
            grade, requisicao.metadados,
            recorte["geometry"]["coordinates"][0])
    except (KeyError, OSError, TypeError, ValueError) as erro:
        raise ContratoInvalido("IMERG GeoTIFF não contém a grade esperada") from erro
    inicio = requisicao.metadados.get("observado_de")
    fim = requisicao.metadados.get("observado_ate")
    if not inicio or not fim:
        raise ContratoInvalido("exportação IMERG sem instante observado")
    fonte = recorte.get("source", {})
    return ConteudoNormalizado(metadados={
        "normalizado": True,
        "identificador": "PRECIPITATION_RECORTE_MUNICIPAL",
        "classe": "ESTIMATIVA_GRADE",
        "produto": f"{NASA_IMERG_COLECAO}.{NASA_IMERG_VERSAO}",
        "variavel_origem": "precipitation",
        "unidade_origem": "mm/hr",
        "observado_de": inicio,
        "observado_ate": fim,
        "resolucao": resolucao,
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


def _amostras_tiff(grade, metadados, poligono):
    altura, largura = tuple(grade.shape)
    if (altura, largura) != (metadados.get("altura"), metadados.get("largura")):
        raise ContratoInvalido("dimensão GeoTIFF diverge da exportação")
    minx, miny, maxx, maxy = metadados["bbox_exportado"]
    passo_x, passo_y = (maxx - minx) / largura, (maxy - miny) / altura
    saida = []
    for linha in range(altura):
        lat = maxy - (linha + 0.5) * passo_y
        for coluna in range(largura):
            lon = minx + (coluna + 0.5) * passo_x
            valor = float(grade[linha, coluna])
            if (_ponto_no_poligono(lon, lat, poligono)
                    and _valor_grade_valido(valor, -9999)):
                saida.append({"longitude": lon, "latitude": lat, "valor": valor})
    return saida, f"{passo_x:g}° × {passo_y:g}°"


def _valor_grade_valido(valor, preenchimento):
    if not math.isfinite(valor):
        return False
    return preenchimento is None or not math.isclose(
        valor, float(preenchimento), rel_tol=0, abs_tol=1e-6)


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
