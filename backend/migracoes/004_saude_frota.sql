-- Sentinela — 004: manutenção por condição (Frente 7 / MANUTENCAO.md).
--
-- O que viabiliza operar 50+ Atalaias em encosta de difícil acesso: visitar
-- por condição em vez de por calendário. Custo de operação é dominado por
-- deslocamento, não pela intervenção.
--
-- ⚠ PROPRIEDADE INTELECTUAL: a referência distribuída (§ abaixo) é candidata a
-- reivindicação de patente (PATENTES.md §3, candidato A). O repositório deve
-- permanecer privado até PT-01 e PT-03 estarem resolvidas — divulgação antes
-- do depósito compromete a novidade.
--
-- Autoria: Matheus Marassi

-- ------------------------------------------- referência distribuída --
-- A rede é o próprio sensor de referência: cada Atalaia é comparada com a
-- mediana das vizinhas do mesmo Farol.
--
--   Se TODAS caem juntas  → tempo nublado. Não é falha.
--   Se UMA cai e as outras não → problema local: sujeira, sombra ou hardware.
--
-- Elimina a variável climática sem instrumento de referência adicional; custo
-- marginal zero; a precisão melhora conforme a rede cresce.

CREATE OR REPLACE VIEW referencia_distribuida AS
WITH ultimo_dia AS (
    SELECT DISTINCT ON (node_id)
           node_id, recebido_em, energia_dia_wh, v_min_mv, dod_pct,
           umidade_interna, reinicios, watchdogs
    FROM saude_atalaia
    ORDER BY node_id, recebido_em DESC
),
base AS (
    SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY energia_dia_wh) AS mediana
    FROM ultimo_dia
    WHERE energia_dia_wh IS NOT NULL
)
SELECT u.node_id,
       u.recebido_em,
       u.energia_dia_wh,
       b.mediana                                   AS mediana_frota_wh,
       CASE WHEN b.mediana > 0
            THEN round((u.energia_dia_wh / b.mediana)::numeric, 3)
       END                                          AS razao,
       u.v_min_mv, u.dod_pct, u.umidade_interna,
       u.reinicios, u.watchdogs
FROM ultimo_dia u CROSS JOIN base b;

COMMENT ON VIEW referencia_distribuida IS
    'MANUTENCAO.md §4. Limiar de 0,75 na razão e as janelas de 7/14 dias sao '
    'ponto de partida [E], nao validados em campo (RC-18) — calibrar com '
    'operacao real antes de virarem gatilho automatico.';

-- ------------------------------------------------- índice de saúde --
-- 0 a 100, para priorizar rota de manutenção. Pesos de MANUTENCAO.md §6:
-- Comunicação 30, Energia 30, Sensores 25, Integridade 15.
--
-- RC-16: qualquer alarme CRÍTICO **zera** o índice, independentemente do
-- resto. Atalaia muda com bateria cheia não é 70 % saudável — é inútil.

CREATE OR REPLACE FUNCTION indice_saude(p_node_id SMALLINT)
RETURNS SMALLINT AS $$
DECLARE
    v_critico   INTEGER;
    v_silencio  INTERVAL;
    v_comunic   NUMERIC := 0;
    v_energia   NUMERIC := 0;
    v_sensores  NUMERIC := 0;
    v_integr    NUMERIC := 0;
    r           RECORD;
BEGIN
    SELECT count(*) INTO v_critico
      FROM alarme
     WHERE node_id = p_node_id AND fechado_em IS NULL AND severidade = 'CRITICO';
    IF v_critico > 0 THEN
        RETURN 0;  -- RC-16
    END IF;

    SELECT now() - max(recebido_em) INTO v_silencio
      FROM leitura WHERE node_id = p_node_id;
    IF v_silencio IS NULL THEN
        v_comunic := 0;
    ELSIF v_silencio < interval '1 hour' THEN
        v_comunic := 30;
    ELSIF v_silencio < interval '6 hours' THEN
        v_comunic := 15;
    END IF;

    SELECT * INTO r FROM referencia_distribuida WHERE node_id = p_node_id;
    IF FOUND AND r.razao IS NOT NULL THEN
        v_energia := least(30, greatest(0, round(r.razao * 30)));
    END IF;

    SELECT coalesce(30 * (
             (flags & 1) + ((flags >> 1) & 1) + ((flags >> 2) & 1)
           ) / 3.0, 0) INTO v_sensores
      FROM leitura WHERE node_id = p_node_id
     ORDER BY recebido_em DESC LIMIT 1;
    v_sensores := least(25, v_sensores);

    IF FOUND THEN
        v_integr := 15;
        IF r.umidade_interna IS NOT NULL AND r.umidade_interna > 70 THEN
            v_integr := 0;  -- RC-14: vedação comprometida
        ELSIF coalesce(r.reinicios, 0) > 3 THEN
            v_integr := 5;
        END IF;
    END IF;

    RETURN least(100, round(v_comunic + v_energia + v_sensores + v_integr));
END;
$$ LANGUAGE plpgsql STABLE;

-- ------------------------------------------------- nó silencioso (RC-02) --
-- Silêncio prolongado é falha, não flutuação. "Atalaia fora do ar é talude sem
-- monitoramento" — lacuna de cobertura num sistema de alerta, por isso a
-- severidade é CRÍTICA e não apenas indisponibilidade de serviço.

CREATE OR REPLACE VIEW no_silencioso AS
SELECT n.node_id,
       n.placa,
       max(l.recebido_em)                     AS ultima_leitura,
       now() - max(l.recebido_em)             AS silencio,
       CASE
         WHEN max(l.recebido_em) IS NULL           THEN 'SEM_DADO'
         WHEN now() - max(l.recebido_em) > interval '6 hours'  THEN 'CRITICO'
         WHEN now() - max(l.recebido_em) > interval '1 hour'   THEN 'ATENCAO'
         ELSE 'OK'
       END                                    AS estado
FROM no n LEFT JOIN leitura l ON l.node_id = n.node_id
GROUP BY n.node_id, n.placa;

-- ------------------------------------- fila de manutenção priorizada --
-- Ordena por índice de saúde. A roteirização geoespacial (MANUTENCAO.md §7)
-- entra sobre esta base: visita por degradação lenta deve **arrastar**
-- intervenções de baixa prioridade nas Atalaias próximas — trocar bateria que
-- ainda duraria 2 meses custa quase nada se a equipe já está a 30 metros.

CREATE OR REPLACE VIEW fila_manutencao AS
SELECT n.node_id,
       n.placa,
       n.posicao,
       indice_saude(n.node_id)                       AS indice,
       (SELECT count(*) FROM alarme a
         WHERE a.node_id = n.node_id AND a.fechado_em IS NULL) AS alarmes_abertos,
       CASE
         WHEN indice_saude(n.node_id) < 50 THEN 'INTERVIR'
         WHEN indice_saude(n.node_id) < 70 THEN 'AGENDAR'
         WHEN indice_saude(n.node_id) < 90 THEN 'OBSERVAR'
         ELSE 'SAUDAVEL'
       END                                           AS faixa
FROM no n
ORDER BY indice ASC;
