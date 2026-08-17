-- Sentinela — 008: corrige o `format()` do teste de enlace.
--
-- **Defeito encontrado ao rodar a 007 contra dados reais.** O `format()` do
-- PostgreSQL aceita apenas `%s`, `%I` e `%L` — **não** tem formatação numérica
-- estilo printf. Os `%.1f` que escrevi na 007 levantavam
-- `unrecognized format() type specifier "."` **exatamente no caminho de
-- reprovação**: o caminho feliz devolvia o motivo sem erro, mas qualquer
-- reprovação estourava exceção em vez de dizer por que reprovou.
--
-- Isso é pior do que parece. A função existe para explicar **por que** uma
-- Atalaia não pode entrar em operação; falhar justamente aí trocaria um
-- diagnóstico acionável ("margem 8 dB abaixo do mínimo 10") por um erro de SQL
-- que o técnico em campo não tem como interpretar.
--
-- Correção: arredondar antes e passar como `%s`.
--
-- Autoria: Luiz Matheus Marassi de Paula

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
    SELECT count(*)                          AS n,
           avg(e.rssi_dbm)::REAL             AS rssi,
           avg(e.snr_db)::REAL               AS snr,
           avg(e.margem_sobe_db)::REAL       AS margem,
           avg(abs(e.assimetria_db))::REAL   AS assim,
           coalesce(sum(e.perdidos), 0)      AS perdidos
      INTO r
      FROM enlace_analise e
     WHERE e.node_id = p_node_id
       AND e.recebido_em > now() - (p_janela_s || ' seconds')::interval;

    amostras := r.n; rssi_med := r.rssi; snr_med := r.snr;
    margem_med := r.margem; assimetria := r.assim; perdas := r.perdidos;

    -- Ordem = utilidade do diagnóstico: primeiro "chegou alguma coisa?",
    -- depois qualidade. Motivo específico, nunca apenas "reprovado".
    IF r.n IS NULL OR r.n < c_amostras THEN
        aprovado := FALSE;
        motivo := format('amostras insuficientes: %s de %s em %ss',
                         coalesce(r.n, 0), round(c_amostras), p_janela_s);
    ELSIF r.perdidos > 0 THEN
        aprovado := FALSE;
        motivo := format('%s pacote(s) perdido(s) na janela — RC-01 exige sequencia limpa',
                         r.perdidos);
    ELSIF r.rssi < c_rssi THEN
        aprovado := FALSE;
        motivo := format('RSSI %s dBm abaixo do minimo %s',
                         round(r.rssi::numeric, 1), round(c_rssi));
    ELSIF r.snr < c_snr THEN
        aprovado := FALSE;
        motivo := format('SNR %s dB abaixo do minimo %s',
                         round(r.snr::numeric, 1), round(c_snr));
    ELSIF r.margem < c_margem THEN
        aprovado := FALSE;
        motivo := format('margem %s dB abaixo do minimo %s',
                         round(r.margem::numeric, 1), round(c_margem));
    ELSIF r.assim > c_assim THEN
        aprovado := FALSE;
        motivo := format('assimetria %s dB acima do maximo %s — obstrucao direcional?',
                         round(r.assim::numeric, 1), round(c_assim));
    ELSE
        aprovado := TRUE;
        motivo := format('%s amostras, margem %s dB, sem perdas',
                         r.n, round(r.margem::numeric, 1));
    END IF;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql STABLE;

-- Mesmo defeito em valida_posicao().
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

    alerta := CASE
        WHEN classe_suscetibilidade IS NULL THEN
            'posicao fora de zona de suscetibilidade cadastrada — exige justificativa'
        WHEN classe_suscetibilidade NOT IN ('ALTA','MUITO_ALTA') THEN
            format('zona de suscetibilidade %s (esperado ALTA/MUITO_ALTA) — exige justificativa',
                   classe_suscetibilidade)
        WHEN distancia_estacao_m IS NULL THEN
            'nenhuma estacao pluviometrica cadastrada'
        WHEN distancia_estacao_m > v_limite THEN
            format('estacao a %s m (>%s m): chuva oficial com representatividade '
                   'limitada; umidade de solo local ganha peso',
                   round(distancia_estacao_m::numeric), round(v_limite))
        ELSE NULL END;
    RETURN NEXT;
END;
$$ LANGUAGE plpgsql STABLE;
