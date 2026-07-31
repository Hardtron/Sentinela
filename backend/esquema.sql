-- Sentinela — esquema do banco (Fase 2/3).
--
-- Roda uma vez, na criação do container (docker-entrypoint-initdb.d).
--
-- O que existe hoje é telemetria de **enlace** (RSSI/SNR/sequência do
-- ping-pong de bring-up). Leitura de sensor ainda não existe: entra na Fase 1
-- com `lib/proto/`, em tabela própria. Nomear a tabela atual de `leitura`
-- seria mentir sobre o que ela contém.
--
-- Autoria: Matheus Marassi

CREATE EXTENSION IF NOT EXISTS timescaledb CASCADE;
CREATE EXTENSION IF NOT EXISTS postgis;

-- ------------------------------------------------------------- cadastro --

CREATE TABLE IF NOT EXISTS no (
    node_id     SMALLINT PRIMARY KEY,   -- NODE_ID compilado no firmware
    placa       TEXT NOT NULL,          -- HTC-01 … HTC-06
    mac         TEXT,
    papel       TEXT,
    antena      BOOLEAN NOT NULL DEFAULT FALSE,
    posicao     GEOGRAPHY(POINT, 4326), -- nulo enquanto a placa está em bancada
    altitude_m  REAL,
    observacao  TEXT
);

COMMENT ON COLUMN no.antena IS
    'Sem antena a placa não pode rodar papel RF-ativo — degrada o PA (A-003).';

-- --------------------------------------------------------------- enlace --
-- Uma linha por quadro recebido pelo gateway. `perdidos` é o buraco na
-- numeração de sequência desde a amostra anterior: como a bridge só publica
-- quando recebe, o que falta no `seq` é exatamente o que se perdeu no ar.

CREATE TABLE IF NOT EXISTS enlace (
    recebido_em     TIMESTAMPTZ NOT NULL,
    node_id         SMALLINT    NOT NULL,
    bridge_id       TEXT        NOT NULL,
    seq             BIGINT,
    sf              SMALLINT,           -- spreading factor vigente na captura
    rssi_dbm        REAL,               -- subida: como o gateway ouviu o nó
    snr_db          REAL,
    rssi_remoto_dbm REAL,               -- descida: como o nó ouviu o gateway
    snr_remoto_db   REAL,
    enviados        BIGINT,
    recebidos       BIGINT,
    perdidos        INTEGER     NOT NULL DEFAULT 0
);

SELECT create_hypertable('enlace', 'recebido_em', if_not_exists => TRUE);

-- A bridge reenvia o buffer em disco quando o broker volta. Sem isto, uma
-- reconexão duplicaria amostras e falsearia a taxa de perda.
CREATE UNIQUE INDEX IF NOT EXISTS enlace_unico
    ON enlace (bridge_id, node_id, seq, recebido_em);

CREATE INDEX IF NOT EXISTS enlace_no_tempo ON enlace (node_id, recebido_em DESC);

-- --------------------------------------------------- saúde da bridge ----
-- RC-02 vale para a bridge tanto quanto para o nó: bridge muda não é
-- diferente de nó mudo.

CREATE TABLE IF NOT EXISTS saude_bridge (
    gerado_em     TIMESTAMPTZ NOT NULL,
    bridge_id     TEXT        NOT NULL,
    publicados    BIGINT,
    fila_pendente INTEGER,
    ativo_desde   TIMESTAMPTZ
);

SELECT create_hypertable('saude_bridge', 'gerado_em', if_not_exists => TRUE);

CREATE UNIQUE INDEX IF NOT EXISTS saude_bridge_unico
    ON saude_bridge (bridge_id, gerado_em);

-- ------------------------------------------------ pontos de ensaio ------
-- Campanha de campo (ensaio 02). Fica no banco, e não só no GeoJSON, para
-- poder ser cruzada com a telemetria e com as bases geoespaciais no QGIS.

CREATE TABLE IF NOT EXISTS ponto_ensaio (
    ensaio        TEXT     NOT NULL,
    ponto         SMALLINT NOT NULL,
    posicao       GEOGRAPHY(POINT, 4326) NOT NULL,
    altitude_m    REAL,
    distancia_m   REAL,
    rssi_med      REAL,
    rssi_min      REAL,
    rssi_max      REAL,
    margem_db     REAL,
    assimetria_db REAL,
    perda_pct     REAL,
    veredito      TEXT,
    motivo        TEXT,
    ambiente      TEXT,
    quando        TIMESTAMPTZ,
    PRIMARY KEY (ensaio, ponto)
);

-- ------------------------------------------------------- sensibilidade --
-- Espelha uiSensitivityDbm() do firmware. Fica como função porque a margem
-- de enlace depende do SF, e o SF vai variar na varredura SF7–SF12.

CREATE OR REPLACE FUNCTION sensibilidade_dbm(sf SMALLINT)
RETURNS REAL AS $$
    SELECT CASE sf
        WHEN 7  THEN -123.0
        WHEN 8  THEN -126.0
        WHEN 9  THEN -129.0
        WHEN 10 THEN -132.0
        WHEN 11 THEN -133.0
        WHEN 12 THEN -136.0
        ELSE -129.0
    END::REAL;
$$ LANGUAGE SQL IMMUTABLE;

-- Margem e assimetria derivadas, para não repetir a conta em cada consulta.
CREATE OR REPLACE VIEW enlace_analise AS
SELECT e.*,
       e.rssi_dbm        - sensibilidade_dbm(e.sf) AS margem_sobe_db,
       e.rssi_remoto_dbm - sensibilidade_dbm(e.sf) AS margem_desce_db,
       e.rssi_dbm        - e.rssi_remoto_dbm       AS assimetria_db
FROM enlace e;

-- --------------------------------------------------- agregação contínua --
-- Pré-calcula o resumo horário. É o mecanismo que a Fase 3 vai usar para os
-- acumulados de chuva de 24/72/96 h; aqui ele já entra exercitado.

CREATE MATERIALIZED VIEW IF NOT EXISTS enlace_hora
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', recebido_em) AS hora,
       node_id,
       sf,
       count(*)              AS amostras,
       sum(perdidos)         AS perdidos,
       avg(rssi_dbm)         AS rssi_sobe_med,
       min(rssi_dbm)         AS rssi_sobe_min,
       avg(rssi_remoto_dbm)  AS rssi_desce_med,
       avg(snr_db)           AS snr_sobe_med
FROM enlace
GROUP BY hora, node_id, sf
WITH NO DATA;

SELECT add_continuous_aggregate_policy('enlace_hora',
    start_offset => INTERVAL '3 hours',
    end_offset   => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE);
