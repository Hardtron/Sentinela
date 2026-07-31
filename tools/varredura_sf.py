#!/usr/bin/env python3
"""Sentinela — automatiza a varredura de alcance por spreading factor.

Grava HTC-01 (PINGER, USB local do Mac) e HTC-03 (bridge/PONGER, USB do
Raspberry Pi, por SSH) para cada SF de 7 a 12, aguarda amostras suficientes
no banco e resume o resultado. Fecha o item "prioritário" da Fase 0
(PLANO.md) — a curva de alcance × SF que dimensiona o projeto inteiro.

As duas placas precisam do mesmo SF para se falar; por isso cada rodada
regrava as duas antes de coletar. O SF é `-D LORA_SF=N` no build
(`platformio.ini`, ambientes `sfN_pinger`/`sfN_bridge`) — board_heltec_v2.h
usa 9 como padrão só quando a flag não é passada.

Pré-requisitos: HTC-01 na USB do Mac, HTC-03 na USB do `sentinelapi`,
`sentinela-ingestor` ativo no homeserver, PlatformIO instalado.

Uso:
    python3 tools/varredura_sf.py                       # SF7-SF12 completo
    python3 tools/varredura_sf.py --sf 7 9 12            # só alguns
    python3 tools/varredura_sf.py --amostras 20 --espera-max 240

Autoria: Matheus Marassi
"""

import argparse
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FIRMWARE = RAIZ / "firmware"

PORTA_LOCAL = "/dev/cu.usbserial-0001"
PIO = str(Path.home() / ".venvs/platformio/bin/pio")
RPI_HOST = "sentinelapi@192.168.15.73"
RPI_PORTA_SERIAL = "/dev/ttyUSB0"
HOMESERVER = "192.168.15.66"

SF_PADRAO = [7, 8, 9, 10, 11, 12]


def executa(cmd, **kw):
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=True, **kw)


# ------------------------------------------------------------------ flash --

def compila(env):
    executa([PIO, "run", "-e", env, "-d", str(FIRMWARE)])


def grava_local(env, porta):
    """HTC-01: PlatformIO já sabe compilar e gravar em um único comando."""
    executa([PIO, "run", "-e", env, "-t", "upload",
             "--upload-port", porta, "-d", str(FIRMWARE)])


def grava_remota(env):
    """HTC-03: o binário é compilado aqui (cross-compile local é rápido) e
    enviado por rsync — evita instalar PlatformIO inteiro no Raspberry Pi só
    para gravar uma placa que já está conectada nele."""
    binario = FIRMWARE / ".pio" / "build" / env / "firmware.bin"
    if not binario.exists():
        sys.exit(f"binário não encontrado: {binario} (build falhou?)")

    executa(["ssh", RPI_HOST, "sudo systemctl stop sentinela-bridge"])
    executa(["rsync", "-az", str(binario), f"{RPI_HOST}:/tmp/sf-bridge.bin"])
    executa(["ssh", RPI_HOST,
             "/home/sentinelapi/sentinela/tools/venv/bin/python -m esptool "
             f"--port {RPI_PORTA_SERIAL} --baud 230400 "
             "write_flash 0x10000 /tmp/sf-bridge.bin"])
    executa(["ssh", RPI_HOST, "sudo systemctl start sentinela-bridge"])


# --------------------------------------------------------------- coleta ----

def consulta_banco(sql):
    """Consulta via SSH até o homeserver — o banco não é exposto na rede
    (backend/README.md). `-t` tira cabeçalho, fica fácil de parsear."""
    r = subprocess.run(
        ["ssh", HOMESERVER,
         f"docker exec sentinela-banco psql -U sentinela -d sentinela -t -A -c \"{sql}\""],
        check=True, capture_output=True, text=True)
    return r.stdout.strip()


