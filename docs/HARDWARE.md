# Hardware

## Inventário disponível

| Qtd | Item | Observação |
|---|---|---|
| **6** | Heltec WiFi LoRa 32 **V2** | ESP32-D0WDQ6, SX1276, OLED, 915 MHz |
| 1 | Raspberry Pi 4 | Bridge/servidor de bancada |
| **2** | Antena, **2 dBi** | Único par disponível — ver §"Restrição de antenas" |
| **2** | Bateria, Li-ion **NCR18650B** (Panasonic, 3,7 V, ~3400 mAh nominal) | Instaladas em `HTC-01` e `HTC-02`, 31/07/2026 — ver §"Baterias" |
| 0 | Sensor (qualquer grandeza) | **Não adquirido** |
| 0 | Concentrador LoRa (SX1302/SX1303) | **Não adquirido** — ver ADR-002 |

Nenhuma compra realizada até o momento. As fases 0 a 3 foram desenhadas para
rodar integralmente com o inventário acima — mas **dentro da fase 0**, a
combinação "6 placas, 2 antenas, sem bateria, sem sensor" exige uma alocação
que separe o que é seguro fazer agora do que espera peça.

## Restrição de antenas — regra operacional

Só existem **2 antenas** para **6 placas**. A armadilha A-003
(nunca transmitir sem antena — degrada o PA) vale por placa: **uma placa sem
antena não pode rodar firmware que chame `radio.transmit()`.** Receber (RX) é
seguro sem antena — só a transmissão é que arrisca o hardware.

Isso definiu dois papéis de firmware, não um:

| Papel | O que faz | Exige antena? |
|---|---|---|
| **RF-ativo** (`node_dev`, `node_range`, `bridge`) | Transmite periodicamente | **Sim, obrigatório** |
| **Bancada** (`ROLE_BENCH`) | Inicializa o rádio, escuta passivamente, nunca transmite; testa OLED, I2C, ADC, watchdog | Não — seguro sem antena |

**Regra prática:** as 2 antenas ficam sempre nas placas RF-ativas do momento
(hoje `HTC-01`/`HTC-03`). As demais rodam em modo bancada até uma antena ficar
disponível para um teste específico (ex.: varredura de SF, segundo Farol). Ver
`firmware/platformio.ini`, ambientes `bench_*`.

**31/07/2026 — antena da `HTC-02` remanejada para a `HTC-03`.** Para validar o
bridge MQTT (fase 2), a antena que estava na `HTC-02` foi movida para a
`HTC-03`, que passou de `bench_03` para `bridge` (RF-ativo, PONGER). A
`HTC-02` ficou sem antena e foi regravada para `bench_02` no mesmo momento,
por segurança (A-003/A-010) — ela não deve voltar a rodar `node_range` até
receber antena de novo.

## Alocação das 6 placas

| ID | Papel | Firmware | Onde |
|---|---|---|---|
| `HTC-01` | Nó de desenvolvimento — PINGER | `node_dev` | Bancada, USB do MacBook, **com antena** |
| `HTC-02` | Nó par de alcance — PONGER | `bench_02` — **sem antena desde 31/07/2026** (remanejada para HTC-03) | Bancada |
| `HTC-03` | Bridge do Raspberry Pi 4 (fase 2) | `bridge` — **RF-ativo, com antena desde 31/07/2026** | USB do RPi 4 |
| `HTC-04` | **Display defeituoso** — firmware headless (`lib/app`/`lib/hal`) | `bench_04` até sensor disponível | Bancada, protoboard |
| `HTC-05` | Reserva / par de varredura de SF | `bench_05` até antena disponível | — |
| `HTC-06` **novo** | Segundo Farol (diversidade multi-gateway, ADR-001) / spare | `bench_06` até antena disponível | — |

O firmware de bancada permite validar **todas as 6 placas hoje** — flash,
MAC, SPI do rádio, OLED, barramento I2C dos sensores, ADC de bateria, watchdog
— sem gastar as duas antenas e sem risco ao PA. Quando bateria e sensores
chegarem, o hardware já está com defeito de fábrica descartado.

