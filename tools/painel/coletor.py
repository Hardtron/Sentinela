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

RE_PENDENCIA = re.compile(
    r"^\|\s*(?:~~)?\*{0,2}"
    r"(PT-\d+|P-\d+|C-\d+|A-\d+|R-\d+|B-\d+|M-\d+|N-\d+|V-\d+)"
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
    "M": ("docs/MERCADO_MUNICIPIOS.md", "mercado municipal"),
    "N": ("docs/MERCADO_MINERACAO.md", "mineração"),
    "V": ("docs/VALUATION.md", "valuation"),
}

# PT-xx colide com P-xx na primeira letra; tratado à parte.
ORIGEM_ESPECIAL = {"PT": ("docs/PATENTES.md", "patentes")}


def pendencias():
    itens = []
    vistos = set()
    fontes = {v[0] for v in ORIGEM_PENDENCIA.values()}
    fontes |= {v[0] for v in ORIGEM_ESPECIAL.values()}
    fontes |= {"docs/CONCORRENCIA.md"}
    for arquivo in sorted(fontes):
        texto = _texto(RAIZ / arquivo)
        for ident, descricao, bloqueia in RE_PENDENCIA.findall(texto):
            if ident in vistos:
                continue
            vistos.add(ident)
            resolvida = "Resolvida" in bloqueia or "Encerrada" in bloqueia
            prefixo = ident.split("-")[0]
            origem = ORIGEM_ESPECIAL.get(prefixo) or ORIGEM_PENDENCIA.get(prefixo)
            itens.append({
                "id": ident,
                "descricao": re.sub(r"[*~`]", "", descricao),
                "situacao": re.sub(r"[*~`]", "", bloqueia),
                "grupo": (origem or ("", "outro"))[1],
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


# ------------------------------------------------------------------ frota --
# Catálogo espelhado de docs/MANUTENCAO.md §5. Vive aqui para o painel exibir
# antes de existir backend; migra para o banco na fase 2.

ALARMES = [
    ("Atalaia silenciosa", "comunicacao", "CRITICO",
     "Sem pacote além de 3 heartbeats", "Verificar energia e enlace no local"),
    ("Farol fora do ar", "comunicacao", "CRITICO",
     "Gateway sem contato", "Afeta todas as Atalaias da área"),
    ("Enlace degradando", "comunicacao", "ATENCAO",
     "Margem média < 10 dB por 7 dias", "Avaliar obstrução nova ou antena"),
    ("Perda crescente", "comunicacao", "ATENCAO",
     "Perda > 5% em média móvel de 24 h", "Investigar interferência"),
    ("Bateria crítica", "energia", "URGENTE",
     "Autonomia projetada < 48 h", "Trocar bateria"),
    ("Sem captação", "energia", "URGENTE",
     "E_dia ~ 0 com vizinhas normais", "Painel desconectado ou coberto"),
    ("Captação reduzida", "energia", "ATENCAO",
     "Razão < 0,75 por 7 dias, janela normal", "Limpar painel"),
    ("Sombreamento crescente", "energia", "ATENCAO",
     "Janela de carga encurta por 14 dias", "Podar vegetação"),
    ("Bateria em fim de vida", "energia", "ATENCAO",
     "V_min em queda com E_dia estável", "Programar troca"),
    ("Consumo anômalo", "energia", "URGENTE",
     "DoD acima do histórico com E_dia estável", "Diagnóstico remoto"),
    ("Sensor sem resposta", "sensores", "URGENTE",
     "Sem leitura válida em 3 ciclos", "Verificar cabo e conector"),
    ("Leitura travada", "sensores", "URGENTE",
     "Valor idêntico além do plausível", "Substituir sensor"),
    ("Fora de faixa", "sensores", "URGENTE",
     "Além do intervalo físico", "Substituir ou recalibrar"),
    ("Deriva suspeita", "sensores", "ATENCAO",
     "Divergência de sensor redundante", "Recalibrar"),
    ("Pluviômetro mudo", "sensores", "URGENTE",
     "Sem pulso com chuva nas vizinhas", "Desobstruir báscula"),
    ("Umidade interna", "integridade", "URGENTE",
     "Umidade no invólucro acima do limiar", "Trocar vedação — antes da água"),
    ("Impacto", "integridade", "URGENTE",
     "Aceleração alta sem chuva associada", "Inspeção — vandalismo ou galho"),
    ("Inclinação sem chuva", "integridade", "URGENTE",
     "Variação sem precipitação nas vizinhas", "Verificar antes de tratar como movimento"),
    ("Temperatura interna alta", "integridade", "ATENCAO",
     "Acima do limite dos componentes", "Avaliar sombreamento do invólucro"),
    ("Reinícios frequentes", "sistema", "URGENTE",
     "Mais de 3 em 24 h", "Diagnóstico de firmware"),
    ("Watchdog disparado", "sistema", "ATENCAO", "Qualquer ocorrência",
     "Registrar e investigar padrão"),
    ("Memória degradando", "sistema", "ATENCAO",
     "Heap livre em queda monotônica", "Investigar vazamento"),
]

ASSINATURAS_ENERGIA = [
    ("E_dia cai gradualmente, janela inalterada", "Sujeira acumulada no painel",
     "Limpeza"),
    ("Janela encurta progressivamente, mesmo horário", "Vegetação sombreando",
     "Poda"),
    ("E_dia cai abruptamente para ~zero", "Painel desconectado ou coberto",
     "Visita urgente"),
    ("Queda de um dia só, com recuperação", "Evento pontual — folha, ave",
     "Registrar, não agir"),
    ("E_dia normal, V_min cai a cada noite", "Bateria degradando",
     "Trocar bateria"),
    ("DoD aumenta com E_dia estável", "Consumo anômalo no dispositivo",
     "Diagnóstico remoto"),
    ("V_fim sobe rápido com E_dia baixa", "Resistência interna alta",
     "Trocar bateria"),
]

PESOS_SAUDE = [
    ("Comunicação", 30, "Heartbeat, margem de enlace, perda"),
    ("Energia", 30, "Razão de captação, autonomia, saúde da bateria"),
    ("Sensores", 25, "Fração de sensores válidos, deriva"),
    ("Integridade", 15, "Umidade interna, temperatura, reinícios"),
]


def frota():
    """Modelo de saúde da frota. Sem dispositivos em campo ainda: expõe o
    catálogo e os pesos para que a operação seja revisável antes de existir."""
    por_severidade = {}
    for _, _, sev, _, _ in ALARMES:
        por_severidade[sev] = por_severidade.get(sev, 0) + 1
    return {
        "operando": 0,
        "previstos": len(PLACAS),
        "alarmes": [{"nome": n, "grupo": g, "severidade": s,
                     "gatilho": t, "acao": a} for n, g, s, t, a in ALARMES],
        "por_severidade": por_severidade,
        "assinaturas": [{"padrao": p, "diagnostico": d, "acao": a}
                        for p, d, a in ASSINATURAS_ENERGIA],
        "pesos_saude": [{"componente": c, "peso": p, "entra_com": e}
                        for c, p, e in PESOS_SAUDE],
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
