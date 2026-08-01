"""HTTP limitado e armazenamento bruto atômico, sem vazar credenciais."""

import hashlib
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from .contrato import Requisicao, Resposta

MAX_BYTES_PADRAO = 50 * 1024 * 1024
SEGREDOS = {"token", "access_token", "apikey", "api_key", "api-key",
            "key", "senha", "password"}


def uri_publica(url):
    """Remove query sensível antes de persistir ou exibir a URI de origem."""
    partes = urlsplit(url)
    limpa = [(k, "[REMOVIDO]" if k.lower() in SEGREDOS else v)
             for k, v in parse_qsl(partes.query, keep_blank_values=True)]
    return urlunsplit((partes.scheme, partes.netloc, partes.path,
                       urlencode(limpa), ""))


def _url(requisicao):
    partes = urlsplit(requisicao.url)
    if partes.scheme != "https":
        raise ValueError("fontes externas exigem HTTPS")
    query = parse_qsl(partes.query, keep_blank_values=True)
    query.extend((str(k), str(v)) for k, v in requisicao.parametros.items())
    return urlunsplit((partes.scheme, partes.netloc, partes.path,
                       urlencode(query), ""))


def busca(requisicao, timeout_s=30, max_bytes=MAX_BYTES_PADRAO, abridor=urlopen):
    url = _url(requisicao)
    cabecalhos = {"User-Agent": "Sentinela-fontes/1",
                  "Accept": "application/json, application/geo+json, */*"}
    cabecalhos.update(requisicao.cabecalhos)
    pedido = Request(url, data=requisicao.corpo,
                     headers=cabecalhos, method=requisicao.metodo)
    try:
        with abridor(pedido, timeout=timeout_s) as resposta:
            tamanho = resposta.headers.get("Content-Length")
            if tamanho and int(tamanho) > max_bytes:
                raise ValueError(f"resposta excede limite de {max_bytes} bytes")
            dados = resposta.read(max_bytes + 1)
            if len(dados) > max_bytes:
                raise ValueError(f"resposta excede limite de {max_bytes} bytes")
            return Resposta(
                uri_publica(url), int(getattr(resposta, "status", 200)),
                resposta.headers.get_content_type(), dados)
    except HTTPError as erro:
        # Não lê nem registra o corpo: ele pode repetir token/credencial.
        raise RuntimeError(f"HTTP {erro.code} em {uri_publica(url)}") from erro


def raiz_dados():
    return Path(os.environ.get(
        "SENTINELA_DADOS_EXTERNOS",
        "/DATA/Projects/Sentinela-Data/externos"))


def guarda_bruto(resposta, provedor, conjunto, raiz=None, agora=None):
    """Grava uma vez por hash, com rename atômico no mesmo filesystem."""
    # ``agora`` permanece no contrato para testes/reprodutibilidade; o caminho
    # é deliberadamente endereçado pelo conteúdo, não pelo relógio.
    _ = agora or datetime.now(timezone.utc)
    digest = hashlib.sha256(resposta.dados).hexdigest()
    base = (raiz or raiz_dados()) / provedor.lower() / conjunto
    pasta = base / "sha256" / digest[:2]
    pasta.mkdir(parents=True, exist_ok=True)
    alvo = pasta / f"{digest}.raw"
    if not alvo.exists():
        descritor, temporario = tempfile.mkstemp(prefix=".aquisicao-", dir=pasta)
        try:
            with os.fdopen(descritor, "wb") as arquivo:
                arquivo.write(resposta.dados)
                arquivo.flush()
                os.fsync(arquivo.fileno())
            os.replace(temporario, alvo)
        finally:
            if os.path.exists(temporario):
                os.unlink(temporario)
    return alvo, digest