### Identificação individual

Os CP2102 destas placas **têm todos o mesmo número de série USB (`0001`)**, então
a porta não distingue uma da outra: com só uma conectada, ela sempre aparece
como `/dev/cu.usbserial-0001`. O que identifica cada placa é o **MAC do ESP32**.

| ID | MAC | Flash |
|---|---|---|
| `HTC-01` | `3c:71:bf:8c:2c:d0` | 4 MB |
| `HTC-02` | `3c:71:bf:8c:2f:9c` | 4 MB |
| `HTC-03` | `3c:71:bf:8c:31:70` | 4 MB |
| `HTC-04` | `3c:71:bf:8c:2f:a4` | 4 MB |
| `HTC-05` | **[?]** a identificar na primeira gravação | — |
| `HTC-06` | **[?]** a identificar na primeira gravação | — |

Ao gravar cada placa nova pela primeira vez, registrar o MAC aqui — é o que
resolve a ambiguidade do E-005/A-009 quando várias placas passam pela mesma
porta ao longo do tempo.

Antes de gravar, conferir qual placa está na porta:

```bash
esptool.py --port /dev/cu.usbserial-0001 flash_id
```

O comando mostra MAC e tamanho de flash de uma vez — resolve a identificação e a
verificação exigida pelo E-005 na mesma chamada.

## Identificação do SoC

Lido diretamente do chip via esptool em 30/07/2026:

```
Chip:     ESP32-D0WDQ6, revisão v1.0, dual core 240 MHz, WiFi + BT
Cristal:  26 MHz          (assinatura Heltec/TTGO; dev boards genéricas usam 40 MHz)
Flash:    4 MB (Winbond ef:4016)
MAC:      3c:71:bf:8c:2c:d0
Bridge:   CP2102 (Silicon Labs) → /dev/cu.usbserial-0001
```

O ESP32-D0WDQ6 confirma **V2** (a V3 usa ESP32-S3 + SX1262). Confirmado
fisicamente pelo rótulo `868-915MHz`, conector de bateria e botões PRG/RST
junto ao USB.

### Driver USB no macOS

O CP2102 usa o **driver CP210x nativo do macOS**. Não instalar o pacote da
Silicon Labs — kext de terceiros em macOS recente causa mais problema do que
resolve. A porta enumera sozinha.

## Firmware de fábrica

As placas vieram com o FactoryTest da Heltec (strings `HelTec_AutoMation`,
`hunter_3120`, `LoRa Initial success!`), particionamento Arduino `default_ota`.

Um dump íntegro dos 4 MB da `HTC-01` foi feito antes de qualquer gravação.
**O dump não está versionado** (binário de 4 MB, ver `.gitignore`); guardar
fora do repositório se houver interesse em restaurar o estado de fábrica.

## Pinagem — Heltec WiFi LoRa 32 V2

| Função | GPIO |
|---|---|
| SX1276 SCK / MISO / MOSI | 5 / 19 / 27 |
| SX1276 NSS / RST | 18 / 14 |
| SX1276 DIO0 / DIO1 / DIO2 | 26 / 35 / 34 |
| OLED SSD1306 SDA / SCL / RST | 4 / 15 / 16 |
| Vext (alimentação de periféricos) | 21 — **ativo em nível BAIXO** |
| LED | 25 |
| Botão PRG | 0 |
| ADC de bateria | 37 |

### GPIOs livres para sensores

`2, 12, 13, 17, 22, 23, 32, 33` e os **input-only** `36, 38, 39`.

Armadilhas conhecidas:

- **GPIO 12** é strapping pin (MTDI). Nível alto no boot seleciona 1,8 V para a
  flash e a placa não sobe. Evitar, ou garantir pull-down externo.
