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

## 2026-07-30 (4) — Primeiras gravações e enlace estabelecido

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **`HTC-01` gravada como PINGER** e `HTC-02` como PONGER. Ambas verificadas
  por hash na gravação e por saída serial no arranque.
- **Enlace LoRa estabelecido**: ensaio 01 registrado em `docs/CAMPO.md`.
  8 pacotes, **0% de perda**, RSSI de −77 a −94 dBm, SNR de +8 a +12 dB,
  margem de 35 a 52 dB sobre a sensibilidade de SF9.
- **Diagnóstico de piso de ruído** adicionado ao PONGER: a cada 5 s reporta o
  RSSI do canal. Sem isso, silêncio no receptor é ambíguo — pode ser
  transmissor desligado ou rádio que não entrou em recepção.
- Identificação individual das placas documentada por **MAC do ESP32**.

### Aprendido

- **Os CP2102 destas placas têm todos o mesmo número de série USB (`0001`)** —
  a porta não distingue uma placa da outra. Só o MAC do ESP32 identifica.
  `esptool.py flash_id` resolve identificação e verificação de flash de uma vez.
- A definição de board do PlatformIO não corresponde ao hardware real destas
  placas (E-005) — assumir o board pronto custou uma gravação inútil.
- **Atenuação medida está 45 a 60 dB acima do esperado em espaço livre** para
  ~10 m. Compatível com paredes e lajes do ambiente do ensaio, mas precisa ser
  confirmado com linha de visada limpa antes de virar linha de base. Se
  persistir sem obstrução, a suspeita passa a ser antena ou conector.
- Variação de até 17 dB entre amostras com os nós parados: multipercurso
  típico de ambiente fechado.

### Próximo

1. Ensaio 02 — linha de visada ao ar livre, para separar obstrução de perda
   de antena.
2. Ensaio 03 — varredura de SF7 a SF12, comparando margem e tempo no ar.
3. Medição de consumo.

---

## 2026-07-30 (3) — Conformidade, contexto de mercado e display de campo

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **`docs/CONFORMIDADE.md`** — levantamento das normas aplicáveis: Anatel
  (Res. 680/2017, Ato 14448/2017, Res. 715/2019), Lei 12.608/2012 (PNPDEC),
  ABNT NBR 11682, NBR 5419/5410, NR-35/NR-10, LGPD, INDE, OGC, Lei 14.133/2021.
  Sete itens de ação numerados C-01 a C-07, com responsável e prazo.
- **`docs/GEOPIXEL.md`** — análise das duas páginas públicas do Geopixel Monitor
  e proposta de valor do Sentinela sobre a plataforma existente.
- **Display de diagnóstico** com quatro páginas navegáveis pelo botão PRG:
  enlace (RSSI grande + barra de margem), histórico gráfico de 128 amostras,
  parâmetros de rádio e saúde do nó. Compila limpo nos dois papéis; RAM 7,5%,
  Flash 10,0%.

### Decidido

- **A homologação Anatel é obrigatória para comercializar** (Lei 9.472/1997 +
  Res. 715/2019). Entra no cronograma e no preço, e passa a ser a primeira
  consulta externa do projeto (C-01/P-006), antes da fase 4. Reforça ADR-004:
  partir de módulo já homologado reduz o escopo de ensaios.
- **Padrões abertos como requisito**, não como preferência: OGC SensorThings,
  CSV/KML e metadados INDE. É o que viabiliza integração com o TerraMA² e o que
  sustenta especificação sem direcionamento em licitação.
- O display é ferramenta de desenvolvimento e fica em `src/`, não em
  `lib/app/` — o nó de campo definitivo não terá tela.
- Tensão de bateria exibida como **não calibrada** em vez de omitida ou
  apresentada como exata (RC-07). Calibração vira P-005.

### Aprendido

- A lacuna da plataforma Geopixel é **estrutural, não de software**: satélite e
  modelo regional não medem poropressão nem deslocamento milimétrico, e a
  revisão de satélite é lenta demais para um evento de horas. O Sentinela
  fornece a camada in situ.
- O custo real do alerta regional impreciso não é o falso positivo em si — é o
  alerta verdadeiro que será ignorado depois que a população perder a confiança.
- O módulo de Vistoria já existente fecha um ciclo nos dois sentidos: o sensor
  prioriza a vistoria, e o laudo da vistoria rotula o dado que calibra os
  limiares locais.
- Caraguatatuba é o piloto natural: encosta da Serra do Mar, alta
  suscetibilidade, prefeitura já cliente e instância da plataforma no ar.

### Próximo

Gravar `HTC-01` e `HTC-02` e fechar o enlace de bancada.

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

- **Clone do projeto no homeserver** em `/DATA/Projects/Sentinela` (remoto SSH,
  chave `id_github` já autorizada). Era isso que faltava para o projeto aparecer
  no aplicativo e no CasaOS: **o app conecta ao homeserver, não ao MacBook**, e
  lista os repositórios de `/DATA/Projects`. Um projeto que existe só no Mac é
  invisível para ele.

### Decidido

- Privado por ora. Abrir depois exige definir licença (P-003).
- Allowlist em `settings.json` **versionado** em vez de `settings.local.json`,
  para a configuração viajar com o repositório.
- Chave SSH do Mac **não** foi autorizada no GitHub e não precisa ser — HTTPS
  via `gh` cobre o fluxo atual (ver E-002). O homeserver, por sua vez, já usava
  SSH e continua assim.
- **Divisão de papéis entre os dois clones:** firmware no MacBook (a placa está
  na USB dele), backend/gateway/documentação no homeserver. Sincronização
  apenas pelo GitHub — ver armadilha A-009.

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