def aguarda_amostras(sf, desde, alvo, espera_max_s):
    """Espera pacotes com este SF chegarem ao banco. Não é só ping do rádio:
    é o ingestor realmente persistindo, então confirma a esteira inteira."""
    fim = time.time() + espera_max_s
    n = 0
    while time.time() < fim:
        n = int(consulta_banco(
            f"SELECT count(*) FROM enlace WHERE sf={sf} AND recebido_em >= '{desde}'"))
        print(f"  SF{sf}: {n}/{alvo} amostras...", flush=True)
        if n >= alvo:
            return n
        time.sleep(5)
    print(f"  SF{sf}: tempo esgotado com {n}/{alvo} — pode indicar que o "
          f"enlace não fecha neste SF (ver ERROS.md).", flush=True)
    return n


def resume_sf(sf, desde):
    """Agregado do que foi coletado nesta rodada — o mesmo que vai para a
    tabela final da campanha."""
    linha = consulta_banco(
        "SELECT count(*), "
        "round(avg(margem_sobe_db)::numeric,1), "
        "round(avg(margem_desce_db)::numeric,1), "
        "round(avg(rssi_dbm)::numeric,1), "
        "round(avg(rssi_remoto_dbm)::numeric,1), "
        "round(avg(snr_db)::numeric,1), "
        "round(avg(assimetria_db)::numeric,1), "
        "sum(perdidos) "
        f"FROM enlace_analise WHERE sf={sf} AND recebido_em >= '{desde}'")
    campos = linha.split("|")
    chaves = ["amostras", "margem_sobe_db", "margem_desce_db", "rssi_sobe_dbm",
              "rssi_desce_dbm", "snr_sobe_db", "assimetria_db", "perdidos"]
    return dict(zip(chaves, campos))


# ---------------------------------------------------------------- rodada ---

def roda_sf(sf, amostras_alvo, espera_max_s):
    print(f"\n=== SF{sf} ===", flush=True)
    desde = datetime.now(timezone.utc).isoformat()

    compila(f"sf{sf}_pinger")
    compila(f"sf{sf}_bridge")
    grava_local(f"sf{sf}_pinger", PORTA_LOCAL)
    grava_remota(f"sf{sf}_bridge")

    time.sleep(6)  # boot das duas placas antes de cobrar amostra
    aguarda_amostras(sf, desde, amostras_alvo, espera_max_s)
    return resume_sf(sf, desde)


def imprime_tabela(resultados):
    print("\n" + "=" * 78)
    print("Resultado da varredura SF7-SF12")
    print("=" * 78)
    cab = ("SF", "amostras", "margem_sobe", "margem_desce", "assimetria",
           "snr_sobe", "perdidos")
    print("{:<4}{:<10}{:<14}{:<15}{:<12}{:<10}{:<9}".format(*cab))
    for sf, r in sorted(resultados.items()):
        print("{:<4}{:<10}{:<14}{:<15}{:<12}{:<10}{:<9}".format(
            sf, r.get("amostras", "0"),
            (r.get("margem_sobe_db") or "—") + " dB",
            (r.get("margem_desce_db") or "—") + " dB",
            (r.get("assimetria_db") or "—") + " dB",
            (r.get("snr_sobe_db") or "—") + " dB",
            r.get("perdidos") or "0"))


def parse_args():
    ap = argparse.ArgumentParser(description="Varredura de alcance por SF")
    ap.add_argument("--sf", type=int, nargs="+", default=SF_PADRAO,
                    choices=range(7, 13))
    ap.add_argument("--amostras", type=int, default=15,
                    help="amostras mínimas por SF antes de avançar")
    ap.add_argument("--espera-max", dest="espera_max", type=int, default=180,
                    help="segundos máximos de espera por SF")
    return ap.parse_args()


def main():
    args = parse_args()
    resultados = {}
    try:
        for sf in args.sf:
            resultados[sf] = roda_sf(sf, args.amostras, args.espera_max)
    finally:
        imprime_tabela(resultados)


if __name__ == "__main__":
    main()
