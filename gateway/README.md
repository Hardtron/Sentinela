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

## Conteúdo previsto (Fase 2)

- `bridge.py` — serial → MQTT, com reconexão e buffer em disco
- Unidade systemd para iniciar no boot e reiniciar em falha
- Publicação de saúde da própria bridge (RC-02 vale para ela também)

## Decisões pendentes

- Mosquitto no RPi 4 ou no homeserver. Inclinação: **no RPi 4**, para que a
  bridge continue enfileirando se o enlace até o homeserver cair.
