# Registro de erros e armadilhas

Objetivo: **não repetir investigação já feita.** Erro resolvido aqui não
volta a custar tempo.

Registrar também as armadilhas conhecidas *antes* de tropeçar nelas — a seção
final existe para isso.

Formato:

```
### E-NNN — Título

**Contexto:** onde apareceu
**Sintoma:** mensagem ou comportamento exato
**Causa:** o que estava realmente acontecendo
**Solução:** o que resolveu
**Status:** resolvido | contornado | aberto
```

---

## Erros encontrados

### E-001 — Falha ao ler a flash em 460800 baud

**Contexto:** dump da flash da `HTC-01` com esptool, 30/07/2026.
**Sintoma:** `A fatal error occurred: Invalid head of packet (0xFF): Possible serial noise or corruption.` logo após `Changing baud rate to 460800`.
**Causa:** o CP2102 não sustenta 460800 de forma confiável neste enlace USB.
**Solução:** usar `--baud 230400`. Os 4 MB saíram íntegros em ~196 s (171 kbit/s).
**Status:** resolvido.

> Regra prática: **230400 é o teto confiável** para essas placas. Não insistir
> em 460800 nem 921600.

---

### E-002 — `git@github.com: Permission denied (publickey)`

**Contexto:** preparação para publicar o repositório, 30/07/2026.
**Sintoma:** o teste `ssh -T git@github.com` retorna permissão negada.
**Causa:** existe chave `~/.ssh/id_ed25519.pub` na máquina, mas ela **não está
autorizada na conta do GitHub**. Não há `gh` CLI nem `GITHUB_TOKEN`.
**Solução:** contornado por outro caminho. Em vez de autorizar a chave SSH,
instalou-se o **GitHub CLI 2.96.0** em `~/.local/bin` e autenticou-se por
**device flow** (`gh auth login --git-protocol https --web`). O token fica no
keyring do macOS e o git usa HTTPS pelo credential helper do `gh`.
**Status:** resolvido — a chave SSH continua não autorizada, e não precisa ser.

> Se um dia o protocolo SSH for necessário (submódulos, CI), aí sim autorizar a
> chave. Para o fluxo atual, HTTPS via `gh` basta.

---

### E-003 — Placa "muda" no serial após o boot

**Contexto:** primeira inspeção da `HTC-01`, 30/07/2026.
**Sintoma:** o serial mostra o log do bootloader ROM e para em
`entry 0x400802e4`. Nada depois, em nenhum baud rate testado.
**Causa:** **não é defeito.** O firmware de fábrica da Heltec (FactoryTest) não
imprime no serial durante a operação normal.
**Solução:** nenhuma necessária. Identificação foi feita por dump da flash e
extração de strings (`HelTec_AutoMation`, `LoRa Initial success!`).
**Status:** resolvido — comportamento esperado.

---

### E-005 — Boot loop após a primeira gravação: flash de 4 MB vs 8 MB

**Contexto:** primeira gravação do firmware na `HTC-01`, 30/07/2026.
**Sintoma:** gravação bem-sucedida com hash verificado, mas a placa entra em
reinício contínuo:

```
E (173) spi_flash: Detected size(4096k) smaller than the size in the
        binary image header(8192k). Probe failed.
assert failed: do_core_init startup.c:328 (flash_ret == ESP_OK)
Rebooting...
```

**Causa:** a definição de board `heltec_wifi_lora_32_V2` do PlatformIO assume
flash de **8 MB**, e o esptool grava esse valor no header da imagem. **Estas
placas têm 4 MB** (Winbond `ef:4016`, confirmado no dump de 30/07). O bootloader
detecta a divergência e aborta.

**Solução:** fixar o tamanho real no `platformio.ini`:

```ini
board_upload.flash_size = 4MB
board_upload.maximum_size = 4194304
board_build.partitions = default.csv
```

Depois disso o arranque é normal e o rádio inicializa.
**Status:** resolvido.

> A Heltec V2 foi vendida em variantes de 4 MB e 8 MB. **Conferir o chip de
> flash antes de gravar uma placa nova** — as cinco do inventário vieram do
> mesmo lote, mas isso não é garantia. `esptool.py flash_id` responde em
> segundos.

---

### E-004 — Aviso de OpenSSL no PlatformIO

