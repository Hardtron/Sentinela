-- Sentinela — 002: leitura de sensor, saúde da Atalaia e alarmes.
--
-- Fecha as lacunas RC-10 (rastreabilidade), RC-12 (energia agregada) e
-- RC-14 (umidade interna), que o esquema inicial não cobria: ele era
-- exclusivamente de **enlace de rádio**, sem nenhuma tabela de sensor.
--
-- Idempotente: pode rodar de novo sem erro. Ver backend/migra.py.
--
-- Autoria: Matheus Marassi

-- ------------------------------------------------------------- leitura --
-- Espelha o quadro `proto::Sensor` (firmware/lib/proto/proto.h). Os valores
-- chegam em unidades de engenharia, não nos inteiros escalados do ar — a
-- conversão é do ingestor, para que consulta em SQL não precise saber que
-- chuva viaja em 0,1 mm/lsb.

CREATE TABLE IF NOT EXISTS leitura (
    recebido_em   TIMESTAMPTZ NOT NULL,
    medido_em     TIMESTAMPTZ,        -- carimbo do próprio nó (RC-06/RC-13)
    node_id       SMALLINT    NOT NULL,
    seq           INTEGER,
    chuva_1h_mm   REAL,
    pitch_graus   REAL,
    roll_graus    REAL,
    umidade_solo  REAL,               -- %
    bateria_mv    INTEGER,
    flags         SMALLINT    NOT NULL DEFAULT 0,

    -- RC-07: bit apagado significa "não mediu", não "mediu zero". Sem estas
    -- colunas, `chuva_1h_mm = 0` seria ambíguo entre seca e sensor morto.
    chuva_valida  BOOLEAN     NOT NULL DEFAULT FALSE,
    inclin_valida BOOLEAN     NOT NULL DEFAULT FALSE,
    solo_valido   BOOLEAN     NOT NULL DEFAULT FALSE,

    -- NEGOCIO.md §4: o sistema deve ingerir instrumento de terceiro em vez de
    -- exigir substituição. Cliente com Worldsensing instalado vira integração,
    -- não concorrência perdida.
    fonte         TEXT        NOT NULL DEFAULT 'sentinela'
);

SELECT create_hypertable('leitura', 'recebido_em', if_not_exists => TRUE);

CREATE UNIQUE INDEX IF NOT EXISTS leitura_unica
    ON leitura (node_id, seq, recebido_em);
CREATE INDEX IF NOT EXISTS leitura_no_tempo
    ON leitura (node_id, recebido_em DESC);

-- --------------------------------------------------- saúde da Atalaia --
-- RC-12. Cadência diária; é o insumo da manutenção por condição
-- (MANUTENCAO.md §3) — o que distingue painel sujo de painel sombreado.

CREATE TABLE IF NOT EXISTS saude_atalaia (
    recebido_em      TIMESTAMPTZ NOT NULL,
    medido_em        TIMESTAMPTZ,
    node_id          SMALLINT    NOT NULL,
    seq              INTEGER,
    energia_dia_wh   REAL,       -- E_dia
    t_ini            SMALLINT,   -- minutos desde 00:00
    t_fim            SMALLINT,
    corrente_pico_ma INTEGER,
    v_min_mv         INTEGER,
    v_fim_mv         INTEGER,
    dod_pct          SMALLINT,
    temp_interna_c   SMALLINT,
    umidade_interna  SMALLINT,   -- RC-14
    reinicios        SMALLINT,
    watchdogs        SMALLINT,
    heap_livre_kb    INTEGER,
    sensores_validos SMALLINT,
    versao_firmware  SMALLINT
);

SELECT create_hypertable('saude_atalaia', 'recebido_em', if_not_exists => TRUE);

CREATE UNIQUE INDEX IF NOT EXISTS saude_atalaia_unica
    ON saude_atalaia (node_id, seq, recebido_em);

-- ------------------------------------------------------------- alarmes --
-- RC-10: todo alerta guarda o dado bruto que o originou. Sem isso não há como
-- auditar um alerta depois — e num sistema que informa decisão de Defesa Civil
-- "por que disparou?" é pergunta que vai ser feita.

CREATE TABLE IF NOT EXISTS alarme (
    id            BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    aberto_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    fechado_em    TIMESTAMPTZ,
    node_id       SMALLINT    NOT NULL,
    nome          TEXT        NOT NULL,
    grupo         TEXT        NOT NULL,
    severidade    TEXT        NOT NULL
        CHECK (severidade IN ('CRITICO', 'URGENTE', 'ATENCAO', 'INFO')),
    gatilho       TEXT,
    acao          TEXT,
    -- RC-10: o dado que originou o alarme, congelado no momento da abertura.
    evidencia     JSONB       NOT NULL DEFAULT '{}'::jsonb
);

-- Idempotência contra reconexão do gateway: o mesmo alarme não pode abrir
-- duas vezes enquanto não for fechado. É o mesmo cuidado que a tabela
-- `enlace` já tem contra reenvio do buffer da bridge.
CREATE UNIQUE INDEX IF NOT EXISTS alarme_aberto_unico
    ON alarme (node_id, nome) WHERE fechado_em IS NULL;

CREATE INDEX IF NOT EXISTS alarme_por_no ON alarme (node_id, aberto_em DESC);
