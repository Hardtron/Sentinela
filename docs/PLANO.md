# Plano de desenvolvimento

Diretriz vigente: **gasto financeiro mínimo**. As fases 0 a 3 rodam
integralmente com o inventário já disponível (6 × Heltec V2 + Raspberry Pi 4,
com apenas 2 antenas — ver HARDWARE.md).
Nenhuma compra é necessária antes da fase 4.

---

## Fase 0 — Bring-up do rádio

**Objetivo.** Provar que o hardware funciona e medir o alcance real.

- [x] Firmware de bring-up: SX1276 em 916,8 MHz, OLED, serial
- [x] Display de diagnóstico com 4 páginas navegáveis pelo botão PRG
- [x] Ping-pong entre `HTC-01` e `HTC-02` com RSSI/SNR — ensaio 01, 0% de perda
- [ ] Medição de consumo em operação e em deep sleep
- [x] **Teste de alcance em campo** — ensaio 02, 7 pontos, modelo n = 2,57
- [ ] Levantamento de alcance por spreading factor (SF7 a SF12) — **prioritário**

**Critério de saída.** Curva de alcance × SF documentada em `docs/CAMPO.md`.

**Por que isso vem primeiro.** O alcance real determina quantos gateways por
município, e portanto o custo de implantação. É o número que dimensiona o
projeto inteiro — todo o resto é estimativa até ele existir.

---

## Fase 1 — Sensores e protocolo

**Objetivo.** Nó que lê o ambiente e transmite payload compacto.

- [ ] `lib/proto/` — payload binário versionado (alvo: ≤ 20 bytes)
- [ ] `lib/hal/esp32/` — rádio, I2C, ADC, sono
- [ ] `lib/app/` — máquina de estados, testável no host
- [ ] Sensores de bancada: temperatura, umidade, pressão, acelerômetro
- [ ] Contador de báscula por interrupção, com persistência em NVS
- [ ] Deep sleep com acordar por RTC e por interrupção externa

**Critério de saída.** `HTC-04` transmitindo leituras reais e sobrevivendo a
reinício sem perder acumulado (RC-06).

---

## Fase 2 — Bridge e ingestão

**Objetivo.** Dados chegando ao banco, ponta a ponta.

- [ ] `HTC-03` como receptor, ligada por USB ao Raspberry Pi 4 — aguarda antena
- [x] Bridge serial → MQTT no RPi 4 — `gateway/bridge.py`, testado sem
      hardware via `--simular`; falta instalar no RPi real (acesso pendente)
- [ ] Mosquitto — unidade systemd pronta em `gateway/sentinela-bridge.service`
- [ ] Ingestor MQTT → banco, decodificando `proto/`
- [x] Detecção de nó silencioso (RC-02) — implementada na bridge (saúde
      publicada a cada 30 s); falta o lado do banco/ingestor

**Critério de saída.** Leitura do sensor visível no banco em menos de 5 s.

---

## Fase 3 — Backend e visualização

**Objetivo.** Transformar telemetria em informação de risco.

- [ ] PostgreSQL + TimescaleDB + PostGIS no homeserver
- [ ] Hypertables e agregação contínua de chuva (24 h / 72 h / 96 h)
- [ ] Modelo geoespacial: nós, taludes, áreas de alcance, população exposta
- [ ] Motor de limiar intensidade-duração
- [ ] Dashboard operacional
- [ ] Integração QGIS sobre a mesma base

**Critério de saída.** Alerta simulado produzindo a informação completa —
grandeza medida, limiar violado, área de alcance e exposição.

**Onde está o diferencial.** Esta fase é a que separa o projeto de uma rede de
sensores comum: o cruzamento com a base geoespacial é o que produz decisão, e
é onde a experiência prévia em geoprocessamento pesa mais.

---

## Fase 4 — Nó de campo definitivo

**Primeira fase que exige compra.**

- [ ] Porte de `hal/` para STM32WLE5 (RAK3172) — ADR-004
- [ ] Migração para LoRaWAN + ChirpStack; concentrador SX1302/SX1303
- [ ] Ancoragem por ponteira cravada, tubo galv. 1.1/2" — ANCORAGEM.md
- [ ] Elevar o gateway em vez do sensor; avaliar Yagi 9 dBi — ANCORAGEM.md §7
- [ ] Caixa IP67, alimentação solar, aterramento e proteção contra surto
- [ ] Ensaio de campo prolongado com medição de autonomia

**Compras previstas:** concentrador (R$ 800–1.000) ou gateway pronto
(R$ 1.200–1.800); módulos RAK3172 (R$ 70–90 cada); sensores de campo; caixas
e alimentação.

---

## Fase 5 — Operação

- [ ] Implantação multi-município
- [ ] Monitoramento da própria frota (bateria, heartbeat, link)
- [ ] Procedimento operacional com a Defesa Civil
- [ ] Calibração de limiares com dados históricos locais
- [ ] Plano de manutenção e de reposição

---

## Pendências abertas

| ID | Pendência | Bloqueia |
|---|---|---|
| ~~P-001~~ | ~~Publicar o repositório~~ | **Resolvida em 30/07/2026** — `github.com/Hardtron/Sentinela`, privado |
| P-002 | Definir municípios-piloto e contato na Defesa Civil | Fase 5 |
| P-003 | Definir licença do projeto | Abrir o repositório |
| P-004 | Verificar disponibilidade de dados do CEMADEN para calibrar limiares | Fase 3 |
| P-005 | Calibrar o divisor de tensão de bateria da Heltec V2 | Medição de autonomia |
| P-006 | Consultar OCD sobre homologação Anatel — item C-01 de CONFORMIDADE.md | **Fase 4 / proposta comercial** |
| P-007 | Validar internamente as perguntas de docs/GEOPIXEL.md §6 | Apresentação |
| ~~P-008~~ | ~~Coordenada do `HTC-02`~~ | **Resolvida em 30/07/2026** — −23,57543, −45,330545 |
| ~~P-009~~ | ~~Testar polarização do nó fixo~~ | **Encerrada** — antena estava vertical; causa é o confinamento por muros (CAMPO.md) |
| P-010 | Configurar acesso SSH ao Raspberry Pi 4 (mesmo padrão do homeserver) | Instalação real da bridge |
| P-011 | Comprar 4 antenas adicionais (2 dBi basta; ver CONFORMIDADE.md §1.1.1 para até quantos dBi valem a pena) | Liberar `HTC-03`–`06` do modo bancada |
| P-012 | Comprar bateria(s) para ensaio de autonomia | Fase 1/4 |
| P-013 | Definir e comprar o primeiro sensor (báscula de chuva é o de maior prioridade, ver SENSORES.md) | Fase 1 |
| A-01 a A-05 | Pendências do projeto de ancoragem | Ver ANCORAGEM.md §10 |
| R-01 a R-06 | Habilitação profissional e responsabilidade técnica | Ver RESPONSABILIDADE_TECNICA.md §10 |
