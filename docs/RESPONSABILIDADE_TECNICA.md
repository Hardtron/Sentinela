# Responsabilidade técnica e habilitação profissional

O Sentinela produz informação usada para decidir sobre risco à vida, e tem como
cliente órgão público. Isso torna a questão da habilitação profissional um
requisito de viabilidade, não uma formalidade posterior.

> **Este documento não é parecer jurídico.** Mapeia o que se aplica e o que
> precisa ser confirmado junto ao CRT-SP, ao CREA-SP e a advogado. Os itens
> marcados **[CONFIRMAR]** não devem ser assumidos como resolvidos.

---

## 1. Resposta curta

**A formação atual não inviabiliza o projeto — mas define uma fronteira clara
sobre o que pode ser assinado.**

O ponto que resolve a maior parte da questão: **desenvolver o sistema e assinar
o laudo geotécnico são coisas diferentes, feitas por pessoas diferentes, e isso
é normal em engenharia.** Quem projeta um monitor cardíaco não precisa ser
médico; o diagnóstico é do médico, e o fabricante responde pelo equipamento.

Aqui vale o mesmo: o desenvolvedor responde pelo **instrumento**; o geotécnico
responde pela **interpretação**; a Defesa Civil responde pela **decisão**.

---

## 2. Correção factual: técnico industrial não se registra mais no CREA

Desde a **Lei nº 13.639/2018**, os técnicos industriais têm conselho próprio —
o **CFT** (Conselho Federal dos Técnicos Industriais) e os **CRTs** regionais.
O registro do Técnico em Mecatrônica é no **CRT**, não no CREA.

