-- Sentinela — 011: contrato auditável para fontes ambientais externas.
--
-- Esta camada NÃO participa de regras automáticas de alarme. Ela preserva a
-- origem, a execução de aquisição, o bruto imutável e as revisões normalizadas
-- para que observação, estimativa, previsão e contexto territorial possam ser
-- comparados sem serem somados como se fossem a mesma grandeza.

CREATE TABLE IF NOT EXISTS fonte_provedor (
    codigo              TEXT PRIMARY KEY,
    nome                TEXT NOT NULL,
    orgao               TEXT NOT NULL,
    acesso              TEXT NOT NULL,
    documentacao_url    TEXT NOT NULL,
    atribuicao          TEXT,
    exige_cadastro      BOOLEAN NOT NULL DEFAULT FALSE,
    cadastrado_em       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS fonte_conjunto (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provedor_codigo     TEXT NOT NULL REFERENCES fonte_provedor(codigo),
    codigo              TEXT NOT NULL,
    titulo              TEXT NOT NULL,
    classe              TEXT NOT NULL CHECK (classe IN (
                            'OBSERVACAO_PONTUAL', 'ESTIMATIVA_GRADE',
                            'PREVISAO', 'RADAR_SATELITE',
                            'CONTEXTO_TERRITORIAL', 'HISTORICO')),
    variavel            TEXT,
    unidade             TEXT,
    uso                 TEXT NOT NULL DEFAULT 'CONTEXTO'
                            CHECK (uso IN ('CONTEXTO', 'OBSERVACAO', 'PESQUISA')),
    estado              TEXT NOT NULL DEFAULT 'AGUARDA_CONFIGURACAO'
                            CHECK (estado IN ('ATIVO', 'PAUSADO',
                                              'AGUARDA_CONFIGURACAO')),
    configuracao        JSONB NOT NULL DEFAULT '{}'::jsonb,
    limitacao           TEXT NOT NULL,
    criado_em           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provedor_codigo, codigo)
);

CREATE TABLE IF NOT EXISTS fonte_execucao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conjunto_id         BIGINT NOT NULL REFERENCES fonte_conjunto(id),
    iniciado_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    terminado_em        TIMESTAMPTZ,
    estado              TEXT NOT NULL CHECK (estado IN (
                            'INICIADA', 'SUCESSO', 'SEM_NOVIDADE',
                            'QUARENTENA', 'FALHA')),
    versao_coletor      TEXT NOT NULL,
    configuracao        JSONB NOT NULL DEFAULT '{}'::jsonb,
    http_status         SMALLINT,
    itens_recebidos     INTEGER,
    itens_aceitos       INTEGER,
    itens_rejeitados    INTEGER,
    erro_resumo         TEXT
);

CREATE INDEX IF NOT EXISTS fonte_execucao_conjunto_tempo
    ON fonte_execucao (conjunto_id, iniciado_em DESC);

CREATE TABLE IF NOT EXISTS fonte_ativo_bruto (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conjunto_id         BIGINT NOT NULL REFERENCES fonte_conjunto(id),
    execucao_id         BIGINT REFERENCES fonte_execucao(id),
    adquirido_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    processado_em       TIMESTAMPTZ,
    observado_de        TIMESTAMPTZ,
    observado_ate       TIMESTAMPTZ,
    emitido_em          TIMESTAMPTZ,
    fonte_uri           TEXT NOT NULL,
    tipo_conteudo       TEXT,
    tamanho_bytes       BIGINT NOT NULL CHECK (tamanho_bytes >= 0),
    sha256              CHAR(64) NOT NULL,
    caminho             TEXT NOT NULL,
    metadados           JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (conjunto_id, sha256)
);

CREATE INDEX IF NOT EXISTS fonte_ativo_conjunto_tempo
    ON fonte_ativo_bruto (conjunto_id, adquirido_em DESC);

CREATE TABLE IF NOT EXISTS fonte_estacao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    provedor_codigo     TEXT NOT NULL REFERENCES fonte_provedor(codigo),
    codigo_externo      TEXT NOT NULL,
    nome                TEXT,
    municipio           TEXT,
    uf                  CHAR(2),
    altitude_m          REAL,
    geom                GEOGRAPHY(POINT, 4326),
    metadados           JSONB NOT NULL DEFAULT '{}'::jsonb,
    vista_primeiro_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    vista_ultimo_em     TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (provedor_codigo, codigo_externo)
);

