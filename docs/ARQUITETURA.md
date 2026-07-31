# Arquitetura — Decisões Registradas (ADR)

Cada decisão registra o contexto, a escolha e o que a reverteria. O objetivo é
não reabrir discussão já resolvida e deixar explícito o que ainda é reversível.

---

## ADR-001 — LoRaWAN é o alvo; P2P é o meio da fase 0

**Status:** aceito · 30/07/2026

**Contexto.** A rede cobrirá vários municípios, com nós heterogêneos e
requisito de longa autonomia. Quatro caminhos foram avaliados: LoRaWAN,
LoRa ponto-a-ponto proprietário, Meshtastic e mesh proprietária.

**Decisão.** O alvo de produção é **LoRaWAN com ChirpStack self-hosted**.
A fase 0 e a fase 1 usam **LoRa P2P** apenas porque ainda não há concentrador
(ver ADR-002).

**Justificativa.**

- *Multi-cidade é nativo.* Vários gateways, com deduplicação no network server.
  Um nó ouvido por dois gateways ganha redundância sem esforço — e gateway único
  é ponto de falha inaceitável em sistema de alerta.
- *Segurança já especificada.* AES-128 com chaves por dispositivo e contador
  anti-replay. Injeção de alerta falso é ameaça concreta aqui; mesh caseira não
  entrega isso de graça.
- *ADR (Adaptive Data Rate) economiza bateria sozinho.* O servidor ajusta o
  spreading factor de cada nó conforme o link medido.
- *Abre o hardware.* Qualquer nó LoRaWAN comercial (Dragino, RAK, Milesight)
  entra na rede sem alterar o servidor.

**Descartados.**

| Opção | Motivo |
|---|---|
| Meshtastic | Mesh por inundação não escala; nós gastam bateria escutando; sem gestão de frota nem servidor de aplicação |
| Mesh proprietária | Reescreveria roteamento, criptografia e OTA — meses de trabalho já resolvidos pela spec |
| P2P como solução final | Sem gestão, sem ADR, sem interoperabilidade |

**O que reverteria.** Encostas sem linha de visada para qualquer ponto alto
servido por internet. Nesse caso, repetidor LoRaWAN ou mesh nas bordas.

---

## ADR-002 — Não comprar concentrador agora; RPi 4 + Heltec como bridge

**Status:** aceito · 30/07/2026

**Contexto.** Há 5 Heltec V2 e 1 Raspberry Pi 4 disponíveis, e a diretriz é
minimizar gasto neste momento. Surgiu a pergunta de se o RPi 4 já serve de
gateway.

**O fato técnico.** O Raspberry Pi **não tem rádio LoRa**. Para ser gateway
LoRaWAN de verdade ele precisa de um concentrador SX1302/SX1303 (RAK5146,
RAK2245 — na ordem de R$ 800–1.000), que é o que escuta 8 canais e vários
spreading factors ao mesmo tempo. Sem ele, não existe gateway LoRaWAN.

**As duas saídas de custo zero, e por que uma foi descartada:**

*Single-channel packet forwarder* — usar uma Heltec como pseudo-gateway
LoRaWAN. Descartado: escuta um único canal em um único SF, quebra o join
procedure, impede ADR e está fora da especificação. Ensina vícios que depois
precisam ser desaprendidos, e falhas dele seriam confundidas com bugs nossos.

*LoRa P2P com bridge no RPi 4* — **escolhido**. Uma Heltec (`HTC-03`) ligada
por USB ao Raspberry Pi 4 recebe os pacotes e publica em MQTT. O RPi 4 roda
Mosquitto e, se conveniente, o restante do stack.

**Consequência — e é a parte importante:** com isso o sistema fica
**ponta a ponta funcional sem gastar nada**. Sensor → rádio → bridge → MQTT →
banco → dashboard, tudo real. O que muda ao adquirir o concentrador é
**apenas a camada de enlace**: como `proto/` é compartilhado entre firmware e
backend, o payload não muda, o ingestor não muda, o banco não muda e o
dashboard não muda. A migração fica contida em `hal/radio_*` e no gateway.

**Quando comprar.** Ao entrar na fase 4 (nós definitivos em campo) ou antes
disso se o teste de alcance da fase 0 indicar necessidade de multi-canal para
a densidade de nós prevista.

---

## ADR-003 — AU915 sub-banda 2; P2P em 916,8 MHz

**Status:** aceito · 30/07/2026

**Contexto.** O módulo é a variante de alta banda do SX1276. A Anatel libera
radiação restrita em 902–907,5 MHz e 915–928 MHz; a janela 907,5–915 MHz **não
é permitida**.

**Decisão.** P2P em **916,8 MHz**. LoRaWAN futuro em **AU915 sub-banda 2**
(canais 8–15, 916,8–918,2 MHz) — o padrão de fato no Brasil, justamente por
cair na faixa alta permitida.

Potência inicial de 17 dBm com PA_BOOST. Com antena de ~3 dBi resulta em ~20 dBm
EIRP, dentro do permitido para radiação restrita com espalhamento espectral.

---

## ADR-004 — Firmware em três camadas; alvo de campo é STM32WLE5

**Status:** aceito · 30/07/2026

**Contexto.** A Heltec V2 consome ~1 mA em deep sleep (regulador + CP2102
sempre alimentados), o que a inviabiliza como nó de campo autônomo. Ela é
excelente placa de desenvolvimento.

**Decisão.** O firmware nasce separado em três camadas:

```
lib/app/     Máquina de estados, limiares, decisão de alerta.
             ZERO código específico de chip. Testável no host.
lib/hal/     Rádio, sensores, sono, energia. Uma implementação por
             plataforma: hal/esp32/, futuramente hal/stm32wl/.
lib/proto/   Codificação de payload. Compartilhada com o backend.
```

