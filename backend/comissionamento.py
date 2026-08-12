#!/usr/bin/env python3
"""Sentinela — comissionamento de Atalaia (Frente 9).

Orquestra a passagem de "placa cadastrada" para "ponto de dado confiável no
mapa". A regra de transição vive no banco (migração 007); aqui fica o que é da
aplicação: ler o EXIF da foto oficial, validar o checklist, montar a pasta da
Atalaia e disparar as transições na ordem certa.

**Por que o checklist chega em JSON e as fotos por pasta.** O plano previa
upload multipart. O servidor do painel é `http.server` da stdlib, e o módulo
`cgi` — que fazia esse parsing — foi **removido no Python 3.13**, que é o que
roda no homeserver. Escrever um parser de multipart à mão para receber foto de
celular seria código frágil no caminho mais crítico do sistema. A alternativa
é melhor e já existe: a equipe deposita as fotos na pasta da Atalaia (rsync,
compartilhamento ou cópia), e o gestor autônomo (Frente 6) já vigia esse
diretório. O formulário envia só o checklist, em JSON.

Autoria: Matheus Marassi
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg

from ingestor import carrega_env

RAIZ = Path(__file__).resolve().parent
# Onde ficam as pastas por Atalaia. O plano previa /DATA/Media/Sentinela, mas
# /DATA/Media pertence ao root no homeserver e o sudo de lá pede senha — criar
# lá exigiria intervenção manual só para o sistema subir. O padrão aponta para
# um caminho que o serviço já pode escrever; para usar /DATA/Media basta criá-lo
# com o dono certo (uma vez, com sudo) e apontar SENTINELA_MEDIA para ele.
MEDIA = Path(os.environ.get("SENTINELA_MEDIA",
                            "/DATA/Runtime/Sentinela-Media/Atalaias"))

SUBPASTAS = ("fotos", "checklist", "documentos", "dados", "manutencao")

# Seções do checklist (§E do plano). Obrigatórias: sem elas não há como
# afirmar que a instalação foi verificada.
SECOES = ("secao_a_identificacao", "secao_b_mecanica", "secao_c_energia",
          "secao_d_estanqueidade", "secao_e_sensoriamento", "secao_f_radio")


class ComissionamentoInvalido(Exception):
    """Recusa explícita, com o motivo. Nunca silenciosa (RC-07)."""


def conecta():
    carrega_env(RAIZ / ".env")
    senha = os.environ.get("POSTGRES_PASSWORD")
    if not senha:
        raise ComissionamentoInvalido("POSTGRES_PASSWORD ausente em backend/.env")
    return psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", "5432")),
        dbname=os.environ.get("POSTGRES_DB", "sentinela"),
        user=os.environ.get("POSTGRES_USER", "sentinela"),
        password=senha)


def pasta_da_atalaia(placa):
    """`ATL-<município>-<seq>` (MANUTENCAO.md §1) — não ID genérico."""
    destino = MEDIA / placa
    for sub in SUBPASTAS:
        (destino / sub).mkdir(parents=True, exist_ok=True)
    return destino


def _exif_da_foto(caminho):
    """Coordenada da foto oficial. Reusa o extrator já existente do projeto."""
    sys.path.insert(0, str(RAIZ.parent / "tools"))
    try:
        import importar_fotos as imp
    except ImportError:
        raise ComissionamentoInvalido(
            "tools/importar_fotos.py indisponível para ler EXIF")
    dados = imp.le_gps(Path(caminho))
    if not dados:
        raise ComissionamentoInvalido(
            f"foto {Path(caminho).name} sem GPS no EXIF — o comissionamento "
            "exige coordenada da instalação, não posição digitada à mão")
    return dados


def _itens_reprovados(payload):
    """Itens marcados como não conformes, em notação `secao.item`."""
    return [f"{s}.{item}"
            for s in SECOES
            for item, valor in (payload.get(s) or {}).items()
            if valor is False or valor == "NAO"]


def valida_checklist(payload):
    """Recusa checklist incompleto **antes** de tocar no banco.

    Um comissionamento aceito com seção vazia viraria uma Atalaia
    'homologada' sem verificação de vedação ou ancoragem — que é exatamente o
    risco RT-09 (falso alarme por flexão, ou destruição por infiltração).
    """
    faltando = [c for c in ("node_id", "submetido_por", "responsavel_campo")
                if not payload.get(c)]
    if faltando:
        raise ComissionamentoInvalido(
            f"campos obrigatórios ausentes: {', '.join(faltando)}")

    vazias = [s for s in SECOES if not payload.get(s)]
    if vazias:
        raise ComissionamentoInvalido(
            f"seções do checklist não preenchidas: {', '.join(vazias)}")

    # Reprovar sem dizer o quê deixa a equipe de campo sem saber o que
    # corrigir na volta — e a volta a uma encosta custa caro.
    reprovados = _itens_reprovados(payload)
    if reprovados and not payload.get("observacoes"):
        raise ComissionamentoInvalido(
            f"itens reprovados ({', '.join(reprovados)}) exigem observação")
    return reprovados


SQL_INSERE = """
INSERT INTO checklist_instalacao (
    node_id, submetido_por, responsavel_campo, responsavel_geotecnico,
    secao_a_identificacao, secao_b_mecanica, secao_c_energia,
    secao_d_estanqueidade, secao_e_sensoriamento, secao_f_radio,
    posicao_exif, classe_suscetibilidade, estacao_codigo, distancia_estacao_m,
    domicilios_300m, populacao_300m, foto_oficial_path,
    justificativa_posicao, observacoes)