CREATE INDEX IF NOT EXISTS fonte_estacao_geom
    ON fonte_estacao USING GIST (geom);

CREATE TABLE IF NOT EXISTS fonte_observacao_pontual (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY,
    conjunto_id         BIGINT NOT NULL REFERENCES fonte_conjunto(id),
    estacao_id          BIGINT NOT NULL REFERENCES fonte_estacao(id),
    medido_em           TIMESTAMPTZ NOT NULL,
    recebido_em         TIMESTAMPTZ NOT NULL DEFAULT now(),
    variavel            TEXT NOT NULL,
    valor               DOUBLE PRECISION NOT NULL,
    unidade             TEXT NOT NULL,
    periodo_s           INTEGER,
    qualificacao_origem TEXT,
    revisao             TEXT NOT NULL DEFAULT 'ORIGINAL',
    ativo_bruto_id      BIGINT REFERENCES fonte_ativo_bruto(id),
    metadados           JSONB NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (id, medido_em)
);

SELECT create_hypertable('fonte_observacao_pontual', 'medido_em',
                         if_not_exists => TRUE);

-- O período faz parte da identidade: acumulados de 1 h e 24 h têm a mesma
-- variável e o mesmo instante, mas não são a mesma observação.
CREATE UNIQUE INDEX IF NOT EXISTS fonte_observacao_unica
    ON fonte_observacao_pontual
       (conjunto_id, estacao_id, medido_em, variavel,
        coalesce(periodo_s, -1), revisao);

CREATE TABLE IF NOT EXISTS fonte_camada (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conjunto_id         BIGINT NOT NULL REFERENCES fonte_conjunto(id),
    ativo_bruto_id      BIGINT NOT NULL REFERENCES fonte_ativo_bruto(id),
    identificador       TEXT,
    valido_de           TIMESTAMPTZ,
    valido_ate          TIMESTAMPTZ,
    rodada_em           TIMESTAMPTZ,
    horizonte_s         INTEGER,
    resolucao           TEXT,
    geom_extensao       GEOMETRY(GEOMETRY, 4326),
    metadados           JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (conjunto_id, ativo_bruto_id, identificador)
);

CREATE INDEX IF NOT EXISTS fonte_camada_geom
    ON fonte_camada USING GIST (geom_extensao);

CREATE TABLE IF NOT EXISTS fonte_feicao (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conjunto_id         BIGINT NOT NULL REFERENCES fonte_conjunto(id),
    ativo_bruto_id      BIGINT NOT NULL REFERENCES fonte_ativo_bruto(id),
    identificador       TEXT NOT NULL,
    geom                GEOMETRY(GEOMETRY, 4326),
    propriedades        JSONB NOT NULL DEFAULT '{}'::jsonb,
    UNIQUE (conjunto_id, ativo_bruto_id, identificador)
);

CREATE INDEX IF NOT EXISTS fonte_feicao_geom
    ON fonte_feicao USING GIST (geom);

