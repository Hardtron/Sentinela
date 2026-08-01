-- Sentinela — 010: histórico de parâmetros e contrato de evidência.
--
-- Não cria nem promove limiares. Preserva os valores existentes e registra
-- cada mudança para que uma homologação ou alarme possa ser reconstruído.

ALTER TABLE criterio_comissionamento
    ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'EXPERIMENTAL',
    ADD COLUMN IF NOT EXISTS vigente_desde TIMESTAMPTZ NOT NULL DEFAULT now(),
    ADD COLUMN IF NOT EXISTS atualizado_por TEXT,
    ADD COLUMN IF NOT EXISTS referencia TEXT;

DO $$ BEGIN
    ALTER TABLE criterio_comissionamento ADD CONSTRAINT criterio_status_valido
        CHECK (status IN ('EXPERIMENTAL', 'INFORMATIVO', 'VALIDADO'));
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;

-- A classificação inicial é conservadora. A presença de [M], [L], [G] ou [N]
-- na fonte não basta, sozinha, para transformar um critério em decisório.
UPDATE criterio_comissionamento
   SET status = 'EXPERIMENTAL'
 WHERE status IS NULL OR status = '';

CREATE TABLE IF NOT EXISTS criterio_comissionamento_historico (
    id              BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chave           TEXT NOT NULL,
    valor           REAL NOT NULL,
    unidade         TEXT,
    fonte           TEXT NOT NULL,
    descricao       TEXT,
    status          TEXT NOT NULL,
    referencia      TEXT,
    vigente_desde   TIMESTAMPTZ NOT NULL,
    registrado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    atualizado_por  TEXT,
    operacao        TEXT NOT NULL CHECK (operacao IN ('BASELINE', 'ALTERACAO'))
);

CREATE INDEX IF NOT EXISTS criterio_historico_chave_tempo
    ON criterio_comissionamento_historico (chave, registrado_em DESC);

INSERT INTO criterio_comissionamento_historico
    (chave, valor, unidade, fonte, descricao, status, referencia,
     vigente_desde, atualizado_por, operacao)
SELECT c.chave, c.valor, c.unidade, c.fonte, c.descricao, c.status,
       c.referencia, c.vigente_desde, c.atualizado_por, 'BASELINE'
  FROM criterio_comissionamento c
 WHERE NOT EXISTS (
       SELECT 1 FROM criterio_comissionamento_historico h
        WHERE h.chave = c.chave);

CREATE OR REPLACE FUNCTION atualiza_vigencia_criterio()
RETURNS TRIGGER AS $$
BEGIN
    IF ROW(NEW.valor, NEW.unidade, NEW.fonte, NEW.descricao, NEW.status,
           NEW.referencia)
       IS DISTINCT FROM
       ROW(OLD.valor, OLD.unidade, OLD.fonte, OLD.descricao, OLD.status,
           OLD.referencia) THEN
        NEW.vigente_desde := now();
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS criterio_comissionamento_vigencia
    ON criterio_comissionamento;
CREATE TRIGGER criterio_comissionamento_vigencia
BEFORE UPDATE ON criterio_comissionamento
FOR EACH ROW EXECUTE FUNCTION atualiza_vigencia_criterio();

CREATE OR REPLACE FUNCTION registra_historico_criterio()
RETURNS TRIGGER AS $$
BEGIN
    IF ROW(NEW.valor, NEW.unidade, NEW.fonte, NEW.descricao, NEW.status,
           NEW.referencia, NEW.vigente_desde, NEW.atualizado_por)
       IS DISTINCT FROM
       ROW(OLD.valor, OLD.unidade, OLD.fonte, OLD.descricao, OLD.status,
           OLD.referencia, OLD.vigente_desde, OLD.atualizado_por) THEN
        INSERT INTO criterio_comissionamento_historico
            (chave, valor, unidade, fonte, descricao, status, referencia,
             vigente_desde, atualizado_por, operacao)
        VALUES
            (NEW.chave, NEW.valor, NEW.unidade, NEW.fonte, NEW.descricao,
             NEW.status, NEW.referencia, NEW.vigente_desde,
             NEW.atualizado_por, 'ALTERACAO');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS criterio_comissionamento_historiza
    ON criterio_comissionamento;
CREATE TRIGGER criterio_comissionamento_historiza
AFTER UPDATE ON criterio_comissionamento
FOR EACH ROW EXECUTE FUNCTION registra_historico_criterio();

-- Snapshot congelado no checklist: mudar um critério amanhã não reescreve a
-- justificativa da homologação feita hoje.
ALTER TABLE checklist_instalacao
    ADD COLUMN IF NOT EXISTS criterio_snapshot JSONB NOT NULL DEFAULT '{}'::jsonb;

CREATE OR REPLACE FUNCTION snapshot_criterios_checklist()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.criterio_snapshot = '{}'::jsonb THEN
        SELECT coalesce(jsonb_object_agg(
                   c.chave,
                   jsonb_build_object(
                       'valor', c.valor, 'unidade', c.unidade,
                       'fonte', c.fonte, 'status', c.status,
                       'referencia', c.referencia,
                       'vigente_desde', c.vigente_desde)), '{}'::jsonb)
          INTO NEW.criterio_snapshot
          FROM criterio_comissionamento c;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS checklist_snapshot_criterios ON checklist_instalacao;
CREATE TRIGGER checklist_snapshot_criterios
BEFORE INSERT ON checklist_instalacao
FOR EACH ROW EXECUTE FUNCTION snapshot_criterios_checklist();

-- Contrato evolutivo para evidência. `evidencia` permanece intacta para
-- compatibilidade; os campos novos declaram formato e proveniência.
ALTER TABLE alarme
    ADD COLUMN IF NOT EXISTS evidencia_versao SMALLINT NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS evidencia_proveniencia JSONB NOT NULL DEFAULT '{}'::jsonb;

COMMENT ON COLUMN alarme.evidencia_versao IS
    'Versão do contrato do JSONB evidencia; não é versão da regra de alerta.';
COMMENT ON COLUMN alarme.evidencia_proveniencia IS
    'Metadados de origem, firmware, regra e parâmetros quando disponíveis. '
    'Não autoriza abertura automática de alarmes.';

CREATE OR REPLACE VIEW criterio_comissionamento_auditoria AS
SELECT c.*, h.registrado_em AS historico_registrado_em, h.operacao
  FROM criterio_comissionamento c
  LEFT JOIN LATERAL (
      SELECT registrado_em, operacao
        FROM criterio_comissionamento_historico h
       WHERE h.chave = c.chave
       ORDER BY registrado_em DESC LIMIT 1
  ) h ON TRUE;
