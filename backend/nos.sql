-- Sentinela — cadastro das placas no banco.
--
-- Espelha docs/HARDWARE.md. Idempotente: reexecutar atualiza em vez de
-- duplicar. `posicao` fica nula enquanto a placa está em bancada — as
-- coordenadas reais entram na campanha de campo.
--
-- Autoria: Matheus Marassi

INSERT INTO no (node_id, placa, mac, papel, antena, observacao) VALUES
    (1, 'HTC-01', '3c:71:bf:8c:33:a8', 'PINGER (posto) — placa substituta', TRUE,
     'Placa original 3c:71:bf:8c:2c:d0 retirada por dano em 31/07/2026; '
     'ensaios 01/01b/02/03a foram feitos com ela, nao com esta'),
    (2, 'HTC-02', '3c:71:bf:8c:2f:9c', 'bancada (bench_02)', FALSE,
     'Antena remanejada para a HTC-03 em 31/07/2026; só escuta'),
    (3, 'HTC-03', '3c:71:bf:8c:2f:a4', 'gateway/Farol (bridge)', TRUE,
     'Placa de display defeituoso, movida ao gateway em 31/07/2026: no '
     'telhado a tela e dispensavel. Destino fisico: telhado da residencia'),
    (4, 'HTC-04', '3c:71:bf:8c:31:70', 'no de campo — aguarda antena', FALSE,
     'Saiu do gateway em 31/07/2026 com display funcional, para uso em campo '
     'onde a tela e instrumento. ATENCAO: saiu com firmware bridge (RF-ativo) '
     'e sem antena — gravar bench_04 antes de energizar (A-003)'),
    (5, 'HTC-05', NULL, 'unica reserva restante (bench_05)', FALSE,
     'Nunca gravada; MAC a identificar na primeira gravação'),
    (6, 'HTC-06', NULL, 'designacao sem placa fisica', FALSE,
     'Era uma das duas reservas; foi promovida ao posto HTC-01 em 31/07/2026')
ON CONFLICT (node_id) DO UPDATE SET
    placa = EXCLUDED.placa, mac = EXCLUDED.mac, papel = EXCLUDED.papel,
    antena = EXCLUDED.antena, observacao = EXCLUDED.observacao;

-- Retroativo: todo o dado coletado até 31/07/2026 saiu com LORA_SF fixo em 9
-- (constante de compilação, nunca alterada). Só a partir do heartbeat que
-- reanuncia o parâmetro é que o SF passou a vir marcado na própria mensagem.
UPDATE enlace SET sf = 9 WHERE sf IS NULL;
