# Gateway — bridge LoRa → MQTT no Raspberry Pi 4

## O que é, e o que não é

O Raspberry Pi **não tem rádio LoRa**. Ele não é, sozinho, um gateway LoRaWAN —
isso exige um concentrador SX1302/SX1303 (RAK5146, RAK2245), que escuta 8 canais
e vários spreading factors simultaneamente.

O que roda aqui nas fases 0–3 é uma **bridge**: a placa `HTC-03`, ligada por USB
ao RPi 4, recebe os quadros LoRa P2P e os entrega por serial; um processo em
Python publica em MQTT.

Isso entrega o sistema **ponta a ponta com custo zero** — sensor → rádio →
bridge → MQTT → banco → dashboard, tudo real. Ver ADR-002 para o raciocínio
completo e para o que muda quando o concentrador for adquirido (resposta curta:
só esta pasta e `lib/hal/`).

## Por que não um "single-channel packet forwarder"

Seria a outra saída de custo zero, e foi descartada: escuta um canal em um único
SF, quebra o join procedure, impede ADR e está fora da especificação LoRaWAN.
Ensina vícios que depois precisam ser desaprendidos, e falhas dele seriam
confundidas com bugs nossos.

## Estado atual

- [x] **`bridge.py`** — serial → MQTT, com reconexão automática de ambos os
      lados e **buffer atômico em disco** (`buffer.jsonl`). Mensagem QoS 1 só
      sai da fila após confirmação do broker; arquivo corrompido é preservado
      com sufixo `corrompido-*`, nunca tratado como fila vazia válida.
- [x] **`sentinela-bridge.service`** — unidade systemd, reinicia sozinha em
      falha.
- [x] Publicação de saúde da própria bridge em `sentinela/bridge/<id>/saude`
      (RC-02 vale para ela também — bridge muda não é diferente de nó mudo).
- [x] **Instalação real no Raspberry Pi 4** — feita em 31/07/2026.
      `sentinelapi@192.168.15.73` (SSH por chave, ADR-007), Mosquitto via
      `apt`, repositório sincronizado por `rsync` (não `git clone` — repo
      privado, o RPi é host de runtime), unidade `sentinela-bridge.service`
      habilitada e ativa. A `HTC-03` está ligada e a telemetria passa ponta a
      ponta.
- [x] **Ethernet preferencial com Wi-Fi de contingência** —
      `rede_failover.py` só desliga o Wi-Fi após confirmar três vezes o caminho
      Ethernet até o Home Server. Duas falhas reativam o Wi-Fi; uma Ethernet
      com carrier mas sem caminho só é afastada depois de o Wi-Fi conectar.
- [x] **Fila durante a troca de rede** — sessão persistente do ingestor no
      Mosquitto, QoS 1, persistência em disco e teto de 50 MiB.

### Rede do Farol

O Raspberry usa NetworkManager. Ethernet é a rota preferencial; Wi-Fi é
contingência e permanece com o rádio desligado enquanto o cabo estiver
operacional. A decisão não usa apenas presença física do cabo: exige endereço,
rota padrão e resposta do Home Server pela própria `eth0`, com histerese para
não oscilar por uma perda isolada. O serviço também reaplica prioridade e
métrica de rota: Ethernet `100`, Wi-Fi `600`.

```bash
sudo cp gateway/sentinela-rede.service /etc/systemd/system/
sudo cp gateway/mosquitto-sentinela.conf /etc/mosquitto/conf.d/sentinela.conf
sudo systemctl daemon-reload
sudo systemctl enable --now sentinela-rede.service
sudo systemctl restart mosquitto
```

Diagnóstico:

```bash
systemctl status sentinela-rede sentinela-bridge mosquitto
journalctl -u sentinela-rede -n 50 --no-pager
nmcli device status
```

Os endereços atuais são `.73` no cabo e `.74` no Wi-Fi, mas consumidores não
devem fixá-los: `sentinelapi.local` acompanha a interface ativa. LoRa opera em
916,8 MHz e o Wi-Fi em 5 GHz, sem sobreposição espectral.

### Testar sem nenhum hardware

`bridge.py` aceita `--simular <arquivo.csv>` no lugar da serial — lê o mesmo
formato CSV de um arquivo e segue o resto do fluxo (parsing, MQTT, buffer)
normalmente. É assim que a lógica foi validada antes de a Atalaia `HTC-03` ter
antena disponível para operar como bridge de verdade (HARDWARE.md):

```bash
./tools/venv/bin/python gateway/bridge.py --simular exemplo.csv --veloz
```

Sem broker MQTT no ar, o comando acima cai no buffer em disco automaticamente
— comportamento verificado: mensagens ficam em `buffer.jsonl` e são reenviadas
assim que o broker aparecer, sem duplicar nem perder nada entre execuções.

### Rodar com hardware real

```bash
# broker local, se ainda não houver um rodando
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto

# a bridge propriamente dita
python3 gateway/bridge.py --porta /dev/ttyUSB0 --broker localhost --bridge-id FAR-01
```

Tópicos publicados: `sentinela/no/<node_id>/telemetria` (uma mensagem por
linha CSV recebida) e `sentinela/bridge/<bridge_id>/saude` (a cada 30 s).

O `--no-id` importa: o CSV do firmware de bring-up **não carrega o identificador
de quem enviou o ping** — só o que o receptor mediu. É esse parâmetro que diz de
qual nó a telemetria fala. Sem ele, tudo sai como `node_id=0`. Hoje o par ativo
é `HTC-01` (PINGER), daí `--no-id 1` na unidade systemd.

### Consumir a telemetria de fora do Raspberry Pi

O Mosquitto escuta **apenas em `localhost`**, e assim deve permanecer enquanto
não houver autenticação e TLS: um broker anônimo aberto na rede aceita comando
de qualquer um. Para o painel no MacBook (ou o futuro ingestor no homeserver)
assinar os tópicos, use um túnel SSH sobre a chave já estabelecida:

```bash
ssh -N -o HostKeyAlias=sentinela-rpi \
  -L 1883:127.0.0.1:1883 sentinelapi@sentinelapi.local
```

O cliente passa a encontrar o broker em `localhost:1883` sem que nada seja
exposto na LAN. Quando o ingestor virar serviço permanente, a decisão a tomar
é entre túnel gerenciado (systemd + `autossh`) e habilitar
`password_file` + TLS no broker — a mesma preocupação que o RC-11 levanta para
o protocolo de rádio.

## Decisões pendentes

- ~~Mosquitto no RPi 4 ou no homeserver~~ — **decidido e implementado: no RPi
  4** (31/07/2026). A sessão persistente do ingestor é a fila que cobre queda
  do enlace até o homeserver; o buffer da bridge cobre queda do broker local.
- ~~Acesso remoto ao Raspberry Pi 4~~ — **resolvido em 31/07/2026**, SSH por
  chave, mesmo padrão do homeserver (ver ADR-007).
