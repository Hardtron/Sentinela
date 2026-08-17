#!/usr/bin/env python3
"""Sentinela — análise de complexidade ciclomática.

Complexidade ciclomática (McCabe) conta os caminhos independentes de execução de
uma função: 1 + número de pontos de decisão. É o indicador mais direto de quanto
esforço a função exige para ser entendida e testada.

Por que isto é política do projeto, e não preferência de estilo: o firmware roda
sem supervisão em encosta, decidindo sobre alerta de risco à vida. Função que
ninguém consegue seguir na leitura é função cujo comportamento em caso raro
ninguém previu — e o caso raro é justamente o evento que o sistema existe para
detectar.

Analisa Python (via AST) e C/C++ (via varredura léxica).

Uso:
    python3 complexidade.py                    # projeto inteiro
    python3 complexidade.py --limite 10        # falha se exceder
    python3 complexidade.py --json             # saída para o painel

Autoria: Luiz Matheus Marassi de Paula
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path

# Faixas de McCabe adotadas pelo projeto. Ver docs/QUALIDADE_CODIGO.md.
FAIXAS = [
    (10, "simples", "verde"),
    (20, "moderada", "amarelo"),
    (50, "complexa", "laranja"),
    (10**9, "critica", "vermelho"),
]

LIMITE_PADRAO = 10

# Palavras que introduzem ramificação em C/C++.
PALAVRAS_C = ("if", "for", "while", "case", "catch")

IGNORAR_DIRS = {".git", ".pio", "venv", "__pycache__", "node_modules",
                ".venv", "dados"}


def classifica(valor):
    for teto, rotulo, cor in FAIXAS:
        if valor <= teto:
            return rotulo, cor
    return "critica", "vermelho"


# --------------------------------------------------------------- Python --

class VisitantePython(ast.NodeVisitor):
    """Conta pontos de decisão de uma função Python.

    Mantido deliberadamente simples: cada tipo de nó soma o que soma, sem
    ramificação condicional própria. A ferramenta que mede complexidade não
    pode ser complexa.
    """

    PESO_DIRETO = (ast.If, ast.For, ast.AsyncFor, ast.While,
                   ast.ExceptHandler, ast.Assert, ast.IfExp)

    # match/case existe a partir do Python 3.10; ausente no 3.9 do sistema.
    NO_MATCH = getattr(ast, "Match", ())

    def __init__(self):
        self.pontos = 0

    def generic_visit(self, node):
        self.pontos += self._peso(node)
        super().generic_visit(node)

    @staticmethod
    def _peso(node):
        if isinstance(node, VisitantePython.PESO_DIRETO):
            return 1
        if isinstance(node, ast.BoolOp):
            return len(node.values) - 1
        if isinstance(node, ast.comprehension):
            return 1 + len(node.ifs)
        if VisitantePython.NO_MATCH and isinstance(node, VisitantePython.NO_MATCH):
            return len(node.cases)
        return 0


def analisa_python(caminho):
    try:
        arvore = ast.parse(caminho.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError) as e:
        return [], str(e)

    resultados = []
    for no in ast.walk(arvore):
        if not isinstance(no, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        visitante = VisitantePython()
        for filho in ast.iter_child_nodes(no):
            visitante.visit(filho)
        resultados.append({
            "nome": no.name,
            "linha": no.lineno,
            "complexidade": visitante.pontos + 1,
        })
    return resultados, None


# ---------------------------------------------------------------- C/C++ --

RE_COMENTARIO_BLOCO = re.compile(r"/\*.*?\*/", re.S)
RE_COMENTARIO_LINHA = re.compile(r"//[^\n]*")
RE_TEXTO = re.compile(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')
RE_FUNCAO = re.compile(
    r"^[A-Za-z_][\w\s\*&:<>,]*?\b([A-Za-z_]\w*)\s*\([^;{]*\)\s*(?:const\s*)?\{",
    re.M)


def limpa_fonte(texto):
    """Remove comentários e literais — evita contar palavra dentro de string."""
    texto = RE_COMENTARIO_BLOCO.sub(" ", texto)
    texto = RE_COMENTARIO_LINHA.sub(" ", texto)
    return RE_TEXTO.sub('""', texto)


def corpo_da_funcao(texto, inicio):
    """Devolve o corpo entre chaves a partir da abertura em `inicio`."""
    profundidade = 0
    for i in range(inicio, len(texto)):
        if texto[i] == "{":
            profundidade += 1
        elif texto[i] == "}":
            profundidade -= 1
            if profundidade == 0:
                return texto[inicio:i + 1]
    return texto[inicio:]


def pontos_decisao_c(corpo):
    total = 0
    for palavra in PALAVRAS_C:
        total += len(re.findall(r"\b" + palavra + r"\b", corpo))
    total += corpo.count("&&") + corpo.count("||")
    total += len(re.findall(r"\?[^:]*:", corpo))
    return total


def analisa_c(caminho):
    try:
        texto = limpa_fonte(caminho.read_text(encoding="utf-8"))
    except UnicodeDecodeError as e:
        return [], str(e)

    resultados = []
    for m in RE_FUNCAO.finditer(texto):
        corpo = corpo_da_funcao(texto, texto.index("{", m.end() - 1))
        resultados.append({
            "nome": m.group(1),
            "linha": texto[:m.start()].count("\n") + 1,
            "complexidade": pontos_decisao_c(corpo) + 1,
        })
    return resultados, None


# ------------------------------------------------------------- varredura --

EXTENSOES = {".py": analisa_python, ".c": analisa_c, ".cpp": analisa_c,
             ".h": analisa_c, ".hpp": analisa_c, ".ino": analisa_c}


def varre(raiz):
    arquivos = []
    for caminho in sorted(Path(raiz).rglob("*")):
        if not caminho.is_file() or caminho.suffix not in EXTENSOES:
            continue
        if any(parte in IGNORAR_DIRS for parte in caminho.parts):
            continue
        funcoes, erro = EXTENSOES[caminho.suffix](caminho)
        if erro:
            continue
        for f in funcoes:
            f["rotulo"], f["cor"] = classifica(f["complexidade"])
        arquivos.append({
            "arquivo": str(caminho.relative_to(raiz)),
            "linguagem": "python" if caminho.suffix == ".py" else "c",
            "funcoes": sorted(funcoes, key=lambda f: -f["complexidade"]),
            "maxima": max((f["complexidade"] for f in funcoes), default=0),
            "total_funcoes": len(funcoes),
        })
    return arquivos


def resume(arquivos):
    todas = [f for a in arquivos for f in a["funcoes"]]
    if not todas:
        return {"funcoes": 0}
    valores = [f["complexidade"] for f in todas]
    distribuicao = {}
    for f in todas:
        distribuicao[f["rotulo"]] = distribuicao.get(f["rotulo"], 0) + 1
    return {
        "funcoes": len(todas),
        "arquivos": len(arquivos),
        "media": round(sum(valores) / len(valores), 1),
        "maxima": max(valores),
        "distribuicao": distribuicao,
        "piores": sorted(todas, key=lambda f: -f["complexidade"])[:10],
    }


def main():
    ap = argparse.ArgumentParser(description="Complexidade ciclomática (McCabe)")
    ap.add_argument("--raiz", default=".")
    ap.add_argument("--limite", type=int, default=LIMITE_PADRAO)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    arquivos = varre(args.raiz)
    resumo = resume(arquivos)

    if args.json:
        print(json.dumps({"arquivos": arquivos, "resumo": resumo},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"Complexidade ciclomática — limite adotado: {args.limite}\n")
    print(f"{'arquivo':<44}{'funcao':<28}{'CC':>5}  faixa")
    print("-" * 92)
    excedentes = 0
    for a in arquivos:
        for f in a["funcoes"]:
            marca = "  <<<" if f["complexidade"] > args.limite else ""
            if marca:
                excedentes += 1
            print(f"{a['arquivo']:<44}{f['nome']:<28}"
                  f"{f['complexidade']:>5}  {f['rotulo']}{marca}")

    print(f"\n{resumo['funcoes']} funções em {resumo['arquivos']} arquivos")
    print(f"média {resumo['media']}   máxima {resumo['maxima']}")
    print(f"distribuição: {resumo['distribuicao']}")
    if excedentes:
        print(f"\n{excedentes} função(ões) acima do limite de {args.limite}")
        return 1
    print(f"\nnenhuma função acima do limite de {args.limite}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
