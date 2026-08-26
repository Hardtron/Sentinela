#!/usr/bin/env python3
"""Sentinela — automatiza a varredura de alcance por spreading factor.

Grava HTC-01 (PINGER, USB local da workstation) e HTC-03 (bridge/PONGER, USB do
Raspberry Pi, por SSH) para cada SF de 7 a 12, aguarda amostras suficientes
no banco e resume o resultado. Fecha o item "prioritário" da Fase 0
(PLANO.md) — a curva de alcance × SF que dimensiona o projeto inteiro.

As duas placas precisam do mesmo SF para se falar; por isso cada rodada
regrava as duas antes de coletar. O SF é `-D LORA_SF=N` no build
(`platformio.ini`, ambientes `sfN_pinger`/`sfN_bridge`) — board_heltec_v2.h
usa 9 como padrão só quando a flag não é passada.

O runtime persistente e a bancada completa podem permanecer indisponíveis durante
a migração Windows + GitHub. Quando a campanha for retomada, a workstation local
pode ser Windows, macOS ou Linux; a descoberta serial inclui portas COM no Windows.

Uso:
    python tools/varredura_sf.py                       # SF7-SF12 completo
    python tools/varredura_sf.py --sf 7 9 12          # só alguns
    python tools/varredura_sf.py --amostras 20 --espera-max 240

Autoria: Luiz Matheus Marassi de Paula
"""

import argparse
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FIRMWARE = RAIZ / "firmware"

ESPTOOL_REMOTO = "/home/sentinelapi/sentinela/tools/venv/bin/python -m esptool"
RPI_HOST = "sentinelapi@192.168.15.73"
RPI_PORTA_SERIAL = "/dev/ttyUSB0"
HOMESERVER = "192.168.15.66"

# macOS/Linux usam devices sob /dev. No Windows, pyserial enumera COM ports.
PADROES_SERIAL = ("cu.usbserial*", "cu.SLAB_USBtoUART*", "ttyUSB*", "ttyACM*")


def acha_pio():
    """Localiza PlatformIO sem depender de um layout único de workstation."""
    candidatos = [
        Path.home() / ".venvs/platformio/bin/pio",
        RAIZ / "tools" / "venv" / "bin" / "pio",
    ]
    for c in candidatos:
        if c.exists():
            return str(c)
    achado = shutil.which("pio")
    if achado:
        return achado
    sys.exit("PlatformIO não encontrado no PATH nem nos ambientes conhecidos")


def acha_esptool():
    """Localiza esptool junto do PlatformIO ou no Python corrente."""
    base = Path.home() / ".platformio" / "packages" / "tool-esptoolpy"
    script = base / "esptool.py"
    python = Path(acha_pio()).parent / "python"
    if script.exists() and python.exists():
        return [str(python), str(script)]
    return [sys.executable, "-m", "esptool"]


def acha_porta_serial():
    """Primeira porta USB-serial presente no sistema em uso."""
    if sys.platform == "win32":
        try:
            from serial.tools import list_ports
        except ImportError:
            return None
        portas = sorted(
            (porta.device for porta in list_ports.comports() if porta.device),
            key=str.casefold,
        )
        return portas[0] if portas else None

    for padrao in PADROES_SERIAL:
        achadas = sorted(Path("/dev").glob(padrao))
        if achadas:
            return str(achadas[0])
    return None


SF_PADRAO = [7, 8, 9, 10, 11, 12]

# HARDWARE.md — checado antes de qualquer gravação RF-ativa. Não é opcional:
# E-007 foi exatamente gravar node_dev (RF-ativo) na HTC-02 (sem antena) por
# assumir identidade da placa sem checar o MAC primeiro.
MAC_HTC01 = "3c:71:bf:8c:33:a8"
MAC_HTC03 = "3c:71:bf:8c:2f:a4"

RE_MAC = re.compile(r"MAC:\s*([0-9a-f:]{17})", re.I)


def executa(cmd, **kw):
    print(f"$ {' '.join(cmd)}", flush=True)
    return subprocess.run(cmd, check=True, **kw)


def _mac_local(porta):
    r = subprocess.run(
        [*acha_esptool(), "--port", porta, "flash_id"],
        capture_output=True,
        text=True,
        check=True,
    )
    achado = RE_MAC.search(r.stdout)
    return achado.group(1).lower() if achado else None


