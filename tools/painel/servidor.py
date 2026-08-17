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

Autoria: Luiz Matheus Marassi de Paula
"""

import argparse
import json
import mimetypes
import os
import sys
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

import banco
import coletor
import telemetria

ESTATICOS = Path(__file__).resolve().parent / "static"

# Pasta das Atalaias (comissionamento.py escreve, o painel só lê). Mesmo
# padrão de `backend/comissionamento.py` — não duplicar o caminho ao mudar.
MEDIA = Path(os.environ.get("SENTINELA_MEDIA",
                            "/DATA/Runtime/Sentinela-Media/Atalaias"))

# Só o que o laudo e o mapa precisam exibir. Lista branca, não lista negra:
# a pasta da Atalaia guarda ART e checklist assinado, documento de terceiro
# que não tem por que sair por HTTP sem autenticação.
MEDIA_EXTENSOES = {".jpg", ".jpeg", ".png", ".webp"}


def operacao():
    """Retrato auditável da cadeia acessível ao processo do painel.

    Não consulta systemd nem Docker: ausência dessa observação precisa
    aparecer como limitação, nunca ser convertida em estado de serviço.
    """
    tel = telemetria.estado()
    db = banco.operacao()
    return {
        "gerado_em": datetime.now(timezone.utc).isoformat(),
        "painel": {
            "classificacao": "OBSERVADO",
            "disponivel": True,
            "evidencia": "esta resposta HTTP foi produzida pelo painel",
        },
        "mqtt": {
            "classificacao": "OBSERVADO",
            "conectado": bool(tel.get("ligacao", {}).get("conectado")),
            "broker": tel.get("ligacao", {}).get("broker"),
            "desde_epoch": tel.get("ligacao", {}).get("desde"),
            "erro": tel.get("ligacao", {}).get("erro"),
            "amostras_memoria": tel.get("amostras", 0),
            "ultima_amostra_idade_s": tel.get("janela", {}).get("idade_ultima_s"),
        },
        "banco": db,
        "limitacoes": [
            "O painel não observa diretamente o estado de systemd ou Docker.",
            "A atividade do ingestor só pode ser inferida pelo último registro persistido.",
            "A janela MQTT existe apenas na memória e reinicia com o painel.",
            "Não há identidade institucional ou RBAC implementados.",
        ],
    }

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
    "/api/operacao": lambda q: operacao(),
    "/api/fontes-externas": lambda q: banco.fontes_externas(),
    "/api/fontes-observacoes": lambda q: banco.fontes_observacoes(),
    "/api/fontes-camadas": lambda q: banco.fontes_camadas(),

    # Leem o banco (backend/). Degradam sozinhas se o PostgreSQL estiver fora
    # do ar — devolvem estrutura vazia com o motivo em `erro`, para a aba
    # dizer que está sem dado em vez de o painel inteiro cair.
    "/api/sensor": lambda q: banco.sensor(),
    "/api/frota-saude": lambda q: banco.frota_saude(),
    "/api/gis/atalaias": lambda q: banco.gis_atalaias(),
    "/api/gis/suscetibilidade": lambda q: banco.gis_suscetibilidade(),
    "/api/gis/estacoes": lambda q: banco.gis_estacoes(),
    "/api/gis/fontes-contexto": lambda q: banco.gis_fontes_contexto(),
    "/api/gis/recorte-piloto": lambda q: banco.recorte_piloto(),
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
        if rota.path.startswith("/media/"):
            return self._responde_midia(rota.path[len("/media/"):])
        if not rota.path.startswith("/api/"):
            return super().do_GET()
        self._responde_api(rota)

    def _responde_midia(self, relativo):
        """Serve a foto oficial da Atalaia a partir da pasta de mídia.

        A pasta fica fora da raiz de estáticos de propósito: ela é dado
        operacional, não código, e vive no volume do homeserver. Por isso o
        caminho é resolvido e conferido contra a raiz — `..` no caminho não
        pode virar leitura de arquivo arbitrário do servidor.
        """
        try:
            alvo = (MEDIA / unquote(relativo)).resolve()
            alvo.relative_to(MEDIA.resolve())
        except (ValueError, OSError):
            return self._json({"erro": "caminho fora da pasta de mídia"}, 403)
        if alvo.suffix.lower() not in MEDIA_EXTENSOES or not alvo.is_file():
            return self._json({"erro": "mídia não encontrada"}, 404)
        dados = alvo.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type",
                         mimetypes.guess_type(alvo.name)[0] or "image/jpeg")
        self.send_header("Content-Length", str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_POST(self):
        """Recepção de comissionamento de Atalaia ou reconhecimento de alarmes."""
        rota = urlparse(self.path)
        if rota.path not in ("/api/comissionamento/cadastrar", "/api/alarme/reconhecer"):
            return self._json({"erro": "rota desconhecida"}, 404)
        try:
            tam = int(self.headers.get("Content-Length") or 0)
            if tam <= 0 or tam > 2_000_000:
                return self._json({"erro": "corpo ausente ou grande demais"}, 400)
            payload = json.loads(self.rfile.read(tam).decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as e:
            return self._json({"erro": f"JSON inválido: {e}"}, 400)

        if rota.path == "/api/comissionamento/cadastrar":
            self._comissiona(payload)
        elif rota.path == "/api/alarme/reconhecer":
            res = banco.reconhece_alarme(payload)
            status = 200 if "ok" in res else 400
            self._json(res, status)

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
