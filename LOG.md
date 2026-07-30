# Log de andamento

Diário do projeto. Entrada por sessão de trabalho, mais recente **no topo**.

Formato:

```
## AAAA-MM-DD — Título

**Fase:** N · **Duração:** ~Xh

### Feito
### Decidido
### Aprendido
### Próximo
```

Decisão técnica que muda o rumo vai para `docs/ARQUITETURA.md` como ADR — aqui
fica apenas a referência. Erro encontrado vai para `ERROS.md` — aqui fica
apenas o apontamento.

---

## 2026-07-30 (2) — Publicação e ambiente de trabalho remoto

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **GitHub CLI 2.96.0** instalado em `~/.local/bin` (binário oficial
  `gh_2.96.0_macOS_arm64.zip`, arm64), adicionado ao PATH no `~/.zshrc`.
  Não há Homebrew nem MacPorts nesta máquina — instalação isolada, sem tocar
  no sistema.
- Autenticação por **device flow**, protocolo git HTTPS. Token no keyring do
  macOS, conta `Hardtron`. Escopos: `repo`, `read:org`, `gist`.
- Repositório publicado: **github.com/Hardtron/Sentinela**, **privado**,
  branch padrão `main`. Dois commits enviados.
- `.claude/settings.json` versionado com allowlist de build, gravação e git —
  permite conduzir o trabalho de outro dispositivo sem aprovar comando a
  comando.
- Diretório do projeto autorizado para acesso fora do diretório de trabalho.
- **Memória do projeto separada** da do Geo_Quality: o Sentinela passou a ter
  espaço próprio, com as memórias do homeserver copiadas (o backend roda lá).
  Os dois projetos ficam independentes.

### Decidido

- Privado por ora. Abrir depois exige definir licença (P-003).
- Allowlist em `settings.json` **versionado** em vez de `settings.local.json`,
  para a configuração viajar com o repositório.
- Chave SSH **não** foi autorizada no GitHub e não precisa ser — HTTPS via
  `gh` cobre o fluxo atual (ver E-002).

### Próximo

Retomar a Fase 0: gravar `HTC-01` e `HTC-02` e fechar o enlace de bancada.

---

## 2026-07-30 — Identificação do hardware e concepção do projeto

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- Identificado o hardware conectado à USB do MacBook: **Heltec WiFi LoRa 32 V2**
  (ESP32-D0WDQ6 rev 1.0, cristal 26 MHz, flash 4 MB, MAC `3c:71:bf:8c:2c:d0`),
  ponte CP2102 em `/dev/cu.usbserial-0001`.
- Confirmado que o **macOS já traz o driver CP210x nativo** — nenhuma instalação
  de driver foi necessária. Ver ERROS.md, nota E-006.
- Dump read-only íntegro dos 4 MB da flash da `HTC-01`, antes de qualquer
  gravação. Firmware de fábrica identificado como Heltec FactoryTest.
- Tabela de partições lida: Arduino `default_ota` (app0/app1 de 1280 K,
  SPIFFS 1468 K, EEPROM 4 K).
- Modelo confirmado como V2 pelo rótulo `868-915MHz`, conector de bateria e
  botões PRG/RST junto ao USB.
- **PlatformIO Core 6.1.19** instalado em venv isolado (`~/.venvs/platformio`),
  adicionado ao PATH no `~/.zshrc`. Python do sistema não foi tocado.
- Homeserver verificado como candidato a backend: Docker 29.6, Compose v5.3,
  111 GB livres, portas 1883/8080/5432/1700 livres.
- Estrutura do repositório criada com documentação de concepção.
- **Firmware de bring-up da Fase 0 escrito e compilando** nos dois papéis
  (PINGER e PONGER), sem warnings. RAM 7,4%, Flash 9,6% — folga confortável.
  Ping-pong com eco de RSSI/SNR, medindo o enlace nos dois sentidos, com saída
  serial em CSV para registro direto do ensaio de campo.
- Ainda **não gravado em nenhuma placa** — a `HTC-01` permanece com o firmware
  de fábrica.

### Decidido

- ADR-001 — LoRaWAN é o alvo; P2P na fase 0.
- ADR-002 — **Não comprar concentrador agora.** RPi 4 + Heltec como bridge
  entrega o sistema ponta a ponta com custo zero.
- ADR-003 — AU915 sub-banda 2; P2P em 916,8 MHz.
- ADR-004 — Firmware em três camadas; alvo de campo é STM32WLE5 (RAK3172).
- ADR-005 — Backend em TimescaleDB + PostGIS.
- ADR-006 — A decisão crítica de alerta roda no nó, não no servidor.
- Requisitos de confiabilidade e alerta aceitos integralmente
  (`docs/REQUISITOS.md`).
- Desenvolvimento do **firmware fica local no MacBook** — precisa da porta USB.
  O **backend vai para o homeserver** (`/DATA/Projects`), conforme a prática já
  estabelecida em outros projetos.

### Aprendido

- Cristal de 26 MHz é assinatura de placa Heltec/TTGO; dev boards genéricas
  ESP32 usam 40 MHz. Serve como triagem rápida de placa desconhecida.
- O firmware de fábrica da Heltec **não emite nada no serial** após o
  bootloader. Isso não é defeito (E-003).
- Reposicionamento técnico relevante: encosta avisa por **deslocamento lento**,
  não por vibração. O acelerômetro entra no projeto como **inclinômetro**, e
  o maior preditor isolado é **chuva acumulada**. Ver `docs/SENSORES.md`.
- A faixa 907,5–915 MHz **não** é permitida no Brasil — daí AU915 sub-banda 2.

### Próximo

1. Resolver P-001 (chave SSH no GitHub) para publicar o repositório.
2. Gravar `HTC-01` (`node_dev`) e `HTC-02` (`node_range`) e rodar o primeiro
   enlace em bancada — com as duas antenas conectadas (armadilha A-003).
3. Medir consumo em transmissão e em repouso.
4. Planejar o percurso do teste de alcance em campo e levantar a curva
   alcance × spreading factor.
