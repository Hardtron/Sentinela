#!/usr/bin/env python3
"""Gerencia Ethernet preferencial e Wi-Fi de contingência no Farol.

O Wi-Fi só é desligado depois de o caminho Ethernet alcançar o Home Server
por várias amostras consecutivas. Se o cabo sair ou o caminho deixar de
funcionar, o rádio volta, usa a conexão já provisionada no NetworkManager e,
quando necessário, afasta uma Ethernet com carrier mas sem conectividade.
"""

from __future__ import annotations

import os
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path


INTERVALO = float(os.environ.get("SENTINELA_REDE_INTERVALO", "2"))
ALVO = os.environ.get("SENTINELA_REDE_ALVO", "192.168.15.66")
ETHERNET = os.environ.get("SENTINELA_REDE_ETHERNET", "eth0")
WIFI = os.environ.get("SENTINELA_REDE_WIFI", "wlan0")
RETESTE_ETHERNET = float(os.environ.get("SENTINELA_REDE_RETESTE", "30"))
CONEXAO_ETHERNET = os.environ.get("SENTINELA_REDE_CONEXAO_ETH", "netplan-eth0")
CONEXAO_WIFI = os.environ.get("SENTINELA_REDE_CONEXAO_WIFI",
                             "netplan-wlan0-Nautila")


def comando(*args, timeout=12):
    return subprocess.run(args, capture_output=True, text=True, timeout=timeout,
                          check=False)


def carrier(interface=ETHERNET):
    caminho = Path("/sys/class/net") / interface / "carrier"
    try:
        return caminho.read_text(encoding="ascii").strip() == "1"
    except (FileNotFoundError, OSError):
        return False


def tem_ipv4(interface):
    resultado = comando("ip", "-4", "-o", "addr", "show", "dev", interface)
    return resultado.returncode == 0 and " inet " in resultado.stdout


def tem_rota_padrao(interface):
    resultado = comando("ip", "-4", "route", "show", "default", "dev",
                        interface)
    return resultado.returncode == 0 and bool(resultado.stdout.strip())


def alcança_alvo(interface=ETHERNET, alvo=ALVO):
    resultado = comando("ping", "-I", interface, "-c", "1", "-W", "1", alvo,
                        timeout=3)
    return resultado.returncode == 0


def ethernet_saudavel():
    return (carrier() and tem_ipv4(ETHERNET) and tem_rota_padrao(ETHERNET)
            and alcança_alvo())


def wifi_conectado():
    resultado = comando("nmcli", "-t", "-f", "DEVICE,STATE", "device",
                        "status")
    return any(linha == f"{WIFI}:connected"
               for linha in resultado.stdout.splitlines())


def wifi_habilitado():
    resultado = comando("nmcli", "-t", "-f", "WIFI", "general")
    return resultado.returncode == 0 and resultado.stdout.strip() == "enabled"


def espera_wifi(limite=8):
    fim = time.monotonic() + limite
    while time.monotonic() < fim:
        if wifi_conectado():
            return True
        time.sleep(0.5)
    return False


def liga_wifi():
    radio_ativado = False
    if not wifi_habilitado():
        comando("nmcli", "--wait", "5", "radio", "wifi", "on")
        radio_ativado = True
    if radio_ativado and espera_wifi():
        return
    if not wifi_conectado():
        comando("nmcli", "--wait", "15", "connection", "up", CONEXAO_WIFI,
                timeout=20)


def desliga_wifi():
    if wifi_habilitado():
        comando("nmcli", "--wait", "5", "radio", "wifi", "off")


def conecta_ethernet():
    comando("nmcli", "--wait", "15", "device", "connect", ETHERNET,
            timeout=20)


def configura_preferencia():
    ajustes = ((CONEXAO_ETHERNET, "100", "100"),
               (CONEXAO_WIFI, "50", "600"))
    for conexao, prioridade, metrica in ajustes:
        comando("nmcli", "connection", "modify", conexao,
                "connection.autoconnect-priority", prioridade,
                "ipv4.route-metric", metrica,
                "ipv6.route-metric", metrica)


def desconecta_ethernet_inoperante():
    if (wifi_conectado() and carrier() and tem_ipv4(ETHERNET)
            and not alcança_alvo()):
        comando("nmcli", "--wait", "5", "device", "disconnect", ETHERNET)


@dataclass
class EstadoFailover:
    sucessos_exigidos: int = 3
    falhas_exigidas: int = 2
    sucessos: int = 0
    falhas: int = 0
    modo: str | None = None

    def observa(self, saudavel):
        if saudavel:
            self.sucessos += 1
            self.falhas = 0
            if self.sucessos >= self.sucessos_exigidos and self.modo != "CABO":
                self.modo = "CABO"
                return "CABO"
        else:
            self.falhas += 1
            self.sucessos = 0
            if self.falhas >= self.falhas_exigidas and self.modo != "WIFI":
                self.modo = "WIFI"
                return "WIFI"
        return None


def anuncia(texto):
    print(f"[rede] {texto}", flush=True)


def aplica(modo):
    if modo == "CABO":
        desliga_wifi()
        anuncia("Ethernet estável; Wi-Fi desabilitado")
    elif modo == "WIFI":
        liga_wifi()
        desconecta_ethernet_inoperante()
        anuncia("Ethernet indisponível; Wi-Fi habilitado")


def main():
    estado = EstadoFailover()
    proximo_reteste = 0.0
    configura_preferencia()
    anuncia(f"iniciado; alvo={ALVO} ethernet={ETHERNET} wifi={WIFI}")
    while True:
        saudavel = ethernet_saudavel()
        transicao = estado.observa(saudavel)
        aplica(transicao)
        if transicao == "WIFI":
            proximo_reteste = time.monotonic() + RETESTE_ETHERNET
        if estado.modo == "WIFI":
            liga_wifi()
            agora = time.monotonic()
            if carrier() and not tem_ipv4(ETHERNET) and agora >= proximo_reteste:
                conecta_ethernet()
                proximo_reteste = agora + RETESTE_ETHERNET
        time.sleep(INTERVALO)


if __name__ == "__main__":
    main()
