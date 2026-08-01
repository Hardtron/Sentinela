#!/usr/bin/env python3
"""Testes locais da persistência da bridge e do contrato do ingestor."""

import importlib.util
import json
import sys
import tempfile
import types
from datetime import datetime, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]


def dependencias_falsas():
    """Permite testar contrato puro com o Python do sistema, sem venv."""
    if "paho.mqtt.client" not in sys.modules:
        cliente = types.ModuleType("paho.mqtt.client")
        cliente.MQTT_ERR_SUCCESS = 0
        paho = types.ModuleType("paho")
        mqtt = types.ModuleType("paho.mqtt")
        mqtt.client = cliente
        paho.mqtt = mqtt
        sys.modules.update({"paho": paho, "paho.mqtt": mqtt,
                            "paho.mqtt.client": cliente})
    if "psycopg" not in sys.modules:
        psycopg = types.ModuleType("psycopg")
        psycopg.Error = Exception
        sys.modules["psycopg"] = psycopg


def importa(nome, caminho):
    spec = importlib.util.spec_from_file_location(nome, caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


dependencias_falsas()
bridge = importa("bridge_teste", RAIZ / "gateway" / "bridge.py")
ingestor = importa("ingestor_teste", RAIZ / "backend" / "ingestor.py")


def verifica(condicao, mensagem):
    if not condicao:
        raise AssertionError(mensagem)


class InfoMQTT:
    rc = 0

    def __init__(self, confirmado):
        self.confirmado = confirmado
        self.esperou = False

    def wait_for_publish(self, timeout):
        self.esperou = timeout > 0

    def is_published(self):
        return self.confirmado


class ClienteMQTT:
    def __init__(self, confirmado):
        self.info = InfoMQTT(confirmado)

    def is_connected(self):
        return True

    def publish(self, *_args, **_kwargs):
        return self.info


class Cursor:
    def __init__(self):
        self.chamada = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros):
        self.chamada = (sql, parametros)


class Conexao:
    def __init__(self):
        self.cursor_falso = Cursor()
        self.confirmou = False

    def cursor(self):
        return self.cursor_falso

    def commit(self):
        self.confirmou = True


def testa_buffer(tmp):
    caminho = tmp / "buffer.jsonl"
    fila = [{"node_id": 1, "seq": 7}, {"node_id": 1, "seq": 8}]
    bridge.buffer_grava(caminho, fila)
    verifica(bridge.buffer_carrega(caminho) == fila, "ida e volta do buffer")
    verifica(not (tmp / ".buffer.jsonl.tmp").exists(), "temporário removido")

    caminho.write_text('{"node_id": 1}\nINVALIDO\n', encoding="utf-8")
    verifica(bridge.buffer_carrega(caminho) == [], "corrupção não vira fila válida")
    preservados = list(tmp.glob("buffer.jsonl.corrompido-*"))
    verifica(len(preservados) == 1, "buffer corrompido deve ser preservado")


def testa_qos():
    antigo = bridge.mqtt.MQTT_ERR_SUCCESS
    cliente = ClienteMQTT(True)
    verifica(bridge.publica(cliente, 1, {"seq": 1}), "PUBACK confirmado")
    verifica(cliente.info.esperou, "publicação deve aguardar confirmação")
    verifica(not bridge.publica(ClienteMQTT(False), 1, {"seq": 2}),
             "sem PUBACK não pode remover da fila")
    verifica(bridge.mqtt.MQTT_ERR_SUCCESS == antigo, "constante MQTT preservada")


def mensagem_valida():
    return {
        "recebido_em": datetime.now(timezone.utc).isoformat(),
        "node_id": 1, "bridge_id": "FAR-01", "seq": 4, "sf": 9,
        "rssi_dbm": -90.0, "snr_db": 7.0, "rssi_remoto_dbm": -91,
        "snr_remoto_db": 6, "enviados": 4, "recebidos": 4, "perdidos": 0,
    }


def testa_ingestor(tmp):
    con = Conexao()
    carga = json.dumps(mensagem_valida()).encode()
    verifica(ingestor.trata_mensagem(con, "sentinela/no/1/telemetria", carga)
             == "enlace", "mensagem válida gravada")
    verifica(con.confirmou, "gravação válida confirmada")

    invalida = mensagem_valida()
    invalida["recebidos"] = 5
    invalida["enviados"] = 4
    caminho = tmp / "quarentena.jsonl"
    antigo = ingestor.registra_quarentena
    ingestor.registra_quarentena = lambda t, c, m: antigo(t, c, m, caminho)
    try:
        verifica(ingestor.trata_mensagem(
            con, "sentinela/no/1/telemetria", json.dumps(invalida).encode()) is None,
            "mensagem inválida recusada")
    finally:
        ingestor.registra_quarentena = antigo
    registro = json.loads(caminho.read_text(encoding="utf-8"))
    verifica("recebidos maior" in registro["motivo"], "motivo rastreável")


def testa_migracao():
    sql = (RAIZ / "backend" / "migracoes" /
           "010_rastreabilidade_parametros.sql").read_text(encoding="utf-8")
    for termo in ("criterio_comissionamento_historico", "criterio_snapshot",
                  "evidencia_versao", "evidencia_proveniencia"):
        verifica(termo in sql, f"migração sem {termo}")


def main():
    with tempfile.TemporaryDirectory() as pasta:
        tmp = Path(pasta)
        testa_buffer(tmp)
        testa_qos()
        testa_ingestor(tmp)
    testa_migracao()
    print("Fluxo robusto: 13 verificações, 0 falha(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
