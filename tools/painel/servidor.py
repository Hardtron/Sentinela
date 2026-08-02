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
import hashlib
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
                            "/DATA/Projects/Sentinela-Media/Atalaias"))

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


def _seleciona_campos(leituras, campos):
    """Projeta leituras sem criar interpretação ou valor derivado."""
    return [{campo: leitura.get(campo) for campo in campos}
            for leitura in leituras]


def _sensores_invalidos(leituras):
    invalidos = []
    campos_validade = (
        ("chuva", "chuva_valida"),
        ("inclinação", "inclin_valida"),
        ("umidade do solo", "solo_valido"),
    )
    for leitura in leituras:
        campos = [nome for nome, chave in campos_validade
                  if leitura.get(chave) is False]
        if campos:
            invalidos.append({
                "node_id": leitura.get("node_id"),
                "placa": leitura.get("placa"),
                "campos_invalidos": campos,
                "recebido_em": leitura.get("recebido_em"),
            })
    return invalidos


def evidencia_contextual():
    """Compõe um retrato exportável das evidências já disponíveis.

    O pacote deliberadamente não calcula nível de risco: ele preserva as
    categorias de observação (pontual, grade, radar/satélite e sensor local),
    os códigos de qualidade e as ausências. O hash protege somente o JSON
    devolvido nesta consulta; persistência/cadeia de custódia continuam sendo
    responsabilidade do registro de alarme ou do arquivo exportado (RC-10).
    """
    gerado_em = datetime.now(timezone.utc).isoformat()
    fontes = banco.fontes_externas()
    observacoes = banco.fontes_observacoes()
    camadas = banco.fontes_camadas()
    sensores = banco.sensor()
    oper = operacao()

    leituras = sensores.get("leituras") or []
    invalidos = _sensores_invalidos(leituras)

    pacote = {
        "esquema": "sentinela.evidencia_contextual.v1",
        "gerado_em": gerado_em,
        "classificacao": "INFORMATIVO",
        "decisao": {
            "nivel_risco": None,
            "regra_automatica_aplicada": False,
            "mensagem": (
                "Evidências para apoio técnico; não constitui alerta "
                "geotécnico nem autoriza ação autônoma."),
        },
        "associacao": {
            "metodo": "camadas independentes, reunidas por tempo e proveniência",
            "soma_entre_provedores": False,
            "limiar_geotecnico": None,
        },
        "camadas": {
            "gatilho_meteorologico": {
                "observacoes_pontuais": observacoes.get("observacoes") or [],
                "produtos_grade_radar_satelite": camadas.get("camadas") or [],
                "escopo": (
                    "Chuva pontual, estimativa em grade e imagens permanecem "
                    "grandezas distintas; divergência não é resolvida por média."),
            },
            "estado_hidrologico_local": {
                "leituras": _seleciona_campos(leituras, (
                    "node_id", "placa", "medido_em", "recebido_em",
                    "umidade_solo", "solo_valido", "fonte")),
                "escopo": "Disponível somente quando o sensor local medir e declarar validade.",
            },
            "resposta_mecanica_local": {
                "leituras": _seleciona_campos(leituras, (
                    "node_id", "placa", "medido_em", "recebido_em",
                    "pitch_graus", "roll_graus", "inclin_valida", "fonte")),
                "escopo": (
                    "Leitura isolada não caracteriza movimento; baseline, "
                    "persistência e corroboração ainda exigem validação local."),
            },
            "qualidade_operacional": {
                "cadeia": oper,
                "sensores_invalidos": invalidos,
                "fontes": fontes.get("fontes") or [],
                "quarentena_fontes_7d": fontes.get("quarentena_7d") or {},
            },
        },
        "ausencias_e_limitacoes": [
            "Quadros de sensor ainda não percorrem a esteira MQTT → banco em produção.",
            "Não existe limiar geotécnico local validado para o piloto.",
            "IMERG é estimativa em grade; REDEMET permanece contexto visual.",
            "O PED observado não fornece coordenadas no payload usado pelo projeto.",
            "Suscetibilidade, exposição e protocolo institucional não estão completos.",
        ],
        "erros_consulta": {
            "fontes": fontes.get("erro"),
            "observacoes": observacoes.get("erro"),
            "camadas": camadas.get("erro"),
            "sensores": sensores.get("erro"),
            "operacao": oper.get("banco", {}).get("erro"),
        },
    }
    canonico = json.dumps(
        pacote, ensure_ascii=False, sort_keys=True,
        separators=(",", ":")).encode("utf-8")
    pacote["integridade"] = {
        "algoritmo": "SHA-256",
        "sha256": hashlib.sha256(canonico).hexdigest(),
        "escopo": "conteúdo deste pacote, antes do campo integridade; não persistido pelo painel",
    }
    return pacote

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
    "/api/evidencia-contextual": lambda q: evidencia_contextual(),
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