- **GPIO 34–39** são somente entrada e **não têm pull-up interno**.
- **GPIO 0** é o botão PRG e também strapping de boot.
- O barramento I2C do OLED (4/15) é compartilhável, mas sensores externos devem
  usar um segundo barramento (`Wire1`, sugerido 22/23) para que um sensor
  travado em campo não derrube o display de diagnóstico.

## A bobina de cobre soldada perto do PRG — não é antena de LoRa

Fotos reais de uma das 6 placas (31/07/2026) mostram uma pequena bobina de
cobre (mola, ~4 voltas, ~3 mm de diâmetro) soldada diretamente na PCB perto do
botão PRG, separada do conector u.FL/SMA usado pela antena externa.

**Identificação: é a antena de WiFi/Bluetooth do ESP32 — não tem relação com o
rádio LoRa.** **[E]**, apoiada em duas evidências:

1. A documentação oficial da Heltec para a mesma família de placas (V3/V4)
   descreve exatamente esse tipo de componente como *"metal spring antenna"*
   para **2,4 GHz** — o WiFi/BT embutido no ESP32
   ([docs.heltec.org](https://docs.heltec.org/en/node/esp32/wifi_lora_32/index.html))
   **[L]**. O diagrama de pinagem oficial da própria V2
   ([PDF](https://resource.heltec.cn/download/WiFi_LoRa_32/WIFI_LoRa_32_V2.pdf))
   mostra a foto de uma placa genuína com a mesma bobina na mesma posição —
   confirma que é componente de fábrica, não modificação de terceiro.
2. **Fisicamente não caberia em 915 MHz.** Um quarto de onda em 915 MHz mede
   ~8,2 cm; a bobina tem só ~1,5–2 cm de fio total, dimensão plausível para
   ressonância em 2,4 GHz (WiFi/BT), não em 915 MHz.

**Consequência prática — respondendo à pergunta que motivou a checagem:** essa
bobina **não traz ganho nenhum para o enlace LoRa atual**, com ou sem as
antenas de 6 dBi. Ela está ligada a uma trilha de RF completamente separada,
que vai até o pino de rádio do ESP32, não até o SX1276. Reaproveitá-la para
915 MHz exigiria dessoldar, reencaminhar trilha de RF e casar impedância para
outra frequência — trabalho de retrabalho de placa, não algo acionável agora.

**[?]** Não localizei datasheet específico da V2 com esse componente
explicitamente rotulado (só o da V3/V4, mesma linguagem). Se aparecer dúvida
que justifique confirmação absoluta, abrir a placa com defeito de display
(abaixo) para inspecionar a trilha sob a bobina é o próximo passo, já que essa
placa está reservada para intervenção física.

## Placa com display defeituoso — reservada para firmware sem tela

Uma das 6 placas tem o **display OLED com defeito** (identificado em
31/07/2026 — tela permanece escura/sem imagem). Em vez de ser uma perda,
resolve um problema real do projeto: **o nó de campo definitivo não tem
display** (`ui_dev.h`, ADR-004) — o firmware de bring-up depende da tela hoje,
mas `lib/app/` e `lib/hal/` precisam funcionar sem ela.

**Decisão:** esta placa vira `HTC-04`, dedicada ao desenvolvimento do firmware
**headless** — `lib/app/` e `lib/hal/esp32/` sem qualquer dependência de
`ui_dev.h`. Como ela fisicamente não pode mostrar nada, força a validação real
de que o caminho de campo não depende de tela — em vez de "esquecer" de testar
sem OLED numa placa saudável.

Diagnóstico só por serial e pelo LED nessa placa; útil também para simular,
desde já, como o nó de campo vai se comportar quando o display for removido
por completo no hardware definitivo (STM32WLE5, ADR-004).

## Rádio

O módulo é a variante de alta banda do SX1276 (~863–928 MHz).

**Operação no Brasil: 915–928 MHz.** A Anatel libera radiação restrita em
902–907,5 MHz e 915–928 MHz; a janela **907,5–915 MHz não é permitida**.

Frequência de trabalho adotada em P2P: **916,8 MHz** (equivalente ao canal 8 do
plano AU915), confortavelmente dentro da faixa alta permitida. Ao migrar para
LoRaWAN: **AU915, sub-banda 2** (canais 8–15, 916,8–918,2 MHz).

> **Nunca transmitir sem antena conectada.** O PA do SX1276 sem carga se degrada.

## Baterias

**31/07/2026 [M]** — duas células **Panasonic NCR18650B** (Li-ion, 3,7 V
nominal, 3400 mAh nominal pelo datasheet do fabricante) instaladas em
`HTC-01` e `HTC-02`, ligadas ao conector JST 2 pinos de bateria da Heltec V2
(a mesma placa que já carrega e monitora tensão via o pino `PIN_VBAT_ADC`).
Etiqueta confirmada por foto: `NCR18650B Li-ion MH12210`.

Fecha **P-012** — a medição de autonomia (item aberto da Fase 0) deixa de
depender de compra.

### Corrente de carga observada

Medidor USB em série com a `HTC-02` durante o carregamento: **0,200 A**. É
a corrente que o circuito carregador da placa está entregando à célula, não
o consumo do circuito em operação (não confundir com os 81 mA/423 mW
medidos em operação normal, seção abaixo — são medições de fenômenos
diferentes: uma é o carregador enchendo a bateria, a outra é o rádio+MCU
consumindo dela).

**[?]** O datasheet do carregador embarcado na Heltec V2 não foi localizado
— não dá para afirmar se 0,200 A é a corrente máxima de carga ou um patamar
intermediário sem medir a curva completa até a célula sinalizar carga
plena (queda de corrente característica do perfil CC/CV do Li-ion).

## Consumo

### Medido em operação — 31/07/2026 **[M]**

Medidor USB em série com a `HTC-01` rodando `node_dev` (PINGER, SF9, 17 dBm,
ping a cada 3 s, OLED ligado), sem sono:

| Grandeza | Valor |
|---|---|
| Tensão de entrada | 5,223 V |
| Corrente | **81 mA** |
| Potência | **423 mW** |
| Acumulado | 320 mAh / 1,664 Wh em ~3,9 h |

O acumulado dividido pelo tempo dá ~81 mA, **igual à leitura instantânea** — o
consumo é estável, como esperado de um nó que passa quase todo o ciclo em
recepção com rajadas curtas de transmissão.

**Três ressalvas que impedem usar esse número direto para autonomia:**

1. **É medido na entrada USB de 5 V, não no barramento de 3,3 V.** O regulador
   linear da placa não converte, ele dissipa: a corrente de entrada é
   praticamente igual à de saída, então ~267 mW chegam ao circuito e ~156 mW
   viram calor. Alimentar por bateria de 3,7 V muda essa conta.
2. **Inclui o CP2102**, que existe só para a USB e **não existirá no nó de
   campo**.
3. **O OLED estava ligado.** A economia de tela por inatividade
   (`TELA_INATIVIDADE_MS`) foi implementada no mesmo dia; medir com a tela
   apagada quantifica quanto ela custa — ensaio ainda não feito.

**Consequência prática:** a 81 mA contínuos, uma célula de 2000 mAh duraria
**cerca de 25 horas**. Isso confirma pelo lado da medição o que o ADR-004 já
sustentava por outro caminho: **sem sono profundo não existe nó de campo
autônomo**, e a V2 não é a plataforma final.

### Deep sleep — limitação conhecida da V2 **[L]**

A Heltec V2 consome tipicamente **~800 µA a 1 mA em deep sleep**, contra os
~20 µA teóricos do ESP32, por causa do regulador e do CP2102 permanentemente
alimentados. **[?]** Ainda não medido nesta bancada — o firmware atual não
dorme; medir exige a Fase 1.

Isso é irrelevante em bancada e **inviabiliza a V2 como nó de campo autônomo**.
Ver ADR-004 para o caminho de migração.
