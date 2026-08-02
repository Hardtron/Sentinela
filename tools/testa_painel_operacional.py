#!/usr/bin/env python3
"""Contratos do painel que não exigem broker, banco ou dados operacionais."""

import importlib
import hashlib
import json
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
PAINEL = RAIZ / "tools" / "painel"
sys.path.insert(0, str(PAINEL))

banco = importlib.import_module("banco")
telemetria = importlib.import_module("telemetria")
servidor = importlib.import_module("servidor")


def _contem_todos(texto, trechos):
    for trecho in trechos:
        assert trecho in texto


def testa_metadados_telemetria():
    estado = telemetria.estado()
    assert estado["fonte"]["classificacao"] == "OBSERVADO"
    assert estado["fonte"]["persistente"] is False
    assert estado["janela"]["capacidade_amostras"] == telemetria.HISTORICO
    assert estado["limiares"]["proveniencia"] == "firmware/src/ui_dev.h"
    assert "não é critério de alerta geotécnico" in estado["limiares"]["uso"]


def testa_operacao_sem_banco():
    with patch.object(banco, "consulta", return_value=[]):
        banco._estado["erro"] = "banco de teste indisponível"
        estado = banco.operacao()
    assert estado["disponivel"] is False
    assert estado["evidencias"] == {}
    assert estado["erro"] == "banco de teste indisponível"


def testa_cadeia_nao_promete_servicos():
    db = {
        "disponivel": True, "consultado_em": "2026-08-01T12:00:00+00:00",
        "evidencias": {"enlace_em": "2026-08-01T11:59:00+00:00"},
        "erro": None, "qualidade": "observado no banco",
    }
    tel = {
        "ligacao": {"conectado": True, "broker": "localhost:1883",
                     "desde": 1, "erro": None},
        "amostras": 2, "janela": {"idade_ultima_s": 3},
    }
    with patch.object(servidor.banco, "operacao", return_value=db), \
            patch.object(servidor.telemetria, "estado", return_value=tel):
        estado = servidor.operacao()
    assert estado["painel"]["classificacao"] == "OBSERVADO"
    assert estado["mqtt"]["ultima_amostra_idade_s"] == 3
    assert any("ingestor" in x.lower() and "inferida" in x.lower()
               for x in estado["limitacoes"])
    assert any("RBAC" in x for x in estado["limitacoes"])


def testa_snapshot_contextual_nao_promove_risco():
    fontes = {"fontes": [{"provedor_codigo": "CEMADEN"}],
              "quarentena_7d": {"total": 0}, "erro": None}
    observacoes = {"observacoes": [{
        "provedor_codigo": "CEMADEN", "codigo_externo": "A",
        "valor": 1.2, "unidade": "mm", "sha256": "a" * 64,
    }], "erro": None}
    camadas = {"camadas": [{
        "provedor_codigo": "NASA_IMERG", "sha256": "b" * 64,
        "metadados": {"produto": "GPM_3IMERGHHE.07"},
    }], "erro": None}
    sensores = {"leituras": [{
        "node_id": 1, "placa": "HTC-01", "umidade_solo": 42,
        "solo_valido": True, "pitch_graus": 0.1, "roll_graus": 0.2,
        "inclin_valida": False, "chuva_valida": False,
    }], "erro": None}
    cadeia = {"gerado_em": "2026-08-02T12:00:00+00:00",
              "banco": {"erro": None}}
    with patch.object(servidor.banco, "fontes_externas", return_value=fontes), \
            patch.object(servidor.banco, "fontes_observacoes", return_value=observacoes), \
            patch.object(servidor.banco, "fontes_camadas", return_value=camadas), \
            patch.object(servidor.banco, "sensor", return_value=sensores), \
            patch.object(servidor, "operacao", return_value=cadeia):
        pacote = servidor.evidencia_contextual()
    assert pacote["classificacao"] == "INFORMATIVO"
    assert pacote["decisao"]["nivel_risco"] is None
    assert pacote["associacao"]["soma_entre_provedores"] is False
    assert pacote["associacao"]["limiar_geotecnico"] is None
    assert pacote["camadas"]["qualidade_operacional"]["sensores_invalidos"]
    integridade = pacote.pop("integridade")
    canonico = json.dumps(pacote, ensure_ascii=False, sort_keys=True,
                          separators=(",", ":")).encode("utf-8")
    assert integridade["sha256"] == hashlib.sha256(canonico).hexdigest()


def testa_interface_declara_escopo():
    html = (PAINEL / "static" / "index.html").read_text(encoding="utf-8")
    js = (PAINEL / "static" / "app.js").read_text(encoding="utf-8")
    assert "Apoio à decisão" in html
    assert 'role="status" aria-live="polite"' in html
    assert 'rotas["operacao"]' in js
    assert "sem classificação automática" in js
    assert "Identidade não verificada" in js
    assert 'api("/api/frota-saude")' in js


def testa_interface_fontes_externas():
    js = (PAINEL / "static" / "app.js").read_text(encoding="utf-8")
    _contem_todos(js, [
        'api("/api/fontes-observacoes")', 'api("/api/gis/fontes-contexto")',
        'api("/api/fontes-camadas")', 'api("/api/gis/recorte-piloto")',
        "o painel não soma estações, modelos ou provedores",
        "centro(s) de célula no recorte", "organizaProdutosRedemet",
        "IMERG · estimativa em grade", "produto.fuso", "Atualizar consulta",
        "STSC adquirido", "PED sem coordenadas",
        'api("/api/evidencia-contextual")', "Baixar snapshot JSON",
        "Não produz nível de risco", "sem soma entre fontes",
    ])
    _contem_todos(servidor.ROTAS, [
        "/api/fontes-externas", "/api/fontes-camadas",
        "/api/gis/recorte-piloto",
        "/api/evidencia-contextual",
    ])


def testa_recorte_piloto_e_escopo():
    recorte = banco.recorte_piloto()
    assert recorte["features"][0]["properties"]["codarea"] == "3510500"
    assert recorte["source"]["orgao"] == "IBGE"
    assert "não representa setor de risco" in recorte["escopo"]


if __name__ == "__main__":
    testa_metadados_telemetria()
    testa_operacao_sem_banco()
    testa_cadeia_nao_promete_servicos()
    testa_snapshot_contextual_nao_promove_risco()
    testa_interface_declara_escopo()
    testa_interface_fontes_externas()
    testa_recorte_piloto_e_escopo()
    print("ok — contratos do painel operacional")