O alvo dos nós definitivos é o **RAK3172 (STM32WLE5)**: MCU e rádio LoRa no
mesmo silício, **~1,6 µA em standby**, stack LoRaWAN certificada, na ordem de
R$ 70–90. Com bateria LiSOCl2 tamanho D e envio horário, a autonomia sai em
anos — o que elimina visita de manutenção, que é o custo real de operar rede
em campo.

**Consequência.** Nenhum `#include <Arduino.h>` em `lib/app/`. Custa pouco
agora e é o que torna a migração de plataforma uma troca de `hal/`.

---

## ADR-005 — Backend em TimescaleDB + PostGIS

**Status:** aceito · 30/07/2026

**Decisão.** `ChirpStack (ou bridge) → MQTT → ingestor → PostgreSQL +
TimescaleDB + PostGIS → dashboard`.

**Justificativa.** Série temporal de sensor em PostgreSQL puro degrada rápido;
hypertable e agregação contínua entregam os acumulados de 24 h/72 h
pré-calculados — e esses acumulados são o principal preditor do sistema
(ver docs/SENSORES.md).

O PostGIS não é acessório: é o que transforma leitura de sensor em informação
de risco. Cruzando a telemetria georreferenciada com carta de suscetibilidade,
cadastro de edificações e população exposta, o alerta deixa de ser "o talude
moveu" e passa a ser *"talude X moveu 0,4° com 180 mm acumulados em 72 h, com
N domicílios na área de alcance"*. É esse cruzamento que sustenta decisão de
Defesa Civil.

---

## ADR-006 — A decisão crítica roda no nó, não no servidor

**Status:** aceito · 30/07/2026

**Contexto.** LoRaWAN Classe A só recebe downlink depois de um uplink, o que
introduz latência incompatível com alerta imediato. Classe C resolve a latência
e destrói a autonomia.

**Decisão.** A regra crítica de alerta é avaliada **no próprio nó**. O servidor
faz correlação entre nós, histórico, refinamento de limiar e notificação à
Defesa Civil — mas o nó permanece capaz de decidir sozinho.

**Consequência.** O nó continua útil com o gateway fora do ar, que é
exatamente o cenário de um evento extremo — quando queda de energia e de enlace
são mais prováveis. Limiares são parametrizáveis por downlink, mas com valores
padrão persistidos em NVS.

---

## ADR-007 — Raspberry Pi OS Lite oficial; nada de sistema próprio

**Status:** aceito · 31/07/2026

**Contexto.** O Raspberry Pi 4 precisa rodar `gateway/bridge.py`, Mosquitto e,
mais adiante, parte do ingestor. Surgiu a pergunta: instalar o sistema oficial
do Raspberry Pi ou construir uma imagem própria (Buildroot, Yocto, ou um
Debian minimalista montado à mão)?

**Decisão.** **Raspberry Pi OS Lite (64-bit), imagem oficial, sem ambiente
gráfico.** Acesso por SSH com chave, mesmo padrão já usado no homeserver
CasaOS do projeto. Nenhuma imagem customizada.

**Justificativa.**

- **O RPi não é o produto — é infraestrutura de bancada.** O que importa é
  `bridge.py`, o systemd e o Mosquitto rodando de forma confiável; o sistema
  operacional por baixo é *commodity*. Investir engenharia em construir uma
  imagem própria seria otimizar a parte errada.
- **Driver e pacote de graça.** CP2102 (USB-serial), Wi-Fi/Ethernet, GPIO e
  Mosquitto via `apt` já vêm prontos e mantidos pela Raspberry Pi Foundation.
  Uma imagem própria exigiria portar e manter cada um desses componentes.
- **Consistência operacional com o homeserver.** Mesmo padrão já validado:
  distribuição Debian-based, boring-by-design, acesso SSH por chave, systemd
  para supervisionar processo. Reduz a quantidade de convenções diferentes
  que o projeto precisa sustentar.
- **Atualização de segurança sem custo.** Ficaria por nossa conta numa imagem
  própria; na oficial, é mantida pela Raspberry Pi Foundation.
- **Onboarding.** Qualquer pessoa que precisar mexer no RPi depois — inclusive
  um parceiro geotécnico ou de TI da Geopixel — já conhece Raspberry Pi OS.
  Sistema próprio é fricção que não se paga neste estágio.

**O que reverteria esta decisão.** Se o Raspberry Pi 4 de bancada virar
produto final de campo (não é o plano — ADR-002 trata o RPi como solução de
custo zero até o concentrador chegar), aí sim entra em jogo imagem enxuta para
inicialização rápida e superfície de ataque reduzida. Não é o cenário atual.

**Passo a passo de instalação:**

1. Raspberry Pi Imager (app oficial) → **Raspberry Pi OS Lite (64-bit)**.
2. Nas opções avançadas do Imager (⚙️ ou Ctrl+Shift+X): habilitar SSH **por
   chave pública** (não senha), definir hostname (sugestão: `sentinela-far01`),
   configurar Wi-Fi se não houver Ethernet disponível na bancada.
3. Gravar no cartão microSD, inicializar o RPi.
4. Confirmar acesso: `ssh pi@sentinela-far01.local` (ou pelo IP).
5. `sudo apt update && sudo apt install -y mosquitto mosquitto-clients python3-venv`
6. Clonar o repositório em `/home/pi/sentinela` (mesmo caminho assumido em
   `gateway/sentinela-bridge.service`), criar o venv, instalar
   `tools/requirements.txt`.
7. Instalar e habilitar a unidade systemd — ver `gateway/README.md`.

Fecha a pendência P-010 quando executado.
