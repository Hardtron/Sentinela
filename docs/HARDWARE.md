# Hardware

## Inventário disponível

| Qtd | Item | Observação |
|---|---|---|
| **6** | Heltec WiFi LoRa 32 **V2** | ESP32-D0WDQ6, SX1276, OLED, 915 MHz |
| 1 | Raspberry Pi 4 | Bridge/servidor de bancada |
| **2** | Antena, **2 dBi** | Único par disponível — ver §"Restrição de antenas" |
| **2** | Bateria, Li-ion **NCR18650B** (Panasonic, 3,7 V, ~3400 mAh nominal) | Instaladas na `HTC-01` **antiga** (retirada) e na `HTC-02`, 31/07/2026 — ver §"Baterias" |
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
| `HTC-01` | Nó de desenvolvimento — PINGER (**placa substituta**, ver §troca) | `bench_01` **até o enlace ser confirmado**; depois `node_dev` | Bancada, USB do MacBook |
| `HTC-02` | Nó par de alcance — PONGER | `bench_02` — **sem antena desde 31/07/2026** (remanejada para HTC-03) | Bancada |
| `HTC-03` | Gateway/Farol — PONGER (**placa de display defeituoso**, ver §troca-03) | `bridge` — RF-ativo, **com antena** | USB do RPi 4, destino: telhado |
| `HTC-04` | Nó de campo (display funcional) — **aguarda antena** | `bench_04` **obrigatório** enquanto não houver antena (A-003) | Solta na bancada |
| `HTC-05` | **Única reserva restante** — a outra virou `HTC-01` | `bench_05` até antena disponível | — |
| ~~`HTC-06`~~ | **Não existe placa física** — a designação era de uma das duas reservas, agora promovida a `HTC-01` | — | — |

O firmware de bancada permite validar **todas as 6 placas hoje** — flash,
MAC, SPI do rádio, OLED, barramento I2C dos sensores, ADC de bateria, watchdog
— sem gastar as duas antenas e sem risco ao PA. Quando bateria e sensores
chegarem, o hardware já está com defeito de fábrica descartado.

### Identificação individual

Os CP2102 destas placas **têm todos o mesmo número de série USB (`0001`)**, então
a porta não distingue uma da outra: com só uma conectada, ela sempre aparece
como `/dev/cu.usbserial-0001`. O que identifica cada placa é o **MAC do ESP32**.

| ID | MAC | Flash | Situação |
|---|---|---|---|
| `HTC-01` | `3c:71:bf:8c:33:a8` | 4 MB | **placa substituta desde 31/07/2026** |
| ~~`HTC-01` (antiga)~~ | `3c:71:bf:8c:2c:d0` | 4 MB | **DANIFICADA — fora do projeto** |
| `HTC-02` | `3c:71:bf:8c:2f:9c` | 4 MB | bancada, sem antena |
| `HTC-03` | `3c:71:bf:8c:2f:a4` | 4 MB | **gateway desde 31/07/2026** — display defeituoso, irrelevante no telhado |
| `HTC-04` | `3c:71:bf:8c:31:70` | 4 MB | **liberada para campo** — display funcional; **sem antena** |
| `HTC-05` | **[?]** a identificar na primeira gravação | — | única reserva restante |

Ao gravar cada placa nova pela primeira vez, registrar o MAC aqui — é o que
resolve a ambiguidade do E-005/A-009 quando várias placas passam pela mesma
porta ao longo do tempo.

### Troca da placa do posto `HTC-01` — 31/07/2026

A placa original do posto `HTC-01` (`3c:71:bf:8c:2c:d0`) foi **retirada do
projeto por dano aparente**. Uma das duas reservas nunca gravadas assumiu o
posto, com MAC `3c:71:bf:8c:33:a8`.

**`HTC-01` passa a designar o posto do PINGER (`NODE_ID=1`, `node_dev`), não
uma placa física específica.** Os dois MACs ficam registrados acima com data
porque **os ensaios 01, 01b, 02 e 03a foram feitos com a placa antiga** — sem
essa distinção não haveria como dizer qual hardware produziu qual medição, e
o histórico de campo perderia rastreabilidade (a mesma razão de existir a
tabela de MACs).

**Consequência no inventário:** as designações `HTC-05` e `HTC-06` nunca
estiveram ligadas a placas físicas (ambas apareciam como **[?]**). Com uma
delas promovida a `HTC-01`, resta **uma única reserva**, mantida como
`HTC-05`. **Não há `HTC-06` físico** — o ambiente `bench_06` continua no
`platformio.ini` como alvo de build, mas não corresponde a placa nenhuma
hoje.

