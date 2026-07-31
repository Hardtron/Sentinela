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
      lados e **buffer em disco** (`buffer.jsonl`) que sobrevive a reinício do
      processo, testado sem broker no ar.
- [x] **`sentinela-bridge.service`** — unidade systemd, reinicia sozinha em
      falha.
- [x] Publicação de saúde da própria bridge em `sentinela/bridge/<id>/saude`
      (RC-02 vale para ela também — bridge muda não é diferente de nó mudo).
- [x] **Instalação real no Raspberry Pi 4** — feita em 31/07/2026.
      `sentinelapi@192.168.15.73` (SSH por chave, ADR-007), Mosquitto via
      `apt`, repositório sincronizado por `rsync` (não `git clone` — repo
      privado, o RPi é host de runtime), unidade `sentinela-bridge.service`
      habilitada e ativa. Falta apenas ligar a `HTC-03` na USB do RPi para o
      primeiro dado real passar ponta a ponta.

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

## Decisões pendentes

- ~~Mosquitto no RPi 4 ou no homeserver~~ — **decidido e implementado: no RPi
  4** (31/07/2026), para que a bridge continue enfileirando se o enlace até o
  homeserver cair.
- ~~Acesso remoto ao Raspberry Pi 4~~ — **resolvido em 31/07/2026**, SSH por
  chave, mesmo padrão do homeserver (ver ADR-007).
