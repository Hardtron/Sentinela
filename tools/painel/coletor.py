#!/usr/bin/env python3
"""Sentinela — coleta o estado do projeto para o painel.

Cada função devolve um bloco de dados já pronto para virar JSON. Nenhuma delas
imprime nem serve HTTP: a separação mantém o servidor trivial e cada coletor
testável isoladamente.

Autoria: Matheus Marassi
"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]

RE_PENDENCIA = re.compile(r"^\|\s*(?:~~)?\*{0,2}(P-\d+|C-\d+|A-\d+|R-\d+|B-\d+)"
                          r"\*{0,2}(?:~~)?\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", re.M)
RE_MARCA = re.compile(r"\*\*\[([MNLGE?])\]\*\*")


def _texto(caminho):
    try:
        return caminho.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _git(*args):
    try:
        r = subprocess.run(["git", "-C", str(RAIZ), *args],
                           capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


# ------------------------------------------------------------- documentos --

def documentos():
    itens = []
    for caminho in sorted(RAIZ.glob("docs/*.md")) + [RAIZ / "README.md",
                                                     RAIZ / "LOG.md",
                                                     RAIZ / "ERROS.md"]:
        if not caminho.exists():
            continue
        texto = _texto(caminho)
        marcas = RE_MARCA.findall(texto)
        contagem = {}
        for m in marcas:
            contagem[m] = contagem.get(m, 0) + 1
        itens.append({
            "arquivo": str(caminho.relative_to(RAIZ)),
            "nome": caminho.stem,
            "linhas": texto.count("\n"),
            "bytes": len(texto.encode("utf-8")),
            "titulo": _primeiro_titulo(texto),
            "marcas": contagem,
            "modificado": datetime.fromtimestamp(
                caminho.stat().st_mtime).isoformat(timespec="seconds"),
        })
    return sorted(itens, key=lambda d: d["nome"])


def _primeiro_titulo(texto):
    for linha in texto.splitlines():
        if linha.startswith("# "):
            return linha[2:].strip()
    return ""


def conteudo_documento(rel):
    caminho = (RAIZ / rel).resolve()
    if RAIZ not in caminho.parents and caminho != RAIZ:
        return None
    if caminho.suffix != ".md" or not caminho.is_file():
        return None
    return _texto(caminho)


# ------------------------------------------------------------- pendências --

ORIGEM_PENDENCIA = {
    "P": ("docs/PLANO.md", "plano"),
    "C": ("docs/CONFORMIDADE.md", "conformidade"),
    "A": ("docs/ANCORAGEM.md", "ancoragem"),
    "R": ("docs/RESPONSABILIDADE_TECNICA.md", "responsabilidade"),
    "B": ("docs/REFERENCIAS.md", "referencias"),
}


def pendencias():
    itens = []
    vistos = set()
    for arquivo in {v[0] for v in ORIGEM_PENDENCIA.values()}:
        texto = _texto(RAIZ / arquivo)
        for ident, descricao, bloqueia in RE_PENDENCIA.findall(texto):
            if ident in vistos:
                continue
            vistos.add(ident)
            resolvida = "Resolvida" in bloqueia or "Encerrada" in bloqueia
            itens.append({
                "id": ident,
                "descricao": re.sub(r"[*~`]", "", descricao),
                "situacao": re.sub(r"[*~`]", "", bloqueia),
                "grupo": ORIGEM_PENDENCIA.get(ident[0], ("", "outro"))[1],
                "resolvida": resolvida,
                "origem": arquivo,
            })
    return sorted(itens, key=lambda p: (p["resolvida"], p["id"]))


# -------------------------------------------------------------- hardware --

def portas_seriais():
    itens = []
    for caminho in sorted(Path("/dev").glob("cu.usbserial*")):
        itens.append({"porta": str(caminho), "presente": True})
    return itens


PLACAS = [
    {"id": "HTC-01", "mac": "3c:71:bf:8c:2c:d0", "papel": "PINGER",
     "env": "node_dev", "flash": "4 MB"},
    {"id": "HTC-02", "mac": "3c:71:bf:8c:2f:9c", "papel": "PONGER",
     "env": "node_range", "flash": "4 MB"},
    {"id": "HTC-03", "mac": None, "papel": "bridge (previsto)",
     "env": "bridge", "flash": "4 MB"},
    {"id": "HTC-04", "mac": None, "papel": "sensores (previsto)",
     "env": "—", "flash": "4 MB"},
    {"id": "HTC-05", "mac": None, "papel": "reserva", "env": "—",
     "flash": "4 MB"},
]


def hardware():
    return {
        "placas": PLACAS,
        "portas": portas_seriais(),
        "radio": {
            "frequencia_mhz": 916.8, "sf": 9, "bw_khz": 125, "cr": "4/7",
            "potencia_dbm": 17, "toa_ms": 169,
            "sensibilidade_dbm": -129.0,
        },
    }


# -------------------------------------------------------------- firmware --

RE_TAM = re.compile(r"(RAM|Flash):\s+\[[= ]*\]\s+([\d.]+)%\s+"
                    r"\(used (\d+) bytes from (\d+) bytes\)")


def firmware():
    ambientes = []
    for env in ("node_dev", "node_range", "bridge"):
        binario = RAIZ / "firmware" / ".pio" / "build" / env / "firmware.bin"
        ambientes.append({
            "env": env,
            "compilado": binario.exists(),
            "bytes": binario.stat().st_size if binario.exists() else 0,
            "modificado": datetime.fromtimestamp(
                binario.stat().st_mtime).isoformat(timespec="seconds")
            if binario.exists() else None,
        })
    return {"ambientes": ambientes}


# ----------------------------------------------------------------- ensaio --

def ensaios():
    caminho = RAIZ / "dados" / "ensaio02.geojson"
    if not caminho.exists():
        return {"pontos": []}
    try:
        dados = json.loads(_texto(caminho))
    except json.JSONDecodeError:
        return {"pontos": []}
    return {"pontos": [f["properties"] | {
        "lon": f["geometry"]["coordinates"][0],
        "lat": f["geometry"]["coordinates"][1]} for f in dados["features"]]}


MODELO = {
    "expoente_n": 3.28, "rms_db": 2.2, "intercepto_dbm": -48.1,
    "coef_log": -32.8, "ganho_altura_db": 9.0,
    "perda_fixa_db": 33.4,
    "referencia_literatura": {"floresta_tropical": 3.22, "visada": 2.31},
}


# -------------------------------------------------------------------- git --

def git():
    linhas = _git("log", "--pretty=%h|%ad|%s", "--date=format:%Y-%m-%d %H:%M",
                  "-40").splitlines()
    commits = []
    for linha in linhas:
        partes = linha.split("|", 2)
        if len(partes) == 3:
            commits.append({"hash": partes[0], "data": partes[1],
                            "assunto": partes[2]})
    return {
        "commits": commits,
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "remoto": _git("config", "--get", "remote.origin.url"),
        "sujo": bool(_git("status", "--porcelain")),
    }


# ------------------------------------------------------------ complexidade --

def complexidade():
    sys.path.insert(0, str(RAIZ / "tools"))
    try:
        import complexidade as mod
    except ImportError:
        return {"resumo": {"funcoes": 0}, "arquivos": []}
    arquivos = mod.varre(RAIZ)
    return {"arquivos": arquivos, "resumo": mod.resume(arquivos),
            "limite": mod.LIMITE_PADRAO}


# -------------------------------------------------------------- visão geral --

def visao_geral():
    docs = documentos()
    pend = pendencias()
    cx = complexidade()
    return {
        "projeto": "Sentinela",
        "fase": "0 — bring-up do rádio",
        "documentos": len(docs),
        "linhas_doc": sum(d["linhas"] for d in docs),
        "pendencias_abertas": sum(1 for p in pend if not p["resolvida"]),
        "pendencias_total": len(pend),
        "funcoes": cx["resumo"].get("funcoes", 0),
        "cc_media": cx["resumo"].get("media", 0),
        "cc_maxima": cx["resumo"].get("maxima", 0),
        "cc_limite": cx.get("limite", 10),
        "modelo": MODELO,
        "gerado_em": datetime.now().isoformat(timespec="seconds"),
    }