**Contexto:** qualquer comando `pio`.
**Sintoma:** `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+,
currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'`.
**Causa:** o Python 3.9 do sistema no macOS é compilado com LibreSSL.
**Solução:** nenhuma — é **cosmético**, o PlatformIO funciona. Só se tornaria
relevante se houvesse falha de download; nesse caso, instalar Python via
Homebrew e recriar o venv.
**Status:** contornado — ignorar.

---

### E-006 — Abrir a porta serial às vezes reseta o ESP32, mesmo com DTR/RTS pré-configurados

**Contexto:** `gateway/bridge.py` conectando na `HTC-03` (`bench_03`), 31/07/2026.
**Sintoma:** ao abrir a porta serial, a placa reinicia e emite o banner de
boot completo — mesmo usando o padrão "configurar DTR/RTS antes de abrir a
porta", que numa sessão anterior havia se mostrado livre de reset com outras
placas/firmware.
**Causa:** não determinada. O circuito de auto-reset do CP2102 (EN pino
comandado por transições de DTR/RTS) explica o mecanismo, mas por que o mesmo
padrão de mitigação funcionou antes e não desta vez — se é a placa, o
firmware, a porta USB usada, ou o próprio driver do macOS — não ficou claro
com os testes feitos.
**Solução:** nenhuma aplicada. Reportado como comportamento observado, não
como bug corrigido — não force uma causa sem evidência.
**Status:** aberto.

> Não depender de "abrir a porta não reseta a placa" como premissa em nenhum
> código novo (bridge, scripts de teste). Se a bridge precisar preservar
> estado através de reconexões, assumir que um reset pode acontecer a
> qualquer abertura de porta.

---

### E-007 — `node_dev` (RF-ativo) gravado na `HTC-02` sem antena, por assumir identidade da placa sem checar

**Contexto:** sessão de 31/07/2026, implementando a página BATERIA no OLED.
**Sintoma:** a placa conectada na USB do MacBook foi tratada como `HTC-01`
por continuidade de contexto ("já estava conectada" numa etapa anterior da
mesma sessão), sem rodar `esptool.py flash_id` para confirmar o MAC antes de
gravar. Era na verdade a `HTC-02` — **sem antena**, remanejada para a
`HTC-03` mais cedo na mesma sessão (LOG.md, entrada 10). `node_dev`
(`ROLE_PINGER`, RF-ativo) ficou rodando nela por aproximadamente 20 minutos,
transmitindo a cada ~3,7 s a 17 dBm sem carga de antena — violação direta de
A-003/A-010.
**Como foi descoberto:** o usuário notou a inconsistência e perguntou
diretamente ("quem está conectado na USB do Mac é a HTC-02"). Não foi
autodetecção — o sintoma indireto (pings sem pong, 0/61 pacotes) já estava
visível antes disso, mas eu o estava investigando pelo lado errado (suspeitei
da `HTC-03`/bridge primeiro, não da identidade da própria placa local).
**Causa:** quebra do protocolo já estabelecido neste mesmo projeto — "conferir
MAC antes de gravar" foi seguido consistentemente em gravações anteriores da
sessão (HTC-01, HTC-02, HTC-03), mas pulado nesta, por assumir que nada havia
mudado desde a verificação anterior. Card also `tools/varredura_sf.py`
(escrito na mesma sessão) tem a mesma lacuna: `grava_local()` grava direto na
porta configurada, sem checar MAC antes.
**Solução:**
1. `HTC-02` regravada imediatamente para `bench_02` (seguro, sem TX) assim
   que identificada — risco cessado, mas exposição real já ocorreu.
2. `tools/varredura_sf.py` deveria ganhar uma checagem de MAC antes de
   `grava_local()` (pendente — anotar como dívida técnica).
**Status:** aberto quanto à integridade física da `HTC-02` — **não há como
confirmar por software se o PA sofreu dano** sem um teste de potência de
saída depois que ela voltar a ter antena. Anotar para inspecionar/medir antes
de devolvê-la a um papel RF-ativo.

> **Regra reforçada, não nova:** "confirmar MAC via `esptool.py flash_id`
> antes de qualquer gravação" vale **mesmo quando a placa "já estava
> conectada"** momentos atrás na mesma sessão — inclusive, e principalmente,
> depois de qualquer intervalo em que outra atividade (trocar foto, discutir
> hardware, etc.) tornou plausível que alguém trocou o cabo. Continuidade de
> contexto não é confirmação.

