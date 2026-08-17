# Sentinela

Rede de sensores LoRa para monitoramento de áreas de risco geológico-hidrológico
em múltiplos municípios.

Cada dispositivo de campo é uma **Atalaia**; o gateway que congrega uma área é
um **Farol**. O sistema mede chuva acumulada, saturação do solo, inclinação de
talude e condições atmosféricas, correlaciona essas grandezas com a base geoespacial de
suscetibilidade e população exposta, e entrega à Defesa Civil informação
acionável sobre risco iminente de deslizamento.

> **O Sentinela é um sistema de apoio à decisão.** Ele não substitui o
> julgamento técnico da Defesa Civil nem aciona evacuação de forma autônoma.
> Ver [docs/REQUISITOS.md](docs/REQUISITOS.md).

## Estado atual

O bring-up de rádio e a esteira de enlace estão operacionais, e o repositório
já contém banco, GIS, painel, chuva oficial e comissionamento. Isso não equivale
a um piloto de sensores: a ingestão dos quadros de sensor, a decisão local e a
abertura automática de alarmes ainda não estão conectadas ponta a ponta. Ver
[LOG.md](LOG.md) para a cronologia e [docs/PARAMETROS.md](docs/PARAMETROS.md)
para a fronteira entre valores experimentais e decisórios.

## Documentação

| Documento | Conteúdo |
|---|---|
| [docs/PLANO.md](docs/PLANO.md) | Fases do projeto, escopo e critérios de saída |
| [docs/ARQUITETURA.md](docs/ARQUITETURA.md) | Decisões técnicas registradas (ADR) |
| [docs/HARDWARE.md](docs/HARDWARE.md) | Inventário, pinagem, alocação das placas |
| [docs/SENSORES.md](docs/SENSORES.md) | Grandezas monitoradas e justificativa |
| [docs/REQUISITOS.md](docs/REQUISITOS.md) | Requisitos de confiabilidade e alerta |
| [docs/ROTEIRO_CAMPO.md](docs/ROTEIRO_CAMPO.md) | Como conduzir o ensaio de alcance |
| [docs/CAMPO.md](docs/CAMPO.md) | Resultados dos ensaios de enlace |
| [docs/PROPAGACAO.md](docs/PROPAGACAO.md) | Modelo de propagação calibrado e dimensionamento |
| [docs/ANCORAGEM.md](docs/ANCORAGEM.md) | Projeto de fixação da Atalaia no talude |
| [docs/MANUTENCAO.md](docs/MANUTENCAO.md) | Saúde da frota, alarmes e manutenção preditiva |
| [docs/CONFORMIDADE.md](docs/CONFORMIDADE.md) | Normas aplicáveis — Anatel, defesa civil, geotecnia, LGPD |
| [docs/RESPONSABILIDADE_TECNICA.md](docs/RESPONSABILIDADE_TECNICA.md) | Habilitação profissional e camadas de responsabilidade |
| [docs/REFERENCIAS.md](docs/REFERENCIAS.md) | **Política de proveniência** e bibliografia central |
| [docs/QUALIDADE_CODIGO.md](docs/QUALIDADE_CODIGO.md) | **Complexidade ciclomática** e padrões de código |
| [docs/PARAMETROS.md](docs/PARAMETROS.md) | Proveniência, status, histórico e uso decisório de parâmetros |
| [docs/GEOPIXEL.md](docs/GEOPIXEL.md) | Contexto de mercado e proposta de valor |
| **[docs/NEGOCIO.md](docs/NEGOCIO.md)** | **Índice das cinco frentes de negócio** |
| [docs/MERCADO_MUNICIPIOS.md](docs/MERCADO_MUNICIPIOS.md) | Frente 1 — mercado municipal |
| [docs/MERCADO_MINERACAO.md](docs/MERCADO_MINERACAO.md) | Frente 2 — barragens de mineração |
| [docs/CONCORRENCIA.md](docs/CONCORRENCIA.md) | Frente 3 — concorrência e originalidade |
| [docs/PATENTES.md](docs/PATENTES.md) | Frente 4 — maturidade para depósito |
| [docs/VALUATION.md](docs/VALUATION.md) | Frente 5 — valor de mercado estimado |
| [docs/PROMPT_PAINEL.md](docs/PROMPT_PAINEL.md) | Prompt autocontido para gerar o painel de resultados |
| [LOG.md](LOG.md) | Diário de andamento |
| [ERROS.md](ERROS.md) | Registro de erros e soluções |

## Estrutura

```
tools/        Ferramentas de ensaio, análise e o painel de controle
firmware/     Firmware dos nós (PlatformIO)
  lib/app/      Lógica de aplicação — sem código específico de chip
  lib/hal/      Abstração de hardware — uma implementação por plataforma
  lib/proto/    Codificação de payload — compartilhada com o backend
gateway/      Bridge LoRa→MQTT no Raspberry Pi 4
backend/      ChirpStack, Mosquitto, TimescaleDB/PostGIS, ingestor
hardware/     Esquemas, caixas, notas de campo
docs/         Documentação de projeto
```

