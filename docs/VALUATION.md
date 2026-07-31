# Frente 5 — Valor de mercado estimado

Tentativa de chegar a um valor para a solução. **Leia primeiro a seção 1** — ela
define o quanto este número pode ser levado a sério.

> **Proveniência.** Tudo aqui é **[E]** — estimativa derivada de premissas
> declaradas. Nenhuma premissa foi validada com cliente real.

---

## 1. Aviso de método

Avaliar um projeto em **fase 0**, sem receita, sem cliente e sem produto
homologado, é exercício de faixa, não de precisão. Qualquer número aqui carrega
incerteza de **uma ordem de grandeza**.

O que torna esta avaliação **menos** especulativa que o normal:

- o mercado está **contado por fonte oficial** (MERCADO_MUNICIPIOS.md);
- existe **obrigação legal** sustentando demanda no segmento de mineração;
- há **canal de distribuição pronto** (Geopixel), o que remove o maior risco de
  um projeto de hardware — a aquisição de cliente.

O que a mantém especulativa:

- **nenhum preço validado** com comprador real;
- **sem homologação Anatel**, não há venda — e ela ainda não foi orçada;
- **concorrentes maduros** com autonomia superior (CONCORRENCIA.md);
- **camada geotécnica** ainda depende de parceria não formalizada.

---

## 2. Três métodos, três respostas

### Método A — Custo de reposição

Quanto custaria a outra empresa chegar onde o projeto está.

| Item | Estimativa **[E]** |
|---|---|
| Engenharia de firmware e ferramentas (já executada) | R$ 60–120 mil |
| Ensaios de campo, modelo de propagação calibrado | R$ 30–60 mil |
| Documentação técnica, conformidade, ancoragem | R$ 40–80 mil |
| **Subtotal — o que existe hoje** | **R$ 130–260 mil** |
| Falta até produto vendável (homologação, nó definitivo, backend) | R$ 250–500 mil |
| **Custo total de reposição do produto completo** | **R$ 380–760 mil** |

Este é o **piso** do valor: abaixo disso, é mais barato refazer.

### Método B — Múltiplo de receita projetada

Premissas de MERCADO_MUNICIPIOS.md e MERCADO_MINERACAO.md, cenário SOM em
regime (3–5 anos):

| Linha | Valor anual **[E]** |
|---|---|
| CAPEX municipal (600–1.200 pontos, amortizado) | R$ 600 mil – 1,8 mi |
| Recorrência municipal | R$ 400 mil – 1,2 mi |
| Mineração (entrada tardia) | R$ 300 mil – 1,5 mi |
| **Receita anual em regime** | **R$ 1,3 – 4,5 mi** |

Múltiplos de referência para negócio de hardware + software com recorrência:
**1,5× a 3× a receita anual** para empresa consolidada; para projeto sem
histórico, aplica-se desconto severo.

**Valor projetado em regime: R$ 2 – 13 mi.** Descontado pela probabilidade de
chegar lá — que em fase 0, com homologação e parcerias pendentes, é
conservadoramente **20% a 35%** **[E]**:

**Valor presente do projeto: R$ 400 mil – 4,5 mi.**

### Método C — Valor incremental para a Geopixel

O mais relevante, porque é o cenário real: o Sentinela não é uma empresa nova,
é um **produto dentro de uma empresa que já vende para este cliente**.

O valor aqui não é a receita do hardware — é o que ele faz com o negócio
existente (GEOPIXEL.md §4.7):

| Efeito | Natureza |
|---|---|
| Aumento de ticket por cliente | Vender equipamento e recorrência a quem já compra software |
| **Retenção** | Cliente com rede física instalada não troca de fornecedor facilmente |
| **Dado proprietário** | Sai da dependência de dado público que qualquer concorrente acessa |
| Diferenciação em licitação | Solução completa contra software puro |
| Novo segmento | Mineração, inacessível só com software |

**O efeito de retenção é o mais valioso e o menos visível.** Uma plataforma que
integra dados públicos é, em princípio, substituível por concorrente com bons
desenvolvedores. Uma rede física instalada em encostas, com série histórica
local, não é.

Se o Sentinela elevar em **15–25%** o valor de contrato dos clientes municipais
existentes e reduzir perda de clientes, o valor incremental pode superar a
receita direta do produto — mas **quantificar isso exige dados internos da
empresa que não tenho** **[?]**.

---

## 3. Faixa consolidada

| Cenário | Valor **[E]** | Condição |
|---|---|---|
| **Piso — hoje, como está** | **R$ 130 – 260 mil** | Custo de reposição do que existe |
| **Realista — produto entregue** | **R$ 800 mil – 3 mi** | Homologado, piloto operando, parceria geotécnica |
| **Otimista — operação consolidada** | **R$ 5 – 13 mi** | Dezenas de municípios, entrada em mineração, série histórica |

**A faixa mais defensável hoje: R$ 130 – 260 mil**, que é o custo de reposição.
É o único número ancorado em algo já realizado.

Os demais são **cenários condicionais** — valem se as condições se cumprirem, e
a probabilidade de cumprimento é o que realmente está sendo avaliado.

---

## 4. O que mais move o valor

Em ordem de impacto:

**1. Homologação Anatel.** Sem ela não há venda a órgão público. Passar de
"protótipo" para "produto homologado" é o **maior salto de valor único** do
cronograma — e está inteiramente sob controle do projeto.

**2. Piloto operando com dado real.** Meses de operação em município real, com
disponibilidade medida, transformam a proposta de promessa em evidência. É
também o que abre a mineração.

**3. Parceria geotécnica formalizada.** Sem responsável técnico, o produto não
pode ser vendido com a interpretação que lhe dá valor
(RESPONSABILIDADE_TECNICA.md).

**4. Patente do método de referência distribuída.** Se a busca de anterioridade
for favorável e o depósito ocorrer, cria barreira defensável — hoje inexistente
(PATENTES.md).

**5. Série histórica local calibrada.** Ativo que **melhora com o tempo** e não
pode ser comprado — o mais difícil de replicar, e o mais lento de construir.

---

## 5. Recomendação franca

**Não trate este projeto como um ativo a ser avaliado e vendido. Trate como uma
capacidade a ser construída dentro da Geopixel.**

O valor isolado de um projeto de hardware em fase 0, sem homologação e com
concorrentes maduros, é baixo — e a tentativa de vendê-lo ou captar sobre ele
provavelmente decepcionaria. O valor **dentro** da empresa que já tem o canal é
substancialmente maior, porque elimina o custo que mata projetos assim: a
aquisição de cliente.

Para a apresentação interna, o argumento mais forte **não é** "isto vale X". É:

> *"Isto transforma um software substituível numa infraestrutura instalada, com
> dado proprietário e receita recorrente — e o mercado está contado por fonte
> oficial: 958 municípios com risco mapeado e 911 barragens sob obrigação legal
> de instrumentação."*

---

## 6. Pendências desta frente

| ID | Item | Situação |
|---|---|---|
| V-01 | Validar preço por ponto com município real | **[?]** — premissa central |
| V-02 | Orçar homologação Anatel (custo e prazo) | **[?]** — ver C-01 |
| V-03 | Obter dados internos da Geopixel: ticket médio, retenção | **[?]** |
| V-04 | Cotação de concorrentes para ancorar preço | **[?]** — CONCORRENCIA.md C-01 |
| V-05 | Refazer esta análise após o piloto | Fase 5 |
