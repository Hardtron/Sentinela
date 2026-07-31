# Frentes de negócio — índice

Cinco estudos abertos em 31/07/2026, separados por frente. Este documento amarra
as conclusões; cada frente tem seu próprio arquivo com dados, fontes e
pendências.

> **Proveniência.** Números de mercado são **[G]** governamentais quando
> possível e **[E]** estimativa própria quando derivados. Nenhuma premissa
> comercial foi validada com cliente real — ver a ressalva em cada documento.

| # | Frente | Documento | Veredito |
|---|---|---|---|
| 1 | Mercado municipal | [MERCADO_MUNICIPIOS.md](MERCADO_MUNICIPIOS.md) | **Prioritário** — mercado contado por fonte oficial e canal já aberto |
| 2 | Barragens de mineração | [MERCADO_MINERACAO.md](MERCADO_MINERACAO.md) | Atraente, **mais difícil** — entrar depois, pelo flanco |
| 3 | Concorrência e originalidade | [CONCORRENCIA.md](CONCORRENCIA.md) | **O hardware não é o diferencial** — reposicionar |
| 4 | Maturidade para patente | [PATENTES.md](PATENTES.md) | **Nível 1–2 de 3** — não atinge o mínimo ainda |
| 5 | Valor de mercado | [VALUATION.md](VALUATION.md) | Piso defensável **R$ 130–260 mil**; cenários condicionais acima |

---

## As cinco conclusões que mais importam

**1. O universo de clientes está contado pelo Estado.** 958 municípios com áreas
de risco mapeadas, 8,27 milhões de pessoas expostas, 911 barragens de mineração
com 118 em alerta ou emergência. Não é preciso estimar demanda por analogia
— os números são oficiais e públicos.

**2. Na mineração, monitorar é obrigação legal, não escolha.** A Lei 14.066/2020
exige armazenar dados de instrumentação e fornecê-los em tempo real quando
requerido. O comprador não precisa ser convencido de que precisa — precisa
escolher fornecedor. Isso é bom e ruim: demanda garantida, concorrência
estabelecida.

**3. O hardware não é original, e insistir nisso é o caminho errado.**
Worldsensing e Senceive fazem sensor de inclinação sem fio há anos, com
autonomia de 10 a 15 anos — melhor que a nossa. Se a proposta fosse construir
esse sensor, o certo seria comprar deles e integrar.

**4. A originalidade defensável está em outro lugar.** Na **referência
distribuída** para diagnóstico de manutenção, na **integração geoespacial** que
traduz dado em decisão, e no **custo por ponto** que permite adensar malha onde
hoje não há nada. O concorrente premium está na barragem crítica; o Sentinela
concorre com o *nada* que existe no talude municipal.

**5. O valor está dentro da Geopixel, não fora.** O maior risco de um projeto de
hardware é a aquisição de cliente — e é exatamente o que a empresa já resolveu.
Isolado, o projeto vale o custo de reposição. Dentro do canal existente, muda o
patamar do negócio.

---

## O reposicionamento que decorre disso

O Sentinela **não é** "mais um sensor de inclinação para talude".

É **uma malha densa e barata de instrumentação, integrada a uma base geoespacial
de risco, com manutenção autodiagnosticada** — vendida por quem já é fornecedor
do município.

Consequência de arquitetura: o sistema deve **ingerir dados de instrumentos de
terceiros**. Cliente que já tem Worldsensing instalado não deve ser obrigado a
substituir — reforça a decisão de padrões abertos (ADR-005) e transforma
concorrente em complemento.

---

## Sequência recomendada

1. **Homologação Anatel** — sem ela não há venda pública. Maior salto de valor
   único do cronograma, e inteiramente sob controle do projeto.
2. **Busca de anterioridade** (PT-01) — barata, rápida e decide se há patente a
   perseguir.
3. **Piloto municipal com dado real** — preferencialmente Caraguatatuba, onde há
   cliente, instância no ar e o cenário calibrado.
4. **Parceria geotécnica formalizada** — condição para vender a interpretação
   que dá valor ao dado.
5. **Mineração por último**, por adensamento de malha e com histórico
   operacional em mãos.

---

## Alerta transversal

**Divulgação pública antes do depósito de patente compromete a novidade.** Isso
inclui a apresentação à Geopixel, o painel de resultados e qualquer publicação
do repositório. Resolver PT-01 e PT-03 **antes** de expor o conteúdo — ver
[PATENTES.md](PATENTES.md) §5.

---

## Pendências consolidadas das cinco frentes

| ID | Frente | Item | Criticidade |
|---|---|---|---|
| **C-01** | Concorrência | Cotação real de Worldsensing e Senceive | **Crítica** — sem ela o preço é especulação |
| **PT-01** | Patentes | Busca de anterioridade | **Crítica** — decide se há o que patentear |
| **PT-03** | Patentes | Definir titularidade com a empresa | **Crítica** — antes de depositar |
| V-02 | Valuation | Orçar homologação Anatel | Alta |
| M-01 | Municipal | Base de setores de risco do CPRM por município | Alta |
| M-03 | Municipal | Validar preço por ponto com município real | Alta |
| V-03 | Valuation | Dados internos da Geopixel — ticket, retenção | Alta |
| N-01 | Mineração | Base pública da ANM com as 911 barragens | Média |
| C-05 | Concorrência | Identificar a startup brasileira de IoT para encostas | Média |
| C-06 | Concorrência | Viabilidade de ingerir dados de terceiros | Média |

Lista completa em cada documento de frente.
