-- Sentinela — 007: comissionamento e ciclo de vida da Atalaia (Frente 9).
--
-- Uma Atalaia comissionada corretamente é um ponto de dado confiável; uma
-- comissionada sem validação é fonte de falso positivo **ou** falso negativo —
-- os dois perigosos num sistema de alerta de risco à vida.
--
-- As pré-condições de transição ficam **no banco**, não só na aplicação: regra
-- que vive só no formulário web é regra que se contorna com um POST manual.
--
-- Autoria: Luiz Matheus Marassi de Paula

-- ------------------------------------------------ ciclo de vida --

ALTER TABLE no ADD COLUMN IF NOT EXISTS estado TEXT NOT NULL DEFAULT 'REGISTRADA';
ALTER TABLE no ADD COLUMN IF NOT EXISTS comissionada_em TIMESTAMPTZ;
ALTER TABLE no ADD COLUMN IF NOT EXISTS comissionada_por TEXT;

DO $$
BEGIN
    ALTER TABLE no ADD CONSTRAINT no_estado_valido CHECK (estado IN (
        'REGISTRADA','INSTALADA','COMISSIONANDO','VALIDANDO_ENLACE',
        'OPERACIONAL','FALHA_ENLACE','MANUTENCAO','DESATIVADA'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- Histórico de transições. Sem isto não há como auditar "quem ativou esta
-- Atalaia e quando" — pergunta que a Defesa Civil vai fazer (RC-10).
CREATE TABLE IF NOT EXISTS transicao_estado (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_id     SMALLINT NOT NULL REFERENCES no(node_id),
    de          TEXT,
    para        TEXT NOT NULL,
    ocorrida_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    autor       TEXT NOT NULL,
    motivo      TEXT
);

CREATE INDEX IF NOT EXISTS transicao_por_no
    ON transicao_estado (node_id, ocorrida_em DESC);

-- ------------------------------------------------------- checklist --
-- Seções em JSONB de propósito: o checklist evolui com a experiência de campo,
-- e exigir migração de esquema a cada item novo garantiria que ele deixasse de
-- evoluir. A validação estrutural é da aplicação.

CREATE TABLE IF NOT EXISTS checklist_instalacao (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    node_id        SMALLINT NOT NULL REFERENCES no(node_id),
    submetido_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    submetido_por  TEXT NOT NULL,

    -- Tripla responsabilidade (RESPONSABILIDADE_TECNICA.md §3): a camada de
    -- produto e a de geotecnia são assinadas por profissionais diferentes, e o
    -- registro precisa dizer quem respondeu por qual.
    responsavel_campo      TEXT NOT NULL,   -- nome + CRT (Camada 1)
    responsavel_geotecnico TEXT,            -- nome + CREA (Camada 2)

    secao_a_identificacao JSONB NOT NULL DEFAULT '{}'::jsonb,
    secao_b_mecanica      JSONB NOT NULL DEFAULT '{}'::jsonb,
    secao_c_energia       JSONB NOT NULL DEFAULT '{}'::jsonb,
    secao_d_estanqueidade JSONB NOT NULL DEFAULT '{}'::jsonb,
    secao_e_sensoriamento JSONB NOT NULL DEFAULT '{}'::jsonb,
    secao_f_radio         JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Preenchido pela validação automática do servidor.
    posicao_exif           GEOGRAPHY(POINT, 4326),
    declividade_graus      REAL,
    classe_suscetibilidade TEXT,
    distancia_estacao_m    REAL,
    estacao_codigo         TEXT,
    domicilios_300m        INTEGER,
    populacao_300m         INTEGER,

    teste_enlace_rssi_med REAL,
    teste_enlace_snr_med  REAL,
    teste_enlace_margem   REAL,
    teste_enlace_perdas   SMALLINT,
    teste_enlace_amostras SMALLINT,
    teste_enlace_aprovado BOOLEAN,

    foto_oficial_path  TEXT,
    checklist_pdf_path TEXT,
    laudo_pdf_path     TEXT,

    -- Justificativa exigida quando a posição cai fora de zona de alta
    -- suscetibilidade: o sistema não rejeita (pode haver motivo técnico), mas
    -- não deixa passar em silêncio.
    justificativa_posicao TEXT,
    observacoes           TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS checklist_por_no
    ON checklist_instalacao (node_id, submetido_em);

-- ---------------------------------------------- limiares de aceite --
-- Vêm do ensaio 02 [M] e do modelo n = 3,28. Ficam em tabela para poderem ser
-- ajustados sem alterar código — mas com o valor de origem documentado.

CREATE TABLE IF NOT EXISTS criterio_comissionamento (
    chave     TEXT PRIMARY KEY,
    valor     REAL NOT NULL,
    unidade   TEXT,
    fonte     TEXT NOT NULL,
    descricao TEXT
);

INSERT INTO criterio_comissionamento (chave, valor, unidade, fonte, descricao) VALUES
    ('rssi_min',        -110, 'dBm', '[M] ensaio 02',
     'Abaixo disso a margem em SF9 fica sob 20 dB e o enlace nao suporta chuva'),
    ('snr_min',           -5, 'dB',  '[M] ensaio 02',
     'SX1276 demodula abaixo disso, mas sem folga para desvanecimento'),
    ('margem_min',        10, 'dB',  '[M] PONTO_MARGEM_MIN_DB (ui_dev.h)',
     'Abaixo disso o enlace cai na primeira chuva forte'),
    ('assimetria_max',    10, 'dB',  '[M] PONTO_ASSIMETRIA_MAX_DB',
     'Acima disso ha obstrucao direcional ou problema de antena'),
    ('amostras_min',      10, 'un',  '[N] RC-01',
     'Heartbeats consecutivos sem perda que provam confiabilidade'),
    ('janela_teste_s',    60, 's',   'Frente 9',
     'Duracao do teste de enlace no comissionamento'),
    ('distancia_estacao_alerta', 5000, 'm', '[L] ITU-R P.833 / SENSORES.md',
     'Acima disso a chuva oficial tem representatividade limitada: celulas '
     'convectivas na Serra do Mar tem 1-5 km')
ON CONFLICT (chave) DO UPDATE SET
    valor = EXCLUDED.valor, fonte = EXCLUDED.fonte,
    descricao = EXCLUDED.descricao;

-- ------------------------------------------ teste de enlace (60 s) --
-- Consulta a tabela `enlace`, e **não** o broker diretamente. Isso é
-- deliberado: validar pelo banco prova a esteira inteira — rádio → bridge →
-- MQTT → ingestor → PostgreSQL. Um teste que só escuta MQTT aprovaria uma
-- Atalaia cujo dado não chega ao banco, que é onde a decisão acontece.

CREATE OR REPLACE FUNCTION teste_enlace(p_node_id SMALLINT,
                                        p_janela_s INTEGER DEFAULT 60)
RETURNS TABLE (
    amostras   BIGINT,
    rssi_med   REAL,
    snr_med    REAL,
    margem_med REAL,
    assimetria REAL,
    perdas     BIGINT,
    aprovado   BOOLEAN,
    motivo     TEXT
) AS $$
DECLARE
    c_rssi   REAL := (SELECT valor FROM criterio_comissionamento WHERE chave='rssi_min');
    c_snr    REAL := (SELECT valor FROM criterio_comissionamento WHERE chave='snr_min');
    c_margem REAL := (SELECT valor FROM criterio_comissionamento WHERE chave='margem_min');
    c_assim  REAL := (SELECT valor FROM criterio_comissionamento WHERE chave='assimetria_max');
    c_amostras REAL := (SELECT valor FROM criterio_comissionamento WHERE chave='amostras_min');
    r RECORD;
BEGIN
    SELECT count(*)                              AS n,
           avg(e.rssi_dbm)::REAL                 AS rssi,
           avg(e.snr_db)::REAL                   AS snr,
           avg(e.margem_sobe_db)::REAL           AS margem,
           avg(abs(e.assimetria_db))::REAL       AS assim,
           coalesce(sum(e.perdidos), 0)          AS perdidos
      INTO r
      FROM enlace_analise e
     WHERE e.node_id = p_node_id
       AND e.recebido_em > now() - (p_janela_s || ' seconds')::interval;

    amostras := r.n; rssi_med := r.rssi; snr_med := r.snr;
    margem_med := r.margem; assimetria := r.assim; perdas := r.perdidos;

    -- Ordem dos testes = ordem de utilidade do diagnóstico: primeiro "chegou
    -- alguma coisa?", depois qualidade. Motivo específico, nunca "reprovado".
    IF r.n IS NULL OR r.n < c_amostras THEN
        aprovado := FALSE;
        motivo := format('amostras insuficientes: %s de %s em %ss',
                         coalesce(r.n,0), c_amostras::int, p_janela_s);
    ELSIF r.perdidos > 0 THEN
        aprovado := FALSE;
        motivo := format('%s pacote(s) perdido(s) na janela — RC-01 exige sequência limpa', r.perdidos);
    ELSIF r.rssi < c_rssi THEN
        aprovado := FALSE;
        motivo := format('RSSI %.1f dBm abaixo do minimo %.0f', r.rssi, c_rssi);
    ELSIF r.snr < c_snr THEN
        aprovado := FALSE;
        motivo := format('SNR %.1f dB abaixo do minimo %.0f', r.snr, c_snr);
    ELSIF r.margem < c_margem THEN
        aprovado := FALSE;
        motivo := format('margem %.1f dB abaixo do minimo %.0f', r.margem, c_margem);
    ELSIF r.assim > c_assim THEN
        aprovado := FALSE;
        motivo := format('assimetria %.1f dB acima do maximo %.0f — obstrucao direcional?',
                         r.assim, c_assim);
    ELSE
        aprovado := TRUE;
        motivo := format('%s amostras, margem %.1f dB, sem perdas', r.n, r.margem);
    END IF;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------- transição de estado --
-- Guardiã do ciclo de vida. Recusa transição inválida com mensagem que diz
-- **qual** pré-condição faltou — erro genérico obrigaria a adivinhar.

CREATE OR REPLACE FUNCTION transita_estado(p_node_id SMALLINT,
                                           p_para TEXT,
                                           p_autor TEXT,
                                           p_motivo TEXT DEFAULT NULL)
RETURNS TEXT AS $$
DECLARE
    v_de       TEXT;
    v_permitido TEXT[];
    v_pos      GEOGRAPHY;
    v_teste    RECORD;
BEGIN
    SELECT estado, posicao INTO v_de, v_pos FROM no WHERE node_id = p_node_id;
    IF v_de IS NULL THEN
        RAISE EXCEPTION 'node_id % nao cadastrado na tabela no', p_node_id;
    END IF;

    v_permitido := CASE v_de
        WHEN 'REGISTRADA'      THEN ARRAY['INSTALADA','DESATIVADA']
        WHEN 'INSTALADA'       THEN ARRAY['COMISSIONANDO','DESATIVADA']
        WHEN 'COMISSIONANDO'   THEN ARRAY['VALIDANDO_ENLACE','INSTALADA','DESATIVADA']
        WHEN 'VALIDANDO_ENLACE' THEN ARRAY['OPERACIONAL','FALHA_ENLACE']
        WHEN 'FALHA_ENLACE'    THEN ARRAY['COMISSIONANDO','DESATIVADA']
        WHEN 'OPERACIONAL'     THEN ARRAY['MANUTENCAO','DESATIVADA']
        WHEN 'MANUTENCAO'      THEN ARRAY['OPERACIONAL','DESATIVADA']
        WHEN 'DESATIVADA'      THEN ARRAY['REGISTRADA']
        ELSE ARRAY[]::TEXT[] END;

    IF NOT (p_para = ANY(v_permitido)) THEN
        RAISE EXCEPTION 'transicao % -> % nao permitida (validas: %)',
                        v_de, p_para, array_to_string(v_permitido, ', ');
    END IF;

    -- Pré-condição: não se valida enlace de Atalaia sem posição. Sem posição
    -- ela não existe no mapa nem tem estação de chuva associada.
    IF p_para = 'VALIDANDO_ENLACE' AND v_pos IS NULL THEN
        RAISE EXCEPTION 'posicao ausente: comissionamento exige coordenada EXIF validada';
    END IF;

    -- Pré-condição: só entra em OPERACIONAL com teste de enlace aprovado.
    -- É o ponto em que a Atalaia passa a informar decisão de risco.
    IF p_para = 'OPERACIONAL' THEN
        SELECT * INTO v_teste FROM teste_enlace(p_node_id);
        IF NOT v_teste.aprovado THEN
            RAISE EXCEPTION 'teste de enlace reprovado: %', v_teste.motivo;
        END IF;
    END IF;

    UPDATE no SET estado = p_para,
                  comissionada_em = CASE WHEN p_para = 'OPERACIONAL'
                                    THEN coalesce(comissionada_em, now())
                                    ELSE comissionada_em END,
                  comissionada_por = CASE WHEN p_para = 'OPERACIONAL'
                                     THEN coalesce(comissionada_por, p_autor)
                                     ELSE comissionada_por END
     WHERE node_id = p_node_id;

    INSERT INTO transicao_estado (node_id, de, para, autor, motivo)
    VALUES (p_node_id, v_de, p_para, p_autor, p_motivo);

    RETURN format('%s -> %s', v_de, p_para);
END;
$$ LANGUAGE plpgsql;

-- -------------------------------------- validação geoespacial --
-- Executada no comissionamento: cruza a coordenada EXIF com tudo que o banco
-- já sabe do território.

CREATE OR REPLACE FUNCTION valida_posicao(p_lon REAL, p_lat REAL)
RETURNS TABLE (
    classe_suscetibilidade TEXT,
    estacao_codigo TEXT,
    distancia_estacao_m REAL,
    domicilios INTEGER,
    populacao INTEGER,
    alerta TEXT
) AS $$
DECLARE
    v_ponto GEOGRAPHY := ST_SetSRID(ST_MakePoint(p_lon, p_lat), 4326)::geography;
    v_raio  INTEGER := 300;
    v_limite REAL := (SELECT valor FROM criterio_comissionamento
                       WHERE chave='distancia_estacao_alerta');
BEGIN
    SELECT s.classe INTO classe_suscetibilidade
      FROM suscetibilidade s
     WHERE ST_Intersects(s.geom, v_ponto)
     ORDER BY CASE s.classe WHEN 'MUITO_ALTA' THEN 1 WHEN 'ALTA' THEN 2
                            WHEN 'MEDIA' THEN 3 ELSE 4 END
     LIMIT 1;

    SELECT e.codigo, ST_Distance(v_ponto, e.geom)::REAL
      INTO estacao_codigo, distancia_estacao_m
      FROM estacao_externa e WHERE e.ativa
     ORDER BY ST_Distance(v_ponto, e.geom) LIMIT 1;

    SELECT coalesce(sum(x.domicilios),0)::INTEGER, coalesce(sum(x.populacao),0)::INTEGER
      INTO domicilios, populacao
      FROM exposicao x WHERE ST_DWithin(x.geom, v_ponto, v_raio);

    -- Não rejeita: informa. O operador pode ter motivo técnico para instalar
    -- fora de zona classificada, mas a justificativa passa a ser obrigatória.
    alerta := CASE
        WHEN classe_suscetibilidade IS NULL THEN
            'posicao fora de zona de suscetibilidade cadastrada — exige justificativa'
        WHEN classe_suscetibilidade NOT IN ('ALTA','MUITO_ALTA') THEN
            format('zona de suscetibilidade %s (esperado ALTA/MUITO_ALTA) — exige justificativa',
                   classe_suscetibilidade)
        WHEN distancia_estacao_m IS NULL THEN
            'nenhuma estacao pluviometrica cadastrada'
        WHEN distancia_estacao_m > v_limite THEN
            format('estacao a %.0f m (>%.0f m): chuva oficial com representatividade limitada; '
                   'umidade de solo local ganha peso', distancia_estacao_m, v_limite)
        ELSE NULL END;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------- painel da frente --

CREATE OR REPLACE VIEW comissionamento_estado AS
SELECT n.node_id, n.placa, n.estado, n.comissionada_em, n.comissionada_por,
       n.posicao IS NOT NULL AS tem_posicao,
       c.submetido_em        AS checklist_em,
       c.responsavel_campo,
       c.responsavel_geotecnico,
       c.classe_suscetibilidade,
       c.distancia_estacao_m,
       c.teste_enlace_aprovado,
       (SELECT count(*) FROM transicao_estado t WHERE t.node_id = n.node_id) AS transicoes
FROM no n
LEFT JOIN LATERAL (
    SELECT * FROM checklist_instalacao ci WHERE ci.node_id = n.node_id
     ORDER BY ci.submetido_em DESC LIMIT 1
) c ON TRUE
ORDER BY n.node_id;
