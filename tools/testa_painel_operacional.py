#!/usr/bin/env python3
"""Contratos do painel que não exigem broker, banco ou dados operacionais."""

import importlib
import sys
from pathlib import Path
from unittest.mock import patch

RAIZ = Path(__file__).resolve().parents[1]
PAINEL = RAIZ / "tools" / "painel"
sys.path.insert(0, str(PAINEL))

banco = importlib.import_module("banco")
telemetria = importlib.import_module("telemetria")
servidor = importlib.import_module("servidor")


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
    assert 'api("/api/fontes-observacoes")' in js
    assert 'api("/api/gis/fontes-contexto")' in js
    assert "o painel não soma estações, modelos ou provedores" in js
    assert "centro(s) de célula no recorte" in js
    assert "/api/fontes-externas" in servidor.ROTAS


if __name__ == "__main__":
    testa_metadados_telemetria()
    testa_operacao_sem_banco()
    testa_cadeia_nao_promete_servicos()
    testa_interface_declara_escopo()
    testa_interface_fontes_externas()
    print("ok — contratos do painel operacional")
