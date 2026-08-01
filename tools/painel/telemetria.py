#!/usr/bin/env python3
"""Sentinela — assinante MQTT que alimenta o monitoramento em tempo real.

Mantém em memória uma janela deslizante da telemetria publicada pela bridge
(`gateway/bridge.py`) e devolve, já calculado, o que o painel precisa para
avaliar a rede: margem de enlace, assimetria, perda e silêncio.

**Por que os cálculos ficam aqui e não no navegador:** os limiares são regra do
projeto (espelham `firmware/src/ui_dev.h`), não preferência de visualização. Se
o critério de "enlace saudável" mudar, ele muda num lugar só.

Este é o único módulo do painel que depende de biblioteca externa
(`paho-mqtt`). A dependência é **opcional por construção**: sem ela, ou sem
broker no ar, o painel inteiro continua funcionando e a aba de monitoramento
explica o que falta em vez de quebrar.

Autoria: Matheus Marassi
"""

import json
import threading
import time
from datetime import datetime, timezone
from collections import deque

try:
    import paho.mqtt.client as mqtt
except ImportError:                                   # pragma: no cover
    mqtt = None

# --- limiares: espelham firmware/src/ui_dev.h -------------------------------
# Sensibilidade do SX1276 em SF9/125 kHz (uiSensitivityDbm). A margem de
# enlace é medida contra este piso — é o número que diz quanta folga existe
# antes de o enlace simplesmente sumir.
SENSIBILIDADE_DBM = -129.0
MARGEM_BOA_DB = 20        # PONTO_MARGEM_BOA_DB — aguenta chuva e vegetação
MARGEM_MIN_DB = 10        # PONTO_MARGEM_MIN_DB — abaixo disso cai na 1ª chuva
ASSIMETRIA_MAX_DB = 10    # PONTO_ASSIMETRIA_MAX_DB

# O PINGER envia a cada 3 s e espera pong por 1,5 s (main.cpp). Três ciclos
# sem nada é a mesma régua do alarme "Atalaia silenciosa" (MANUTENCAO.md §5):
# silêncio prolongado é falha, não flutuação.
SILENCIO_S = 15.0

# ~30 min de histórico a 3 s por pacote. Suficiente para ver tendência sem
# virar consumo de memória que ninguém vigia.
HISTORICO = 600

_trava = threading.Lock()
_amostras = deque(maxlen=HISTORICO)
_nos = {}
_bridges = {}
_ligacao = {"conectado": False, "broker": None, "erro": None, "desde": None}


# ------------------------------------------------------------------ coleta --

def _perdidos_desde(anterior, atual):
    """Buraco na sequência = ping que não chegou ao gateway.

    A bridge só imprime linha quando recebe; então o que falta na contagem de
    `seq` é exatamente o que se perdeu no ar, sem precisar de outro contador.
    """
    if anterior is None:
        return 0
    a, b = anterior.get("seq"), atual.get("seq")
    if a is None or b is None or b <= a:
        return 0
    return b - a - 1


def _registra_telemetria(dados):
    agora = time.time()
    with _trava:
        anterior = _amostras[-1] if _amostras else None
        dados["t"] = agora
        dados["perdidos"] = _perdidos_desde(anterior, dados)
        _amostras.append(dados)

        no = _nos.setdefault(dados.get("node_id"),
                             {"pacotes": 0, "perdidos": 0})
        no["pacotes"] += 1
        no["perdidos"] += dados["perdidos"]
        no["ultimo_t"] = agora
        no["ultimo_seq"] = dados.get("seq")


def _registra_saude(dados):
    ident = dados.get("bridge_id")
    if not ident:
        return
    with _trava:
        dados["t"] = time.time()
        _bridges[ident] = dados


