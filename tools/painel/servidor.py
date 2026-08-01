#!/usr/bin/env python3
"""Sentinela — painel de controle do projeto.

Servidor HTTP local que expõe o estado do projeto e serve a interface.
Só a biblioteca padrão, com uma exceção isolada: o monitoramento em tempo
real usa `paho-mqtt` (ver telemetria.py). Sem essa biblioteca — ou sem broker
no ar — todo o resto do painel continua funcionando normalmente.

Uso:
    python3 tools/painel/servidor.py            # http://localhost:8765
    python3 tools/painel/servidor.py --porta 9000
    python3 tools/painel/servidor.py --broker 192.168.15.73

O broker padrão é `localhost`, o que cobre os dois casos usuais: painel
rodando no próprio Raspberry Pi, ou no MacBook com um túnel SSH aberto
(`ssh -N -L 1883:127.0.0.1:1883 sentinelapi@<ip-do-rpi>`). O túnel evita expor
o broker sem autenticação na rede — ver gateway/README.md.

Autoria: Matheus Marassi
"""

import argparse
import json
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import banco
import coletor
import telemetria

ESTATICOS = Path(__file__).resolve().parent / "static"

ROTAS = {
    "/api/visao-geral": lambda q: coletor.visao_geral(),
    "/api/documentos": lambda q: coletor.documentos(),
    "/api/pendencias": lambda q: coletor.pendencias(),
    "/api/hardware": lambda q: coletor.hardware(),
    "/api/firmware": lambda q: coletor.firmware(),
    "/api/ensaios": lambda q: coletor.ensaios(),
    "/api/git": lambda q: coletor.git(),
    "/api/frota": lambda q: coletor.frota(),
    "/api/complexidade": lambda q: coletor.complexidade(),
    "/api/telemetria": lambda q: telemetria.estado(),

    # Leem o banco (backend/). Degradam sozinhas se o PostgreSQL estiver fora
    # do ar — devolvem estrutura vazia com o motivo em `erro`, para a aba
    # dizer que está sem dado em vez de o painel inteiro cair.
    "/api/sensor": lambda q: banco.sensor(),
    "/api/frota-saude": lambda q: banco.frota_saude(),
    "/api/gis/atalaias": lambda q: banco.gis_atalaias(),
    "/api/gis/suscetibilidade": lambda q: banco.gis_suscetibilidade(),
    "/api/gis/estacoes": lambda q: banco.gis_estacoes(),
    "/api/situacao": lambda q: banco.situacao(),
    "/api/comissionamento": lambda q: banco.comissionamento(),
    "/api/laudo": lambda q: banco.laudo(int((q.get("no") or ["1"])[0])),
    "/api/gis/ensaios": lambda q: banco.gis_ensaios(),
    "/api/historico": lambda q: banco.historico(
        int((q.get("no") or ["1"])[0]), int((q.get("horas") or ["72"])[0])),
}


class Manipulador(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ESTATICOS), **kwargs)

    def do_GET(self):
        rota = urlparse(self.path)
        if not rota.path.startswith("/api/"):
            return super().do_GET()
        self._responde_api(rota)

    def do_POST(self):
        """Só o comissionamento escreve. Corpo em JSON, não multipart: o
        módulo `cgi` saiu no Python 3.13 e escrever parser de multipart à mão
        no caminho mais crítico do sistema seria fragilidade gratuita. As
        fotos chegam pela pasta da Atalaia, que o gestor autônomo já vigia."""
        rota = urlparse(self.path)
        if rota.path != "/api/comissionamento/cadastrar":
            return self._json({"erro": "rota desconhecida"}, 404)
        try:
            tam = int(self.headers.get("Content-Length") or 0)
            if tam <= 0 or tam > 2_000_000:
                return self._json({"erro": "corpo ausente ou grande demais"}, 400)
            payload = json.loads(self.rfile.read(tam).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            return self._json({"erro": f"JSON inválido: {e}"}, 400)
        self._comissiona(payload)

    def _comissiona(self, payload):
        """Recusa de validação é 400 com o motivo — o técnico em campo precisa
        saber o que corrigir, não receber 500 genérico."""
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))
        try:
            import comissionamento
        except ImportError as e:
            return self._json({"erro": f"backend indisponível: {e}"}, 503)
        try:
            self._json(comissionamento.comissiona(
                payload, payload.get("foto_oficial")))
        except comissionamento.ComissionamentoInvalido as e:
            self._json({"erro": str(e), "recusado": True}, 400)
        except Exception as e:                          # noqa: BLE001
            self._json({"erro": str(e)}, 500)

    def _responde_api(self, rota):
        consulta = parse_qs(rota.query)
        if rota.path == "/api/documento":
            return self._responde_documento(consulta)
        funcao = ROTAS.get(rota.path)
        if funcao is None:
            return self._json({"erro": "rota desconhecida"}, 404)
        try:
            self._json(funcao(consulta))
        except Exception as e:                      # noqa: BLE001
            self._json({"erro": str(e)}, 500)

    def _responde_documento(self, consulta):
        rel = (consulta.get("path") or [""])[0]
        texto = coletor.conteudo_documento(rel)
        if texto is None:
            return self._json({"erro": "documento nao encontrado"}, 404)
        self._json({"path": rel, "conteudo": texto})

    def _json(self, dados, status=200):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()   # o cabeçalho de cache é adicionado em end_headers
        self.wfile.write(corpo)

    def end_headers(self):
        """Desliga o cache de estáticos: o painel é ferramenta de
        desenvolvimento e precisa refletir a edição no recarregamento."""
        self.send_header("Cache-Control", "no-store, must-revalidate")
        super().end_headers()

    def log_message(self, formato, *args):
        """Silencia o log de acesso — o terminal fica para mensagens úteis."""


def main():
    ap = argparse.ArgumentParser(description="Painel de controle do Sentinela")
    ap.add_argument("--porta", type=int, default=8765)
    ap.add_argument("--broker", default="localhost",
                    help="broker MQTT do monitoramento em tempo real")
    ap.add_argument("--porta-mqtt", dest="porta_mqtt", type=int, default=1883)
    args = ap.parse_args()

    telemetria.inicia(args.broker, args.porta_mqtt)

    servidor = ThreadingHTTPServer(("127.0.0.1", args.porta), Manipulador)
    print(f"Sentinela — painel em http://localhost:{args.porta}")
    print(f"telemetria: assinando {args.broker}:{args.porta_mqtt}")
    print("Ctrl+C encerra.")
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        print("\nencerrado")
    finally:
        servidor.server_close()


if __name__ == "__main__":
    main()
