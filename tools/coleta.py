#!/usr/bin/env python3
"""Sentinela — coleta do ensaio de campo.

Captura a saída serial do nó PINGER, carimba cada amostra com a hora local e
grava em disco. Mantém estatísticas por ponto de medição e mostra o veredito ao
vivo, aplicando os mesmos critérios do firmware.

O que este script resolve: as estatísticas do firmware vivem em RAM e somem no
primeiro reinício ou ao desconectar a placa. Aqui elas viram arquivo.

O carimbo de hora não é detalhe — é o que permite casar cada ponto com as fotos
do celular depois, pelo EXIF (ver georreferenciar.py).

Uso:
    python3 coleta.py --porta /dev/cu.usbserial-0001 --ensaio 02

Encerrar com Ctrl+C. O resumo é gravado a cada ponto, então uma queda de energia
no meio do ensaio não leva junto o que já foi medido.

Autoria: Matheus Marassi
"""

import argparse
import csv
import re
import signal
import sys
from datetime import datetime
from pathlib import Path

try:
    import serial
except ImportError:
    sys.exit("pyserial nao encontrado. Instale com: pip install pyserial")

# Critérios de aprovação — espelham firmware/src/ui_dev.h.
MIN_AMOSTRAS = 20
MARGEM_BOA_DB = 20
MARGEM_MIN_DB = 10
PERDA_MAX_PCT = 5.0
ASSIMETRIA_MAX_DB = 10

SENSIBILIDADE = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}

RE_PONTO = re.compile(r"=+\s*PONTO\s+(\d+)\s*=+")
RE_SF = re.compile(r"sf=(\d+)")

_encerrar = False


def _sinal(_signum, _frame):
    global _encerrar
    _encerrar = True


class Ponto:
    """Acumula as amostras de um ponto de medição."""

    def __init__(self, numero, inicio):
        self.numero = numero
        self.inicio = inicio
        self.fim = inicio
        self.enviados = 0
        self.recebidos = 0
        self.rssi = []
        self.snr = []
        self.rssi_remoto = []

    def amostra(self, quando, rssi, snr, rssi_rem, enviados, recebidos):
        self.fim = quando
        self.enviados = enviados
        self.recebidos = recebidos
        if rssi is not None:
            self.rssi.append(rssi)
            self.snr.append(snr)
        if rssi_rem is not None:
            self.rssi_remoto.append(rssi_rem)

    @property
    def perda_pct(self):
        if self.enviados == 0:
            return 0.0
        return 100.0 * (self.enviados - self.recebidos) / self.enviados

    def margem(self, sf):
        if not self.rssi:
            return None
        media = sum(self.rssi) / len(self.rssi)
        return media - SENSIBILIDADE.get(sf, -129.0)

    def assimetria(self):
        if not self.rssi or not self.rssi_remoto:
            return None
        return abs(
            sum(self.rssi) / len(self.rssi)
            - sum(self.rssi_remoto) / len(self.rssi_remoto)
        )

    def veredito(self, sf):
        """Mesma ordem de avaliação do firmware: a primeira falha decide."""
        if self.recebidos < MIN_AMOSTRAS:
            return "COLETANDO", f"{self.recebidos}/{MIN_AMOSTRAS} amostras"
        if self.perda_pct > PERDA_MAX_PCT:
            return "REPROVADO", f"perda {self.perda_pct:.0f}%"
        m = self.margem(sf)
        if m is None:
            return "COLETANDO", "sem amostras de RSSI"
        if m < MARGEM_MIN_DB:
            return "REPROVADO", f"margem {m:.0f} dB"
        if m < MARGEM_BOA_DB:
            return "LIMITE", f"margem {m:.0f} dB"
        a = self.assimetria()
        if a is not None and a > ASSIMETRIA_MAX_DB:
            return "LIMITE", f"assimetria {a:.0f} dB"
        return "APROVADO", f"margem {m:.0f} dB"

    def resumo(self, sf):
        v, motivo = self.veredito(sf)
        return {
            "ponto": self.numero,
            "inicio": self.inicio.isoformat(timespec="seconds"),
            "fim": self.fim.isoformat(timespec="seconds"),
            "enviados": self.enviados,
            "recebidos": self.recebidos,
            "perda_pct": round(self.perda_pct, 1),
            "rssi_med": round(sum(self.rssi) / len(self.rssi), 1) if self.rssi else "",
            "rssi_min": min(self.rssi) if self.rssi else "",
            "rssi_max": max(self.rssi) if self.rssi else "",
            "snr_med": round(sum(self.snr) / len(self.snr), 1) if self.snr else "",
            "margem_db": round(self.margem(sf), 1) if self.margem(sf) is not None else "",
            "assimetria_db": (
                round(self.assimetria(), 1) if self.assimetria() is not None else ""
            ),
            "veredito": v,
            "motivo": motivo,
        }


