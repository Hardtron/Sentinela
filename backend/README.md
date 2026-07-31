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

## Estado atual — no ar desde 31/07/2026

```
HTC-01 →(LoRa)→ HTC-03/bridge →(MQTT)→ túnel SSH → ingestor → TimescaleDB+PostGIS
        RPi 4 (192.168.15.73)              homeserver (192.168.15.66)
```

| Peça | Como roda | Estado |
|---|---|---|
| Banco | `docker compose` no homeserver, preso em `127.0.0.1:5432` | TimescaleDB 2.29 + PostGIS 3.6 |
| Túnel MQTT | `sentinela-tunel-mqtt.service` (unidade de **usuário**) | ativo |
| Ingestor | `sentinela-ingestor.service` (unidade de **usuário**) | ativo |

```bash
cd backend && docker compose up -d          # banco
systemctl --user status sentinela-ingestor  # ingestor
journalctl --user -u sentinela-ingestor -f  # log ao vivo
```

Consulta rápida:

```bash
docker exec -it sentinela-banco psql -U sentinela -d sentinela
```

### Por que unidades de usuário, e não de sistema

O `sudo` do homeserver pede senha interativa, e nenhum dos dois serviços
precisa de privilégio: o ingestor fala com `localhost` e o túnel usa uma chave
SSH do próprio usuário. Para sobreviverem a reboot foi habilitado
`loginctl enable-linger` (não exigiu sudo).

### Por que o ingestor roda no homeserver, e não no RPi

Assim a credencial do PostgreSQL **nunca sai de `localhost`**. O que atravessa
a rede é só o MQTT, dentro de um túnel SSH cuja chave está registrada no RPi
com `restrict,port-forwarding,permitopen="127.0.0.1:1883"` — ela não abre
shell nem encaminha nada além da porta do broker, mesmo se vazar.

### Tabelas que já existem

- `no` — cadastro das 6 placas, com geometria (nula enquanto em bancada)
- `enlace` — hypertable da telemetria de enlace (RSSI/SNR/sequência)
- `enlace_analise` — view com margem e assimetria derivadas do SF
- `enlace_hora` — agregação contínua horária
- `saude_bridge` — hypertable de saúde da bridge (RC-02)
- `ponto_ensaio` — os 7 pontos do ensaio 02 em PostGIS

`leitura` (sensor) **ainda não existe**: entra na Fase 1 com `lib/proto/`.
Chamar a tabela atual de `leitura` seria mentir sobre o que ela contém.

### Idempotência

A bridge reenvia o buffer em disco quando o broker volta. O índice único
`(bridge_id, node_id, seq, recebido_em)` com `ON CONFLICT DO NOTHING` impede
que isso duplique amostra e falseie a taxa de perda.

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