def _ao_receber(_cliente, _userdata, msg):
    try:
        dados = json.loads(msg.payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return
    if msg.topic.endswith("/telemetria"):
        _registra_telemetria(dados)
    elif msg.topic.endswith("/saude"):
        _registra_saude(dados)


def _ao_conectar(cliente, _userdata, _flags, _rc, _props=None):
    _ligacao["conectado"] = True
    _ligacao["erro"] = None
    _ligacao["desde"] = time.time()
    cliente.subscribe("sentinela/#", qos=0)


def _ao_desconectar(_cliente, _userdata, *_resto):
    _ligacao["conectado"] = False


def inicia(broker, porta=1883):
    """Liga o assinante em segundo plano. Nunca levanta exceção: o painel tem
    de subir mesmo sem broker — a aba de monitoramento é que reporta a falta."""
    _ligacao["broker"] = f"{broker}:{porta}"
    if mqtt is None:
        _ligacao["erro"] = "paho-mqtt nao instalado"
        return None

    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2,
                          client_id=f"painel-{int(time.time())}")
    cliente.on_connect = _ao_conectar
    cliente.on_disconnect = _ao_desconectar
    cliente.on_message = _ao_receber
    cliente.reconnect_delay_set(min_delay=1, max_delay=15)
    try:
        cliente.connect_async(broker, porta, keepalive=30)
        cliente.loop_start()
    except (OSError, ValueError) as e:                # pragma: no cover
        _ligacao["erro"] = str(e)
    return cliente


# --------------------------------------------------------------- estatística --

def _estat(valores):
    vals = [v for v in valores if v is not None]
    if not vals:
        return None
    return {"min": round(min(vals), 1), "max": round(max(vals), 1),
            "media": round(sum(vals) / len(vals), 1), "n": len(vals)}


def _margem(rssi):
    return None if rssi is None else round(rssi - SENSIBILIDADE_DBM, 1)


def classifica_margem(margem):
    """Veredito de uma margem de enlace, na mesma régua do display de campo."""
    if margem is None:
        return "sem dados"
    if margem >= MARGEM_BOA_DB:
        return "confortavel"
    if margem >= MARGEM_MIN_DB:
        return "limite"
    return "critico"


def _assimetria(a):
    """Diferença entre os dois sentidos do mesmo enlace.

    Positiva = o gateway ouve o nó melhor do que o nó ouve o gateway. Assimetria
    grande denuncia antena, obstrução próxima ou ruído local em uma das pontas —
    é o tipo de defeito que só aparece medindo os dois sentidos.
    """
    sobe, desce = a.get("rssi_dbm"), a.get("rssi_remoto_dbm")
    if sobe is None or desce is None:
        return None
    return round(sobe - desce, 1)


def _taxa_pacotes(amostras):
    """Pacotes por minuto observados na janela."""
    if len(amostras) < 2:
        return 0.0
    span = amostras[-1]["t"] - amostras[0]["t"]
    return round(len(amostras) / span * 60, 1) if span > 0 else 0.0


def _perda_pct(amostras):
    """Perda no sentido nó → gateway, medida pelos buracos de sequência."""
    perdidos = sum(a.get("perdidos", 0) for a in amostras)
    total = len(amostras) + perdidos
    return round(perdidos / total * 100, 1) if total else 0.0


# ------------------------------------------------------------------- saída --