def _mac_remoto():
    r = subprocess.run(
        [
            "ssh",
            RPI_HOST,
            f"{ESPTOOL_REMOTO} --port {RPI_PORTA_SERIAL} flash_id",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    achado = RE_MAC.search(r.stdout)
    return achado.group(1).lower() if achado else None


def confere_mac(mac_lido, mac_esperado, placa):
    """Aborta a campanha se a placa física não for a esperada."""
    if mac_lido is None:
        sys.exit(f"não foi possível ler o MAC de {placa} — abortando por segurança")
    if mac_lido != mac_esperado.lower():
        sys.exit(
            f"MAC inesperado em {placa}: lido {mac_lido}, esperado {mac_esperado}. "
            "Confira HARDWARE.md antes de continuar."
        )
    print(f"  MAC confere: {placa} = {mac_lido}", flush=True)


def compila(env):
    executa([acha_pio(), "run", "-e", env, "-d", str(FIRMWARE)])


def grava_local(env, porta):
    confere_mac(_mac_local(porta), MAC_HTC01, "HTC-01")
    executa(
        [
            acha_pio(),
            "run",
            "-e",
            env,
            "-t",
            "upload",
            "--upload-port",
            porta,
            "-d",
            str(FIRMWARE),
        ]
    )


def grava_remota(env):
    confere_mac(_mac_remoto(), MAC_HTC03, "HTC-03")
    binario = FIRMWARE / ".pio" / "build" / env / "firmware.bin"
    if not binario.exists():
        sys.exit(f"binário não encontrado: {binario} (build falhou?)")

    executa(["ssh", RPI_HOST, "sudo systemctl stop sentinela-bridge"])
    executa(["rsync", "-az", str(binario), f"{RPI_HOST}:/tmp/sf-bridge.bin"])
    executa(
        [
            "ssh",
            RPI_HOST,
            "/home/sentinelapi/sentinela/tools/venv/bin/python -m esptool "
            f"--port {RPI_PORTA_SERIAL} --baud 230400 "
            "write_flash 0x10000 /tmp/sf-bridge.bin",
        ]
    )
    executa(["ssh", RPI_HOST, "sudo systemctl start sentinela-bridge"])


def consulta_banco(sql):
    r = subprocess.run(
        [
            "ssh",
            HOMESERVER,
            f'docker exec sentinela-banco psql -U sentinela -d sentinela -t -A -c "{sql}"',
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return r.stdout.strip()


def aguarda_amostras(sf, desde, alvo, espera_max_s):
    fim = time.time() + espera_max_s
    n = 0
    while time.time() < fim:
        n = int(
            consulta_banco(
                f"SELECT count(*) FROM enlace WHERE sf={sf} AND recebido_em >= '{desde}'"
            )
        )
        print(f"  SF{sf}: {n}/{alvo} amostras...", flush=True)
        if n >= alvo:
            return n
        time.sleep(5)
    print(
        f"  SF{sf}: tempo esgotado com {n}/{alvo} — pode indicar que o enlace não fecha neste SF.",
        flush=True,
    )
    return n


def resume_sf(sf, desde):
    linha = consulta_banco(
        "SELECT count(*), "
        "round(avg(margem_sobe_db)::numeric,1), "
        "round(avg(margem_desce_db)::numeric,1), "
        "round(avg(rssi_dbm)::numeric,1), "
        "round(avg(rssi_remoto_dbm)::numeric,1), "
        "round(avg(snr_db)::numeric,1), "
        "round(avg(assimetria_db)::numeric,1), "
        "sum(perdidos) "
        f"FROM enlace_analise WHERE sf={sf} AND recebido_em >= '{desde}'"
    )
    campos = linha.split("|")
    chaves = [
        "amostras",
        "margem_sobe_db",
        "margem_desce_db",
        "rssi_sobe_dbm",
        "rssi_desce_dbm",
        "snr_sobe_db",
        "assimetria_db",
        "perdidos",
    ]
    return dict(zip(chaves, campos))


def roda_sf(sf, amostras_alvo, espera_max_s, porta):
    print(f"\n=== SF{sf} ===", flush=True)
    desde = datetime.now(timezone.utc).isoformat()
    compila(f"sf{sf}_pinger")
    compila(f"sf{sf}_bridge")
    grava_local(f"sf{sf}_pinger", porta)
    grava_remota(f"sf{sf}_bridge")
    time.sleep(6)
    aguarda_amostras(sf, desde, amostras_alvo, espera_max_s)
    return resume_sf(sf, desde)


def imprime_tabela(resultados):
    print("\n" + "=" * 78)
    print("Resultado da varredura SF7-SF12")
    print("=" * 78)
    cab = (
        "SF",
        "amostras",
        "margem_sobe",
        "margem_desce",
        "assimetria",
        "snr_sobe",
        "perdidos",
    )
    print("{:<4}{:<10}{:<14}{:<15}{:<12}{:<10}{:<9}".format(*cab))
    for sf, r in sorted(resultados.items()):
        print(
            "{:<4}{:<10}{:<14}{:<15}{:<12}{:<10}{:<9}".format(
                sf,
                r.get("amostras", "0"),
                (r.get("margem_sobe_db") or "—") + " dB",
                (r.get("margem_desce_db") or "—") + " dB",
                (r.get("assimetria_db") or "—") + " dB",
                (r.get("snr_sobe_db") or "—") + " dB",
                r.get("perdidos") or "0",
            )
        )


def parse_args():
    ap = argparse.ArgumentParser(description="Varredura de alcance por SF")
    ap.add_argument("--sf", type=int, nargs="+", default=SF_PADRAO, choices=range(7, 13))
    ap.add_argument("--amostras", type=int, default=15)
    ap.add_argument("--espera-max", dest="espera_max", type=int, default=180)
    ap.add_argument("--porta", default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    porta = args.porta or acha_porta_serial()
    if porta is None:
        sys.exit("nenhuma porta USB-serial encontrada — use --porta para indicar")
    print(f"porta serial: {porta}", flush=True)

    resultados = {}
    try:
        for sf in args.sf:
            resultados[sf] = roda_sf(sf, args.amostras, args.espera_max, porta)
    finally:
        imprime_tabela(resultados)


if __name__ == "__main__":
    main()
