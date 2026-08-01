# Grandezas monitoradas

> **Proveniência.** Números e afirmações neste documento seguem a política de
> [REFERENCIAS.md](REFERENCIAS.md): **[M]** medido em ensaio próprio, **[N]**
> norma, **[L]** literatura revisada, **[G]** fonte governamental, **[E]**
> estimativa própria derivada, **[?]** pendente de referência.

## Premissa que orienta a escolha

Encosta não avisa com vibração — avisa com **deslocamento lento**.

O processo típico de um deslizamento deflagrado por chuva é: precipitação
satura o solo → a poropressão sobe → a coesão cai → o talude entra em *creep*,
movendo-se milímetros por dia durante horas ou dias → ruptura.

Duas consequências diretas para a instrumentação:

1. Um acelerômetro medindo **vibração** só percebe a ruptura, quando já não há
   o que alertar. O mesmo sensor usado como **inclinômetro** — medindo o vetor
   gravidade para detectar que a haste cravada no talude girou frações de grau —
   antecipa o evento. É assim que ele entra no projeto.
2. Sismo regional **não** é detectável por MEMS de baixo custo, e a sismicidade
   brasileira é baixa. "Monitoramento sísmico" não é objetivo do sistema; o que
   o acelerômetro faz é detectar movimento **local** do talude instrumentado.

O preditor de maior peso é **chuva acumulada**. A referência fundacional
brasileira é a curva de **Tatizana et al. (1987)**, que correlaciona chuva
acumulada em 24 h e em 72 h com a ocorrência de escorregamentos na Serra do Mar
([discussão e aplicação](https://www.researchgate.net/profile/Rodolfo-Mendes-2/publication/349413120_Proposicao_de_limiares_criticos_ambientais_para_uso_em_sistema_de_alertas_de_deslizamentos/links/602ed1b34585158939b4703a/Proposicao-de-limiares-criticos-ambientais-para-uso-em-sistema-de-alertas-de-deslizamentos.pdf)) **[L]**.

Operacionalmente, o **CEMADEN** baseia sua atuação em previsão meteorológica,
**limiares de chuva acumulada em 24 h e 72 h por município** e vistorias de
campo, monitorando também **umidade do solo até 3,0 m de profundidade**
([Cemaden/MCTI](https://www.gov.br/cemaden/pt-br)) **[G]**.

O mecanismo físico que liga chuva a ruptura está descrito em ANCORAGEM.md §3:
poropressão positiva com fluxo paralelo à encosta sobre horizonte menos
permeável **[L]**.

## Prioridade de instrumentação

| # | Grandeza | Sensor | Interface | Papel |
|---|---|---|---|---|
| 1 | Chuva acumulada | Báscula (tipping bucket) | Pulso/IRQ | Maior poder preditivo; consumo desprezível |
| 2 | Umidade do solo (2–3 profundidades) | Capacitivo industrial ou TDR | ADC / SDI-12 | Saturação = perda de coesão |
| 3 | Inclinação do talude | ADXL355 (crítico) / ADXL345 (triagem) | SPI / I2C | Detecta movimento precursor |
| 4 | Evento de ruptura | Mesmo acelerômetro, modo interrupção | I2C | Confirma e dispara alerta imediato |
| 5 | Temperatura e umidade do ar | SHT41 ou BME280 | I2C | Contexto; evapotranspiração e secagem |
| 6 | Pressão barométrica | BME280 (mesmo encapsulamento) | I2C | Entrada de frente / tempestade |
| — | Abertura de trinca | Extensômetro de fio ou potenciômetro linear | ADC | Barato e muito diagnóstico |
| — | Nível freático | Piezômetro / sensor de pressão | ADC / I2C | Poropressão medida diretamente |
| — | Tensão de bateria e RSSI | Interno | — | Saúde do nó (requisito RC-03) |

## Estratégia de custo no acelerômetro

Instrumentos MEMS dedicados a inclinometria geotécnica apresentam resolução da
ordem de **0,0025°**
([Sisgeo](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/),
[ESS](https://www.essearth.com/product/geostring-in-place-mems-inclinometer/))
**[L]**. Acelerômetros de uso geral, como o ADXL345, ficam ordens de grandeza
acima disso; o ADXL355, de baixo ruído, se aproxima.

Regra de alocação **[E]**: sensor de baixo ruído nos taludes classificados como
críticos, sensor de triagem na malha ampla. **A definição de qual resolução é
suficiente depende do limiar adotado para o sítio, que é definição geotécnica**
(RESPONSABILIDADE_TECNICA.md §5) — não do projeto.

Valores de preço citados anteriormente foram removidos por não terem cotação
(B-07 em REFERENCIAS.md).

## Nota de calibração

Inclinômetro de campo mede **variação**, não valor absoluto. A referência é
estabelecida na instalação e o que importa é a deriva em relação a ela.
Compensação térmica é obrigatória: MEMS apresenta deriva com temperatura, e um
talude exposto ao sol varia sensivelmente ao longo do dia. Sem compensar, o
ciclo térmico diário tende a aparecer como movimento aparente — esta é a
principal fonte de falso positivo esperada no sistema **[E]**.

Que a instrumentação MEMS de referência declare **baixa dependência térmica**
como característica de projeto **[L]** confirma que o efeito é reconhecido e
precisa ser tratado. **[?]** Quantificar a deriva do sensor escolhido a partir
do datasheet — item B-06 em REFERENCIAS.md.

---

## Revisão de prioridade — 01/08/2026 (ADR-009)

**O pluviômetro saiu do escopo do piloto.** A chuva passa a vir da rede
oficial (CEMADEN/INMET **[G]**), e o primeiro sensor a adquirir passa a ser o
de **umidade de solo**.

O raciocínio, em uma linha: a rede oficial já mede chuva por município melhor
do que um sensor nosso mediria, mas **não mede saturação naquele talude** — e
é a saturação, não a chuva, que rompe a encosta (poropressão, ANCORAGEM.md
§3). Instrumentar o que já existe é gastar; instrumentar o que falta é o
produto.

| Grandeza | Quem mede | Por quê |
|---|---|---|
| Chuva acumulada 24/72 h | **CEMADEN/INMET [G]** | Já existe, é certificado e é juridicamente mais defensável que medição própria não calibrada |
| **Umidade de solo** | **Atalaia** | A rede oficial não tem por talude; é a variável mais próxima do mecanismo de ruptura |
| **Inclinação** | **Atalaia** | Ninguém mede; é o sinal de que o movimento já começou |

Consequência para a decisão local do nó e a releitura do RC-09: ver ADR-009.
