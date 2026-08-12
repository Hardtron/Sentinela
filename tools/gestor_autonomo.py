#!/usr/bin/env python3
"""Sentinela — gestor autônomo de insumos (Frente 6).

Automatiza **dados e insumos**: fotos de campo, boletins governamentais, cache
de tiles e manutenção das séries no banco.

**Fronteira deliberada de segurança:** não atualiza software, pacote de
sistema, venv nem firmware. Isso fica sob controle manual. Um gestor que
atualiza pacote sozinho troca um problema conhecido (insumo velho) por um
desconhecido (ambiente de produção quebrado às 3 da manhã).

RC-07 na prática: se uma API externa cair, o gestor **registra e preserva o
insumo local vigente**. Nunca substitui dado bom por dado vazio, e nunca
inventa. Falha de rede não pode virar mapa em branco durante tempestade.

Uso:
    python3 tools/gestor_autonomo.py            # ciclo completo
    python3 tools/gestor_autonomo.py --so fotos # uma tarefa só
    python3 tools/gestor_autonomo.py --seco     # mostra o que faria

Autoria: Matheus Marassi
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

# MANUTENCAO.md §1: ATL-<município>-<sequencial>, ex. ATL-CGB-014.
# Onde ficam as pastas por Atalaia. O plano previa /DATA/Media/Sentinela, mas
# /DATA/Media pertence ao root no homeserver e o sudo de lá pede senha — criar
# lá exigiria intervenção manual só para o sistema subir. O padrão aponta para
# um caminho que o serviço já pode escrever; para usar /DATA/Media basta criá-lo
# com o dono certo (uma vez, com sudo) e apontar SENTINELA_MEDIA para ele.
MEDIA = Path(os.environ.get("SENTINELA_MEDIA",
                            "/DATA/Runtime/Sentinela-Media/Atalaias"))
TILES = Path(os.environ.get("SENTINELA_TILES", "/DATA/Tiles"))

SUBPASTAS = ("fotos", "dados", "documentos", "manutencao")

TEMPO_LIMITE_S = 20


def agora():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def log(msg):
    print(f"[gestor {agora()}] {msg}", flush=True)


# ------------------------------------------------------------------ fotos --

def estrutura_atalaia(node_dir):
    """Garante as subpastas previstas. Idempotente."""
    for sub in SUBPASTAS:
        (node_dir / sub).mkdir(parents=True, exist_ok=True)


def varre_fotos(seco=False):
    """Georreferencia fotos novas de instalação/vistoria.

    O EXIF da foto tirada na fixação é a fonte de coordenada mais barata que
    existe — o técnico já ia fotografar de qualquer jeito.
    """
    if not MEDIA.exists():
        log(f"pasta de mídia ausente ({MEDIA}) — nada a varrer")
        return 0
    total = 0
    for node_dir in sorted(p for p in MEDIA.iterdir() if p.is_dir()):
        estrutura_atalaia(node_dir)
        fotos = sorted((node_dir / "fotos").glob("*.[jJ][pP]*[gG]"))
        fotos += sorted((node_dir / "fotos").glob("*.[hH][eE][iI][cC]"))
        if not fotos:
            continue
        log(f"{node_dir.name}: {len(fotos)} foto(s)")
        total += len(fotos)
        if seco:
            continue
        script = RAIZ / "tools" / "georreferenciar.py"
        if script.exists():
            subprocess.run([sys.executable, str(script),
                            "--fotos", str(node_dir / "fotos")],
                           check=False)
    return total


# --------------------------------------------------- boletins governamentais --

def _baixa_json(url):
    """Devolve (dados, erro). Nunca levanta: indisponibilidade de órgão
    externo é rotina, não exceção."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Sentinela/1.0"})
        with urllib.request.urlopen(req, timeout=TEMPO_LIMITE_S) as r:
            return json.loads(r.read().decode("utf-8")), None
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:
        return None, str(e)


def sincroniza_boletins(seco=False):
    """Alertas do CEMADEN/INMET.

    **[?] Endpoints não confirmados.** Os feeds abertos desses órgãos mudam de
    endereço e formato, e a P-004 (verificar disponibilidade de dados do
    CEMADEN) continua aberta. Enquanto ela não for resolvida, esta função
    registra a tentativa e preserva o que já existe — deliberadamente não
    inventa URL nem parseia formato suposto, porque boletim de risco errado é
    pior que boletim ausente.
    """
    destino = TILES.parent / "Boletins"
    if seco:
        log(f"[seco] boletins iriam para {destino}")
        return 0
    destino.mkdir(parents=True, exist_ok=True)
    log("boletins: P-004 em aberto — endpoint oficial não confirmado; "
        "insumo local preservado, nada sobrescrito")
    return 0


# --------------------------------------------------------- cache de tiles --

def cache_tiles(seco=False):
    """Prepara o cache offline de mapa.

    **Requisito de confiabilidade, não conveniência (RT-03):** é durante a
    tempestade — quando a internet tende a cair — que o operador mais precisa
    do mapa. Tile que só existe online é tile que some na hora do uso.
    """
    if seco:
        log(f"[seco] cache de tiles em {TILES}")
        return 0
    TILES.mkdir(parents=True, exist_ok=True)
    marca = TILES / "ULTIMA_VARREDURA"
    marca.write_text(agora() + "\n", encoding="utf-8")
    log(f"cache de tiles pronto em {TILES} "
        "(pré-geração por área depende da definição do município-piloto, P-002)")
    return 0


# ------------------------------------------------------ manutenção do banco --

def manutencao_banco(seco=False):
    """Aplica migrações pendentes e atualiza as agregações contínuas."""
    migra = RAIZ / "backend" / "migra.py"
    venv = RAIZ / "backend" / "venv" / "bin" / "python"
    py = str(venv) if venv.exists() else sys.executable
    if seco:
        log(f"[seco] rodaria {migra}")
        return 0
    if migra.exists():
        subprocess.run([py, str(migra)], check=False)
    return 0


TAREFAS = {
    "fotos": varre_fotos,
    "boletins": sincroniza_boletins,
    "tiles": cache_tiles,
    "banco": manutencao_banco,
}


def main():
    ap = argparse.ArgumentParser(description="Gestor autônomo de insumos")
    ap.add_argument("--so", choices=sorted(TAREFAS), help="roda uma tarefa só")
    ap.add_argument("--seco", action="store_true", help="não altera nada")
    args = ap.parse_args()

    escolhidas = [args.so] if args.so else list(TAREFAS)
    log(f"iniciando: {', '.join(escolhidas)}{' (seco)' if args.seco else ''}")
    for nome in escolhidas:
        try:
            TAREFAS[nome](seco=args.seco)
        except Exception as e:                        # noqa: BLE001
            # Uma tarefa que falha não pode derrubar as outras: o cache de
            # tiles não deve deixar de ser atualizado porque o CEMADEN caiu.
            log(f"ERRO em {nome}: {e}")
    log("fim")
    return 0


if __name__ == "__main__":
    sys.exit(main())
