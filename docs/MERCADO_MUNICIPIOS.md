# Frente 1 — Mercado municipal

Dimensionamento do mercado de prefeituras e defesa civil no Brasil.

> **Proveniência.** Segue [REFERENCIAS.md](REFERENCIAS.md): **[G]** fonte
> governamental, **[L]** literatura, **[E]** estimativa própria derivada,
> **[?]** pendente. Cifras de mercado são **[E]** e dependem das premissas
> declaradas em cada seção.

---

## 1. O universo existe e está contado

Este mercado tem uma característica incomum e favorável: **o Estado brasileiro
já mapeou e publicou o universo de clientes potenciais.** Não é preciso estimar
demanda por analogia — os números são oficiais.

| Indicador | Valor | Fonte |
|---|---|---|
| Municípios monitorados pelo CEMADEN | **1.295** (mar/2026) | [Cemaden](https://www.gov.br/cemaden/pt-br/assuntos/noticias-cemaden/cemaden-expande-rede-de-monitoramento-e-passa-a-monitorar-1-295-municipios) **[G]** |
| Meta declarada de cobertura | **2.095** municípios suscetíveis | [Agência Gov](https://agenciagov.ebc.com.br/noticias/202511/cemaden-aumentara-numero-de-municipios-monitorados-para-desastres-para-2.095) **[G]** |
| Municípios críticos com áreas de risco mapeadas | **958** | Cemaden/CPRM **[G]** |
| Municípios com áreas de risco identificadas | **872** | [IBGE + Cemaden](https://www.ibge.gov.br/geociencias/informacoes-ambientais/estudos-ambientais/21538-populacao-em-areas-de-risco-no-brasil.html) **[G]** |
| Pessoas vivendo em áreas de risco | **8.270.127** | IBGE + Cemaden (Censo 2010) **[G]** |
| Domicílios em áreas de risco | **2.471.349** | IBGE + Cemaden **[G]** |
| Municípios com deslizamento registrado em 2023 | **262** | REINDESC/Cemaden **[G]** |
| Municípios com inundação registrada em 2023 | **397** | REINDESC/Cemaden **[G]** |

**Concentração regional:** o Sudeste responde por **4.266.301 pessoas expostas**
em 308 municípios avaliados — mais da metade do total nacional **[G]**. É também
onde está a Serra do Mar, o cenário para o qual o modelo de propagação e o
projeto de ancoragem foram calibrados.

> **Ressalva importante:** a base de população em risco vem do **Censo 2010**. A
> atualização com o Censo 2022 está prevista mas ainda não publicada **[G]**.
> Como a ocupação de encosta cresceu no período, os números devem ser tratados
> como **piso**, não como estimativa corrente. **[?]** Acompanhar a publicação.

---

## 2. Segmentação — onde o produto se encaixa

Nem todo município do universo é cliente. A segmentação que importa:

| Camada | Municípios | Característica |
|---|---|---|
| **Universo suscetível** | 2.095 | Meta de cobertura do CEMADEN |
| **Com risco mapeado** | 958 | Já têm setores de risco delimitados — **o alvo** |
| **Com evento recente** | 262/ano | Deslizamento registrado, orçamento sensibilizado |
| **Alvo inicial realista** | ~50–100 | Sudeste, porte médio, defesa civil estruturada |

**Por que o alvo é "com risco mapeado" e não "suscetível":** onde há mapeamento
do CPRM, os setores de risco já estão delimitados e classificados. Isso elimina
a etapa mais cara da venda — convencer o município de que ele tem o problema — e
transforma a conversa em *quantos pontos instrumentar*. Também dá ao geotécnico
parceiro a base para definir onde instalar.

**O que descarta um município** como alvo inicial: ausência de defesa civil
estruturada, inexistência de mapeamento e porte pequeno demais para sustentar
manutenção. Municípios muito pequenos são melhor atendidos por consórcio
intermunicipal — que é caminho de venda, não obstáculo.

---

## 3. Dinâmica de compra pública

Três aspectos definem o ciclo comercial neste mercado:

**Existe fonte de recurso vinculada.** A expansão do CEMADEN se dá no âmbito do
**novo PAC** **[G]**, o que indica orçamento federal para o tema. Municípios
também acessam recursos de defesa civil e emendas parlamentares. **A verba
tende a existir; o gargalo costuma ser a especificação técnica.**

**O gatilho é o evento.** Historicamente, investimento em prevenção sobe após
desastre com repercussão. Isso cria um ciclo comercial reativo e sazonal
(verão), com decisão acelerada logo após ocorrência. É desconfortável, mas é
real — e afeta previsão de receita.

**A barreira é documental, não técnica.** Como registrado em
[CONFORMIDADE.md](CONFORMIDADE.md) §6, a Lei 14.133/2021 exige comprovação:
homologação Anatel, ART do responsável técnico e atestados de capacidade. Sem
homologação **não há venda** — nenhuma sofisticação técnica compensa isso.

---

## 4. Dimensionamento do mercado **[E]**

Premissas declaradas — todas revisáveis, e nenhuma validada com cliente real:

- Pontos instrumentados por município: **5 a 30**, conforme número de setores
  críticos. Mediana adotada: **12**.
- Preço por Atalaia instalada: **R$ 3.000 a R$ 6.000** **[E]**, incluindo
  equipamento, instalação e primeiro ano de operação.
- Recorrência anual: **20 a 30% do CAPEX** (telemetria, manutenção, calibração,
  suporte).
- Um Farol por município na maioria dos casos.

| Recorte | Municípios | Pontos | CAPEX potencial **[E]** |
|---|---|---|---|
| **TAM** — universo suscetível | 2.095 | ~25.000 | R$ 75–150 mi |
| **SAM** — com risco mapeado | 958 | ~11.500 | R$ 35–70 mi |
| **SOM** — alvo em 3–5 anos | 50–100 | 600–1.200 | **R$ 2–7 mi** |

Receita recorrente no cenário SOM, em regime: **R$ 400 mil a R$ 2 mi/ano** **[E]**.

> **Estes números são estimativa de ordem de grandeza, não projeção.** Servem
> para responder "isso é um mercado de milhões ou de bilhões?" — e a resposta é
> **dezenas de milhões de CAPEX potencial no Brasil**, com captura realista na
> casa de poucos milhões em horizonte de anos. Não é mercado que sustenta
> capital de risco agressivo; é mercado que sustenta um produto sólido dentro de
> uma empresa que já vende para prefeituras.

---

## 5. Leitura estratégica

**O ativo mais valioso aqui não é o hardware — é o canal.** A Geopixel já vende
para prefeituras, já tem instância em produção em Caraguatatuba e já é
fornecedora homologada. O custo de aquisição de cliente para uma empresa
entrante neste mercado é alto; para quem já está dentro, é marginal.

Isso inverte a leitura de viabilidade: **o Sentinela não precisa abrir mercado,
precisa aprofundar um mercado já aberto** — vendendo mais para quem já compra,
com um produto que a concorrência de software não tem
([GEOPIXEL.md](GEOPIXEL.md) §4.7).

**Concentre no Sudeste.** Mais da metade da população exposta, o cenário
calibrado, e a proximidade de Caraguatatuba como piloto.

**O ciclo reativo pode ser mitigado** posicionando o produto como
**infraestrutura contínua de monitoramento** — com recorrência — e não como
resposta a evento. Contrato plurianual protege contra a sazonalidade.

---

## 6. Pendências desta frente

| ID | Item | Situação |
|---|---|---|
| M-01 | Obter a base de setores de risco do CPRM/SGB por município | **Bloqueada na fonte para o piloto:** em 01/08/2026 a camada oficial consultada não continha feições nem município distinto para Caraguatatuba (`3510500`); não substituir por vazio ou classificação inventada |
| M-02 | Acompanhar publicação da atualização com Censo 2022 | **[?]** |
| M-03 | Validar preço por ponto com um município real | **[?]** — premissa não testada |
| M-04 | Mapear editais recentes de monitoramento geotécnico municipal | **[?]** |
| M-05 | Avaliar consórcios intermunicipais como canal | **[?]** |