def grava_resumo(caminho, pontos, sf):
    campos = [
        "ponto", "inicio", "fim", "enviados", "recebidos", "perda_pct",
        "rssi_med", "rssi_min", "rssi_max", "snr_med", "margem_db",
        "assimetria_db", "veredito", "motivo",
    ]
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        for p in pontos:
            w.writerow(p.resumo(sf))


def main():
    ap = argparse.ArgumentParser(description="Coleta do ensaio de campo do Sentinela")
    ap.add_argument("--porta", default="/dev/cu.usbserial-0001")
    ap.add_argument("--baud", type=int, default=115200)
    ap.add_argument("--ensaio", default="00", help="identificador do ensaio, ex: 02")
    ap.add_argument("--saida", default="dados", help="pasta de saida")
    args = ap.parse_args()

    pasta = Path(args.saida)
    pasta.mkdir(parents=True, exist_ok=True)
    carimbo = datetime.now().strftime("%Y%m%d-%H%M")
    base = pasta / f"ensaio{args.ensaio}-{carimbo}"
    f_bruto = base.with_name(base.name + "-amostras.csv")
    f_resumo = base.with_name(base.name + "-pontos.csv")

    signal.signal(signal.SIGINT, _sinal)

    # O ESP32 reinicia quando DTR/RTS são acionados na abertura da porta — e um
    # reinício apaga o ponto em andamento. Configurar as linhas ANTES de abrir
    # evita isso: com Serial() sem porta, os estados valem já na abertura.
    try:
        porta = serial.Serial()
        porta.port = args.porta
        porta.baudrate = args.baud
        porta.timeout = 0.5
        porta.dtr = False
        porta.rts = False
        porta.open()
    except Exception as e:
        sys.exit(f"nao foi possivel abrir {args.porta}: {e}")

    print(f"gravando em {f_bruto}")
    print(f"resumo em   {f_resumo}")
    print("toque longo no botao PRG marca um novo ponto. Ctrl+C encerra.\n")

    sf = 9
    pontos = []
    atual = Ponto(0, datetime.now())
    pontos.append(atual)

    bruto = open(f_bruto, "w", newline="", encoding="utf-8")
    wb = csv.writer(bruto)
    wb.writerow(["hora", "ponto", "seq", "rssi_dbm", "snr_db",
                 "rssi_remoto_dbm", "snr_remoto_db", "enviados", "recebidos"])

    ultimo_veredito = None
    try:
        while not _encerrar:
            linha = porta.readline().decode("utf-8", "replace").strip()
            if not linha:
                continue
            agora = datetime.now()

            if linha.startswith("#"):
                m = RE_SF.search(linha)
                if m:
                    sf = int(m.group(1))
                    print(f"[config] SF{sf}, sensibilidade {SENSIBILIDADE[sf]} dBm")
                m = RE_PONTO.search(linha)
                if m:
                    grava_resumo(f_resumo, pontos, sf)
                    atual = Ponto(int(m.group(1)), agora)
                    pontos.append(atual)
                    ultimo_veredito = None
                    print(f"\n=== PONTO {atual.numero} iniciado ===")
                continue

            campos = linha.split(",")
            if len(campos) != 7:
                continue
            try:
                seq = int(campos[0])
                rssi = float(campos[1]) if campos[1] else None
                snr = float(campos[2]) if campos[2] else None
                rssi_rem = int(campos[3]) if campos[3] else None
                snr_rem = int(campos[4]) if campos[4] else None
                enviados = int(campos[5])
                recebidos = int(campos[6])
            except ValueError:
                continue

            atual.amostra(agora, rssi, snr, rssi_rem, enviados, recebidos)
            wb.writerow([agora.isoformat(timespec="seconds"), atual.numero, seq,
                         campos[1], campos[2], campos[3], campos[4],
                         enviados, recebidos])
            bruto.flush()

            v, motivo = atual.veredito(sf)
            rssi_txt = f"{rssi:6.1f}" if rssi is not None else "  ----"
            print(f"P{atual.numero} #{seq:<4} rssi {rssi_txt} dBm  "
                  f"perda {atual.perda_pct:4.0f}%  {v} ({motivo})")
            if v != ultimo_veredito:
                if v == "APROVADO":
                    print("   >>> ponto APROVADO")
                elif v == "REPROVADO":
                    print("   >>> ponto REPROVADO — procure outra posicao")
                ultimo_veredito = v
    finally:
        bruto.close()
        porta.close()
        grava_resumo(f_resumo, pontos, sf)

    print("\n\n=== RESUMO DO ENSAIO ===")
    for p in pontos:
        if p.enviados == 0:
            continue
        r = p.resumo(sf)
        print(f"P{r['ponto']:<3} {r['recebidos']:>4}/{r['enviados']:<4} pac  "
              f"perda {r['perda_pct']:>5}%  rssi {r['rssi_med']:>7}  "
              f"margem {r['margem_db']:>6}  {r['veredito']} ({r['motivo']})")
    print(f"\narquivos: {f_bruto}\n          {f_resumo}")


if __name__ == "__main__":
    main()