---

### E-008 — Placa "morta" na bateria; só liga pela USB com a bateria removida

**Contexto:** 31/07/2026, logo após instalar as NCR18650B na `HTC-01` e
`HTC-02` e atualizar o firmware.
**Sintoma:** com a bateria conectada, a placa não liga — nem na bateria
sozinha, nem com USB + bateria. Removendo a bateria, liga normal pela USB.
Funcionava bem antes das baterias entrarem.
**Investigação:**
- **Polaridade invertida foi a primeira hipótese e está DESCARTADA** —
  confirmado pelo usuário, e a `HTC-02` passou a ligar normalmente na
  bateria depois de carregar, com a mesma fiação.
- **Firmware novo (página BATERIA / `temperatureRead()`) está DESCARTADO
  como causa**, com evidência de hardware e não por análise: a `HTC-02`
  roda exatamente o mesmo `readTempChip()` (mesmo `ui_dev.cpp`, chamada no
  laço `ROLE_BENCH`, `main.cpp:408`) e liga na bateria sem problema.
  Revisão do código confirma ainda: nenhuma chamada de `deep_sleep`,
  `light_sleep`, `WiFi`, mudança de clock, e `vextOff()` **nunca é
  chamada** em lugar nenhum — o firmware não desliga nada.
**Causa mais provável [E], não confirmada:** célula ainda muito descarregada
no momento do teste. Isso explica os três sintomas de uma vez: sem carga
suficiente não liga sozinha; o carregador puxando corrente para uma célula
vazia disputa o orçamento da porta USB (e o chaveamento automático
USB/bateria da V2 pode preferir a bateria descarregada); removida a bateria,
toda a corrente da USB sobra para a placa. A `HTC-02` ter voltado a
funcionar **depois de carregar** sustenta essa leitura.
**Hipótese secundária [E]:** *brownout* por pico de transmissão. Vale só
para `node_dev`/`node_range` (RF-ativos, 17 dBm a cada 3 s), não para
`bench_*`. Distingue-se da anterior pela página BATERIA: se for brownout,
ela mostra `reset: brownout`.
**Solução:** carregar a célula até a corrente cair (fim do CC/CV) antes de
concluir qualquer coisa. A 0,200 A, célula de 3400 mAh vazia leva ~17 h.
**Status:** aberto — aguarda carga completa para confirmar ou refutar.

> Antes de diagnosticar "placa com defeito" numa alimentação por bateria
> nova, **carregar até o fim primeiro**. Célula grande com corrente de carga
> modesta demora horas, e quase todo sintoma de "morta" desaparece com carga
> — inclusive os que parecem falha de hardware.

---

### E-009 — Painel "no ar" servindo código velho, e LaunchAgent barrado pelo TCC

**Contexto:** 31/07/2026, ao tornar o painel permanentemente acessível.
**Sintoma:** `http://localhost:8792` não abria (porta de teste, encerrada), e
`http://localhost:8765` abria **com a aba Monitoramento quebrada** —
`/api/telemetria` devolvia `404 rota desconhecida`.
**Causa (dupla, e a segunda só apareceu ao corrigir a primeira):**
1. Havia um processo do painel no ar **desde as 06:56**, anterior à criação de
   `telemetria.py`. Python carrega os módulos no arranque: o servidor seguia
   servindo o código de horas antes, sem a rota nova. Rodava ainda com o
   Python do sistema, sem `paho-mqtt` — então nem com a rota teria dado.
2. Ao tentar resolver com um LaunchAgent no Mac, ele falhou com
   `PermissionError: Operation not permitted` em `tools/venv/pyvenv.cfg`. É o
   **TCC do macOS**: serviços em segundo plano não têm acesso a
   `~/Documents`. Confirmado que não era peculiaridade do venv — um agente de
   teste rodando só `head README.md` no repositório também foi bloqueado.
**Solução:** painel movido para o **homeserver** como unidade de usuário
(`tools/painel/sentinela-painel.service`), com o Mac apenas encaminhando a
porta 8765 por SSH (`tools/launchd/com.sentinela.painel-tunel.plist`). Resolve
os dois problemas de uma vez e ainda cobre o terceiro, que ninguém tinha
levantado: **o Mac dorme**, então mesmo sem TCC o painel não estaria "sempre"
disponível ali. Recuperação automática verificada matando os processos à
força nas duas pontas.
**Status:** resolvido.

