"""Teste isolado do registro de atendimento de alarmes no painel."""

import importlib.util
from pathlib import Path


ARQUIVO = Path(__file__).parent / "painel" / "banco.py"
SPEC = importlib.util.spec_from_file_location("banco_painel", ARQUIVO)
banco = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(banco)


class Cursor:
    def __init__(self):
        self.chamada = None

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql, parametros):
        self.chamada = (sql, parametros)


class Conexao:
    def __init__(self):
        self.cursor_falso = Cursor()
        self.confirmou = False

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def cursor(self):
        return self.cursor_falso

    def commit(self):
        self.confirmou = True


class PsycopgFalso:
    def __init__(self):
        self.conexao = Conexao()

    def connect(self, **_):
        return self.conexao


def verifica(esperado, recebido, rotulo):
    if esperado != recebido:
        raise AssertionError(f"{rotulo}: esperado {esperado!r}, recebido {recebido!r}")


def main():
    antigo_psycopg = banco.psycopg
    antigo_dsn = banco._dsn
    falso = PsycopgFalso()
    banco.psycopg = falso
    banco._dsn = lambda: {"dbname": "teste"}
    try:
        resposta = banco.reconhece_alarme({
            "alarme_id": 9,
            "operador": "Equipe de Campo",
            "acao_tomada": "DESPACHO_CAMPO",
            "despacho_equipe": True,
            "nota_operador": "Equipe acionada.",
        })
        verifica(True, resposta.get("ok"), "registro aceito")
        verifica(True, falso.conexao.confirmou, "transação confirmada")
        verifica(9, falso.conexao.cursor_falso.chamada[1][0], "identificador")
        verifica("Equipe de Campo", falso.conexao.cursor_falso.chamada[1][1], "operador")
        verifica({"erro": "operador é obrigatório"},
                 banco.reconhece_alarme({"alarme_id": 9}),
                 "operador obrigatório")
    finally:
        banco.psycopg = antigo_psycopg
        banco._dsn = antigo_dsn
    print("Reconhecimento de alarme: 4 verificações, 0 falha(s)")


if __name__ == "__main__":
    main()
