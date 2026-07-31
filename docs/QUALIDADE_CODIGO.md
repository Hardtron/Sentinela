# Qualidade de código

Política permanente do projeto. Vale para **todo** código do repositório —
firmware embarcado, ferramentas Python e o painel — e é verificada
automaticamente.

Ferramenta: `tools/complexidade.py`. Visualização: painel, aba **Qualidade**.

---

## 1. Complexidade ciclomática

A complexidade ciclomática (McCabe) conta os caminhos independentes de execução
de uma função: **1 + número de pontos de decisão**. É o indicador mais direto de
quanto esforço a função exige para ser entendida e, principalmente, **testada**:
uma função de complexidade N precisa de pelo menos N casos de teste para
cobertura de caminhos.

### Por que é requisito, e não preferência de estilo

O firmware roda **sem supervisão, em encosta, decidindo sobre alerta de risco à
vida**. Função que ninguém consegue seguir na leitura é função cujo
comportamento em caso raro ninguém previu — e o caso raro é justamente o evento
que o sistema existe para detectar.

Some-se a isso que o projeto tem exposição a responsabilidade civil
([RESPONSABILIDADE_TECNICA.md](RESPONSABILIDADE_TECNICA.md)): código verificável
e verificado é parte da demonstração de diligência.

### Limites adotados

| Faixa | Complexidade | Situação |
|---|---|---|
| **Simples** | 1 – 10 | Aceita |
| Moderada | 11 – 20 | **Refatorar** |
| Complexa | 21 – 50 | Refatorar antes de seguir |
| Crítica | > 50 | Bloqueia |

**Limite do projeto: 10.** Nenhuma função pode ser mesclada acima disso.

O limite é intencionalmente mais rígido que o clássico de McCabe (que tolera até
20): o custo de dividir uma função é baixo, e o benefício em código que decide
sobre alerta é alto.

---

## 2. Como verificar

```bash
./tools/venv/bin/python tools/complexidade.py --limite 10
```

Sai com código 1 se alguma função exceder — serve para automação. Para a saída
consumida pelo painel:

```bash
./tools/venv/bin/python tools/complexidade.py --json
```

**Quando rodar:** antes de cada commit que toque em código, e sempre que uma
função ganhar um novo ramo. A aba **Qualidade** do painel mostra o estado
corrente sem precisar do terminal.

---

## 3. O que conta como ponto de decisão

**Python** (via AST): `if`, `for`, `while`, `except`, `assert`, expressão
condicional, cada `and`/`or` além do primeiro, comprehensions e seus filtros,
cada `case` de `match`.

**C/C++** (varredura léxica, com comentários e literais removidos): `if`, `for`,
`while`, `case`, `catch`, cada `&&` e `||`, cada operador ternário.

A varredura léxica não é um parser completo de C++ — é aproximação deliberada.
Erra para mais em macros exóticas, o que é o lado seguro do erro.

---

## 4. Como refatorar quando estoura

A saída da ferramenta diz **qual função e em que linha**. Padrões que resolvem a
maior parte dos casos:

**Extrair bloco coeso.** Se a função tem seções separadas por comentário, cada
seção provavelmente é uma função. Foi assim que `pagLink` no firmware saiu de
CC 12 para 3, virando `blocoRssi`, `blocoMargem`, `blocoEco` e `blocoSelo` — e o
código ficou mais legível, não menos.

**Substituir cadeia de condicionais por tabela.** Um `switch` que só mapeia
valor para valor vira dicionário ou tabela de constantes. Foi o caso de
`seloDoVeredito`.

**Separar leitura de decisão.** Função que valida e processa ao mesmo tempo vira
duas: uma que devolve dados ou `None`, outra que age. `parse_amostra` e
`processa_linha` em `coleta.py` seguem esse padrão.

**Tirar o laço da função.** Laço com corpo grande vira laço curto chamando uma
função por item. Foi o que reduziu os `main` das ferramentas de 25 e 19 para
menos de 10.

> **Regra que evita o efeito colateral errado:** dividir para reduzir o número
> não vale nada se as partes não fizerem sentido isoladamente. Se a função
> extraída não tem nome óbvio, o corte foi no lugar errado.

---

## 5. Estado atual

Verificado em 31/07/2026, após refatoração:

| Métrica | Valor |
|---|---|
| Funções analisadas | 116 |
| Complexidade média | 3,4 |
| Complexidade máxima | 10 |
| Acima do limite | **nenhuma** |

Funções refatoradas nesta rodada: `pagLink` (12 → 3) no firmware,
`georreferenciar.main` (25 → 6), `coleta.main` (19 → 5) e
`importar_fotos.main` (18 → 8).

---

## 6. Além da complexidade

A complexidade ciclomática é o indicador verificado automaticamente, mas não é
o único critério de qualidade que o projeto adota:

- **Firmware em três camadas** — `app/` sem código específico de chip, para que
  a lógica de decisão seja testável no host (ADR-004).
- **Falha explícita** — sensor com defeito é reportado, nunca mascarado (RC-07).
- **Comentário explica o porquê**, não o quê. O código já diz o quê.
- **Nomes em português** no domínio do projeto, mantendo os termos técnicos
  consagrados em inglês onde traduzir atrapalharia.
- **Sem dependência externa desnecessária** — o painel usa apenas biblioteca
  padrão; o firmware, apenas RadioLib e U8g2.
