# Backend

```
bridge/ChirpStack → MQTT → ingestor → PostgreSQL + TimescaleDB + PostGIS → dashboard
```

Roda no homeserver (Docker 29.6, Compose v5.3). Portas 1883, 5432, 8080 e 1700
verificadas livres em 30/07/2026.

## Componentes

| Componente | Papel |
|---|---|
| Mosquitto | Broker MQTT |
| Ingestor | Decodifica `proto/`, valida, grava, detecta nó silencioso (RC-02) |
| TimescaleDB | Série temporal com agregação contínua dos acumulados |
| PostGIS | Base geoespacial: taludes, áreas de alcance, exposição |
| Dashboard | Visão operacional |
| ChirpStack | Só na Fase 4, com o concentrador |

## Por que TimescaleDB e PostGIS juntos

O Timescale resolve o volume: série de sensor em PostgreSQL puro degrada, e os
acumulados de 24 h/72 h/96 h — que são o principal preditor do sistema — ficam
pré-calculados por agregação contínua em vez de recomputados a cada consulta.

O PostGIS é o que transforma leitura em informação de risco. Telemetria
georreferenciada cruzada com carta de suscetibilidade, cadastro de edificações e
população exposta muda o alerta de *"o talude moveu"* para *"talude X moveu 0,4°
com 180 mm acumulados em 72 h, com N domicílios na área de alcance"*. É esse
cruzamento que sustenta decisão de Defesa Civil — e é onde a experiência prévia
em geoprocessamento pesa mais (ADR-005).

A mesma base é consultável direto no QGIS, sem exportação intermediária.

## Modelo de dados previsto (Fase 3)

- `no` — cadastro dos nós, com geometria e talude associado
- `leitura` — hypertable de telemetria
- `talude` — polígono, classificação de suscetibilidade, área de alcance
- `exposicao` — edificações e população na área de alcance
- `alerta` — alertas emitidos, **com os dados brutos que os originaram** (RC-10)
- `saude_no` — bateria, RSSI, reinícios, heartbeat (RC-03)

## Segurança

Credenciais em `.env`, fora do versionamento. Chaves LoRaWAN nunca entram no
repositório. Ver `.gitignore`.