A separação em três camadas dentro de `firmware/lib` é deliberada: permite
trocar a plataforma dos nós de campo (ESP32 → STM32WLE5) mexendo apenas em
`hal/`. Ver ADR-004.

## Ambiente de desenvolvimento

O projeto vive em **dois clones**, com papéis distintos:

| Onde | Caminho | Papel | Remoto |
|---|---|---|---|
| MacBook | `~/Documents/Claude Projects/Sentinela` | **Firmware** — precisa da porta USB | HTTPS (via `gh`) |
| Homeserver | `/DATA/Projects/Sentinela` | **Backend, gateway, documentação** e acesso remoto pelo iPhone | SSH (`id_github`) |

O firmware só pode ser gravado e monitorado do MacBook: a placa está na USB
dele. O clone do homeserver existe porque é a ele que o aplicativo se conecta —
é o que torna o projeto editável remotamente.

> **Regra para evitar divergência:** `git pull` **antes** de começar a trabalhar,
> em qualquer um dos dois lados, e `git push` ao terminar. Os dois clones se
> falam apenas através do GitHub. Ver armadilha A-009 em [ERROS.md](ERROS.md).

### Display de diagnóstico

O OLED integrado é a interface de campo — no teste de alcance não há laptop.
Quatro páginas, alternadas pelo **botão PRG**:

| Página | Mostra | Para quê |
|---|---|---|
| **ENLACE** | RSSI em fonte grande, barra de margem, SNR, RSSI remoto, perda | Ler o estado do link a um olhar, caminhando |
| **PONTO** | Resumo do ponto e **faixa de veredito**: `APROVADO` / `LIMITE` / `REPROVA` / `COLETANDO` | A tela que se fotografa antes de mudar de local |
| **HISTORICO** | Gráfico dos últimos 128 pacotes, com mín/méd/máx | A forma da curva denuncia obstrução — um degrau não é distância |
| **RADIO** | Frequência, SF, BW, CR, potência, tempo no ar, sensibilidade | Confirmar que a placa está na configuração que se pensa |
| **SISTEMA** | Tempo ativo, heap, reinícios, tensão de bateria | Embrião da telemetria de saúde exigida por RC-03 |

O botão PRG tem duas funções: **toque curto** muda de página, **toque longo**
(>1 s) marca um novo ponto de medição, zerando as estatísticas.

A **barra de margem** é o número que decide um ponto de instalação: distância
até a sensibilidade do SF em uso. Margem baixa significa link que cai na
primeira chuva forte — que é exatamente quando o sistema precisa funcionar.

> A tensão de bateria aparece rotulada como **`nc`** (não calibrada): o divisor
> da Heltec V2 não foi caracterizado. Valor plausível porém errado é pior que
> valor ausente (RC-07). Pendência P-005.

### Comandos de firmware

```bash
pio run -e node_dev          # compila o firmware do nó
pio run -e node_dev -t upload --upload-port /dev/cu.usbserial-0001
pio device monitor -b 115200
```

PlatformIO Core instalado em `~/.venvs/platformio` (fora do Python do sistema)
**nas duas máquinas** — MacBook e homeserver. GitHub CLI em `~/.local/bin/gh`.

#### Duas estações de trabalho

O projeto roda em duas pontas, e **compilar funciona nas duas**. O que muda é
o que está fisicamente ligado a cada uma:

| | MacBook | homeserver |
|---|---|---|
| Compilar firmware | sim | sim |
| Gravar placa local | sim (placas na USB) | só se a placa estiver ligada nele |
| Gravar a `HTC-03` | sim (por SSH até o RPi) | sim (por SSH até o RPi) |
| Painel, banco, ingestor | — | sim, sempre no ar |

**Compatibilidade entre os sistemas** já está resolvida no código, não é
manual: a porta serial se chama `cu.usbserial-*` no macOS e `ttyUSB*` no
Linux, então tanto o painel (`portas_seriais()`) quanto a varredura
(`acha_porta_serial()`) procuram os dois padrões. `tools/varredura_sf.py`
também descobre onde estão o `pio` e o `esptool` em tempo de execução, e
aceita `--porta` para sobrescrever.

**O que ainda exige o Mac:** só o que depende de placa fisicamente conectada
nele. Se precisar gravar a `HTC-01` a partir do homeserver, é preciso mover o
cabo USB para lá — o resto (compilar, gravar a `HTC-03`, rodar a varredura,
consultar o banco, usar o painel) funciona igual dos dois lados.

### Painel de controle

**Sempre no ar em <http://localhost:8765>** — não precisa iniciar nada.

