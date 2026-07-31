-- Sentinela — cadastro das placas no banco.
--
-- Espelha docs/HARDWARE.md. Idempotente: reexecutar atualiza em vez de
-- duplicar. `posicao` fica nula enquanto a placa está em bancada — as
-- coordenadas reais entram na campanha de campo.
--
-- Autoria: Matheus Marassi

INSERT INTO no (node_id, placa, mac, papel, antena, observacao) VALUES
    (1, 'HTC-01', '3c:71:bf:8c:2c:d0', 'PINGER (node_dev)', TRUE,
     'Nó de desenvolvimento; origem do ping'),
    (2, 'HTC-02', '3c:71:bf:8c:2f:9c', 'bancada (bench_02)', FALSE,
     'Antena remanejada para a HTC-03 em 31/07/2026; só escuta'),
    (3, 'HTC-03', '3c:71:bf:8c:31:70', 'bridge/PONGER do RPi 4', TRUE,
     'Gateway: recebe e responde; ligada à USB do Raspberry Pi'),
    (4, 'HTC-04', '3c:71:bf:8c:2f:a4', 'bancada (bench_04)', FALSE,
     'Display defeituoso — reservada ao firmware headless'),
    (5, 'HTC-05', NULL, 'reserva (bench_05)', FALSE,
     'Nunca gravada; MAC a identificar na primeira gravação'),
    (6, 'HTC-06', NULL, 'segundo Farol previsto (bench_06)', FALSE,
     'Nunca gravada; MAC a identificar na primeira gravação')
ON CONFLICT (node_id) DO UPDATE SET
    placa = EXCLUDED.placa, mac = EXCLUDED.mac, papel = EXCLUDED.papel,
    antena = EXCLUDED.antena, observacao = EXCLUDED.observacao;

-- Retroativo: todo o dado coletado até 31/07/2026 saiu com LORA_SF fixo em 9
-- (constante de compilação, nunca alterada). Só a partir do heartbeat que
-- reanuncia o parâmetro é que o SF passou a vir marcado na própria mensagem.
UPDATE enlace SET sf = 9 WHERE sf IS NULL;
