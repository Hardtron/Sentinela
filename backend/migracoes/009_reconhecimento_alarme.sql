-- Sentinela — 009: Reconhecimento e despacho de alarmes (Frente 10 / T-27).
--
-- Transforma alarmes estáticos em itens operacionais com ciclo de atendimento:
-- 1. Abertura automática (pelo ingestor / monitor de saúde)
-- 2. Reconhecimento pelo operador / Defesa Civil (registra operador + data)
-- 3. Despacho de equipe de campo / ação preventiva
-- 4. Encerramento automático ou manual com nota técnica
--
-- Autoria: Matheus Marassi

ALTER TABLE alarme
    ADD COLUMN IF NOT EXISTS reconhecido_em    TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reconhecido_por   TEXT,
    ADD COLUMN IF NOT EXISTS acao_tomada       TEXT,
    ADD COLUMN IF NOT EXISTS despacho_equipe   BOOLEAN DEFAULT FALSE,
    ADD COLUMN IF NOT EXISTS nota_operador     TEXT;

COMMENT ON COLUMN alarme.reconhecido_em IS 'Data/hora em que o operador visualizou e tomou ciência do alarme (RC-10).';
COMMENT ON COLUMN alarme.reconhecido_por IS 'Identificação do operador ou agente da Defesa Civil que reconheceu o alarme.';
COMMENT ON COLUMN alarme.acao_tomada IS 'Ação imediata registrada (ex: DESPACHO_CAMPO, MONITORAMENTO_INTENSIFICADO, FALSO_POSITIVO).';
COMMENT ON COLUMN alarme.despacho_equipe IS 'Indica se foi gerada Ordem de Serviço / equipe enviada a campo.';
COMMENT ON COLUMN alarme.nota_operador IS 'Observações registradas pela central de operações.';

CREATE TABLE IF NOT EXISTS alarme_evento (
    id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    alarme_id   BIGINT NOT NULL REFERENCES alarme(id),
    registrado_em TIMESTAMPTZ NOT NULL DEFAULT now(),
    operador    TEXT NOT NULL,
    acao        TEXT NOT NULL,
    despacho_equipe BOOLEAN NOT NULL DEFAULT FALSE,
    nota        TEXT
);

CREATE INDEX IF NOT EXISTS alarme_evento_por_alarme
    ON alarme_evento (alarme_id, registrado_em DESC);

-- --------------------------------------------- procedure de reconhecimento --

CREATE OR REPLACE FUNCTION reconhecer_alarme(
    p_alarme_id BIGINT,
    p_operador  TEXT,
    p_acao      TEXT DEFAULT 'RECONHECIDO',
    p_despacho  BOOLEAN DEFAULT FALSE,
    p_nota      TEXT DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    IF btrim(coalesce(p_operador, '')) = '' THEN
        RAISE EXCEPTION 'Operador é obrigatório.';
    END IF;

    UPDATE alarme
       SET reconhecido_em  = coalesce(reconhecido_em, now()),
           reconhecido_por = p_operador,
           acao_tomada     = p_acao,
           despacho_equipe = p_despacho,
           nota_operador   = p_nota
     WHERE id = p_alarme_id;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Alarme % não encontrado.', p_alarme_id;
    END IF;

    INSERT INTO alarme_evento (
        alarme_id, operador, acao, despacho_equipe, nota
    ) VALUES (
        p_alarme_id, p_operador, p_acao, p_despacho, p_nota
    );
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION reconhecer_alarme IS
    'Registra a tomada de ciência e providências adotadas pela central de operações.';
