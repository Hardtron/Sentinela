#!/usr/bin/env python3
"""Sentinela — ingestor MQTT → PostgreSQL/TimescaleDB.

Assina os tópicos publicados pela bridge e grava no banco. É a peça que faz o
dado **parar de evaporar**: antes disto a esteira funcionava de ponta a ponta,
mas nada era persistido — o painel guardava uma janela em memória e o broker
não guarda histórico.

Roda no homeserver, junto do banco: assim as credenciais do PostgreSQL nunca
saem de `localhost`. O broker, que vive no Raspberry Pi, chega por túnel SSH
(`sentinela-tunel-mqtt.service`) — nenhum dos dois é exposto na LAN.

Idempotente por construção: a bridge reenvia o buffer em disco quando o broker
volta, e o `ON CONFLICT DO NOTHING` impede que isso duplique amostra e falseie
a taxa de perda.

Uso:
    python3 ingestor.py                      # lê backend/.env
    python3 ingestor.py --broker localhost --banco-host localhost

Autoria: Matheus Marassi
"""

import argparse
import json
import math
import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import paho.mqtt.client as mqtt
import psycopg

RAIZ = Path(__file__).resolve().parent
QUARENTENA_PATH = RAIZ / "quarentena.jsonl"

SQL_ENLACE = """
INSERT INTO enlace (recebido_em, node_id, bridge_id, seq, sf, rssi_dbm, snr_db,
                    rssi_remoto_dbm, snr_remoto_db, enviados, recebidos, perdidos)
VALUES (%(recebido_em)s, %(node_id)s, %(bridge_id)s, %(seq)s, %(sf)s,
        %(rssi_dbm)s, %(snr_db)s, %(rssi_remoto_dbm)s, %(snr_remoto_db)s,
        %(enviados)s, %(recebidos)s, %(perdidos)s)
ON CONFLICT DO NOTHING
"""

SQL_SAUDE = """
INSERT INTO saude_bridge (gerado_em, bridge_id, publicados, fila_pendente, ativo_desde)
VALUES (%(gerado_em)s, %(bridge_id)s, %(publicados)s, %(fila_pendente)s, %(ativo_desde)s)
ON CONFLICT DO NOTHING
"""

_encerrar = False
_estado = {"enlace": 0, "saude": 0, "erros": 0, "quarentena": 0,
           "ultimo_seq": None}


def _sinal(_signum, _frame):
    global _encerrar
    _encerrar = True


def carrega_env(caminho):
    """Lê o .env sem dependência extra. Não sobrescreve o que já veio do
    ambiente — systemd e shell continuam tendo a palavra final."""
    if not caminho.exists():
        return
    for linha in caminho.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip())


# ------------------------------------------------------------- conversão --

def _instante(valor):
    """Aceita ISO-8601 (telemetria) e epoch em segundos (ativo_desde)."""
    if valor is None:
        return None
    if isinstance(valor, (int, float)):
        return datetime.fromtimestamp(valor, timezone.utc)
    try:
        return datetime.fromisoformat(str(valor))
    except ValueError:
        return None


def _inteiro(valor, minimo=0, maximo=None):
    if isinstance(valor, bool) or not isinstance(valor, int):
        return False
    return valor >= minimo and (maximo is None or valor <= maximo)


def _numero_ou_nulo(valor):
    return valor is None or (isinstance(valor, (int, float))
                             and not isinstance(valor, bool)
                             and math.isfinite(valor))


def _valida_radio(d):
    if d.get("sf") is not None and d["sf"] not in range(7, 13):
        return "sf inválido"
    for campo in ("rssi_dbm", "snr_db", "rssi_remoto_dbm", "snr_remoto_db"):
        if not _numero_ou_nulo(d.get(campo)):
            return f"{campo} inválido"
    return None


