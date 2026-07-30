# Grandezas monitoradas

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

O preditor de maior peso, consolidado na literatura e a base operacional do
CEMADEN no Brasil, é **chuva acumulada** — limiares do tipo
intensidade-duração, tipicamente sobre acumulados de 24 h, 72 h e 96 h.

## Prioridade de instrumentação

| # | Grandeza | Sensor | Interface | Papel |
|---|---|---|---|---|
| 1 | Chuva acumulada | Báscula (tipping bucket) | Pulso/IRQ | Maior poder preditivo; consumo desprezível |
| 2 | Umidade do solo (2–3 profundidades) | Capacitivo industrial ou TDR | ADC / SDI-12 | Saturação = perda de coesão |
| 3 | Inclinação do talude | ADXL355 (crítico) / ADXL345 (triagem) | SPI / I2C | Detecta *creep* pré-ruptura |
| 4 | Evento de ruptura | Mesmo acelerômetro, modo interrupção | I2C | Confirma e dispara alerta imediato |
| 5 | Temperatura e umidade do ar | SHT41 ou BME280 | I2C | Contexto; evapotranspiração e secagem |
| 6 | Pressão barométrica | BME280 (mesmo encapsulamento) | I2C | Entrada de frente / tempestade |
| — | Abertura de trinca | Extensômetro de fio ou potenciômetro linear | ADC | Barato e muito diagnóstico |
| — | Nível freático | Piezômetro / sensor de pressão | ADC / I2C | Poropressão medida diretamente |
| — | Tensão de bateria e RSSI | Interno | — | Saúde do nó (requisito RC-03) |

## Estratégia de custo no acelerômetro

O ADXL345 (~R$ 20) resolve cerca de 0,2° — suficiente para detectar movimento
grosseiro e para triar quais taludes merecem instrumentação fina. O ADXL355
(~R$ 400) resolve milésimos de grau e é o que efetivamente enxerga *creep*.

Regra de alocação: **ADXL355 apenas nos taludes classificados como críticos**;
ADXL345 na malha ampla. Isso mantém o custo por ponto baixo sem abrir mão da
sensibilidade onde ela decide.

## Nota de calibração

Inclinômetro de campo mede **variação**, não valor absoluto. A referência é
estabelecida na instalação e o que importa é a deriva em relação a ela.
Compensação térmica é obrigatória: MEMS deriva com temperatura, e um talude
exposto ao sol varia dezenas de graus ao longo do dia. Sem compensar, o ciclo
térmico diário vira falso movimento — esta é a principal fonte de falso
positivo esperada no sistema.
