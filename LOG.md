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

## 2026-07-31 (17) — Baterias reais, correção do ensaio 03a e página BATERIA no OLED

**Fase:** 0 · **Duração:** média

### Feito

- **Correção factual no ensaio 03a (CAMPO.md) e na entrada 16 deste log**: o
  usuário esclareceu que `HTC-01` e `HTC-03` estavam em **cômodos separados
  por alvenaria, ~18 m, com portas abertas e pessoas transitando** durante a
  varredura SF7–SF12 — não na mesma bancada. As placas ficaram **paradas**
  o tempo todo; a hipótese original registrada ("manuseio físico a cada
  regravação") foi **descartada e substituída** pela explicação real: o que
  variava entre rodadas era qual percurso de propagação dominava (direto
  atenuado pela parede, difratado pelo vão da porta, refletido) — plausível
  para explicar os ~11 dB de variação de RSSI observados. A conclusão prática
  não muda (a tabela de bancada segue não sendo curva de alcance × SF
  confiável), mas a causa registrada agora é a real, não um palpite.
- **Baterias adquiridas**: 2× **Panasonic NCR18650B** (Li-ion, 3,7 V,
  ~3400 mAh nominal), instaladas em `HTC-01` e `HTC-02` via conector JST da
  Heltec V2. Fecha **P-012**. Foto confirma a etiqueta da célula.
  `HTC-02` mostrou **0,200 A** de corrente de carga no medidor USB — anotado
  como medição do carregador enchendo a célula, explicitamente distinto dos
  81 mA/423 mW já medidos em operação (fenômenos diferentes, não comparáveis
  direto). Documentado em HARDWARE.md, nova seção "Baterias".
- **Página BATERIA no OLED** (`ui_dev.h`/`ui_dev.cpp`), sexta página do
  display: tensão em fonte grande (mantendo o rótulo "nc" — divisor segue
  não calibrado, P-005), barra de carga estimada por curva de referência de
  célula Li-ion (também rotulada "nc", RC-07: número plausível errado é pior
  que ausente), temperatura interna do chip (`temperatureRead()`, sensor de
  fábrica do ESP32) e motivo do último reinício (`esp_reset_reason()` —
  energia, watchdog, brownout, deep sleep etc.). Reúne o que é possível medir
  **só com o hardware da própria placa**: não há fuel gauge nem pino de
  status de carga na Heltec V2, então "carregando: sim/não" continua sendo
  algo que só o medidor externo do usuário sabe dizer, não o firmware.
- MAC/flash confirmado (`3c:71:bf:8c:2c:d0`), `HTC-01` regravada com
  `node_dev` atualizado e boot verificado por serial, sem erro.

### Aprendido

- **`switch` com 10 casos estoura o limite de complexidade do projeto**
  (`motivoReset()` deu CC 11 num primeiro rascunho). Convertido para tabela
  `{codigo, texto}` + busca linear — mesmo padrão já usado em
  `bateriaPercentualAprox` e, no painel web, nos objetos `CORES_*` do
  `app.js`. Reforça que "switch grande" é sempre candidato a virar tabela
  neste projeto, não só quando o limite já estourou.
- **Revisão de layout pegou uma colisão antes de gravar**: o selo "BAIXA"
  desenhado como caixa invertida no canto superior direito ocuparia o mesmo
  espaço que `cabecalho()` já usa para "P.. n.. PAPEL". Corrigido para texto
  simples na mesma linha da tensão — mesmo padrão, mais simples, já usado
  com segurança em `pagSys`.
- Não há como verificar visualmente o layout do OLED remotamente (sem
  câmera apontada para a placa) — a verificação desta sessão ficou limitada
  a compilação limpa, complexidade dentro do limite e boot sem erro via
  serial. Revisão de geometria de pixel foi feita por leitura de código
  contra os padrões já validados nas páginas existentes, não por captura de
  tela real.

### Próximo

1. `HTC-02` precisa ser reconectada à USB para receber o firmware
   atualizado (está no carregador no momento). `HTC-03` segue com o
   firmware anterior — atualizar é opcional, ninguém olha o OLED dela
   dentro do Raspberry Pi.
2. Ensaio de autonomia real agora é possível (baterias resolvidas) — falta
   decidir o protocolo (carga cheia até `VBAT_BAIXA_V`, cronometrado).
3. Calibração do divisor de tensão (P-005) segue como pré-requisito para
   qualquer conclusão numérica de autonomia — a página BATERIA deixa isso
   visível todo boot ("nc"), não escondido.

---

## 2026-07-31 (16) — Varredura SF7–SF12 automatizada: método validado, curva de campo pendente

**Fase:** 0 · **Duração:** média

### Feito

- **`LORA_SF` vira parâmetro de build** (`-D LORA_SF=N`, `firmware/include/
  board_heltec_v2.h`, guardado por `#ifndef` — 9 continua padrão quando a
  flag não é passada). `firmware/platformio.ini` ganhou 12 ambientes
  (`sf7_pinger`/`sf7_bridge` … `sf12_pinger`/`sf12_bridge`).
- **Armadilha corrigida antes de rodar a campanha**: o timeout de espera do
  pong era `TIMEOUT_PONG_MS=1500` fixo — folgado em SF9 (toa~170 ms), mas
  perto demais do limite em SF12 (toa~1155 ms, `tools/alcance.py`). Rodar a
  varredura sem corrigir teria produzido "perda" que seria do software
  esperando de menos, não do rádio — contaminando exatamente o dado que a
  campanha existe para medir. Virou `timeoutPongMs`, calculado em `setup()`
  a partir do toa real (`toa*3 + 200`).
- **`tools/varredura_sf.py`** automatiza o ciclo: compila e grava as duas
  pontas para cada SF (HTC-01 local via cabo, HTC-03 remota via SSH+esptool,
  sem tirar a placa da USB do RPi), espera amostras chegarem ao banco via o
  ingestor, e resume margem/assimetria/perda por SF. Validado com teste de
  fumaça em SF7 isolado antes de comprometer a campanha inteira.
- **Campanha SF7–SF12 rodada em bancada**: **0% de perda em todo o
  intervalo**, inclusive SF12 — confirma que a correção do timeout funcionou
  sob a condição mais apertada. Resultado completo e análise em
  `docs/CAMPO.md`, ensaio 03a.
- Placas devolvidas ao firmware operacional (SF9: `node_dev`/`bridge`) ao
  final, e confirmado dado voltando a fluir normalmente.

### Aprendido

- **A margem não subiu de forma suave com o SF, como a teoria prevê** (SF7→
  SF12 deveria ganhar ~14 dB de sensibilidade em degraus de ~2,5–2,8 dB).
  Investigado a fundo em vez de aceitar o número: isolando cada rodada pelos
  buracos de tempo entre gravações (uma consulta ad-hoc inicial estava
  misturando o teste de fumaça com a campanha oficial — descartada depois de
  identificar a contaminação), o RSSI bruto variou ~11 dB entre rodadas sem
  relação com o SF. **Causa (confirmada pelo usuário, não mais hipótese):**
  as placas ficaram fixas — `HTC-01` e `HTC-03` em cômodos separados por
  alvenaria, ~18 m, com portas abertas e pessoas transitando em momentos
  diferentes de cada rodada. O que mudava entre rodadas não era posição, era
  qual percurso de propagação dominava (direto atenuado, difratado pelo vão
  da porta, refletido) — ordem de grandeza comparável ao ganho teórico
  inteiro que a varredura queria isolar. **A tabela de bancada não é uma
  curva de alcance × SF confiável; é validação de tooling.** Registrado sem
  maquiar em CAMPO.md — o dado ruim documentado corretamente vale mais que
  um número bonito sem essa ressalva. (Correção: a hipótese original,
  registrada antes de confirmar com o usuário, apontava manuseio físico da
  placa — descartada.)
- **A assimetria ficou estável (12,5–14,1 dB) em todo o SF**, e isso é
  esperado: SF muda sensibilidade (limiar de decodificação), não RSSI
  (potência recebida) — assimetria é diferença de RSSI puro, não deveria
  variar com SF. Serviu de teste de sanidade da própria campanha: se tivesse
  variado descontroladamente, seria sinal de pipeline quebrado, não de
  física real.

### Próximo

1. **Ensaio 03 de verdade**: mesma ferramenta, mas em campo, no P6 (ponto
   alto já caracterizado no ensaio 02), com as placas **fixas** — sem
   recabear entre SF, já que `varredura_sf.py` resolve isso remotamente. É
   isso que falta para fechar o critério de saída da Fase 0.
2. `lib/proto/` seguirá sendo o próximo item de firmware depois disso.

---

## 2026-07-31 (15) — O dado para de evaporar: ingestor, banco e consumo medido

**Fase:** 2 → 3 · **Duração:** longa

### Feito

- **Achado que motivou a prioridade:** 549 pacotes já haviam trafegado
  ponta a ponta e **nenhum existia em lugar nenhum**. O `buffer.jsonl` só
  guarda o que *falha* ao publicar (e nada falhava), o `mosquitto.db` tinha
  286 bytes (mensagem retida, não histórico) e o painel mantinha 600 amostras
  em RAM. A esteira estava completa e era um cano aberto.
- **Banco no ar no homeserver**: TimescaleDB 2.29 + PostGIS 3.6 na mesma
  instância (`backend/docker-compose.yml`), porta presa em `127.0.0.1`.
  Tabelas: `no`, `enlace` (hypertable), `saude_bridge` (hypertable),
  `ponto_ensaio`, view `enlace_analise` e agregação contínua `enlace_hora`.
- **Ingestor rodando** (`backend/ingestor.py`), idempotente por índice único
  `(bridge_id, node_id, seq, recebido_em)` + `ON CONFLICT DO NOTHING` — a
  bridge reenvia o buffer ao reconectar, e sem isso a taxa de perda ficaria
  falseada por duplicata. **763 amostras persistidas** na primeira meia hora.
- **Ensaio 02 carregado no PostGIS** (`backend/carrega_ensaio.py`). Serviu de
  verificação cruzada: as distâncias registradas em campo batem com as
  calculadas por `ST_Distance` a partir do nó fixo **dentro de 0,3 m**.
- **Firmware da `HTC-03` atualizado remotamente, pela própria RPi**, sem
  mover a placa: `esptool` instalado no RPi, binário enviado por `rsync`,
  gravado em 0x10000 com hash verificado. Estabelece a capacidade de atualizar
  o gateway à distância — o que importa quando ele estiver num poste.
- **Consumo medido** (medidor USB, `HTC-01` em `node_dev`): **81 mA / 423 mW
  a 5,2 V**, com o acumulado (320 mAh em ~3,9 h) confirmando a leitura
  instantânea. Registrado em HARDWARE.md com as ressalvas que impedem usar o
  número direto para autonomia.

### Decidido

- **Ingestor no homeserver, não no RPi.** Assim a credencial do PostgreSQL
  nunca sai de `localhost`; o que cruza a rede é só MQTT, dentro de túnel SSH.
- **Chave SSH dedicada e restrita** para o túnel, registrada no RPi com
  `restrict,port-forwarding,permitopen="127.0.0.1:1883"`: não abre shell nem
  encaminha outra porta, mesmo se vazar.
- **Unidades de usuário em vez de sistema**, porque o `sudo` do homeserver
  pede senha interativa — que eu não digito — e nenhum dos dois serviços
  precisa de privilégio. `loginctl enable-linger` (sem sudo, via polkit)
  resolveu a sobrevivência a reboot.
- **Tabela de telemetria chama `enlace`, não `leitura`.** O que existe hoje é
  qualidade de enlace, não leitura de sensor; `leitura` fica reservada para a
  Fase 1. Nomear errado seria mentir sobre o conteúdo.

### Aprendido

- **Capturar parâmetro em banner de boot é frágil.** O `sf` saía nulo porque a
  bridge, ao reiniciar, conecta-se a uma placa que já está rodando e nunca vê o
  banner. Corrigido fazendo o firmware **reanunciar o `sf=` no heartbeat** a
  cada 5 s: o dado passa a se autodescrever independentemente de quem reiniciou
  primeiro. Isso importa porque o SF define a sensibilidade contra a qual a
  margem é medida — e a varredura SF7–SF12 vai variá-lo.
- A medição de consumo confirma **pelo lado empírico** o que o ADR-004
  sustentava por análise: a 81 mA contínuos uma célula de 2000 mAh dura ~25 h.
  Sem sono profundo não existe nó de campo autônomo.

### Próximo

1. **Varredura SF7–SF12** é agora o item de maior valor: fecha a Fase 0, e
   toda amostra já cai no banco marcada com o SF correto. Falta tornar o SF
   ajustável em execução — hoje é `#define`, e trocar exigiria 12 regravações
   com o notebook em campo.
2. `lib/proto/` — o `--no-id` só funciona porque existe um transmissor só.
3. Painel lendo do banco (histórico) além do MQTT (tempo real).

---

## 2026-07-31 (14) — Monitoramento da rede em tempo real no painel

**Fase:** 2 · **Duração:** média

### Feito

- **Nova aba *Monitoramento*** no painel, alimentada pelo MQTT ao vivo
  (`tools/painel/telemetria.py` + rota `/api/telemetria`, atualização a cada
  2 s). Mostra:
  - **Margem de enlace nos dois sentidos**, com as linhas de 20 dB
    (confortável) e 10 dB (mínimo) desenhadas no gráfico — é o número que
    decide se um ponto serve, não o RSSI cru.
  - **RSSI e SNR de subida e descida** separados. Subida = nó → gateway;
    descida = gateway → nó. Medir os dois é o que revela enlace assimétrico.
  - **Assimetria** com faixa de ±10 dB marcada.
  - **Perda de pacotes** medida por **buraco na numeração de sequência** — a
    bridge só imprime quando recebe, então o que falta no `seq` é exatamente o
    que se perdeu no ar, sem precisar de outro contador. Tira de hastes mostra
    se a perda é isolada (desvanecimento) ou em rajada (interferência).
  - **Tabela da frota** cruzando as 6 placas com quem está de fato falando, e
    **tabela de bridges** com fila em disco e tempo no ar.
- **Limiares vivem no servidor, não no navegador** (`telemetria.py` espelha
  `firmware/src/ui_dev.h`): sensibilidade −129 dBm em SF9, margem boa 20 dB,
  mínima 10 dB, assimetria máx. 10 dB, silêncio 15 s. São regra do projeto, não
  preferência de visualização — mudar o critério muda num lugar só.
- **`coletor.py` tinha catálogo de placas desatualizado** (HTC-03 sem MAC,
  HTC-02 ainda como PONGER, HTC-06 ausente). Corrigido contra `HARDWARE.md` e
  acrescido de `node_id` e `antena` — é o `node_id` que casa placa física com
  telemetria MQTT.

### Decidido

- **O broker continua fechado em `localhost`; o acesso externo é por túnel
  SSH** (`ssh -N -L 1883:127.0.0.1:1883 sentinelapi@…`). A alternativa —
  `listener 1883` + `allow_anonymous true` — foi escrita e descartada: broker
  anônimo exposto na LAN aceita publicação de qualquer um, e um sistema de
  alerta que aceita telemetria forjada é pior do que um que não tem
  telemetria. O túnel usa a chave já estabelecida e não expõe nada.
  Quando o ingestor virar serviço permanente, decidir entre `autossh` e
  `password_file` + TLS.
- A dependência de `paho-mqtt` é **opcional por construção**: sem ela, ou sem
  broker, a aba explica o que falta e o resto do painel segue funcionando.

### Aprendido

- Regra de CSS que atinge `.serie` vence atributo de apresentação `stroke` no
  SVG — as duas curvas saíram da mesma cor até trocar para `style="stroke:…"`.
  Vale para qualquer atributo de apresentação em SVG estilizado por classe.
- A ausência de telemetria tem **três causas distintas** e confundi-las
  esconderia defeito real: a bridge não aparece como nó porque é ela quem
  recebe; a placa de bancada não transmite de propósito (A-003); a placa nunca
  gravada não existe na rede. A tabela distingue as três.

### Próximo

1. Ingestor MQTT → banco continua sendo o item que falta para fechar a Fase 2.
2. A telemetria só descreve o par `HTC-01` ↔ `HTC-03`. Quando houver mais de um
   nó transmitindo, o `--no-id` deixa de bastar — o `node_id` precisa vir
   dentro do quadro, o que já está previsto para `lib/proto/` na Fase 1.

---

## 2026-07-31 (13) — Primeira telemetria ponta a ponta: rádio → MQTT

**Fase:** 2 · **Duração:** curta

### Feito

- **`HTC-03` conectada fisicamente na USB do Raspberry Pi 4.** Reiniciada a
  `sentinela-bridge.service`: conectou serial (`/dev/ttyUSB0`) e MQTT sem
  erro, sem precisar de nenhuma intervenção manual — confirma que o
  `Restart=always` + espera tolerante a porta ausente funcionam como
  desenhado.
- **Corrigido `--no-id` ausente na unidade systemd**: sem ele, `bridge.py`
  usa o padrão `0` e a telemetria saía em `sentinela/no/0/telemetria` — não
  é bug do script, é parâmetro operacional mesmo (o CSV do firmware não
  carrega o `node_id` de quem enviou o ping, só de quem recebeu; por isso
  `--no-id` existe). Adicionado `--no-id 1` ao `ExecStart` (par ativo hoje:
  `HTC-01` como PINGER). Também adicionado `Environment=PYTHONUNBUFFERED=1`,
  fechando a pendência anotada na entrada 9 — sem isso o `journalctl` não
  mostrava as linhas de log do processo em tempo real.
- **Primeira telemetria real ponta a ponta confirmada**: `mosquitto_sub` no
  próprio RPi mostrou `sentinela/no/1/telemetria` publicando a cada ~3–4 s,
  com `enviados`/`recebidos` subindo em paridade (65/65 no momento da
  checagem) e RSSI em torno de −83 dBm local / −90 dBm remoto. Fecha o
  critério de saída da Fase 2 ("leitura visível no banco em menos de 5 s") no
  trecho que já existe — falta só o ingestor MQTT → banco.

### Aprendido

- `--no-id` é por-par, não por-protocolo: se um dia houver mais de um
  PINGER falando com a mesma bridge, o esquema atual não distingue a origem
  — é limitação conhecida do formato CSV do firmware de bring-up, aceitável
  na Fase 0/2, não algo a corrigir agora.

### Próximo

1. Ingestor MQTT → banco (`sentinela/no/<id>/telemetria` → TimescaleDB) —
   primeiro item real que falta para fechar a Fase 2 de ponta a ponta.
2. Deixar `HTC-01` com alimentação independente (poder ficar sem estar preso
   à USB do Mac) para o ensaio poder rodar por mais tempo sem depender do
   notebook ligado.

---

## 2026-07-31 (12) — SSH do Raspberry Pi resolvido; bridge instalada de verdade

**Fase:** 2 · **Duração:** média

### Feito

- **P-010 fechada: acesso SSH por chave ao Raspberry Pi 4 estabelecido**,
  `sentinelapi@192.168.15.73` (Debian 13/Trixie, aarch64). O usuário rodou
  `ssh-copy-id` pelo próprio terminal (chave adicionada com sucesso); eu não
  toquei em nenhuma senha, mesma regra de sempre.
  - No caminho, `ssh-copy-id` acusou `REMOTE HOST IDENTIFICATION HAS
    CHANGED` — esperado (não incidente de segurança): o SD card foi
    regravado desde a última tentativa, então o host gerou chaves SSH novas
    para o mesmo IP. Resolvido limpando a entrada antiga com `ssh-keygen -R
    192.168.15.73` antes de repetir o `ssh-copy-id`.
- **Mosquitto instalado e ativo no RPi 4** via `apt` (decide a dúvida em
  aberto do `gateway/README.md`: broker fica no RPi, não no homeserver, para
  a bridge continuar enfileirando se o link até o homeserver cair).
- **Bridge instalada de verdade no RPi 4**: repositório sincronizado com
  `rsync` (não `git clone` — o repo é privado e o RPi é host de runtime, não
  precisa de outra chave de deploy do GitHub), venv criado com
  `pyserial`/`paho-mqtt`. Unidade `gateway/sentinela-bridge.service` ajustada
  (usuário real é `sentinelapi`, não `pi` como no template) e instalada via
  `systemctl enable --now` — confirmado `active (running)`, sem loop de
  reinício mesmo com a `HTC-03` ainda não conectada fisicamente (a bridge
  tolera a porta serial ausente, como projetado).

### Aprendido

- `ssh-copy-id` falhando por causa de host key não é automaticamente motivo
  de alarme quando há uma explicação concreta na própria sessão (SD card
  regravado) — mas vale sempre checar o porquê antes de simplesmente apagar
  a entrada, para não normalizar ignorar o aviso.
- Rodar o setup do RPi (apt install, pip install) em background evitou
  travar a sessão em instalações lentas de primeira execução numa placa
  ARM — o padrão de "background + notificação" funcionou bem aqui.

### Próximo

1. Conectar a `HTC-03` fisicamente na USB do Raspberry Pi 4 e confirmar que
   `journalctl -u sentinela-bridge -f` mostra telemetria chegando (ou ao
   menos a porta serial sendo aberta sem erro).
2. Publicar uma mensagem MQTT de teste (`mosquitto_sub` no próprio RPi) para
   fechar o ciclo ponta a ponta desta fase antes do ingestor existir.
3. Ingestor MQTT → banco ainda não existe — próximo item real da Fase 2.

---

## 2026-07-31 (11) — HTC-01 regravada com o firmware atual (economia de tela)

**Fase:** 0 · **Duração:** curta

### Feito

- **`HTC-01` regravada com `node_dev`** (PINGER, `NODE_ID=1`, com antena) —
  MAC conferido antes (`3c:71:bf:8c:2c:d0`, bate com `HARDWARE.md`). Motivo:
  o firmware anterior da placa é de antes da economia de energia do OLED
  (entrada 9 deste log); a regravação traz `HTC-01` para o mesmo binário já
  validado nas demais placas. Boot confirmado por serial: `no=1 papel=PING`,
  rádio ok, primeiro ping enviado sem pong (esperado — `HTC-02` está sem
  antena no momento, ver entrada 10).

### Próximo

1. Raspberry Pi sendo conectado pelo usuário para iniciar os testes de
   bridge — retomar o acompanhamento do acesso SSH e da instalação do
   Mosquitto/`gateway/bridge.py` assim que ele estiver na rede.

---

## 2026-07-31 (10) — HTC-03 vira bridge de verdade; antena remanejada da HTC-02

**Fase:** 2 · **Duração:** curta

### Feito

- **`HTC-03` regravada de `bench_03` para `bridge`** (RF-ativo, ROLE_PONGER,
  `NODE_ID=3`), com antena conectada — confirmado pelo usuário e verificado
  por boot serial (`no=3` implícito no ambiente, heartbeat `# rx ativo | ruido
  -87 dBm | recebidos 0`). Passa a ser o receptor real para validar o bridge
  MQTT com o Raspberry Pi.
- A antena veio da **`HTC-02`**, que ficou sem antena. Por segurança
  (A-003/A-010: nunca RF-ativo sem antena confirmada), a `HTC-02` foi
  imediatamente regravada para um novo ambiente **`bench_02`** (criado em
  `firmware/platformio.ini`, mesmo padrão dos demais `bench_*`). Boot
  confirmado por serial: `# no=2 papel=BENCH boots=1`.
- MAC conferido antes de cada gravação via `esptool.py flash_id`: `HTC-03` =
  `3c:71:bf:8c:31:70`, `HTC-02` = `3c:71:bf:8c:2f:9c` — ambos batem com
  `HARDWARE.md`.
- `docs/HARDWARE.md`, `docs/PLANO.md` (P-011, item da Fase 2) e
  `firmware/platformio.ini` atualizados para refletir a nova alocação de
  antenas: hoje só `HTC-01` e `HTC-03` têm antena; `HTC-02`, `HTC-04`,
  `HTC-05`, `HTC-06` seguem em modo bancada até a compra de mais antenas
  (P-011).

### Aprendido

- Reconfirma o achado de E-006: abrir a porta serial nem sempre reseta a
  placa. Para capturar o boot completo de uma placa recém-gravada (útil em
  `ROLE_BENCH`, que só imprime uma vez, sem heartbeat periódico como o
  PONGER), o método confiável foi encadear `esptool.py --after hard_reset
  flash_id` (que sempre reseta via RTS ao final) imediatamente antes de abrir
  a porta para leitura — não confiar em toggles manuais de DTR/RTS via
  pyserial, que nesta sessão chegaram a travar o processo sem gerar reset
  nem erro.

### Próximo

1. Conectar fisicamente a `HTC-03` na USB do Raspberry Pi assim que o SSH
   estiver acessível, e rodar `gateway/bridge.py` real (não mais
   `--simular`) para validar a chegada de telemetria via MQTT ponta a ponta.
2. `HTC-02` some da lista de nós de campo ativos até uma antena nova chegar
   (P-011) — não usar `node_range` nela enquanto isso.

---

## 2026-07-31 (9) — Economia de tela e teste serial da HTC-03

**Fase:** 0 · **Duração:** curta

### Feito

- **Economia de energia do OLED**: `ui_dev.h`/`ui_dev.cpp` ganharam
  `uiRegistrarAtividade()` e `uiChecaInatividade()`. A tela apaga via
  `oled.setPowerSave(1)` após `TELA_INATIVIDADE_MS` (60 s) sem toque no botão
  PRG, e liga de volta (`setPowerSave(0)`) no primeiro toque, sem perder o
  conteúdo da GDDRAM. `uiDraw()` agora retorna cedo se a tela está apagada,
  evitando tráfego I2C à toa. Ligado em `main.cpp`: `pollButton()` registra
  atividade ao detectar o botão pressionado, e todo laço que redesenha a tela
  (`idleWithUi` do PINGER, espera de pong, `loop()` do PONGER e do BENCH)
  chama `uiChecaInatividade()` a cada iteração. Compilado com sucesso nos 7
  ambientes (`node_dev`, `node_range`, `bridge`, `bench_03` a `bench_06`);
  complexidade ciclomática máxima no firmware segue em 8 (`tools/complexidade.py
  --limite 10`).
- **`gateway/bridge.py` testado contra a `HTC-03` real** (não mais
  `--simular`): conectou normalmente (`serial conectada:
  /dev/cu.usbserial-0001`), sem publicar telemetria — esperado, pois
  `bench_03` só escuta e nunca imprime linha CSV de pacote recebido (esse
  comportamento é exclusivo do papel PONGER/`bridge`).

### Aprendido

- **Reset do ESP32 ao abrir a porta serial permanece inconsistente entre
  sessões/placas.** Repeti o padrão "configurar DTR/RTS antes de abrir a
  porta", já validado como livre de reset numa sessão anterior com outras
  placas/firmware, e desta vez a HTC-03 mesmo assim mostrou o banner completo
  de reset ao abrir. Não há evidência suficiente para apontar causa única
  (parece característica do driver CP210x/macOS por combinação específica de
  placa, não bug isolado do `bridge.py`) — registrado aqui sem forçar uma
  conclusão que os dados não sustentam.
- Buffering padrão do Python esconde a saída do `bridge.py` quando o stdout
  vai para arquivo em vez de TTY; `python -u` resolve. Vale considerar
  `PYTHONUNBUFFERED=1` na unidade systemd de produção (`gateway/sentinela-bridge.service`)
  para não repetir a confusão em campo.

### Próximo

1. HTC-03 segue em `bench_03` (sem antena) — decidir com o usuário se ela é
   reflashada para `bridge` (RF-ativo, exige antena) antes de ligar na USB
   do Raspberry Pi, ou se fica em modo bancada só para validar a conexão
   física por enquanto.
2. Retomar acesso SSH ao Raspberry Pi assim que o usuário rodar
   `ssh-copy-id` — não usar senha em nenhuma hipótese (ver decisão registrada
   na entrada anterior).
3. Gravar `HTC-05`/`HTC-06` com `bench_05`/`bench_06` quando conectadas,
   seguindo o mesmo protocolo de identificação por MAC.

---

## 2026-07-31 (8) — HTC-03 gravada; Raspberry Pi vivo na rede

**Fase:** 0 → 2 · **Duração:** curta

### Feito

- **`HTC-03` gravada com `bench_03`** e verificada por hash. MAC confirmado:
  `3c:71:bf:8c:31:70`. Sem antena conectada — segue em modo bancada até uma
  antena ser destinada a ela (RF-ativa, papel `bridge`, exige confirmação
  física antes de regravar).
- **Raspberry Pi 4 gravado e confirmado vivo na rede**, via a porta `eth1` do
  roteador — apareceu como `sentinelapi` em dois IPs (Ethernet + Wi-Fi, mesma
  placa), com MAC `b8:27:eb:...` (prefixo genuíno da Raspberry Pi Foundation).
  A gravação da imagem havia terminado com **falha de verificação no
  Raspberry Pi Imager**, mas o sistema subiu e chegou a anunciar hostname via
  mDNS — sinal de que ao menos parte da customização (hostname) persistiu.
- **SSH ainda não estabelecido** — porta 22 recusando conexão nos dois IPs no
  momento da checagem. Hipótese mais provável: o script de primeiro boot
  (`firstrun.sh`, usado pelo Raspberry Pi OS Trixie para aplicar usuário/SSH
  da customização do Imager) não terminou de rodar, ou foi parcialmente afetado
  pela mesma falha de verificação — o hostname pegou, o SSH pode não ter
  pegado.
- Usuário do Pi esquecido pelo usuário; senha (`fordf7572`) foi informada no
  chat, mas **não foi usada por mim** — política do projeto proíbe eu digitar
  senha em qualquer campo, mesmo de sistema próprio. Orientado o usuário a
  rodar `ssh-copy-id` no próprio terminal para estabelecer acesso por chave,
  mesmo padrão do homeserver.

### Aprendido

- **Diagnóstico anterior de "cartão com defeito de hardware" ficou parcialmente
  refutado pelo resultado real**: a mesma combinação cartão+leitor que falhou
  em três testes diretos (Imager, `diskutil` partição, `diskutil` montagem)
  ACABOU produzindo um Raspberry Pi que boota e aparece na rede. Isso não
  invalida os testes — mostra que a falha de verificação pode ser parcial
  (afeta alguns blocos/arquivos, não a imagem inteira) e que **"verificação
  falhou" não é sinônimo de "sistema não vai funcionar"**, mas também não
  garante que tudo funcionará (o SSH não estabelecido é candidato a ser
  exatamente esse dano parcial).
- Luz de link no roteador/switch não prova que o Linux terminou de bootar —
  pode vir de negociação de PHY em estágio bem anterior ao SO. mDNS respondendo
  com hostname correto é evidência bem mais forte de que o userspace subiu.
- Duas entradas ARP com mesmo hostname e MACs diferentes, ambas respondendo
  ping, é o padrão esperado quando o mesmo Pi tem Ethernet e Wi-Fi ativos
  simultaneamente — não é dois dispositivos.

### Próximo

Usuário vai rodar `ssh-copy-id` no terminal local para estabelecer acesso por
chave ao Pi. Depois disso: confirmar se SSH realmente não vinha funcionando por
falta de serviço (pode precisar reiniciar o Pi ou aguardar o firstrun.sh
terminar) e seguir para instalação de Mosquitto + `bridge.py` (ADR-007).

---

## 2026-07-31 (7) — HTC-04 gravada: primeira placa em modo bancada

**Fase:** 0 · **Duração:** curta

### Feito

- **`HTC-04` (placa com display defeituoso) gravada com `bench_04`** e
  verificada por hash. MAC confirmado: `3c:71:bf:8c:2f:a4` — registrado em
  HARDWARE.md.
- Confirmado por serial: `no=4 papel=BENCH boots=1`, rádio inicializado,
  varredura I2C rodou (0 sensores, esperado sem hardware ainda). Sem antena
  conectada e sem chamada de `radio.transmit()` — exatamente o comportamento
  que a armadilha A-010 exige.

### Aprendido

- O venv Python isolado criado numa sessão anterior (`scratchpad/venv-esp`)
  não persistiu entre sessões — o scratchpad é efêmero. `esptool.py` já vem
  empacotado com o PlatformIO (`~/.platformio/packages/tool-esptoolpy/`), o
  que evita recriar esse venv toda vez; usar esse caminho como padrão daqui
  em diante para inspeção rápida de MAC/flash sem gravar.

### Próximo

Gravar as demais placas sem antena (`HTC-03`, `05`, `06`) em modo bancada
conforme forem conectadas, confirmando MAC antes de cada gravação (E-005/A-010).

---

## 2026-07-31 (6) — Bobina identificada, placa sem display realocada, SO do RPi decidido

**Fase:** transversal · **Duração:** ~1 sessão

### Feito

- **Fotos reais de uma das placas analisadas.** Identificada a bobina de cobre
  perto do PRG: **antena de WiFi/Bluetooth do ESP32, sem relação com o rádio
  LoRa.** Cruzada com a documentação oficial da Heltec (V3/V4 chama esse
  componente de "metal spring antenna" para 2,4 GHz) e com o dimensionamento
  físico (quarto de onda em 915 MHz mede ~8,2 cm; a bobina tem ~1,5–2 cm de
  fio, plausível só para 2,4 GHz). Registrado em HARDWARE.md com marca [E] —
  não há datasheet da V2 com o componente explicitamente rotulado.
- **Placa com display defeituoso identificada** e realocada para `HTC-04`,
  dedicada ao firmware **headless** (`lib/app`/`lib/hal` sem `ui_dev.h`) — o nó
  de campo definitivo não tem tela (ADR-004), então essa placa força a
  validação real do caminho sem display em vez de depender de disciplina para
  não "espiar" a tela numa placa saudável.
- **ADR-007** — Raspberry Pi OS Lite (64-bit) oficial, sem imagem própria.
  Passo a passo de instalação documentado, fecha P-010 quando executado.

### Aprendido

- **A bobina não resolve a escassez de antena.** Está numa trilha de RF
  totalmente separada (ESP32 → WiFi, não SX1276 → LoRa); reaproveitá-la para
  915 MHz exigiria dessoldar e reencaminhar trilha — retrabalho de placa, não
  algo acionável agora. P-011 (comprar antenas de 6 dBi) continua sendo o
  caminho.
- Falha de hardware pode virar ativo de projeto quando o produto final já
  previa o cenário que a falha força — a placa sem display só antecipa um
  teste que a fase 4 exigiria de qualquer forma.

### Decidido

- **HTC-04 = protótipo sem display**, não mais "futuro nó de sensores"
  genérico — mudança na tabela de alocação de HARDWARE.md.
- **Nenhuma imagem própria para o RPi.** O Raspberry Pi 4 é infraestrutura de
  bancada (ADR-002), não produto final — imagem customizada só faria sentido
  se isso mudasse, e não é o plano.

### Próximo

Executar o passo a passo do ADR-007 quando o cartão microSD/Raspberry Pi
estiver disponível para gravação. Corrigido P-011 para especificar 6 dBi (não
2 dBi) como alvo de compra.

---

## 2026-07-31 (5) — Ganho de antena resolvido, modo bancada e bridge do RPi

**Fase:** 0 → 2 · **Duração:** ~1 sessão

### Contexto

Atualização de inventário: **6 placas Heltec V2** (não mais 5) e **1
Raspberry Pi 4**, mas **apenas 2 antenas de 2 dBi**, sem bateria e sem sensor
ainda. Sessão focada em decidir o que é seguro e produtivo fazer nesse cenário.

### Feito

- **Texto integral do Ato Anatel 14448/2017 obtido** — resolve C-02, que estava
  `[VERIFICAR]` desde a auditoria de proveniência.
- **`docs/CONFORMIDADE.md` §1.1.1** — regra de ganho de antena documentada com
  a norma primária: item 10.5 fixa **6 dBi como ganho de referência** para
  equipamentos de espalhamento espectral (LoRa/CSS se enquadra). Acima disso,
  redução de potência dB-a-dB — o que torna o EIRP de transmissão **constante**
  além de 6 dBi, qualquer que seja o ganho adicional.
- **`ROLE_BENCH`** no firmware — papel novo, seguro sem antena: inicializa o
  rádio, escuta passivamente, nunca transmite. Testa I2C externo, ADC de
  bateria e OLED. Ambientes `bench_03` a `bench_06` em `platformio.ini`.
  Compila limpo nos 6 ambientes; complexidade máxima do arquivo caiu (loop do
  bench = CC 4).
- **`gateway/bridge.py`** — serial → MQTT com reconexão automática dos dois
  lados e buffer em disco. Aceita `--simular <csv>` para testar sem hardware
  nenhum — validado: publica quando há broker, cai para o buffer quando não
  há, e retoma o buffer entre execuções sem duplicar nem perder mensagem.
- **`gateway/sentinela-bridge.service`** — unidade systemd, reinicia sozinha.
- `docs/HARDWARE.md` reescrito para 6 placas, com a restrição de antenas como
  regra operacional explícita e tabela de alocação por papel/firmware.
- Armadilha **A-010** registrada: nunca gravar papel RF-ativo em placa sem
  antena confirmada fisicamente.

### Aprendido

- **A resposta a "quantos dBi podemos usar" não é um limite de hardware — é
  puramente regulatório, e tem um número exato.** O conector SMA/u.FL aceita
  qualquer antena de 50 Ω; o que limita é a Anatel. Subir de 2 para 6 dBi dá
  **+4 dB de EIRP de graça**, sem mexer no firmware. Acima de 6 dBi, a regra de
  redução de potência cancela o ganho extra — **zero benefício de alcance em
  transmissão**, mas ganho real de **recepção** (não regulado), o que explica
  por que o SitkaNet usou Yagi de 9 dBi só no hub, não nos nós de campo.
- RX é seguro sem antena; só TX arrisca o PA (reflexão em carga aberta). Isso
  permitiu desenhar um papel de firmware genuinamente útil (não um stub vazio)
  para as 4 placas sem antena hoje.
- Testar a bridge sem hardware via arquivo simulando a serial provou toda a
  lógica de resiliência (buffer, reconexão) que só apareceria em campo depois
  de já estar em produção — encontrar isso agora custou zero.

### Decidido

- **As 2 antenas ficam sempre nas placas RF-ativas do momento** (hoje
  `HTC-01`/`HTC-02`); as demais rodam `bench_*` até uma antena ficar disponível
  para teste específico.
- Novas pendências P-010 a P-013: acesso SSH ao RPi 4, compra de antenas
  adicionais, bateria e primeiro sensor.

### Próximo

Confirmar qual placa está de fato na porta antes de gravar (checklist A-010);
gravar `bench_04`/`05`/`06` nas placas sem antena para validar hardware;
configurar acesso ao Raspberry Pi 4 (P-010) para instalar a bridge de verdade.

---

## 2026-07-31 (4) — Cinco frentes de negócio: mercado, concorrência, patente e valor

**Fase:** transversal · **Duração:** ~1 sessão

### Feito

- **`docs/NEGOCIO.md`** — índice que amarra as cinco frentes, com as conclusões
  consolidadas e a sequência recomendada.
- **`docs/MERCADO_MUNICIPIOS.md`** — dimensionamento do mercado de prefeituras,
  com dados oficiais do CEMADEN, IBGE e CPRM.
- **`docs/MERCADO_MINERACAO.md`** — barragens de mineração, obrigação legal e
  por que este mercado é mais difícil que o municipal.
- **`docs/CONCORRENCIA.md`** — o que já existe e é sólido, onde não somos
  originais e onde há originalidade defensável.
- **`docs/PATENTES.md`** — escala de três níveis contra as exigências do INPI.
- **`docs/VALUATION.md`** — três métodos de avaliação e faixa consolidada.
- Coletor do painel estendido para reconhecer as pendências das novas frentes
  (M, N, PT, V) — 54 pendências consolidadas, 51 abertas.

### Aprendido

- **O universo de clientes está contado pelo Estado.** 1.295 municípios
  monitorados pelo CEMADEN com meta de 2.095; **958 com áreas de risco
  mapeadas**; 8.270.127 pessoas em 2.471.349 domicílios expostos, em 872
  municípios **[G]**. Não é preciso estimar demanda por analogia.
- A base de população em risco ainda é do **Censo 2010** — deve ser tratada como
  piso, não como estimativa corrente.
- **Na mineração, monitorar é obrigação legal.** A Lei 14.066/2020 exige
  armazenar dados de instrumentação e fornecê-los em tempo real quando requerido
  **[N]**. São 911 barragens, 461 sob PNSB, **118 em alerta ou emergência** —
  recorde histórico, resultado de endurecimento regulatório **[G]**.
- **O hardware não é original.** Worldsensing e Senceive fazem sensor de
  inclinação sem fio com **10 a 15 anos de bateria** — melhor que o nosso — e a
  Senceive posiciona explicitamente para barragens de rejeito **[L]**. Se a
  proposta fosse construir esse sensor, o certo seria comprar deles.
- **Preços do setor não são públicos** — venda consultiva. Obter cotação real
  virou a pendência mais crítica da frente comercial (C-01).
- A originalidade defensável está na **referência distribuída** de manutenção,
  na **integração geoespacial** e no **custo por ponto** que permite adensar
  malha. O concorrente premium está na barragem crítica; o Sentinela concorre
  com o *nada* que existe no talude municipal.
- **Para patente, o INPI exige novidade, atividade inventiva e aplicação
  industrial**, mais suficiência descritiva **[N]**. Modelo de Utilidade tem
  exigência menor (ato inventivo) e vigência de 15 anos contra 20 da invenção.

### Decidido

- **Sequência: municipal primeiro, mineração depois.** Consolidar onde há canal,
  piloto e menor barreira de credibilidade; entrar na mineração por
  **adensamento de malha**, não por substituição de instrumento crítico, e com
  histórico operacional em mãos.
- **Reposicionamento do produto:** não é "mais um sensor de inclinação", é uma
  malha densa e barata integrada a base geoespacial, com manutenção
  autodiagnosticada.
- **O sistema deve ingerir dados de instrumentos de terceiros** — cliente com
  Worldsensing instalado não deve ser obrigado a substituir. Transforma
  concorrente em complemento e reforça ADR-005.
- **Patente: nível 1–2 de 3.** Não atinge o mínimo para depósito. Falta busca de
  anterioridade (PT-01) e implementação do candidato mais forte. A distância até
  o nível 3 é menor do que parece.
- **Valuation: piso defensável de R$ 130–260 mil** (custo de reposição do que
  existe). Cenários acima são condicionais. O valor está **dentro da Geopixel**,
  não fora — o canal já resolvido elimina o maior risco de um projeto de
  hardware.

### Próximo

Três pendências críticas antes de qualquer exposição pública: cotação de
concorrentes (C-01), busca de anterioridade (PT-01) e definição de titularidade
(PT-03). Divulgar antes do depósito compromete a novidade.

---

## 2026-07-31 (3) — Atalaia: nome, saúde da frota e manutenção preditiva

**Fase:** transversal (projeto para as fases 1–3) · **Duração:** ~1 sessão

### Feito

- **Nomenclatura definida:** o dispositivo de campo passa a ser a **Atalaia**;
  o gateway que congrega uma área, o **Farol**; uma campanha ativa sobre um
  conjunto de taludes, uma **Vigília**. Identificação `ATL-<município>-<seq>`.
- **`docs/MANUTENCAO.md`** — engenharia de saúde da frota: a curva de carga
  solar como instrumento de diagnóstico, sete assinaturas de falha, catálogo de
  22 alarmes com severidade e ação, índice de saúde e roteirização.
- **Sete requisitos novos**, RC-12 a RC-18, em `docs/REQUISITOS.md`.
- **Aba "Frota e alarmes"** no painel, com as assinaturas de energia, o
  catálogo filtrável por grupo e a composição do índice de saúde.
- Corrigido cache de estáticos no servidor do painel — impedia ver edição sem
  limpar o navegador.

### Aprendido

- **A curva de carga solar é uma assinatura, não só um número.** Sujeira reduz a
  captação de forma aproximadamente uniforme ao longo do dia; sombra atua em
  janela horária específica que se desloca com a estação. É a **forma** da
  curva que separa as duas — daí registrar `t_ini` e `t_fim` importar tanto
  quanto registrar `E_dia`.
- Sombreamento **parcial** derruba a corrente de forma desproporcional à área
  sombreada, porque as células estão em série. Isso facilita a detecção.
- A indústria fotovoltaica detecta sujeira com **painel de referência limpo** ou
  sensor óptico dedicado **[L]** — ambos caros por ponto, e o projeto tem
  dezenas de pontos.
- **Referência distribuída:** comparar cada Atalaia com a **mediana das vizinhas
  do mesmo Farol** elimina a variável climática sem sensor adicional. Se todas
  caem juntas, foi o tempo; se uma cai sozinha, o problema é local. Custo
  marginal zero e melhora conforme a rede cresce.
- **Umidade dentro do invólucro é o alarme de melhor retorno do catálogo**:
  custa um sensor barato e detecta falha de vedação antes de a água destruir a
  eletrônica — transforma perda total em troca de anel de vedação.
- O custo de operação é dominado por **deslocamento**, não por intervenção.
  Então a saída útil do sistema é uma **rota agrupada**, não uma lista de
  alarmes — e uma visita programada deve arrastar as pendências de baixa
  prioridade das Atalaias próximas.

### Decidido

- **RC-17 — referência distribuída em vez de limiar absoluto.** Limiar absoluto
  gera alarme falso em semana nublada, que é o modo de falha que faz sistemas de
  alarme perderem credibilidade.
- **RC-16 — alarme crítico zera o índice de saúde.** Atalaia muda com bateria
  cheia não é 70% saudável; é inútil.
- **RC-18 — sugestão antes de ordem de serviço.** As assinaturas são derivadas
  de princípio físico e da literatura fotovoltaica, **ainda não validadas em
  campo neste projeto**. Os limiares numéricos (0,75 de razão, 7 e 14 dias) são
  ponto de partida e precisam de calibração com operação real antes de virarem
  despacho automático de equipe.
- **Nota de propriedade intelectual registrada:** o uso da mediana da própria
  frota como referência de irradiância, dispensando painel de referência, é
  candidato a reivindicação. Não divulgar antes de consultar o INPI.

### Próximo

Ensaio 03 — varredura de spreading factor.

---

## 2026-07-31 (2) — Painel de controle e complexidade ciclomática como política

**Fase:** transversal · **Duração:** ~1 sessão

### Feito

- **`tools/complexidade.py`** — análise de complexidade ciclomática (McCabe)
  para Python (via AST) e C/C++ (varredura léxica), com faixas, limite
  configurável e saída JSON.
- **`docs/QUALIDADE_CODIGO.md`** — política permanente: limite 10 para toda
  função do repositório, incluindo firmware. Padrões de refatoração
  documentados.
- **Refatoração de todo o código acima do limite**, com verificação funcional:
  `pagLink` no firmware (12 → 3), `georreferenciar.main` (25 → 6),
  `coleta.main` (19 → 5), `importar_fotos.main` (18 → 8).
- **`tools/painel/`** — painel de controle do projeto: servidor HTTP em
  biblioteca padrão e interface em nove seções, com tema claro/escuro,
  navegação por hash, gráficos SVG próprios e conversor Markdown próprio.
  Zero dependência externa e zero CDN.

### Aprendido

- Refatorar por complexidade **melhorou a legibilidade**, não piorou. As quatro
  funções divididas ficaram com partes que fazem sentido isoladamente —
  `blocoRssi`, `blocoMargem`, `parse_amostra`, `escreve_kml`. Onde a divisão
  não produz nome óbvio, o corte estaria errado.
- O firmware já estava saudável antes da política: só uma função acima do
  limite, e as demais em torno de 5. O problema estava nas ferramentas Python,
  onde os `main` acumulavam parsing, laço, escrita e impressão.

### Decidido

- **Limite de 10 para toda função**, mais rígido que o clássico de McCabe (20).
  O custo de dividir é baixo; o benefício em código que decide sobre alerta é
  alto. Verificação obrigatória antes de commit que toque em código.
- Painel sem dependência externa: biblioteca padrão no servidor, SVG e
  Markdown próprios no navegador. Mantém o projeto auditável e sem CDN.

### Próximo

Ensaio 03 — varredura de spreading factor.

---

## 2026-07-31 — Política de proveniência e auditoria retroativa

**Fase:** transversal · **Duração:** ~1 sessão

### Feito

- **`docs/REFERENCIAS.md`** — política de proveniência com marcação obrigatória
  (**[M]** medido, **[N]** norma, **[L]** literatura, **[G]** governamental,
  **[E]** estimativa, **[?]** pendente), bibliografia central por área e
  registro de revisões.
- **Auditoria retroativa** de toda a documentação, com quatro correções
  aplicadas (R1 a R4).
- `tools/haste.py` refeito sobre a **ABNT NBR 6123**, com fatores S1/S2 e
  velocidade característica por altura.
- Notas de proveniência inseridas nos documentos técnicos.

### Aprendido

- **Erro próprio encontrado na auditoria:** os cálculos de vento usavam 20 m/s,
  valor arbitrário e **não normativo**. A NBR 6123 dá isopletas de 30 a 48 m/s;
  com V₀ = 40 m/s, categoria III e S₁ = 1,15, a velocidade característica a
  1,5 m é **35,8 m/s**. Como a força varia com o quadrado, as deflexões
  publicadas estavam **subestimadas em ~3×**.
  A conclusão qualitativa não mudou — **ficou mais forte**. Mas o eletroduto
  3/4", antes aceitável a 1,5 m, saiu da recomendação (0,08° → 0,27°).
- **O limiar de "0,1 a 0,5°" não tinha origem.** A literatura é explícita em que
  limiares de inclinação são **específicos do sítio**. O projeto passou a
  especificar **capacidade de medição** (resolução e ruído estrutural), não
  limiar — que é definição geotécnica.
- **Referência fundacional brasileira localizada:** curva de **Tatizana et al.
  (1987)**, correlacionando chuva acumulada em 24 h e 72 h com escorregamentos
  na Serra do Mar. É a base dos sistemas operacionais de alerta.
- **Mecanismo de ruptura agora referenciado:** escorregamentos translacionais
  rasos mobilizam quase só o horizonte superior do solo, com ruptura no
  **contato solo residual/saprolítico**, por poropressão positiva com fluxo
  paralelo à encosta. O CEMADEN monitora umidade **até 3,0 m**.
- Documentação rigorosa serve simultaneamente a três funções: defesa em
  responsabilidade civil, demonstração de estado da técnica para patente e
  suficiência descritiva. Convém separar com clareza **o que é nosso** do que é
  estado da técnica.

### Decidido

- **Regra dura:** afirmação de domínio geológico, geotécnico ou geográfico
  **nunca** recebe marcação [E]. Só [L], [N] ou [G]. Sem fonte, sai do documento.
- Preços de materiais e sensores rebaixados a **[E]**, com cotação formal
  pendente (B-07). Valores sem cotação foram removidos de SENSORES.md.
- **[VERIFICAR]** com agente do INPI antes de qualquer divulgação pública ampla
  — publicar antes de depositar pode comprometer a novidade. O repositório é
  privado, o que preserva a opção.

### Próximo

Resolver os itens B-01 a B-08 de REFERENCIAS.md §5 antes de proposta comercial
ou pedido de patente. Ensaio 03 segue pendente.

---

## 2026-07-30 (9) — Projeto de ancoragem: o inclinômetro decide a altura

**Fase:** 0 → 4 (projeto) · **Duração:** ~1 sessão

### Feito

- **`docs/ANCORAGEM.md`** — projeto padronizado de fixação do nó no talude:
  método, profundidade, material, procedimento e kit, com custo estimado.
- **`tools/haste.py`** — calcula deflexão por vento, altura de antena exigida
  pela geometria de Fresnel e o trade-off de investir altura no sensor ou no
  gateway.
- Análise da perda fixa **corrigida**: com a informação de que a antena do
  `HTC-02` estava vertical a 1,5 m, a hipótese de polarização caiu. A causa são
  os **muros a ~3 m em todos os lados** — obstrução em campo próximo, que é
  desproporcionalmente danosa — somada à antena baixa nas duas pontas.
  Não é necessário repetir os pontos; P-009 encerrada.

### Aprendido

- **Haste alta e inclinômetro são incompatíveis no mesmo elemento.** Sob vento
  de 72 km/h, uma haste de 4 m deflete de 0,2° (tubo 2") a 1,6° (eletroduto
  3/4"). O *creep* a detectar é de 0,1 a 0,5° — o vento encobre o sinal. A
  1,5 m, a deflexão cai para 0,01–0,08°, uma ordem de grandeza abaixo.
  **Isso reverteu a recomendação anterior de haste de 3–4 m.**
- **PVC está descartado como elemento estrutural**: 1,19° já a 1,5 m, pior que o
  fenômeno medido.
- **Contra-senso da profundidade:** cravar *abaixo* da superfície de ruptura
  ancora o sensor no material estável e ele **deixa de medir** o movimento. A
  estaca precisa estar **dentro da camada que se move** — 0,8 a 1,2 m para
  deslizamentos rasos.
- **O desnível do terreno se cancela** em rampa uniforme: a folga de Fresnel no
  meio do vão vale (h_sensor + h_gateway)/2 − h_vegetação. Quem ajuda é o perfil
  **côncavo**; o **convexo** atrapalha e nenhuma haste resolve. Corrige a
  afirmação anterior de que "declive ajuda" — depende do formato, não da
  inclinação.
- **Elevar o gateway é N vezes mais eficiente** que elevar N sensores, já que as
  duas alturas entram com o mesmo peso na folga. Com gateway a 15 m, o sensor
  dispensa haste em vãos de até 1 km.
- **Yagi de 9 dBi no gateway rende o mesmo que haste de 4 m no sensor** — sem
  estrutura, sem vento, sem captor de raio no nó. A direcionalidade não é
  problema: encosta monitorada ocupa setor angular estreito.
- Do SitkaNet: **falhas de transmissão correlacionaram com chuva intensa** —
  confirma que o enlace degrada durante o evento que o sistema monitora, e
  sustenta a margem de 20 dB. Acelerômetro por limiar de vibração deu falsos
  alarmes e foi desativado. Bateria durou 2–3 meses contra >6 previstos. Apenas
  12 de 18 sensores de umidade deram dado confiável.

### Decidido

- **Arquitetura de duas funções separadas:** inclinômetro na **base engastada**
  (deflexão nula por definição), antena no topo a **1,5 m**. Mastro estaiado
  independente só quando o vão exigir.
- **Tubo de aço galvanizado a fogo 1.1/2", 2,5 m**, ~R$ 110 — 0,02° de deflexão,
  disponível em qualquer depósito.
- **Ponteira cravada com marreta, sem concreto**: instala e mede no mesmo dia,
  é reversível e acopla melhor ao solo superficial que um bloco de concreto.
- Estrutura de ancoragem estimada em **~R$ 300 por nó**.

### Próximo

Ensaio 03 — varredura de spreading factor.

---

## 2026-07-30 (8) — Modelo de propagação calibrado contra a literatura

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **Coordenada do `HTC-02` registrada** (−23,57543, −45,330545, alt 9,4 m,
  quintal murado com teto livre) — fecha a pendência P-008 e permite recalcular
  o ensaio 02 com distâncias reais.
- **Modelo refeito:** com as distâncias corretas, **n = 3,28 com RMS de 2,2 dB**
  sobre 5 pontos (antes 2,57, com P0 como referência errada).
- **`docs/PROPAGACAO.md`** — modelo calibrado, confronto com a literatura,
  dimensionamento de haste, zona de Fresnel e comparação SF × autonomia.
- **`tools/alcance.py`** — calculadora de alcance por cenário, spreading factor,
  altura de antena e perda fixa do ambiente.
- Foto do nó fixo preservada como âncora do ensaio.

### Aprendido

- **Nosso n = 3,28 é praticamente idêntico ao n = 3,22 medido em floresta
  tropical a 923 MHz.** Alvenaria esparsa e mata atenuam de forma comparável —
  ambos são meios com obstruções distribuídas. Consequência prática grande: os
  dados urbanos servem como **proxy do cenário de encosta com mata**, o que
  permite dimensionar antes de ter acesso ao talude real.
- **O modelo de dois raios prevê o ganho de altura com precisão**: previa
  +8,8 dB para a elevação de 6,2 → 17,0 m, medimos +9 dB. Isso autoriza usá-lo
  para dimensionar as hastes dos sensores.
- **Haste de 3 a 4 m é o ponto ótimo**: entrega 6,6 a 9,1 dB — equivalente a
  dois ou três spreading factors, **sem custo de energia**. O ganho é
  logarítmico, então acima de 4 m o custo estrutural e de SPDA cresce mais
  rápido que o benefício.
- **Elevar antena é melhor troca que subir SF.** SF7 → SF12 rende 14 dB ao custo
  de 28× de tempo de rádio ligado; uma haste de 4 m rende 9 dB de graça. Regra:
  primeiro altura e posicionamento, SF alto só para o que sobrar.
- **A perda fixa de 33,4 dB é a maior incerteza aberta e a maior oportunidade.**
  Reduzi-la para ~15 dB (gateway bem instalado) multiplicaria o alcance por
  ~3,6. Hipóteses: muros do quintal, antena baixa e — a mais provável —
  **polarização cruzada**, com o `HTC-02` deitado. Polarização cruzada custa
  20 a 30 dB e sozinha explicaria a maior parte.
- Literatura alerta: com **dossel acima de ~23 m** o enlace passa a depender de
  difração, RSSI cai para −120 a −127 dBm e o alcance fica em torno de 250 m em
  área florestada montanhosa. Nossos P3/P4 mediram exatamente essa faixa.
- **O relevo que cria o risco ajuda o rádio.** Em declive, a linha entre sensor
  na encosta e gateway em cota alta passa acima do terreno intermediário por
  geometria — a folga de Fresnel vem do desnível, não da haste.

### Decidido

- **P-009 vira prioridade sobre o ensaio 03.** Testar polarização e altura do nó
  fixo pode reclassificar todo o dimensionamento da rede, e custa meia hora.
- Haste de **3 a 4 m** entra no escopo da fase 4 como item de projeto, com a
  ressalva de que precisa ser solidária ao solo medido e rígida — haste que
  oscila com vento vira falso movimento no inclinômetro.

### Próximo

1. **P-009** — repetir o P6 com antena do `HTC-02` vertical e acima do muro.
2. Ensaio 03 — varredura de SF, já com o nó fixo corrigido.

---

## 2026-07-30 (7) — Ensaio 02 em campo: altura vence distância

**Fase:** 0 · **Duração:** ~14 min de percurso, 7 pontos

### Feito

- **Ensaio 02 executado** em percurso urbano noturno, sob sereno e chuva fina,
  com 7 pontos até ~205 m do ponto de partida.
- **`tools/importar_fotos.py`** — importa ensaio registrado só por fotos: lê a
  transcrição das telas, extrai GPS do EXIF (via `mdls`, que abre HEIC) e gera
  GeoJSON, KML e CSV, mais análise de distância e perda de percurso.
- Sete pontos georreferenciados **sem nenhuma anotação manual de coordenada**.
- Fotos originais preservadas em `dados/fotos/ensaio02/` como evidência (RC-10).

### Aprendido

- **Altura vence distância, e por muito.** P5/P6, a 206 m e 17 m de altitude,
  mediram **5 dB melhor** que P3/P4, a 156 m e 6 m de altitude — apesar de
  estarem 51 m mais longe. Descontado o custo da distância, a elevação entregou
  cerca de **8 dB por 11 metros**. Equivale a sextuplicar a potência, ou a subir
  dois spreading factors. O P6 fechou 20/20 pacotes, zero perda, sendo o ponto
  mais distante do ensaio.
- **Modelo de propagação ajustado: n = 2,57, resíduo RMS 2,2 dB.** Ajuste muito
  bom para 4 pontos em ambiente real com chuva. Fica entre espaço livre (2,0) e
  urbano denso (3,5–4,0), coerente com área residencial de baixa densidade.
- **Obstrução domina a distância nesta escala.** P3, a 138 m com alvenaria, mede
  pior que P4, a 174 m em descampado.
- **A sensibilidade real supera a tabela**: P2 recebeu pacote a −133 dBm, abaixo
  da sensibilidade nominal de SF9 (−129 dBm). O LoRa demodula com SNR negativo,
  então a margem exibida é conservadora — o critério de 20 dB tem folga extra.
- Chuva fina em 915 MHz atenua de forma desprezível, mas **folhagem molhada
  absorve bastante**. As medições representam, portanto, o caso degradado — o que
  é vantajoso, já que o sistema precisa funcionar durante a chuva.

### Decidido

- **O posicionamento do gateway passa a ser a decisão de engenharia de maior
  impacto do sistema**, acima de potência, antena e spreading factor. Vale para
  a fase 4 e para a proposta comercial.
- Ensaio 03 (varredura de SF) vira **prioritário**, e deve ser feito no P6, que
  já está caracterizado: SF12 acrescenta 8 dB sobre SF9 e, pelo modelo ajustado,
  isso **dobra o alcance** — ao custo de ~6× mais tempo de rádio ligado, o que
  impacta autonomia e ocupação de canal.

### Próximo

1. Ensaio 03 — varredura SF7/SF9/SF12 no P6.
2. Registrar coordenada e altura do `HTC-02` (P-008) para fechar a análise
   absoluta e permitir calibrar o modelo contra o MDE.

---

## 2026-07-30 (6) — Ferramentas de coleta e georreferenciamento

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **`tools/coleta.py`** — captura a serial do PINGER, carimba cada amostra com a
  hora, grava `-amostras.csv` e `-pontos.csv`, e mostra o veredito ao vivo
  aplicando os mesmos critérios do firmware. O resumo é regravado a cada novo
  ponto, então queda no meio do ensaio não leva junto o que já foi medido.
- **`tools/georreferenciar.py`** — casa os pontos medidos com as fotos do
  celular pelo EXIF e gera **GeoJSON, KML e CSV** com RSSI, margem, perda e
  veredito como atributos.
- Cadeia validada ponta a ponta contra hardware real: serial → CSV → EXIF →
  GeoJSON/KML.
- Ensaio 01b registrado (validação das ferramentas, mas com resultado técnico
  próprio).

### Aprendido

- **Perda de dados por não haver registro.** Uma rodada de medições do usuário
  se perdeu: as estatísticas viviam só na RAM da placa e sumiram no reinício.
  Foi o que motivou as ferramentas — a partir daqui, todo ensaio grava em disco.
- **Abrir a porta serial reinicia o ESP32** se DTR/RTS forem acionados na
  abertura, apagando o ponto em andamento. Corrigido configurando as linhas
  **antes** de abrir (`Serial()` sem porta, depois `open()`). Detectado no teste
  porque o `seq` voltava a 1.
- **As antenas estão boas**: assimetria de **0,1 dB** entre os dois sentidos no
  ensaio 01b. Derruba a hipótese de antena ou conector defeituoso.
- **iOS não expõe serial USB a aplicativos de terceiros** — exige o programa MFi
  da Apple, e o CP2102 não é MFi. Registrar pelo iPhone via cabo está descartado;
  o caminho, se um dia for necessário, é BLE do próprio ESP32.
- **Foto de celular carrega coordenada no EXIF** — é o que permite
  georreferenciar sem digitar coordenada nenhuma.

### Decidido

- **MacBook na mochila** como forma padrão de conduzir o ensaio: alimenta a
  placa e registra tudo, resolvendo de uma vez a falta de bateria e a anotação
  manual.
- Coordenada por foto em vez de digitada: menos trabalho em campo e menos erro.

### Próximo

Ensaio 02 com coleta automática — linha de visada, 10 m → 25 m → 50 m → 100 m.

---

## 2026-07-30 (5) — Instrumentação de campo e roteiro de ensaio

**Fase:** 0 · **Duração:** ~1 sessão

### Feito

- **Validador de ponto na tela.** O firmware avalia o ponto contra os critérios
  do roteiro e mostra o veredito pronto — `COLETANDO n/20`, `APROVADO`,
  `LIMITE` ou `REPROVA`, com o fator dominante. Faixa em vídeo invertido na
  página PONTO (moldura dupla quando reprovado) e selo compacto `OK/LIM/REP` na
  página ENLACE, que é a aberta enquanto se caminha. Os limiares ficam
  agrupados em `ui_dev.h`, porque mudá-los muda o que o campo aprova.

- **Marcação de pontos de medição** no firmware: toque longo no PRG (>1 s) zera
  as estatísticas, incrementa o ponto e marca a transição no CSV, com
  confirmação por LED. Toque curto segue trocando de página.
- **Nova página PONTO** com o resumo consolidado — pacotes, perda %, RSSI
  mínimo/médio/máximo e margem. É a tela que o operador fotografa antes de
  mudar de local.
- **Leitura de bateria parametrizada** (`VBAT_FATOR_DIVISOR`,
  `VBAT_CALIBRACAO`, `VBAT_BAIXA_V`) com procedimento de calibração documentado
  e aviso discreto de bateria baixa. Continua rotulada `nc` até P-005.
- **`docs/ROTEIRO_CAMPO.md`** — procedimento completo do ensaio de alcance:
  preparação, alimentação, papéis dos nós, procedimento por ponto, sequência de
  ensaios, interpretação de margem e segurança.
- `HTC-02` regravada com o firmware de campo, após conferência do MAC.
- Display validado pelo usuário: legível em todas as páginas.

### Decidido

- **O operador caminha com o PINGER.** Só ele conta os pacotes que *não* foram
  respondidos — o PONGER enxerga apenas o que chegou. Sem isso não há taxa de
  perda, que é metade do resultado.
- **Margem mínima de 20 dB** para aprovar um ponto de instalação. Chuva intensa
  e folhagem molhada atenuam, e é durante a chuva forte que o sistema precisa
  funcionar: enlace dimensionado no limite em dia de sol falha exatamente no
  evento que existe para monitorar.
- Power bank como alimentação inicial (custo zero), com a ressalva de que muitos
  desligam sozinhos no consumo baixo da placa. LiPo no JST fica como opção B,
  com alerta de conector 1,25 mm e conferência de polaridade por multímetro.
- **O número do ponto é chave de ligação**, não identificador decorativo: a
  placa não tem GPS, então ele é o que amarra a medição de rádio à coordenada
  registrada por fora. Destino do dado: planilha → camada PostGIS → mapa de
  cobertura → decisão de onde ficam os gateways.
- Coordenada de cada ponto passa a ser **obrigatória**, porque é entrada do
  modelo de propagação. Com pontos medidos e um MDE, dá para calibrar o modelo
  contra o terreno real e **predizer cobertura onde não se mediu** — o que
  transforma trabalho de campo, que não escala, em modelo, que escala. É
  argumento forte para a proposta e apoia-se justamente na competência de
  geoprocessamento já existente.

### Aprendido

- O ambiente do ensaio 01 era interno com **paredes de alvenaria** — consistente
  com os 45–60 dB de atenuação extra. Segue como hipótese até a medição de 10 m
  com visada limpa, que é o teste decisivo do ensaio 02.

### Próximo

Ensaio 02 — linha de visada, 10 m → 25 m → 50 m → 100 m.

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