def _valida_contadores(d):
    for campo in ("enviados", "recebidos", "perdidos"):
        if d.get(campo) is not None and not _inteiro(d[campo]):
            return f"{campo} inválido"
    if (d.get("enviados") is not None and d.get("recebidos") is not None
            and d["recebidos"] > d["enviados"]):
        return "recebidos maior que enviados"
    return None


def valida_enlace(d):
    """Contrato estrutural do CSV de bring-up, sem criar limites de campo."""
    if not isinstance(d, dict):
        return "carga não é objeto JSON"
    if _instante(d.get("recebido_em")) is None:
        return "recebido_em ausente ou inválido"
    if not _inteiro(d.get("node_id"), 0, 65535):
        return "node_id ausente ou fora do contrato uint16"
    if d.get("seq") is not None and not _inteiro(d["seq"]):
        return "seq inválido"
    return _valida_radio(d) or _valida_contadores(d)


def valida_saude(d):
    if not isinstance(d, dict):
        return "carga não é objeto JSON"
    if _instante(d.get("gerado_em")) is None:
        return "gerado_em ausente ou inválido"
    if not isinstance(d.get("bridge_id"), str) or not d["bridge_id"].strip():
        return "bridge_id ausente ou inválido"
    for campo in ("publicados", "fila_pendente"):
        if d.get(campo) is not None and not _inteiro(d[campo]):
            return f"{campo} inválido"
    if d.get("ativo_desde") is not None and _instante(d["ativo_desde"]) is None:
        return "ativo_desde inválido"
    return None


