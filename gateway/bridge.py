#!/usr/bin/env python3
"""Sentinela — bridge serial → MQTT no Raspberry Pi 4.

A placa `HTC-03` (papel PONGER/bridge) escuta os quadros LoRa e emite CSV pela
serial. Este processo lê essa serial, publica em MQTT e mantém um **buffer em
disco** para não perder dados se o broker cair — ver gateway/README.md §
"Conteúdo previsto".

Sem sensor real ainda (fase 0), o que trafega é o CSV de bring-up (RSSI/SNR do
ping-pong). O formato do payload muda na fase 1, com `lib/proto/`; a estrutura
da bridge — serial → fila → MQTT → saúde — não muda.

**Testável sem hardware nenhum**, via `--simular`: lê o mesmo formato CSV de um
arquivo, no lugar da serial. É o que permite desenvolver e validar esta ponta
antes de a Atalaia `HTC-03` ter antena disponível (HARDWARE.md).

Uso:
    python3 bridge.py --porta /dev/ttyUSB0 --broker localhost
    python3 bridge.py --simular exemplo.csv --veloz     # sem hardware nenhum

Autoria: Matheus Marassi
"""

import argparse
import json
import re
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    import serial
except ImportError:
    serial = None

try:
    import paho.mqtt.client as mqtt
except ImportError:
    mqtt = None

RE_CSV = re.compile(
    r"^(\d+),([\-\d.]*),([\-\d.]*),([\-\d.]*),([\-\d.]*),(\d+),(\d+)$")

# O firmware imprime `# freq=916.8MHz sf=9 bw=125kHz ...` ao subir.
RE_SF = re.compile(r"\bsf=(\d+)")

TOPICO_TELEMETRIA = "sentinela/no/{node_id}/telemetria"
TOPICO_SAUDE = "sentinela/bridge/{bridge_id}/saude"

BUFFER_PATH = Path(__file__).resolve().parent / "buffer.jsonl"
SAUDE_INTERVALO_S = 30.0

_encerrar = False


def _sinal(_signum, _frame):
    global _encerrar
    _encerrar = True


# ------------------------------------------------------------- fontes de dado --

def linhas_da_serial(porta, baud):
    """Gerador resiliente: reabre a porta sozinho se ela cair (cabo solto,
    placa reiniciada). É o comportamento que uma bridge de produção precisa
    ter — ninguém vai reiniciar o processo manualmente em campo."""
    while not _encerrar:
        try:
            with serial.Serial(porta, baud, timeout=1) as sp:
                print(f"[bridge] serial conectada: {porta}")
                while not _encerrar:
                    linha = sp.readline().decode("utf-8", "replace").strip()
                    if linha:
                        yield linha
        except (OSError, serial.SerialException) as e:
            print(f"[bridge] serial indisponivel ({e}); nova tentativa em 5s")
            time.sleep(5)


def linhas_de_arquivo(caminho, veloz):
    """Reproduz um CSV gravado como se fosse a serial — a bridge não distingue
    uma fonte da outra, o que é o ponto: testa a lógica real sem hardware."""
    with open(caminho, encoding="utf-8") as f:
        for linha in f:
            linha = linha.strip()
            if linha:
                yield linha
            if not veloz:
                time.sleep(0.2)


# ----------------------------------------------------------------- parsing --

def parse_linha(linha):
    """CSV do bring-up: seq,rssi,snr,rssi_remoto,snr_remoto,enviados,recebidos.
    Campos vazios (ping sem resposta) viram None, não zero — RC-07."""
    m = RE_CSV.match(linha)
    if not m:
        return None
    seq, rssi, snr, rssi_r, snr_r, enviados, recebidos = m.groups()
    return {
        "seq": int(seq),
        "rssi_dbm": float(rssi) if rssi else None,
        "snr_db": float(snr) if snr else None,
        "rssi_remoto_dbm": int(rssi_r) if rssi_r else None,
        "snr_remoto_db": int(snr_r) if snr_r else None,
        "enviados": int(enviados),
        "recebidos": int(recebidos),
    }


def anota_parametros(linha, estado):
    """Captura o SF anunciado pelo firmware nos comentários de boot.

    Faz a telemetria se autodescrever: quando a varredura SF7–SF12 trocar o
    fator de espalhamento, o dado gravado já sai com o valor correto, sem
    depender de alguém lembrar de ajustar um parâmetro na linha de comando —
    e o SF é o que define a sensibilidade contra a qual a margem é medida.
    """
    achado = RE_SF.search(linha)
    if achado:
        estado["sf"] = int(achado.group(1))


def monta_mensagem(dados, node_id, estado):
    return {
        "node_id": node_id,
        "bridge_id": estado.get("bridge_id"),
        "sf": estado.get("sf"),
        "recebido_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        **dados,
    }


# --------------------------------------------------------------------- MQTT --