Reúne visão geral, pendências consolidadas de todos os documentos, hardware,
ensaios de rede com gráfico, builds do firmware, complexidade ciclomática, a
documentação renderizada e uma **janela MQTT em memória**, consultada pelo
navegador a cada 2 segundos, para observar a rede LoRa
(margem de enlace nos dois sentidos, RSSI, SNR, assimetria, perda de pacotes,
estado de cada placa e da bridge).

A página **Cadeia e fontes** distingue evidência observada, inferência e falta
de dado, sempre com timestamp/idade quando disponível. Registro recente no
banco não é apresentado como prova de que um serviço continua ativo. Os
critérios do monitor MQTT são experimentais e servem ao ensaio de enlace; não
são critérios de alerta geotécnico.

**Limites operacionais atuais:** o painel não observa diretamente systemd ou
Docker, a janela MQTT reinicia com o processo, e ainda não existem identidade
institucional, RBAC, operação multiusuário coordenada ou protocolo formal de
incidentes. O nome informado em ações é declaratório. Essas lacunas impedem
tratar o painel como pronto para operação crítica institucional.

A mesma página cataloga aquisições ambientais e territoriais externas e exibe
configuração, última execução, último dado e limitação. A esteira preserva o
bruto e a proveniência, mas não mistura observação, estimativa, previsão ou
contexto e não cria regras automáticas de alerta. Operação e fontes oficiais:
[`docs/FONTES_EXTERNAS.md`](docs/FONTES_EXTERNAS.md).

#### Como está montado

| Onde | O quê | Serviço |
|---|---|---|
| homeserver | Painel, preso em `127.0.0.1:8765` | `sentinela-painel.service` (usuário) |
| homeserver | Túnel MQTT até o broker do RPi | `sentinela-tunel-mqtt.service` (usuário) |
| MacBook | Traz a porta 8765 para `localhost` | `com.sentinela.painel-tunel` (LaunchAgent) |

**Por que o painel roda no homeserver, e não no Mac.** Duas razões, e as duas
importam: o Mac dorme (e "sempre acessível" não combina com isso), e o **TCC
do macOS bloqueia serviços em segundo plano de lerem `~/Documents`** — um
LaunchAgent apontando para o repositório falha com `Operation not permitted`
antes mesmo de subir. Encaminhar porta não esbarra nisso, porque o `ssh` não
toca no repositório.

Nada é exposto na LAN: painel e broker ficam em `127.0.0.1` nas respectivas
máquinas, e o que atravessa a rede são túneis SSH sobre chave.

No Raspberry, Ethernet é preferencial e desliga o Wi-Fi após validação do
caminho. Sem cabo, o Wi-Fi assume automaticamente. O túnel usa o nome mDNS do
Farol e o broker mantém uma sessão QoS 1 persistente durante a troca; ver
ADR-010 e `gateway/README.md`.

Ambas as camadas se reerguem sozinhas (`Restart=always` no systemd,
`KeepAlive` no launchd) — verificado matando os processos à força.

#### Instalação (uma vez, por máquina)

```bash
# homeserver
cp tools/painel/sentinela-painel.service ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now sentinela-painel

# MacBook
cp tools/launchd/com.sentinela.painel-tunel.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.sentinela.painel-tunel.plist
```

#### Diagnóstico

```bash
ssh 192.168.15.66 "journalctl --user -u sentinela-painel -n 30"
```

```bash
launchctl list | grep sentinela
```

Rodar o painel **local** no Mac (para ver builds do firmware e portas seriais,
que só existem lá) continua funcionando pelo terminal, em outra porta:

```bash
./tools/venv/bin/python tools/painel/servidor.py --porta 8766
```

### Verificação de qualidade

```bash
./tools/venv/bin/python tools/verifica.py
```

O comando executa contratos de protocolo, decodificação, robustez do fluxo,
reconhecimento de alarmes, contratos do painel e a verificação de complexidade.
Nenhuma função pode passar de 10 — ver [QUALIDADE_CODIGO.md](docs/QUALIDADE_CODIGO.md).

### Coleta do ensaio de campo

```bash
./tools/venv/bin/python tools/coleta.py --ensaio 02
./tools/venv/bin/python tools/georreferenciar.py \
    --pontos dados/ensaio02-...-pontos.csv --fotos ~/Desktop/fotos-ensaio02
```

O primeiro grava cada amostra com carimbo de hora e resume por ponto; o segundo
casa esses pontos com as fotos do celular pelo EXIF e gera GeoJSON, KML e CSV
para o QGIS. Detalhes em [ROTEIRO_CAMPO.md](docs/ROTEIRO_CAMPO.md) §4.3 e §4.4.

## Licença

Este projeto é **OPEN SOURCE**.

---
Autoria: Luiz Luiz Matheus Marassi de Paula de Paula