def registra_quarentena(topico, carga, motivo, caminho=QUARENTENA_PATH):
    """Preserva entrada recusada sem deixá-la parecer telemetria válida."""
    registro = {
        "registrado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "topico": topico,
        "motivo": motivo,
        "carga": carga.decode("utf-8", "replace")[:8192],
    }
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with open(caminho, "a", encoding="utf-8") as f:
        f.write(json.dumps(registro, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    _estado["quarentena"] += 1


def monta_enlace(d):
    """Traduz a mensagem da bridge para as colunas de `enlace`.

    Descarta o que não tem instante nem nó: sem esses dois a amostra não é
    localizável no tempo nem atribuível a ninguém — guardar seria acumular
    lixo que depois passa por dado.
    """
    recebido = _instante(d.get("recebido_em"))
    if recebido is None or d.get("node_id") is None:
        return None
    return {
        "recebido_em": recebido,
        "node_id": d["node_id"],
        "bridge_id": d.get("bridge_id") or "desconhecida",
        "seq": d.get("seq"),
        "sf": d.get("sf"),
        "rssi_dbm": d.get("rssi_dbm"),
        "snr_db": d.get("snr_db"),
        "rssi_remoto_dbm": d.get("rssi_remoto_dbm"),
        "snr_remoto_db": d.get("snr_remoto_db"),
        "enviados": d.get("enviados"),
        "recebidos": d.get("recebidos"),
        "perdidos": d.get("perdidos") or 0,
    }


def monta_saude(d):
    gerado = _instante(d.get("gerado_em"))
    if gerado is None or not d.get("bridge_id"):
        return None
    return {
        "gerado_em": gerado,
        "bridge_id": d["bridge_id"],
        "publicados": d.get("publicados"),
        "fila_pendente": d.get("fila_pendente"),
        "ativo_desde": _instante(d.get("ativo_desde")),
    }


# ---------------------------------------------------------------- gravação --

def grava(conexao, sql, linha):
    with conexao.cursor() as cur:
        cur.execute(sql, linha)
    conexao.commit()


def trata_mensagem(conexao, topico, carga):
    """Devolve o nome do que foi gravado, ou None se a mensagem foi ignorada."""
    try:
        dados = json.loads(carga.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        registra_quarentena(topico, carga, f"JSON inválido: {e}")
        return None

    if topico.endswith("/telemetria"):
        erro = valida_enlace(dados)
        if erro:
            registra_quarentena(topico, carga, erro)
            return None
        linha = monta_enlace(dados)
        if linha:
            grava(conexao, SQL_ENLACE, linha)
            _estado["ultimo_seq"] = linha["seq"]
            return "enlace"
    elif topico.endswith("/saude"):
        erro = valida_saude(dados)
        if erro:
            registra_quarentena(topico, carga, erro)
            return None
        linha = monta_saude(dados)
        if linha:
            grava(conexao, SQL_SAUDE, linha)
            return "saude"
    return None


def ao_receber(cliente, _userdata, msg):
    conexao = cliente.conexao
    try:
        tipo = trata_mensagem(conexao, msg.topic, msg.payload)
    except psycopg.Error as e:
        # Não derruba o processo: o systemd reiniciaria e perderíamos a fila
        # do broker. Erro de banco é registrado e a próxima mensagem tenta.
        _estado["erros"] += 1
        conexao.rollback()
        print(f"[ingestor] erro de banco: {e}", flush=True)
        return
    if tipo:
        _estado[tipo] += 1


def ao_conectar(cliente, _userdata, _flags, rc, _props=None):
    print(f"[ingestor] MQTT conectado (rc={rc})", flush=True)
    cliente.subscribe("sentinela/#", qos=1)


# ---------------------------------------------------------------- principal --

def parse_args():
    ap = argparse.ArgumentParser(description="Sentinela — ingestor MQTT -> banco")
    ap.add_argument("--broker", default=os.environ.get("MQTT_HOST", "localhost"))
    ap.add_argument("--porta-mqtt", dest="porta_mqtt", type=int,
                    default=int(os.environ.get("MQTT_PORT", "1883")))
    ap.add_argument("--banco-host", dest="banco_host",
                    default=os.environ.get("POSTGRES_HOST", "localhost"))
    ap.add_argument("--banco-porta", dest="banco_porta", type=int,
                    default=int(os.environ.get("POSTGRES_PORT", "5432")))
    ap.add_argument("--intervalo-relato", dest="relato", type=float, default=60.0)
    return ap.parse_args()


def conecta_banco(args):
    senha = os.environ.get("POSTGRES_PASSWORD")
    if not senha:
        sys.exit("POSTGRES_PASSWORD ausente — defina em backend/.env")
    return psycopg.connect(
        host=args.banco_host, port=args.banco_porta,
        dbname=os.environ.get("POSTGRES_DB", "sentinela"),
        user=os.environ.get("POSTGRES_USER", "sentinela"),
        password=senha, connect_timeout=10, autocommit=False)


def main():
    carrega_env(RAIZ / ".env")
    args = parse_args()
    signal.signal(signal.SIGINT, _sinal)
    signal.signal(signal.SIGTERM, _sinal)

    conexao = conecta_banco(args)
    print(f"[ingestor] banco conectado: {args.banco_host}:{args.banco_porta}",
          flush=True)

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, client_id="ingestor")
    cliente.conexao = conexao
    cliente.on_connect = ao_conectar
    cliente.on_message = ao_receber
    cliente.reconnect_delay_set(min_delay=1, max_delay=30)
    cliente.connect_async(args.broker, args.porta_mqtt, keepalive=30)
    cliente.loop_start()

    proximo = 0.0
    try:
        while not _encerrar:
            if time.time() >= proximo:
                print(f"[ingestor] enlace={_estado['enlace']} "
                      f"saude={_estado['saude']} erros={_estado['erros']} "
                      f"quarentena={_estado['quarentena']} "
                      f"ultimo_seq={_estado['ultimo_seq']}", flush=True)
                proximo = time.time() + args.relato
            time.sleep(0.5)
    finally:
        cliente.loop_stop()
        conexao.close()
        print(f"[ingestor] encerrado — {_estado['enlace']} enlaces gravados",
              flush=True)


if __name__ == "__main__":
    main()