def cria_cliente_mqtt(args):
    if mqtt is None:
        print("[bridge] paho-mqtt nao instalado — rodando so com buffer em disco")
        return None
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id=args.bridge_id)
    cliente.on_connect = lambda c, u, f, rc, props=None: print(
        f"[bridge] MQTT conectado (rc={rc})")
    try:
        cliente.connect(args.broker, args.porta_mqtt, keepalive=30)
    except (OSError, ConnectionRefusedError) as e:
        print(f"[bridge] MQTT indisponivel no start ({e}); buffer em disco ativo")
    cliente.loop_start()
    return cliente


def publica(cliente, node_id, msg):
    if cliente is None or not cliente.is_connected():
        return False
    topico = TOPICO_TELEMETRIA.format(node_id=node_id)
    info = cliente.publish(topico, json.dumps(msg, ensure_ascii=False), qos=1)
    return info.rc == mqtt.MQTT_ERR_SUCCESS


def publica_saude(cliente, bridge_id, estado, fila_len):
    msg = {
        "bridge_id": bridge_id,
        "ativo_desde": estado["inicio"],
        "publicados": estado["publicados"],
        "fila_pendente": fila_len,
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    if cliente is not None and cliente.is_connected():
        cliente.publish(TOPICO_SAUDE.format(bridge_id=bridge_id),
                        json.dumps(msg, ensure_ascii=False), qos=1, retain=True)
    print(f"[bridge] saude: {fila_len} pendente(s), {estado['publicados']} publicados")


# ------------------------------------------------------------ buffer em disco --
# Existe para que uma queda do broker (ou do enlace RPi->homeserver) não perca
# dado — fica em disco até conseguir publicar. Ver README desta pasta.

def buffer_carrega(caminho):
    if not caminho.exists():
        return []
    try:
        with open(caminho, encoding="utf-8") as f:
            return [json.loads(l) for l in f if l.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def buffer_grava(caminho, fila):
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "w", encoding="utf-8") as f:
        for msg in fila:
            f.write(json.dumps(msg, ensure_ascii=False) + "\n")


def tenta_esvaziar_fila(cliente, node_id, fila):
    if not fila or cliente is None or not cliente.is_connected():
        return
    restante = []
    for msg in fila:
        if not publica(cliente, msg.get("node_id", node_id), msg):
            restante.append(msg)
    fila[:] = restante
    buffer_grava(BUFFER_PATH, fila)


# ---------------------------------------------------------------- principal --

def processa_linha(linha, fila, cliente, node_id_padrao, estado):
    if not linha:
        return
    if linha.startswith("#"):
        anota_parametros(linha, estado)
        return
    dados = parse_linha(linha)
    if dados is None:
        return
    msg = monta_mensagem(dados, node_id_padrao, estado)
    if publica(cliente, node_id_padrao, msg):
        estado["publicados"] += 1
    else:
        fila.append(msg)
        buffer_grava(BUFFER_PATH, fila)


def parse_args():
    ap = argparse.ArgumentParser(description="Sentinela — bridge serial -> MQTT")
    ap.add_argument("--porta", default="/dev/ttyUSB0")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--broker", default="localhost")
    ap.add_argument("--porta-mqtt", dest="porta_mqtt", type=int, default=1883)
    ap.add_argument("--bridge-id", dest="bridge_id", default="FAR-01")
    ap.add_argument("--no-id", dest="no_id", type=int, default=0,
                    help="node_id usado quando o CSV nao identifica a origem")
    ap.add_argument("--simular", default=None,
                    help="arquivo CSV para reproduzir sem hardware (teste)")
    ap.add_argument("--veloz", action="store_true",
                    help="nao esperar entre linhas do --simular")
    return ap.parse_args()


def main():
    if serial is None and sys.argv.count("--simular") == 0:
        sys.exit("pyserial nao encontrado. Instale com: pip install pyserial")

    args = parse_args()
    estado = {"inicio": time.time(), "publicados": 0,
              "bridge_id": args.bridge_id, "sf": None}
    fila = buffer_carrega(BUFFER_PATH)
    cliente = cria_cliente_mqtt(args)
    origem = (linhas_de_arquivo(args.simular, args.veloz) if args.simular
              else linhas_da_serial(args.porta, args.baud))

    signal.signal(signal.SIGINT, _sinal)
    print(f"[bridge] iniciado, bridge_id={args.bridge_id}, "
          f"{len(fila)} mensagem(ns) pendente(s) do buffer anterior")

    proxima_saude = 0.0
    try:
        for linha in origem:
            if _encerrar:
                break
            processa_linha(linha, fila, cliente, args.no_id, estado)
            tenta_esvaziar_fila(cliente, args.no_id, fila)
            if time.time() >= proxima_saude:
                publica_saude(cliente, args.bridge_id, estado, len(fila))
                proxima_saude = time.time() + SAUDE_INTERVALO_S
    finally:
        buffer_grava(BUFFER_PATH, fila)
        if cliente is not None:
            cliente.loop_stop()
        print(f"[bridge] encerrado — {estado['publicados']} publicados, "
              f"{len(fila)} pendente(s) em disco")


if __name__ == "__main__":
    main()