**[?] Causa do dano na placa antiga não foi diagnosticada.** Ela vinha do
episódio de alimentação por bateria (E-008) e chegou a rodar `node_dev`
normalmente depois disso, com enlace fechando. Não há laudo — só o
comportamento observado pelo usuário. Se voltar a ser útil investigar,
medir potência de saída é o teste que separa PA degradado de outra falha.

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

## Troca da placa do posto `HTC-03` — 31/07/2026 {#troca-03}

Uma das 6 placas tem o **display OLED com defeito** (tela permanece
escura/sem imagem). Ela era a `HTC-04`, de bancada. **Passou a ocupar o posto
do gateway (`HTC-03`)**, e a placa que estava no gateway (display funcional)
foi liberada para campo.

**O raciocínio é bom e vale registrar:** o gateway vai ficar **no telhado**.
Display ali não é só dispensável — é inútil, porque ninguém vai subir para
olhar a tela. Já o nó de campo é carregado na mão pelo operador, que **lê o
RSSI e o veredito na tela enquanto caminha** (ROTEIRO_CAMPO.md). Ou seja: a
placa defeituosa foi para o único posto onde o defeito não custa nada, e a
boa foi para o posto onde a tela é ferramenta de trabalho. Nada foi
desperdiçado.

| Posto | Placa (MAC) | Display | Papel |
|---|---|---|---|
| `HTC-03` | `3c:71:bf:8c:2f:a4` | **defeituoso** | gateway no telhado — não precisa de tela |
| `HTC-04` | `3c:71:bf:8c:31:70` | funcional | nó de campo — a tela é o instrumento |

### O que isso muda no plano de firmware headless

A `HTC-04` existia para forçar a validação do firmware **sem tela**
(`lib/app/`, `lib/hal/esp32/` sem depender de `ui_dev.h`, ADR-004) — o nó de
campo definitivo não terá display. Essa exigência **não sumiu: mudou de posto
e ficou mais forte.**

Agora quem não tem tela utilizável é o **gateway**, e ele vai para um telhado,
onde diagnóstico presencial é caro. Isso torna obrigatório o que antes era
exercício: **a `HTC-03` precisa ser inteiramente diagnosticável à distância**
— por serial, LED e, principalmente, pela telemetria de saúde que ela já
publica em `sentinela/bridge/<id>/saude` (RC-02).

**⚠ Risco pendente:** a placa `31:70` saiu do gateway **ainda com o firmware
`bridge` gravado, que é RF-ativo**, e está **sem antena** (as duas antenas
estão na `HTC-01` e na `HTC-03`). Ligá-la nessa condição transmite sem carga e
degrada o PA (A-003) — foi exatamente assim que se perdeu uma placa no E-007.
**Gravar `bench_04` nela antes de energizá-la**, e só voltar a papel RF-ativo
quando houver uma terceira antena (P-011).

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

### Compatibilidade da NCR18650B com a Heltec V2 **[L]**

**Compatível quanto à química e à tensão.** A NCR18650B é célula Li-ion
única, 3,6–3,7 V nominal, carga até 4,2 V — exatamente a faixa do
gerenciamento de bateria embarcado da V2, que a documentação da Heltec
descreve como *"Li-Po battery management system"* com carga/descarga,
proteção de sobrecarga, detecção de nível e **chaveamento automático
USB/bateria**. O circuito não distingue formato cilíndrico 18650 de pouch
LiPo: o que importa é a curva de tensão de célula única, e ela é a mesma.

**A capacidade é que muda a conta:** ~3400 mAh da NCR18650B contra as
poucas centenas de mAh típicas de pouch pequena. Isso favorece autonomia,
mas **alonga muito o tempo de carga** — a 0,200 A observados, uma célula
vazia levaria da ordem de **17 h** para encher (3400/200). Não é defeito; é
consequência de carregar célula grande com corrente modesta.

**Ponto de atenção — corrente de pico em transmissão.** O papel `node_dev`
(PINGER) transmite a 17 dBm a cada 3 s; o pico do PA soma-se ao consumo do
resto da placa. Com célula ainda pouco carregada, ou com resistência de
contato no suporte 18650, esse pico pode derrubar a tensão abaixo do limiar
do detector de *brownout* do ESP32 e reiniciar a placa em laço — sintoma que
de fora parece "placa morta". A página **BATERIA** exibe justamente o motivo
do último reinício (`esp_reset_reason()`): se for esse o caso, ela mostra
`reset: brownout`. É o diagnóstico direto, sem precisar de serial.

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