VALUES (%(node_id)s, %(submetido_por)s, %(responsavel_campo)s,
        %(responsavel_geotecnico)s,
        %(a)s, %(b)s, %(c)s, %(d)s, %(e)s, %(f)s,
        ST_SetSRID(ST_MakePoint(%(lon)s, %(lat)s), 4326)::geography,
        %(classe)s, %(estacao)s, %(dist)s, %(dom)s, %(pop)s, %(foto)s,
        %(justificativa)s, %(obs)s)
RETURNING id
"""


def _coordenada(payload, foto_oficial):
    """Coordenada da instalação. A foto com EXIF é a fonte preferida porque
    tem rastreabilidade: hora, aparelho e posição vêm juntos e não são
    digitados. Posição manual é aceita, mas exige justificativa registrada."""
    if foto_oficial:
        gps = _exif_da_foto(foto_oficial)
        return gps["lat"], gps["lon"]
    if payload.get("lat") is not None and payload.get("lon") is not None:
        if not payload.get("justificativa_posicao"):
            raise ComissionamentoInvalido(
                "posição sem foto EXIF exige justificativa_posicao")
        return float(payload["lat"]), float(payload["lon"])
    raise ComissionamentoInvalido(
        "informe a foto oficial georreferenciada ou lat/lon com justificativa")


def _leva_ate_comissionando(cur, node_id, estado, autor):
    """Avança o ciclo de vida até COMISSIONANDO, seja qual for o ponto de
    partida — recomissionar após FALHA_ENLACE é caso normal, não exceção."""
    if estado == "REGISTRADA":
        cur.execute("SELECT transita_estado(%s::smallint,'INSTALADA',%s)", (node_id, autor))
        estado = "INSTALADA"
    if estado in ("INSTALADA", "FALHA_ENLACE"):
        cur.execute("SELECT transita_estado(%s::smallint,'COMISSIONANDO',%s)", (node_id, autor))


def _grava_baseline(destino, payload, teste, val):
    """Ponto zero da manutenção preditiva (Frente 7): até haver frota
    suficiente para a referência distribuída, a Atalaia é sua própria
    referência."""
    baseline = {
        "comissionado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "enlace": {k: teste[k] for k in
                   ("amostras", "rssi_med", "snr_med", "margem_med",
                    "assimetria", "perdas", "aprovado", "motivo")},
        "geoespacial": {k: val[k] for k in
                        ("classe_suscetibilidade", "estacao_codigo",
                         "distancia_estacao_m", "domicilios", "populacao")},
    }
    (destino / "dados" / "baseline_comissionamento.json").write_text(
        json.dumps(baseline, indent=2, ensure_ascii=False, default=str),
        encoding="utf-8")
    (destino / "checklist" / "checklist_digital.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _copia_foto(destino, foto_oficial):
    if not foto_oficial:
        return None
    alvo = destino / "fotos" / Path(foto_oficial).name
    if Path(foto_oficial).resolve() != alvo.resolve():
        shutil.copy2(foto_oficial, alvo)
    return f"fotos/{Path(foto_oficial).name}"


def comissiona(payload, foto_oficial=None):
    """Executa o comissionamento inteiro. Devolve o relatório.

    Ordem deliberada: valida tudo que dá para validar **antes** de mexer em
    estado. Comissionamento abortado no meio deixaria a Atalaia num estado que
    não corresponde ao que existe em campo.
    """
    reprovados = valida_checklist(payload)
    node_id = int(payload["node_id"])
    lat, lon = _coordenada(payload, foto_oficial)

    with conecta() as con, con.cursor() as cur:
        cur.execute("SELECT placa, estado FROM no WHERE node_id = %s", (node_id,))
        linha = cur.fetchone()
        if not linha:
            raise ComissionamentoInvalido(f"node_id {node_id} não cadastrado")
        placa, estado = linha

        cur.execute("SELECT * FROM valida_posicao(%s::real, %s::real)", (lon, lat))
        cols = [d[0] for d in cur.description]
        val = dict(zip(cols, cur.fetchone()))

        if val["alerta"] and "justificativa" in (val["alerta"] or "") \
                and not payload.get("justificativa_posicao"):
            raise ComissionamentoInvalido(val["alerta"])

        destino = pasta_da_atalaia(placa)
        caminho_foto = _copia_foto(destino, foto_oficial)

        cur.execute(SQL_INSERE, {
            "node_id": node_id,
            "submetido_por": payload["submetido_por"],
            "responsavel_campo": payload["responsavel_campo"],
            "responsavel_geotecnico": payload.get("responsavel_geotecnico"),
            "a": json.dumps(payload["secao_a_identificacao"]),
            "b": json.dumps(payload["secao_b_mecanica"]),
            "c": json.dumps(payload["secao_c_energia"]),
            "d": json.dumps(payload["secao_d_estanqueidade"]),
            "e": json.dumps(payload["secao_e_sensoriamento"]),
            "f": json.dumps(payload["secao_f_radio"]),
            "lon": lon, "lat": lat,
            "classe": val["classe_suscetibilidade"],
            "estacao": val["estacao_codigo"],
            "dist": val["distancia_estacao_m"],
            "dom": val["domicilios"], "pop": val["populacao"],
            "foto": caminho_foto,
            "justificativa": payload.get("justificativa_posicao"),
            "obs": payload.get("observacoes"),
        })
        checklist_id = cur.fetchone()[0]

        cur.execute("UPDATE no SET posicao = ST_SetSRID(ST_MakePoint(%s,%s),4326)::geography "
                    "WHERE node_id = %s", (lon, lat, node_id))

        autor = payload["submetido_por"]
        _leva_ate_comissionando(cur, node_id, estado, autor)
        cur.execute("SELECT transita_estado(%s::smallint,'VALIDANDO_ENLACE',%s)", (node_id, autor))

        # O teste roda contra o banco, não contra o broker: aprova só se o dado
        # atravessou a esteira inteira até onde a decisão é tomada.
        cur.execute("SELECT * FROM teste_enlace(%s::smallint)", (node_id,))
        cols = [d[0] for d in cur.description]
        teste = dict(zip(cols, cur.fetchone()))

        cur.execute("""
            UPDATE checklist_instalacao SET
                teste_enlace_rssi_med=%s, teste_enlace_snr_med=%s,
                teste_enlace_margem=%s, teste_enlace_perdas=%s,
                teste_enlace_amostras=%s, teste_enlace_aprovado=%s
             WHERE id=%s""",
            (teste["rssi_med"], teste["snr_med"], teste["margem_med"],
             teste["perdas"], teste["amostras"], teste["aprovado"], checklist_id))

        estado_final = "OPERACIONAL" if teste["aprovado"] else "FALHA_ENLACE"
        cur.execute("SELECT transita_estado(%s::smallint,%s,%s,%s)",
                    (node_id, estado_final, autor, teste["motivo"]))

        _grava_baseline(destino, payload, teste, val)
        con.commit()

    return {
        "checklist_id": checklist_id, "node_id": node_id, "placa": placa,
        "estado": estado_final, "teste_enlace": teste, "geoespacial": val,
        "itens_reprovados": reprovados, "pasta": str(destino),
        "alerta_posicao": val["alerta"],
    }