def _serie(amostras, limite=180):
    """Série temporal para os gráficos, reamostrada para não trafegar 600
    pontos que o gráfico não conseguiria distinguir mesmo."""
    passo = max(1, len(amostras) // limite)
    return [{
        "seq": a.get("seq"),
        "t": round(a["t"], 1),
        "rssi_sobe": a.get("rssi_dbm"),
        "rssi_desce": a.get("rssi_remoto_dbm"),
        "snr_sobe": a.get("snr_db"),
        "snr_desce": a.get("snr_remoto_db"),
        "margem_sobe": _margem(a.get("rssi_dbm")),
        "margem_desce": _margem(a.get("rssi_remoto_dbm")),
        "assimetria": _assimetria(a),
        "perdidos": a.get("perdidos", 0),
    } for a in amostras[::passo]]


def _resumo_nos(agora):
    itens = []
    for node_id, n in sorted(_nos.items(), key=lambda kv: (kv[0] is None, kv[0])):
        silencio = agora - n.get("ultimo_t", agora)
        total = n["pacotes"] + n["perdidos"]
        itens.append({
            "node_id": node_id,
            "pacotes": n["pacotes"],
            "perdidos": n["perdidos"],
            "perda_pct": round(n["perdidos"] / total * 100, 1) if total else 0.0,
            "ultimo_seq": n.get("ultimo_seq"),
            "silencio_s": round(silencio, 1),
            "estado": "silencioso" if silencio > SILENCIO_S else "ativo",
        })
    return itens


def _resumo_bridges(agora):
    return [{
        "bridge_id": ident,
        "publicados": b.get("publicados", 0),
        "fila_pendente": b.get("fila_pendente", 0),
        "ativa_ha_s": round(agora - b.get("ativo_desde", agora)),
        "silencio_s": round(agora - b.get("t", agora), 1),
        "estado": "ativa" if agora - b.get("t", agora) <= 90 else "sem contato",
    } for ident, b in sorted(_bridges.items())]


def _metricas(amostras):
    """Agregados da janela — o que responde 'a rede está saudável agora?'."""
    margens_sobe = [_margem(a.get("rssi_dbm")) for a in amostras]
    ultima = amostras[-1] if amostras else {}
    return {
        "rssi_sobe": _estat([a.get("rssi_dbm") for a in amostras]),
        "rssi_desce": _estat([a.get("rssi_remoto_dbm") for a in amostras]),
        "snr_sobe": _estat([a.get("snr_db") for a in amostras]),
        "snr_desce": _estat([a.get("snr_remoto_db") for a in amostras]),
        "margem_sobe": _estat(margens_sobe),
        "margem_desce": _estat([_margem(a.get("rssi_remoto_dbm"))
                                for a in amostras]),
        "assimetria": _estat([_assimetria(a) for a in amostras]),
        "perda_pct": _perda_pct(amostras),
        "pacotes_min": _taxa_pacotes(amostras),
        "margem_atual": _margem(ultima.get("rssi_dbm")),
        "veredito": classifica_margem(_margem(ultima.get("rssi_dbm"))),
    }


def estado():
    """Retrato completo para o painel. Uma chamada, um instante coerente."""
    agora = time.time()
    with _trava:
        amostras = list(_amostras)
        nos = _resumo_nos(agora)
        bridges = _resumo_bridges(agora)
    return {
        "ligacao": dict(_ligacao),
        "amostras": len(amostras),
        "metricas": _metricas(amostras),
        "serie": _serie(amostras),
        "nos": nos,
        "bridges": bridges,
        "limiares": {
            "sensibilidade_dbm": SENSIBILIDADE_DBM,
            "margem_boa_db": MARGEM_BOA_DB,
            "margem_min_db": MARGEM_MIN_DB,
            "assimetria_max_db": ASSIMETRIA_MAX_DB,
            "silencio_s": SILENCIO_S,
            "uso": "ensaio de enlace; não é critério de alerta geotécnico",
            "proveniencia": "firmware/src/ui_dev.h",
        },
        "gerado_em": time.strftime("%Y-%m-%d %H:%M:%S"),
        "gerado_em_iso": datetime.now(timezone.utc).isoformat(),
        "fonte": {
            "classificacao": "OBSERVADO",
            "origem": "MQTT sentinela/#",
            "armazenamento": "memória do processo do painel",
            "persistente": False,
        },
        "janela": {
            "capacidade_amostras": HISTORICO,
            "inicio_em_epoch": amostras[0]["t"] if amostras else None,
            "fim_em_epoch": amostras[-1]["t"] if amostras else None,
            "idade_ultima_s": round(agora - amostras[-1]["t"], 1)
            if amostras else None,
        },
    }