CREATE TABLE IF NOT EXISTS fonte_quarentena (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conjunto_id         BIGINT REFERENCES fonte_conjunto(id),
    execucao_id         BIGINT REFERENCES fonte_execucao(id),
    registrado_em       TIMESTAMPTZ NOT NULL DEFAULT now(),
    etapa               TEXT NOT NULL,
    motivo              TEXT NOT NULL,
    fonte_uri           TEXT,
    sha256              CHAR(64),
    detalhe             JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS fonte_quarentena_tempo
    ON fonte_quarentena (registrado_em DESC);

CREATE OR REPLACE VIEW fonte_estado AS
SELECT p.codigo AS provedor_codigo, p.nome AS provedor, p.orgao, p.acesso,
       p.exige_cadastro, c.id AS conjunto_id, c.codigo AS conjunto_codigo,
       c.titulo, c.classe, c.variavel, c.unidade, c.uso,
       c.estado AS configuracao_estado, c.limitacao,
       e.iniciado_em AS ultima_execucao_em,
       e.terminado_em AS ultima_conclusao_em,
       e.estado AS ultima_execucao_estado,
       e.itens_recebidos, e.itens_aceitos, e.itens_rejeitados,
       e.erro_resumo,
       a.adquirido_em AS ultimo_ativo_em,
       a.processado_em AS ultimo_processado_em,
       a.observado_ate AS ultimo_observado_em,
       a.sha256 AS ultimo_sha256
  FROM fonte_conjunto c
  JOIN fonte_provedor p ON p.codigo = c.provedor_codigo
  LEFT JOIN LATERAL (
      SELECT x.* FROM fonte_execucao x
       WHERE x.conjunto_id = c.id
       ORDER BY x.iniciado_em DESC LIMIT 1) e ON TRUE
  LEFT JOIN LATERAL (
      SELECT b.* FROM fonte_ativo_bruto b
       WHERE b.conjunto_id = c.id
       ORDER BY b.adquirido_em DESC LIMIT 1) a ON TRUE;

COMMENT ON VIEW fonte_estado IS
    'Estado observado das aquisições; não é estado meteorológico nem autoriza alerta.';

CREATE OR REPLACE VIEW fonte_observacao_atual AS
SELECT DISTINCT ON (conjunto_id, estacao_id, medido_em, variavel,
                    coalesce(periodo_s, -1))
       id, conjunto_id, estacao_id, medido_em, recebido_em, variavel,
       valor, unidade, periodo_s, qualificacao_origem, revisao,
       ativo_bruto_id, metadados
  FROM fonte_observacao_pontual
 ORDER BY conjunto_id, estacao_id, medido_em, variavel,
          coalesce(periodo_s, -1), recebido_em DESC, id DESC;

COMMENT ON VIEW fonte_observacao_atual IS
    'Revisão mais recente por estação/instante/variável/período; revisões anteriores permanecem na tabela base.';

CREATE OR REPLACE VIEW fonte_feicao_atual AS
SELECT f.*
  FROM fonte_feicao f
  JOIN fonte_ativo_bruto a ON a.id = f.ativo_bruto_id
  JOIN LATERAL (
      SELECT x.id FROM fonte_ativo_bruto x
       WHERE x.conjunto_id = f.conjunto_id
       ORDER BY x.adquirido_em DESC, x.id DESC LIMIT 1
  ) atual ON atual.id = a.id;

COMMENT ON VIEW fonte_feicao_atual IS
    'Feições do ativo bruto mais recente de cada conjunto; a história permanece em fonte_feicao.';

INSERT INTO fonte_provedor
    (codigo, nome, orgao, acesso, documentacao_url, atribuicao, exige_cadastro)
VALUES
 ('CEMADEN', 'Plataforma de Estações de Dados', 'CEMADEN/MCTI',
  'REST JSON com token', 'https://sws.cemaden.gov.br/PED/api/ui/',
  'CEMADEN/MCTI', TRUE),
 ('ANA', 'HidroWebService', 'ANA', 'REST JSON com OAuth/JWT',
  'https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html', 'ANA', TRUE),
 ('SGB', 'Setorização de Risco', 'Serviço Geológico do Brasil',
  'ArcGIS FeatureServer/GeoJSON',
  'https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/risco/FeatureServer/0',
  'Serviço Geológico do Brasil', FALSE),
 ('INPE_MERGE', 'MERGE/GPM', 'CPTEC/INPE', 'HTTPS/GRIB2',
  'https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/', 'CPTEC/INPE', FALSE),
 ('INPE_WRF', 'WRF 7 km', 'CPTEC/INPE', 'HTTPS/arquivos',
  'https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/', 'CPTEC/INPE', FALSE),
 ('NOAA_GFS', 'Global Forecast System', 'NOAA/NCEP', 'HTTPS/GRIB2',
  'https://nomads.ncep.noaa.gov/info.php?page=gribfilter', 'NOAA/NCEP', FALSE),
 ('REDEMET', 'Produtos meteorológicos aeronáuticos', 'DECEA',
  'REST JSON/imagens com chave',
  'https://ajuda.decea.mil.br/base-de-conhecimento/api-redemet-o-que-e/',
  'REDEMET/DECEA', TRUE),
 ('INMET', 'Dados meteorológicos', 'INMET', 'arquivo oficial/RSS',
  'https://portal.inmet.gov.br/dadoshistoricos', 'INMET', FALSE),
 ('NASA_IMERG', 'IMERG', 'NASA GES DISC/PPS', 'HTTPS/OPeNDAP/arquivos',
  'https://gpm.nasa.gov/data/imerg', 'NASA', TRUE),
 ('CHIRPS', 'CHIRPS', 'Climate Hazards Center/UCSB', 'HTTPS/COG/NetCDF',
  'https://www.chc.ucsb.edu/data/chirps', 'CHC/UCSB', FALSE),
 ('NOAA_GOES', 'GOES/GLM', 'NOAA/NESDIS', 'HTTPS/cloud/NetCDF',
  'https://www.ncei.noaa.gov/products/satellite/goes-r-series', 'NOAA', FALSE)
ON CONFLICT (codigo) DO NOTHING;

INSERT INTO fonte_conjunto
    (provedor_codigo, codigo, titulo, classe, variavel, unidade, uso, estado,
     limitacao)
VALUES
 ('CEMADEN','acumulados-recentes','Acumulados recentes de pluviômetros',
  'OBSERVACAO_PONTUAL','precipitacao_acumulada','mm','OBSERVACAO',
  'AGUARDA_CONFIGURACAO','Exige token e recorte por município/estação; representatividade espacial deve ser exibida.'),
 ('ANA','telemetria-adotada','Série telemétrica adotada',
  'OBSERVACAO_PONTUAL',NULL,NULL,'OBSERVACAO','AGUARDA_CONFIGURACAO',
  'Exige credencial e códigos de estações definidos; códigos de qualificação permanecem junto ao dado.'),
 ('SGB','setorizacao-risco','Setorização de áreas de risco',
  'CONTEXTO_TERRITORIAL',NULL,NULL,'CONTEXTO','AGUARDA_CONFIGURACAO',
  'Exige recorte municipal explícito; classificação do órgão não é produzida nem reinterpretada pelo Sentinela.'),
 ('INPE_MERGE','gpm-merge','Precipitação MERGE/GPM',
  'ESTIMATIVA_GRADE','precipitacao','conforme metadado GRIB2','CONTEXTO','AGUARDA_CONFIGURACAO',
  'Estimativa em grade não equivale a observação de estação; URL/produto e recorte devem ser fixados.'),
 ('INPE_WRF','ams-07km','Previsão WRF 7 km',
  'PREVISAO',NULL,NULL,'CONTEXTO','AGUARDA_CONFIGURACAO',
  'Previsão deve carregar rodada, validade e horizonte; produto/recorte ainda requer definição.'),
 ('NOAA_GFS','gfs','Previsão global GFS',
  'PREVISAO',NULL,NULL,'CONTEXTO','AGUARDA_CONFIGURACAO',
  'Previsão não é observação; variáveis, níveis, rodada e recorte devem ser explícitos.'),
 ('REDEMET','radar-satelite','Produtos de radar e satélite',
  'RADAR_SATELITE',NULL,NULL,'CONTEXTO','AGUARDA_CONFIGURACAO',
  'Produtos podem ser imagens; não são convertidos em precipitação numérica sem contrato oficial do produto.'),
 ('INMET','arquivos-oficiais','Arquivos e boletins oficiais',
  'HISTORICO',NULL,NULL,'CONTEXTO','AGUARDA_CONFIGURACAO',
  'Não há endpoint de estação presumido; usar somente arquivo/feed oficialmente documentado e configurado.'),
 ('NASA_IMERG','imerg','Precipitação IMERG',
  'ESTIMATIVA_GRADE','precipitacao','conforme produto','PESQUISA','AGUARDA_CONFIGURACAO',
  'Produto, latência e autenticação dependem da coleção escolhida; não é fonte decisória por padrão.'),
 ('CHIRPS','chirps','Série histórica CHIRPS',
  'HISTORICO','precipitacao','conforme produto','PESQUISA','AGUARDA_CONFIGURACAO',
  'Adequado a contexto histórico, não a estado operacional imediato.'),
 ('NOAA_GOES','goes-glm','GOES/GLM',
  'RADAR_SATELITE',NULL,NULL,'PESQUISA','AGUARDA_CONFIGURACAO',
  'Coleção, setor, latência e processamento NetCDF exigem definição antes da ativação.')
ON CONFLICT (provedor_codigo, codigo) DO NOTHING;
