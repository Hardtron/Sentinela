# Hardware

## Inventário disponível

| Qtd | Item | Observação |
|---|---|---|
| **6** | Heltec WiFi LoRa 32 **V2** | ESP32-D0WDQ6, SX1276, OLED, 915 MHz |
| 1 | Raspberry Pi 4 | Bridge/servidor de bancada |
| **2** | Antena, **2 dBi** | Único par disponível — ver §"Restrição de antenas" |
| 0 | Bateria | **Não adquirida** |
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
| **RF-ativo** (`node_dev`, `node_range`) | Transmite periodicamente | **Sim, obrigatório** |
| **Bancada** (`ROLE_BENCH`) | Inicializa o rádio, escuta passivamente, nunca transmite; testa OLED, I2C, ADC, watchdog | Não — seguro sem antena |

**Regra prática:** as 2 antenas ficam sempre nas placas RF-ativas do momento
(hoje `HTC-01`/`HTC-02`). As demais rodam em modo bancada até uma antena ficar
disponível para um teste específico (ex.: varredura de SF, segundo Farol). Ver
`firmware/platformio.ini`, ambientes `bench_*`.

## Alocação das 6 placas

| ID | Papel | Firmware | Onde |
|---|---|---|---|
| `HTC-01` | Nó de desenvolvimento — PINGER | `node_dev` | Bancada, USB do MacBook, **com antena** |
| `HTC-02` | Nó par de alcance — PONGER | `node_range` | Campo/bancada, **com antena** |
| `HTC-03` | Bridge do Raspberry Pi 4 (fase 2) | `bench_03` até antena disponível, depois `bridge` | USB do RPi 4 |
| `HTC-04` | Futuro nó de sensores (fase 1) | `bench_04` até sensor disponível | Bancada, protoboard |
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
| `HTC-03` | **[?]** a identificar na primeira gravação | — |
| `HTC-04` | **[?]** a identificar na primeira gravação | — |
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

## Rádio

O módulo é a variante de alta banda do SX1276 (~863–928 MHz).

**Operação no Brasil: 915–928 MHz.** A Anatel libera radiação restrita em
902–907,5 MHz e 915–928 MHz; a janela **907,5–915 MHz não é permitida**.

Frequência de trabalho adotada em P2P: **916,8 MHz** (equivalente ao canal 8 do
plano AU915), confortavelmente dentro da faixa alta permitida. Ao migrar para
LoRaWAN: **AU915, sub-banda 2** (canais 8–15, 916,8–918,2 MHz).

> **Nunca transmitir sem antena conectada.** O PA do SX1276 sem carga se degrada.

## Consumo — limitação conhecida da V2

A Heltec V2 consome tipicamente **~800 µA a 1 mA em deep sleep**, contra os
~20 µA teóricos do ESP32, por causa do regulador e do CP2102 permanentemente
alimentados.

Isso é irrelevante em bancada e **inviabiliza a V2 como nó de campo autônomo**.
Ver ADR-004 para o caminho de migração.
