-- Sentinela — 006: chuva de rede oficial (ADR-009) e limiares por município.
--
-- A chuva deixa de ser medida pelo nó e passa a vir de rede oficial [G]. O nó
-- mede o que a rede não tem por talude: inclinação e umidade de solo.
--
-- Autoria: Luiz Matheus Marassi de Paula

-- ------------------------------------------------- estações oficiais --
-- Pluviômetros do CEMADEN/INMET. Posição em PostGIS porque a associação
-- Atalaia↔estação é geométrica.

CREATE TABLE IF NOT EXISTS estacao_externa (
    codigo     TEXT PRIMARY KEY,          -- código oficial do órgão
    nome       TEXT,
    municipio  TEXT,
    uf         CHAR(2),
    rede       TEXT NOT NULL,             -- CEMADEN, INMET, ...
    altitude_m REAL,
    ativa      BOOLEAN NOT NULL DEFAULT TRUE,
    geom       GEOGRAPHY(POINT, 4326) NOT NULL
);

CREATE INDEX IF NOT EXISTS estacao_externa_geom ON estacao_externa USING GIST (geom);

COMMENT ON TABLE estacao_externa IS
    'Rede oficial [G]. O Cemaden instala pluviometros automaticos junto a '
    'areas de risco e transmite acumulado a cada 10 min — ver SENSORES.md.';

-- ------------------------------------------------------ chuva oficial --
-- Uma linha por leitura de estação. O CEMADEN publica **acumulado do
-- intervalo** (mm nos últimos 10 min), não taxa — guardar como veio evita
-- conversão silenciosa.

CREATE TABLE IF NOT EXISTS chuva_oficial (
    medido_em     TIMESTAMPTZ NOT NULL,
    codigo        TEXT        NOT NULL REFERENCES estacao_externa(codigo),
    chuva_mm      REAL        NOT NULL,   -- acumulado no intervalo
    intervalo_min SMALLINT    NOT NULL DEFAULT 10,
    importado_em  TIMESTAMPTZ NOT NULL DEFAULT now()
);

SELECT create_hypertable('chuva_oficial', 'medido_em', if_not_exists => TRUE);

-- Reimportar o mesmo arquivo não pode duplicar acumulado — duplicata aqui
-- inflaria a chuva acumulada, que é justamente o preditor.
CREATE UNIQUE INDEX IF NOT EXISTS chuva_oficial_unica
    ON chuva_oficial (codigo, medido_em);

-- ------------------------------------- associação Atalaia ↔ estação --
-- Estação mais próxima de cada Atalaia, com a distância explícita.
--
-- **A distância não é detalhe, é a principal limitação do método.** A chuva na
-- Serra do Mar é orográfica e convectiva: célula de 1–5 km de diâmetro. Uma
-- estação a 8 km pode registrar 20 mm enquanto o talude recebe 80 mm. Por isso
-- a distância viaja junto com o dado, e a interface tem de mostrá-la — usar
-- chuva de estação distante como se fosse local é o erro que este campo
-- existe para impedir.

CREATE OR REPLACE VIEW atalaia_estacao AS
SELECT DISTINCT ON (n.node_id)
       n.node_id,
       n.placa,
       e.codigo,
       e.nome        AS estacao,
       e.rede,
       round(ST_Distance(n.posicao, e.geom)::numeric, 0) AS distancia_m
FROM no n
JOIN estacao_externa e ON e.ativa AND n.posicao IS NOT NULL
ORDER BY n.node_id, ST_Distance(n.posicao, e.geom);

-- --------------------------------------------- acumulados oficiais --
-- Janelas de 24 h, 72 h e **84 h**.
--
-- 84 h não é arbitrário: é a janela da envoltória de Tatizana et al. (1987)
-- para a Serra do Mar **[L]**, referência fundacional brasileira do tema.
-- 24 h e 72 h acompanham porque são as janelas com que o CEMADEN opera
-- limiares por município **[G]**.

CREATE OR REPLACE VIEW chuva_oficial_acumulada AS
SELECT c.codigo,
       max(c.medido_em) AS ate,
       sum(c.chuva_mm) FILTER (WHERE c.medido_em > now() - interval '1 hour')  AS mm_1h,
       sum(c.chuva_mm) FILTER (WHERE c.medido_em > now() - interval '24 hours') AS mm_24h,
       sum(c.chuva_mm) FILTER (WHERE c.medido_em > now() - interval '72 hours') AS mm_72h,
       sum(c.chuva_mm) FILTER (WHERE c.medido_em > now() - interval '84 hours') AS mm_84h
FROM chuva_oficial c
WHERE c.medido_em > now() - interval '84 hours'
GROUP BY c.codigo;

-- ------------------------------------------ limiares por município --
-- A envoltória de escorregamento tem a forma  I = a · Ac^(−b)  , com I a
-- intensidade horária (mm/h) e Ac o acumulado da janela (mm).
--
-- **Os coeficientes ficam NULL de propósito.** A literatura é explícita em que
-- a envoltória precisa ser **calibrada localmente** e atualizada com o
-- histórico do próprio município — os coeficientes de Cubatão não valem para
-- outro lugar. Enquanto não houver calibração local com registro de
-- ocorrências, **o sistema acumula e exibe, mas não dispara limiar
-- automático** (RC-18).
--
-- Preencher um número aqui sem calibração seria dar aparência de critério
-- técnico a um chute — e afirmação geotécnica nunca pode ser [E]
-- (REFERENCIAS.md §1).

CREATE TABLE IF NOT EXISTS limiar_municipio (
    municipio   TEXT PRIMARY KEY,
    janela_h    SMALLINT NOT NULL DEFAULT 84,
    coef_a      REAL,        -- NULL = não calibrado; não dispara
    expoente_b  REAL,
    fonte       TEXT,        -- [L]/[G] de onde vieram os coeficientes
    calibrado_em DATE,
    observacao  TEXT
);

COMMENT ON COLUMN limiar_municipio.coef_a IS
    'NULL enquanto nao calibrado com ocorrencias locais. Sem isso o sistema '
    'nao emite alerta automatico de chuva — apenas informa acumulado (RC-18).';

-- ------------------------------------ situação combinada por Atalaia --
-- Junta as três fontes na granularidade em que cada uma é boa:
--   chuva  → rede oficial, regional
--   solo   → Atalaia, local
--   incl.  → Atalaia, local
--
-- É a materialização do ADR-009: nenhuma fonte é usada fora da escala em que
-- ela é confiável, e a procedência viaja junto.

CREATE OR REPLACE VIEW situacao_atalaia AS
SELECT n.node_id,
       n.placa,
       ae.codigo            AS estacao_codigo,
       ae.estacao,
       ae.rede,
       ae.distancia_m       AS estacao_distancia_m,
       ca.mm_24h            AS chuva_oficial_24h,
       ca.mm_72h            AS chuva_oficial_72h,
       ca.mm_84h            AS chuva_oficial_84h,
       ul.umidade_solo,
       ul.solo_valido,
       ul.pitch_graus,
       ul.roll_graus,
       ul.inclin_valida,
       ul.recebido_em       AS ultima_leitura,
       lm.coef_a IS NOT NULL AS limiar_calibrado
FROM no n
LEFT JOIN atalaia_estacao ae ON ae.node_id = n.node_id
LEFT JOIN chuva_oficial_acumulada ca ON ca.codigo = ae.codigo
LEFT JOIN LATERAL (
    SELECT * FROM leitura l WHERE l.node_id = n.node_id
     ORDER BY l.recebido_em DESC LIMIT 1
) ul ON TRUE
LEFT JOIN limiar_municipio lm ON TRUE;
