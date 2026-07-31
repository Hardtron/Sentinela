# Sentinela

Rede de sensores LoRa para monitoramento de áreas de risco geológico-hidrológico
em múltiplos municípios.

O sistema mede chuva acumulada, saturação do solo, inclinação de talude e
condições atmosféricas, correlaciona essas grandezas com a base geoespacial de
suscetibilidade e população exposta, e entrega à Defesa Civil informação
acionável sobre risco iminente de deslizamento.

> **O Sentinela é um sistema de apoio à decisão.** Ele não substitui o
> julgamento técnico da Defesa Civil nem aciona evacuação de forma autônoma.
> Ver [docs/REQUISITOS.md](docs/REQUISITOS.md).

## Estado atual

**Fase 0 — bring-up do rádio.** Nenhum hardware além do já disponível foi
adquirido. Ver [LOG.md](LOG.md) para o andamento e
[ERROS.md](ERROS.md) para armadilhas já mapeadas.

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
| [docs/ANCORAGEM.md](docs/ANCORAGEM.md) | Projeto de fixação do nó no talude |
| [docs/CONFORMIDADE.md](docs/CONFORMIDADE.md) | Normas aplicáveis — Anatel, defesa civil, geotecnia, LGPD |
| [docs/RESPONSABILIDADE_TECNICA.md](docs/RESPONSABILIDADE_TECNICA.md) | Habilitação profissional e camadas de responsabilidade |
| [docs/REFERENCIAS.md](docs/REFERENCIAS.md) | **Política de proveniência** e bibliografia central |
| [docs/QUALIDADE_CODIGO.md](docs/QUALIDADE_CODIGO.md) | **Complexidade ciclomática** e padrões de código |
| [docs/GEOPIXEL.md](docs/GEOPIXEL.md) | Contexto de mercado e proposta de valor |
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

### Comandos de firmware (somente no MacBook)

```bash
pio run -e node_dev          # compila o firmware do nó
pio run -e node_dev -t upload --upload-port /dev/cu.usbserial-0001
pio device monitor -b 115200
```

PlatformIO Core instalado em `~/.venvs/platformio` (fora do Python do sistema).
GitHub CLI em `~/.local/bin/gh`.

### Painel de controle

```bash
./tools/venv/bin/python tools/painel/servidor.py
```

Abre em `http://localhost:8765`. Reúne visão geral, pendências consolidadas de
todos os documentos, hardware, ensaios de rede com gráfico, builds do firmware,
complexidade ciclomática e a documentação renderizada com navegação entre
documentos.

### Verificação de qualidade

```bash
./tools/venv/bin/python tools/complexidade.py --limite 10
```

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

Ainda não definida. Ver LOG.md, pendência P-003.

---
Autoria: Matheus Marassi
