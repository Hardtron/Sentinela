#!/usr/bin/env python3
"""Contratos locais do failover de rede, sem alterar interfaces reais."""

import importlib.util
import sys
from pathlib import Path


RAIZ = Path(__file__).resolve().parents[1]


def importa():
    caminho = RAIZ / "gateway" / "rede_failover.py"
    spec = importlib.util.spec_from_file_location("rede_failover_teste", caminho)
    modulo = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modulo
    spec.loader.exec_module(modulo)
    return modulo


def verifica(condicao, mensagem):
    if not condicao:
        raise AssertionError(mensagem)


def testa_histerese(rede):
    estado = rede.EstadoFailover(sucessos_exigidos=3, falhas_exigidas=2)
    verifica(estado.observa(True) is None, "não troca no primeiro sucesso")
    verifica(estado.observa(True) is None, "não troca no segundo sucesso")
    verifica(estado.observa(True) == "CABO", "cabo exige estabilidade")
    verifica(estado.observa(False) is None, "não cai no primeiro ruído")
    verifica(estado.observa(False) == "WIFI", "duas falhas acionam Wi-Fi")
    verifica(estado.observa(False) is None, "não repete a mesma transição")
    verifica(estado.observa(True) is None, "retorno também tem histerese")
    verifica(estado.observa(True) is None, "retorno aguarda três sucessos")
    verifica(estado.observa(True) == "CABO", "Ethernet recuperada volta")


def testa_artefatos():
    unidade = (RAIZ / "gateway" / "sentinela-rede.service").read_text()
    broker = (RAIZ / "gateway" / "mosquitto-sentinela.conf").read_text()
    tunel = (RAIZ / "backend" / "sentinela-tunel-mqtt.service").read_text()
    ingestor = (RAIZ / "backend" / "ingestor.py").read_text()
    verifica("NetworkManager.service" in unidade, "unidade depende da rede")
    verifica("SENTINELA_REDE_CONEXAO_ETH" in unidade, "perfil Ethernet explícito")
    verifica("ipv4.route-metric" in (RAIZ / "gateway" / "rede_failover.py").read_text(),
             "preferência deve ser reaplicada")
    verifica("time.monotonic() + RETESTE_ETHERNET" in
             (RAIZ / "gateway" / "rede_failover.py").read_text(),
             "reteste não pode religar Ethernet imediatamente")
    verifica("max_queued_bytes" in broker, "fila MQTT precisa de teto")
    verifica("HostKeyAlias=sentinela-rpi" in tunel, "host key deve ser estável")
    verifica("sentinelapi.local" in tunel, "túnel não pode depender do IP")
    verifica("clean_session=False" in ingestor, "sessão MQTT deve ser durável")


def main():
    rede = importa()
    testa_histerese(rede)
    testa_artefatos()
    print("Failover de rede: 17 verificações, 0 falha(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
