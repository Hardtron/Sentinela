-- Sentinela — 003: camada geoespacial de risco e janelas de chuva acumulada.
--
-- É aqui que telemetria vira informação de risco (ADR-005): sem o cruzamento
-- com suscetibilidade e exposição, "o talude moveu" não vira "talude X moveu
-- com N domicílios na área de alcance".
--
-- Autoria: Matheus Marassi

-- --------------------------------------------------- suscetibilidade --
-- Cartas de suscetibilidade a movimento de massa. **Camada 2 da tripla
-- responsabilidade** (RESPONSABILIDADE_TECNICA.md): a classificação
-- geotécnica não é produzida pelo projeto — entra como referência a fonte
-- institucional (CPRM/SGB, IPT, Defesa Civil) e por isso `fonte` e
-- `referencia` não são opcionais.

CREATE TABLE IF NOT EXISTS suscetibilidade (
    id         BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    municipio  TEXT NOT NULL,
    classe     TEXT NOT NULL
        CHECK (classe IN ('MUITO_ALTA', 'ALTA', 'MEDIA', 'BAIXA')),
    fonte      TEXT NOT NULL,        -- órgão emissor — [G] obrigatório
    referencia TEXT,                 -- documento/carta/ano
    carregado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    geom       GEOGRAPHY(POLYGON, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS suscetibilidade_geom ON suscetibilidade USING GIST (geom);

COMMENT ON COLUMN suscetibilidade.fonte IS
    'Órgão emissor. Afirmação geotécnica nunca é [E] — ver REFERENCIAS.md §1.';

-- ----------------------------------------------------------- exposição --
-- População e edificações na área de alcance. É o que transforma alerta em
-- informação acionável para a Defesa Civil (RC-00: apoio à decisão).

CREATE TABLE IF NOT EXISTS exposicao (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    municipio   TEXT NOT NULL,
    setor       TEXT,                -- setor censitário, quando aplicável
    domicilios  INTEGER,
    populacao   INTEGER,
    fonte       TEXT NOT NULL,       -- IBGE, cadastro municipal — [G]
    referencia  TEXT,
    geom        GEOGRAPHY(POLYGON, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS exposicao_geom ON exposicao USING GIST (geom);

-- --------------------------------------------- chuva acumulada (1/24/72 h) --
-- O principal preditor do sistema (SENSORES.md; curva de Tatizana et al. 1987).
--
-- Feito como view sobre janela deslizante, e **não** como agregação contínua:
-- agregação contínua em balde fixo responde "quanto choveu na hora cheia", que
-- não é a pergunta. O limiar intensidade-duração precisa de janela móvel — o
-- deslizamento ocorre quando o acumulado das últimas 72 h passa do limite, não
-- quando o relógio marca hora cheia.

CREATE OR REPLACE VIEW chuva_acumulada AS
SELECT
    l.node_id,
    max(l.recebido_em) AS ate,
    sum(l.chuva_1h_mm) FILTER (
        WHERE l.chuva_valida AND l.recebido_em > now() - interval '1 hour'
    ) AS mm_1h,
    sum(l.chuva_1h_mm) FILTER (
        WHERE l.chuva_valida AND l.recebido_em > now() - interval '24 hours'
    ) AS mm_24h,
    sum(l.chuva_1h_mm) FILTER (
        WHERE l.chuva_valida AND l.recebido_em > now() - interval '72 hours'
    ) AS mm_72h
FROM leitura l
WHERE l.recebido_em > now() - interval '72 hours'
GROUP BY l.node_id;

-- Resumo horário da leitura, este sim em balde fixo — serve para gráfico
-- histórico e para reduzir volume em consulta longa.
CREATE MATERIALIZED VIEW IF NOT EXISTS leitura_hora
WITH (timescaledb.continuous) AS
SELECT time_bucket('1 hour', recebido_em) AS hora,
       node_id,
       count(*)                      AS amostras,
       sum(chuva_1h_mm)              AS chuva_mm,
       avg(pitch_graus)              AS pitch_med,
       avg(roll_graus)               AS roll_med,
       avg(umidade_solo)             AS solo_med,
       min(bateria_mv)               AS bateria_min_mv
FROM leitura
GROUP BY hora, node_id
WITH NO DATA;

SELECT add_continuous_aggregate_policy('leitura_hora',
    start_offset => INTERVAL '3 days',
    end_offset   => INTERVAL '10 minutes',
    schedule_interval => INTERVAL '10 minutes',
    if_not_exists => TRUE);

-- ------------------------------------------- exposição por Atalaia (GIS) --
-- Responde, para um nó, o que existe ao redor dentro de um raio dado. É a
-- consulta que o alerta usa para dizer "N domicílios na área de alcance".
--
-- **Não é laudo.** O raio é geométrico, não é área de alcance de massa
-- calculada por engenheiro geotécnico (Camada 2). Serve para priorizar
-- vistoria e dimensionar exposição, não para delimitar risco.

CREATE OR REPLACE FUNCTION exposicao_ao_redor(p_node_id SMALLINT,
                                              p_raio_m INTEGER DEFAULT 300)
RETURNS TABLE (domicilios BIGINT, populacao BIGINT, classes TEXT[]) AS $$
    SELECT
        coalesce(sum(e.domicilios), 0)::BIGINT,
        coalesce(sum(e.populacao), 0)::BIGINT,
        coalesce(array_agg(DISTINCT s.classe) FILTER (WHERE s.classe IS NOT NULL),
                 ARRAY[]::TEXT[])
    FROM no n
    LEFT JOIN exposicao e
           ON n.posicao IS NOT NULL
          AND ST_DWithin(e.geom, n.posicao, p_raio_m)
    LEFT JOIN suscetibilidade s
           ON n.posicao IS NOT NULL
          AND ST_DWithin(s.geom, n.posicao, p_raio_m)
    WHERE n.node_id = p_node_id;
$$ LANGUAGE SQL STABLE;
