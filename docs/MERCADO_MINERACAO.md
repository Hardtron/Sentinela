# Frente 2 — Barragens de mineração

Mineradoras como cliente. Avaliação honesta: o mercado é atraente, e é **mais
difícil** que o municipal.

> **Proveniência.** Segue [REFERENCIAS.md](REFERENCIAS.md).

---

## 1. O universo

| Indicador | Valor | Fonte |
|---|---|---|
| Barragens de mineração no Brasil | **911** | ANM, via [IBRAM](https://ibram.org.br/noticia/relatorio-da-anm-aponta-que-mais-de-68-das-barragens-de-mineracao-do-pais-estao-fora-de-risco/) **[G]** |
| Classificadas sob a PNSB | **461** | ANM **[G]** |
| Em alerta ou emergência (nov/2024) | **118** — recorde histórico | [Observatório da Mineração/Fiocruz](https://observatorio.minas.fiocruz.br/dados/) **[G]** |
| Nível de Emergência 1 | 63 | ANM **[G]** |
| Nível de Emergência 2 | 5 | ANM **[G]** |
| Nível de Emergência 3 (ruptura iminente) | **4** — todas em Minas Gerais | ANM **[G]** |

O salto de 94 para 118 estruturas em situação crítica decorre da
**Resolução ANM nº 175/2024** e da campanha de Declaração de Condição de
Estabilidade **[G]** — ou seja, é resultado de **endurecimento regulatório**,
não necessariamente de degradação física. Para quem vende monitoramento, o
efeito prático é o mesmo: mais estruturas sob exigência.

---

## 2. A obrigação legal é o motor comercial

Este é o ponto que separa o mercado de mineração do municipal.

A **Lei nº 12.334/2010** institui a Política Nacional de Segurança de Barragens.
A **Lei nº 14.066/2020** endureceu o regime e — este é o dispositivo relevante —
passou a exigir que o empreendedor **armazene os dados de instrumentação e os
forneça ao órgão fiscalizador periodicamente e em tempo real quando requerido**
**[N]**.

Traduzindo para o produto: **monitoramento instrumentado com telemetria não é
diferencial competitivo neste setor — é obrigação legal.** O comprador não
precisa ser convencido de que precisa; ele precisa escolher fornecedor.

Some-se a **Resolução ANM nº 95/2022** **[N]**, que detalha requisitos de
segurança, e o quadro é de demanda regulada e permanente.

---

## 3. Por que este mercado é mais difícil que o municipal

Sendo direto, porque a diferença muda a estratégia:

**O comprador é sofisticado e já é atendido.** Mineradoras de grande porte têm
equipe geotécnica própria, contratos com fornecedores estabelecidos e
instrumentação instalada. Não há lacuna de percepção a explorar — há concorrente
a deslocar. Ver [CONCORRENCIA.md](CONCORRENCIA.md).

**O custo do erro é catastrófico e público.** Mariana e Brumadinho definem o
contexto. Nenhuma mineradora troca fornecedor de monitoramento de barragem por
preço, e a barreira de credibilidade para um entrante é severa: exige histórico,
responsável técnico sênior, seguro e, provavelmente, certificação adicional.

**A exigência técnica é maior.** Barragem de rejeito demanda piezômetros,
medidores de nível d'água, marcos superficiais com precisão geodésica, radar de
parede e, frequentemente, **inclinômetro em furo profundo** — que é justamente o
que o desenho atual da Atalaia **não** faz (ANCORAGEM.md §3: mede rotação do
bloco superficial).

**O ciclo de venda é longo** e passa por qualificação de fornecedor, auditoria e
homologação interna.

---

## 4. Onde há espaço real

Não é no núcleo da barragem — é na periferia e nas estruturas menores.

**Estruturas de menor porte e menor criticidade.** Das 911 barragens, muitas são
de pequeno porte, de empresas médias, com instrumentação mínima. É aqui que a
diferença de custo por ponto pesa.

**Adensamento de malha.** Uma barragem monitorada com poucos instrumentos caros
pode ganhar dezenas de pontos de baixo custo em torno — taludes de acesso,
diques auxiliares, encostas marginais, pilhas de estéril. **A proposta não
compete com o inclinômetro de furo; ela adensa a cobertura onde hoje não há
nada.**

**A jusante.** A área potencialmente afetada — a mancha de inundação — precisa
ser monitorada e alertada, e é território geoespacial. Aqui a competência da
Geopixel pesa mais que o hardware.

**Mineradoras médias e pequenas**, sem equipe geotécnica robusta, que precisam
cumprir a lei com orçamento limitado.

---

## 5. Dimensionamento **[E]**

Premissas: 20 a 60 pontos por estrutura em adensamento de malha; preço por ponto
superior ao municipal (**R$ 6.000 a R$ 12.000** **[E]**) por exigência de
robustez, redundância e responsabilidade técnica.

| Recorte | Estruturas | Pontos | CAPEX potencial **[E]** |
|---|---|---|---|
| **TAM** — todas as barragens | 911 | ~35.000 | R$ 200–400 mi |
| **SAM** — classificadas sob PNSB | 461 | ~18.000 | R$ 110–220 mi |
| **SOM** — alvo em 3–5 anos | 5–15 estruturas | 150–600 | **R$ 1–7 mi** |

O ticket por cliente é muito maior que no municipal, e o número de clientes é
muito menor. **Mercado de poucos contratos grandes**, em oposição ao municipal,
de muitos contratos pequenos.

---

## 6. Recomendação

**Não perseguir mineração agora. Entrar depois, pelo flanco.**

A sequência que faz sentido:

1. **Consolidar o municipal primeiro** — onde há canal, piloto e menor barreira
   de credibilidade.
2. **Construir histórico operacional** — meses de dados reais, incidentes
   detectados, disponibilidade medida. É esse histórico que abre a porta na
   mineração.
3. **Entrar por adensamento de malha**, não por substituição de instrumento
   crítico, e preferencialmente por mineradora média.
4. **Considerar parceria** com empresa de instrumentação geotécnica já
   qualificada, entrando como camada de telemetria e geoprocessamento em vez de
   fornecedor primário.

O que **não** funciona: tentar vender a uma grande mineradora um sistema de baixo
custo sem histórico, para monitorar estrutura crítica. A assimetria de risco do
comprador torna a proposta inaceitável independentemente do mérito técnico.

> **Nota de responsabilidade.** Monitoramento de barragem tem responsabilidade
> técnica ainda mais pesada que encosta municipal, e a camada geotécnica é
> obrigatória e sênior — [RESPONSABILIDADE_TECNICA.md](RESPONSABILIDADE_TECNICA.md).
> Entrar neste mercado exige o arranjo de responsável técnico resolvido **antes**,
> não durante.

---

## 7. Pendências desta frente

| ID | Item | Situação |
|---|---|---|
| N-01 | Obter a base pública da ANM com as 911 barragens, porte e classificação | **[?]** |
| N-02 | Ler a Resolução ANM 95/2022 quanto a requisitos de instrumentação | **[?]** |
| N-03 | Verificar se há exigência de certificação de instrumento para aceite | **[?]** |
| N-04 | Mapear fornecedores atuais das mineradoras médias | **[?]** |
| N-05 | Avaliar parceria com empresa de instrumentação já qualificada | **[?]** |