> Processo de servidor no ar **não é garantia de que o código no ar é o
> atual**. Depois de mexer em qualquer módulo do painel, reiniciar o serviço —
> ou, melhor, deixar que um supervisor (systemd/launchd) o gerencie, em vez de
> processos soltos que ninguém lembra de ter iniciado.

---

## Armadilhas conhecidas (ainda não encontradas)

Registradas preventivamente. Se alguma se manifestar, promover para a seção
acima com o número de erro.

### A-001 — GPIO 12 impede o boot

Strapping pin (MTDI). Nível alto no boot seleciona 1,8 V para a flash e a placa
não sobe. **Não usar para sensores**, ou garantir pull-down externo.

### A-002 — GPIO 34–39 são somente entrada

Não têm pull-up interno e não podem ser saída. Vale para os pinos livres 36, 38
e 39 — e lembrar que 34 e 35 já são DIO2/DIO1 do rádio.

### A-003 — Transmitir sem antena danifica o PA

Nunca energizar o rádio em transmissão sem antena conectada.

### A-004 — Vext é ativo em nível BAIXO

`digitalWrite(21, LOW)` **liga** a alimentação dos periféricos. Invertido em
relação à intuição.

### A-005 — Deep sleep da Heltec V2 consome ~1 mA

Regulador e CP2102 permanecem alimentados. Não tirar conclusão de autonomia de
campo a partir de medição feita nesta placa (ADR-004).

### A-006 — Faixa 907,5–915 MHz não é permitida no Brasil

Anatel libera 902–907,5 e 915–928 MHz para radiação restrita. Conferir a
frequência antes de qualquer transmissão (ADR-003).

### A-007 — Deriva térmica do inclinômetro gera falso positivo

MEMS deriva com temperatura, e talude exposto ao sol varia dezenas de graus por
dia. Sem compensação térmica, o ciclo diário vira "movimento". É a principal
fonte de falso positivo esperada (RC-09).

### A-009 — Dois clones do projeto podem divergir

O projeto existe no MacBook (firmware, porque a placa está na USB dele) e no
homeserver em `/DATA/Projects/Sentinela` (backend, documentação e acesso remoto
pelo aplicativo). **Os dois só se comunicam pelo GitHub.**

`git pull` antes de começar, `git push` ao terminar — dos dois lados. Editar a
mesma documentação nos dois sem sincronizar gera conflito desnecessário.

Corolário: **nunca** colocar o projeto em `/DATA/Files` no homeserver — o
Syncthing corrompe o `.git`. `/DATA/Projects` é o lugar certo.

### A-008 — Sensor travado no I2C do OLED derruba o diagnóstico

Por isso sensores externos vão em `Wire1` (sugerido GPIO 22/23), separados do
barramento do display.

### A-010 — Mais placas que antenas: nunca gravar papel RF-ativo numa placa sem antena

Com 6 Atalaias e apenas 2 antenas no inventário (HARDWARE.md), é fácil gravar
sem pensar o firmware errado numa placa que não tem antena — e `node_dev` ou
`node_range` chamam `radio.transmit()` a cada poucos segundos, o que degrada o
PA sem carga (A-003).

**Solução adotada:** papel `ROLE_BENCH` (`firmware/platformio.ini`, ambientes
`bench_03` a `bench_06`). Inicializa o rádio e escuta passivamente — nunca
transmite. Compilador confirma em tempo de build que não há caminho de TX
(`sendPacket()` nem é compilado nesse papel). Serve também para validar
hardware das placas sem sensor: escaneia o barramento I2C externo, lê o ADC de
bateria, testa o OLED — tudo isso não precisa de antena nem de peça que ainda
não chegou.

**Regra antes de gravar qualquer placa:** confirmar fisicamente se há antena
parafusada **e** confirmar o MAC via `esptool.py flash_id` — as duas, sempre,
mesmo quando parece óbvio qual placa está na porta. Isso não é teórico: foi
o que aconteceu no E-007, gravando `node_dev` na `HTC-02` sem antena por
assumir identidade sem checar.
