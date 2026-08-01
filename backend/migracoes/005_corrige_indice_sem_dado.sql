-- Sentinela — 005: corrige o índice de saúde para nó sem dado.
--
-- **Defeito encontrado ao verificar a 004 contra o banco real:** todos os seis
-- nós devolviam índice 25 mesmo sem nunca terem reportado leitura. Causa:
-- `SELECT ... INTO` sem linhas deixa a variável NULL, e `least(25, NULL)`
-- devolve **25** no PostgreSQL (least/greatest ignoram NULL). Ou seja, a
-- ausência total de dado estava sendo creditada como pontuação de sensor.
--
-- É exatamente o modo de falha que o RC-07 proíbe: **ausência de medição não
-- pode virar valor plausível.** Num índice cuja função é priorizar visita de
-- manutenção, creditar pontos a quem nunca falou é o erro mais caro possível —
-- esconde justamente o nó que precisa de atenção.
--
-- Correção: nó que nunca reportou devolve **NULL** (desconhecido), não 0 e não
-- 25. Zero diria "medimos e está péssimo"; NULL diz "não sabemos", que é a
-- verdade. A fila de manutenção passa a exibir esses como `SEM_DADO`.
--
-- Autoria: Matheus Marassi

CREATE OR REPLACE FUNCTION indice_saude(p_node_id SMALLINT)
RETURNS SMALLINT AS $$
DECLARE
    v_critico   INTEGER;
    v_ultima    TIMESTAMPTZ;
    v_silencio  INTERVAL;
    v_flags     INTEGER;
    v_comunic   NUMERIC := 0;
    v_energia   NUMERIC := 0;
    v_sensores  NUMERIC := 0;
    v_integr    NUMERIC := 0;
    r           RECORD;
    tem_saude   BOOLEAN := FALSE;
BEGIN
    -- Sem nenhuma leitura, o índice é desconhecido — não é zero.
    SELECT max(recebido_em) INTO v_ultima FROM leitura WHERE node_id = p_node_id;
    IF v_ultima IS NULL THEN
        RETURN NULL;
    END IF;

    SELECT count(*) INTO v_critico
      FROM alarme
     WHERE node_id = p_node_id AND fechado_em IS NULL AND severidade = 'CRITICO';
    IF v_critico > 0 THEN
        RETURN 0;  -- RC-16: alarme crítico zera, qualquer que seja o resto
    END IF;

    -- Comunicação (30)
    v_silencio := now() - v_ultima;
    IF v_silencio < interval '1 hour' THEN
        v_comunic := 30;
    ELSIF v_silencio < interval '6 hours' THEN
        v_comunic := 15;
    END IF;

    -- Energia (30) — só pontua se houver quadro de saúde; sem ele fica 0,
    -- e o motivo aparece na fila como ausência de telemetria de energia.
    SELECT * INTO r FROM referencia_distribuida WHERE node_id = p_node_id;
    tem_saude := FOUND;
    IF tem_saude AND r.razao IS NOT NULL THEN
        v_energia := least(30, greatest(0, round(r.razao * 30)));
    END IF;

    -- Sensores (25) — proporção de sensores válidos na última leitura.
    SELECT flags INTO v_flags FROM leitura
     WHERE node_id = p_node_id ORDER BY recebido_em DESC LIMIT 1;
    IF v_flags IS NOT NULL THEN
        v_sensores := 25.0 * (
            (v_flags & 1) + ((v_flags >> 1) & 1) + ((v_flags >> 2) & 1)
        ) / 3.0;
    END IF;

    -- Integridade (15)
    IF tem_saude THEN
        v_integr := 15;
        IF r.umidade_interna IS NOT NULL AND r.umidade_interna > 70 THEN
            v_integr := 0;   -- RC-14: vedação comprometida
        ELSIF coalesce(r.reinicios, 0) > 3 THEN
            v_integr := 5;
        END IF;
    END IF;

    RETURN least(100, round(v_comunic + v_energia + v_sensores + v_integr));
END;
$$ LANGUAGE plpgsql STABLE;

-- A fila precisa distinguir "não sabemos" de "está ruim". Sem isso, um nó
-- nunca implantado apareceria no topo da rota de manutenção junto com um nó
-- realmente degradado.
CREATE OR REPLACE VIEW fila_manutencao AS
SELECT n.node_id,
       n.placa,
       n.posicao,
       indice_saude(n.node_id)                       AS indice,
       (SELECT count(*) FROM alarme a
         WHERE a.node_id = n.node_id AND a.fechado_em IS NULL) AS alarmes_abertos,
       CASE
         WHEN indice_saude(n.node_id) IS NULL THEN 'SEM_DADO'
         WHEN indice_saude(n.node_id) < 50    THEN 'INTERVIR'
         WHEN indice_saude(n.node_id) < 70    THEN 'AGENDAR'
         WHEN indice_saude(n.node_id) < 90    THEN 'OBSERVAR'
         ELSE 'SAUDAVEL'
       END                                           AS faixa
FROM no n
ORDER BY indice ASC NULLS LAST;