As atribuições específicas do Técnico em Mecatrônica estão na
[Resolução CFT nº 120/2020](https://www.crtsp.gov.br/wp-content/uploads/2020/12/RESOLUCAO-no-120.2020-Define-as-Atribuicoes-do-Tecnico-em-Mecatronica.pdf).

Consequência prática: o técnico emite **TRT** (Termo de Responsabilidade
Técnica) pelo CRT, não ART pelo CREA. **[CONFIRMAR]** com o CRT-SP a forma
correta para este caso.

---

## 3. As três camadas de responsabilidade

A confusão nesse tipo de projeto vem de tratar como uma só coisa o que são três:

| Camada | O que é | Quem responde |
|---|---|---|
| **1. Produto** | O equipamento funciona conforme especificado | Fabricante, com responsável técnico |
| **2. Aplicação** | Onde instrumentar, o que a leitura significa naquele talude | **Engenheiro geotécnico ou geólogo, com ART** |
| **3. Decisão** | Alertar, evacuar, interditar | **Defesa Civil / poder público** |

O projeto já está desenhado com essa separação — é o que RC-00 estabelece
(REQUISITOS.md). Isso não foi acidente: é o que torna o arranjo defensável.

---

## 4. O que a formação atual permite

**Técnico em Mecatrônica**, conforme o
[Decreto nº 90.922/1985](https://www2.camara.leg.br/legin/fed/decret/1980-1987/decreto-90922-6-fevereiro-1985-441525-publicacaooriginal-1-pe.html),
art. 4º, e a Resolução CFT 120/2020:

- **executar e conduzir a execução técnica** de trabalhos profissionais
- **orientar e coordenar equipes** de instalação, montagem, operação, reparo e
  manutenção
- **prestar assistência técnica e assessoria no estudo de viabilidade e
  desenvolvimento de projetos e pesquisas tecnológicas**

Essa última é literal no decreto e cobre boa parte do que o projeto é hoje.

Aplicado ao Sentinela, isso abrange:

- desenvolvimento do hardware, firmware e integração dos sensores
- condução técnica da **instalação e manutenção** dos equipamentos em campo
- coordenação da equipe de instalação
- ensaios de propagação, caracterização de enlace, dimensionamento de rede
- assessoria técnica no desenvolvimento do produto

**Limite explícito do decreto:** *"Nenhum profissional poderá desempenhar
atividades além daquelas que lhe competem pelas características de seu currículo
escolar."* A mecatrônica cobre eletrônica, instrumentação e automação — **não
cobre geotecnia nem estabilidade de encostas**.

**Software não é profissão regulamentada** no Brasil. Toda a camada de firmware,
backend, banco e painel pode ser desenvolvida e assinada sem conselho algum.
O curso de ADS agrega competência, não habilitação — e aqui isso não é
limitação.

---

## 5. O que exige outro profissional

| Atividade | Quem pode | Por quê |
|---|---|---|
| Laudo de estabilidade de talude, fator de segurança, superfície de ruptura | **Eng. civil/geotécnico ou geólogo, com ART** | ABNT NBR 11682; atividade privativa |
| Definir onde e a que profundidade instrumentar, com base geotécnica | **Eng. geotécnico ou geólogo** | Decorre da análise de estabilidade |
| Interpretar a leitura como indicativo de risco de ruptura | **Eng. geotécnico ou geólogo** | É diagnóstico, não medição |
| Projeto de SPDA e aterramento | **Eng. eletricista** | ABNT NBR 5419 |
| Responsabilidade técnica na homologação Anatel | **[CONFIRMAR]** com o OCD | Resolução Anatel 715/2019 |
| Obra de contenção decorrente do alerta | **Eng. civil** | Fora do escopo do projeto |

A regra que separa as coisas com clareza: **medir é instrumentação; dizer o que
a medida significa em termos de estabilidade é geotecnia.**

O Sentinela mede inclinação, chuva e umidade — isso é instrumentação. Afirmar
"este talude vai romper" é geotecnia, e não pode partir do sistema nem do seu
desenvolvedor.

---

## 6. A Geografia é a formação mais estratégica do conjunto

Vale mais atenção do que costuma receber. O **Geógrafo** é profissão
regulamentada pela
[Lei nº 6.664/1979](https://planalto.gov.br/ccivil_03/leis/1970-1979/L6664.htm),
**com registro no CREA** e ART própria, vinculada a **meio ambiente, ordenamento
territorial e cartografia**.

Competências que incidem diretamente no núcleo de valor do produto:

- reconhecimentos, levantamentos, estudos e pesquisas de caráter
  **físico-geográfico** e **antropogeográfico**
- **mapeamento** e cartografia temática
- **ordenamento territorial** e análise ambiental

Traduzindo para o produto: **a camada que dá valor ao Sentinela — cruzar
telemetria georreferenciada com suscetibilidade, uso do solo e população
exposta — cai dentro da atribuição do geógrafo.** É exatamente o diferencial
descrito em GEOPIXEL.md §4.

**Distinção fina, e importante:**

| Atividade | Geógrafo | Geotécnico |
|---|---|---|
| **Mapeamento de suscetibilidade** em escala municipal | **Sim** | Sim |
| Análise territorial, exposição, ordenamento | **Sim** | — |
| **Laudo de estabilidade de um talude específico** | **Não** | Sim |
| Fator de segurança, parâmetros de resistência do solo | **Não** | Sim |

Concluir a Geografia dá registro profissional em uma habilitação que cobre a
metade do produto que ninguém mais na empresa provavelmente cobre. **É o caminho
de habilitação mais rápido e mais aderente ao projeto** — mais do que seria uma
engenharia genérica.

**[CONFIRMAR]** com o CREA-SP quais ARTs de geógrafo se aplicam a mapeamento de
áreas de risco, e onde exatamente termina a atribuição.

---

## 7. Arranjos que viabilizam o projeto

Nenhum deles depende de mudar de formação.

**A. Responsável técnico na empresa.** A Geopixel — ou a empresa que
comercializar — mantém RT habilitado registrado. O desenvolvimento é conduzido
por você; a RT do produto é da empresa. É o arranjo mais comum na indústria.

**B. Parceria com geotécnico.** Engenheiro geotécnico ou geólogo, contratado ou
sócio, assina a camada de aplicação: onde instrumentar, limiares por talude,
interpretação. Pode ser por projeto, não precisa ser em tempo integral.

**C. Parceria acadêmica.** Universidade com laboratório de geotecnia agrega ART
de professores, validação científica e credibilidade institucional — que pesa em
contratação pública. Também abre publicação conjunta a partir da série histórica
(GEOPIXEL.md §4.3).

**D. Convênio com a Defesa Civil municipal.** Ela frequentemente já tem
engenheiro ou geólogo no quadro, e é a autoridade do alerta. Formaliza a camada 3.

**Recomendado: A + B desde a fase 4**, com C quando houver piloto real.

---

## 8. Exposição a risco, e como reduzi-la

Sendo direto: **num sistema de alerta de desastre, existe exposição civil e
potencialmente criminal se houver falha e dano.** Isso vale para o fabricante,
para quem instalou e para quem interpretou — cada um na sua camada. Não é motivo
para desistir; é motivo para estruturar.

O que reduz exposição, e já está no projeto:

| Medida | Onde |
|---|---|
| Posicionamento explícito como apoio à decisão | RC-00 |
| Nunca acionar evacuação de forma autônoma | RC-00 |
| Rastreabilidade: todo alerta guarda o dado bruto | RC-10 |
| Heartbeat e detecção de nó silencioso | RC-01, RC-02 |
| Sensor falho reportado, nunca mascarado | RC-07 |
| Registro de erros e decisões | LOG.md, ERROS.md |

O que ainda falta:

- **contrato** delimitando responsabilidade por camada, e explicitando que o
  sistema não substitui inspeção nem julgamento técnico
- **seguro de responsabilidade civil profissional** **[CONFIRMAR]** viabilidade
  e custo
- **manual de operação** com limitações declaradas — o que o sistema não detecta
  (movimento profundo, ruptura súbita sem precursor, falha durante queda de
  energia prolongada)
- **termo de aceitação** do órgão contratante reconhecendo os limites

A documentação técnica rigorosa do repositório — decisões registradas, erros
assumidos, limitações declaradas — **é também instrumento de defesa**. Mostra
diligência, e diligência documentada é o que separa acidente de negligência.

---

## 9. Conclusão

**Você pode conduzir este projeto.** O desenvolvimento do instrumento, os
ensaios, o dimensionamento da rede, a instalação e a plataforma de software estão
dentro do que sua formação atual permite — e a parte de software não exige
habilitação nenhuma.

**Você não pode, sozinho, assinar a camada geotécnica**, e não deve tentar. Ela
precisa de engenheiro ou geólogo com ART, por projeto ou por parceria.

**A Geografia muda o quadro de forma relevante** e vale priorizar: dá registro no
CREA e cobre justamente a camada geoespacial que é o diferencial competitivo do
produto.

O que **não** funciona é o meio-termo: desenvolver o sistema e deixar a camada
geotécnica implícita, sem responsável declarado. Nesse arranjo, na prática a
responsabilidade recai sobre quem entregou o sistema — que é a pior posição
possível, porque acumula o risco sem a habilitação.

---

## 10. Ações

| ID | Ação | Quando |
|---|---|---|
| R-01 | Confirmar no **CRT-SP** o registro como Técnico em Mecatrônica e o alcance do TRT | Antes da fase 4 |
| R-02 | Confirmar no **CREA-SP** as ARTs de geógrafo aplicáveis a mapeamento de risco | Ao concluir a graduação |
| R-03 | Identificar **engenheiro geotécnico ou geólogo** parceiro | Antes do piloto |
| R-04 | Verificar com OCD quem assina a responsabilidade técnica na homologação Anatel | Junto com C-01 |
| R-05 | Consultar advogado sobre contrato, limites e seguro de RC profissional | Antes da proposta comercial |
| R-06 | Redigir manual com limitações declaradas do sistema | Antes do piloto |

**Fontes:**
[Decreto nº 90.922/1985](https://www2.camara.leg.br/legin/fed/decret/1980-1987/decreto-90922-6-fevereiro-1985-441525-publicacaooriginal-1-pe.html) ·
[Resolução CFT nº 120/2020 — Atribuições do Técnico em Mecatrônica](https://www.crtsp.gov.br/wp-content/uploads/2020/12/RESOLUCAO-no-120.2020-Define-as-Atribuicoes-do-Tecnico-em-Mecatronica.pdf) ·
[Lei nº 6.664/1979 — Profissão de Geógrafo](https://planalto.gov.br/ccivil_03/leis/1970-1979/L6664.htm) ·
[Lei nº 13.639/2018 — Criação do CFT](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13639.htm)
