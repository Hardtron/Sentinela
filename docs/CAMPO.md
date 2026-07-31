# Ensaios de enlace

Registro dos testes de rádio. Cada ensaio anota configuração, ambiente e
resultado bruto — o objetivo final é a **curva alcance × spreading factor**,
que dimensiona quantos gateways por município (critério de saída da Fase 0).

## Metodologia

O nó PINGER transmite a cada 3 s; o PONGER responde ecoando o RSSI/SNR com que
ouviu. Cada troca mede o enlace **nos dois sentidos** — link LoRa é
frequentemente assimétrico, e um lado pode ouvir bem enquanto o outro não.

Saída serial em CSV:

```
seq,rssi_local_dbm,snr_local_db,rssi_remoto_dbm,snr_remoto_db,enviados,recebidos
```

Campos vazios indicam ping sem resposta. O PONGER também emite, a cada 5 s, o
piso de ruído do canal — que distingue "transmissor desligado" de "receptor que
não entrou em recepção".

---

## Ensaio 01 — Bancada, ~10 m com obstrução

**Data:** 30/07/2026 · **Nós:** `HTC-01` (PINGER) e `HTC-02` (PONGER)
**Configuração:** 916,8 MHz · SF9 · BW 125 kHz · CR 4/7 · 17 dBm · ToA 169 ms
**Ambiente:** interno, ~10 m de separação, **paredes de alvenaria** entre os nós
**Alimentação:** `HTC-01` em carregador de celular; `HTC-02` na USB do MacBook

### Resultado

| Métrica | Valor |
|---|---|
| Pacotes | 8 enviados, 8 recebidos — **0% de perda** |
| RSSI local (HTC-02 ouvindo) | −77 a −94 dBm |
| RSSI remoto (HTC-01 ouvindo) | −78 a −97 dBm |
| SNR | +8 a +12 dB |
| Piso de ruído do canal | −98 a −104 dBm |
| Margem sobre a sensibilidade SF9 (−129 dBm) | **35 a 52 dB** |

### Leitura

**O enlace é sólido.** Zero perda, SNR folgado e simetria boa entre os dois
sentidos — a diferença entre o que cada lado ouve fica dentro de poucos dB, o
que indica que não há problema de antena em um dos nós.

**Mas a atenuação é alta para a distância.** Em espaço livre, 10 m a 915 MHz
custam cerca de 52 dB de perda de percurso; com 17 dBm de transmissão, o
esperado seria da ordem de −30 dBm no receptor. O medido ficou entre −77 e
−94 dBm, ou seja, **45 a 60 dB de atenuação adicional**.

Isso é compatível com propagação interna atravessando paredes e lajes, que é o
cenário do ensaio. Mas é atenuação suficiente para merecer verificação no
próximo teste: **repetir com linha de visada limpa**. Se a atenuação extra
persistir sem obstrução, a suspeita passa a ser casamento de antena ou conexão
do conector — e é melhor descobrir isso na bancada do que num talude.

**Variação de até 17 dB entre amostras consecutivas**, com os nós parados, é
assinatura de multipercurso — reflexões em superfícies internas. Esperado em
ambiente fechado; deve reduzir bastante ao ar livre.

**Sobre o piso de ruído:** −104 dBm é o RSSI de canal com o transmissor calado.
Vale lembrar que isso **não** corta a sensibilidade do LoRa: a modulação
desespalha o sinal e demodula com SNR negativo, então recepção abaixo do piso
medido continua possível. O número serve como indicador de **interferência** —
se subir muito em algum local, há emissor concorrente na faixa.

### Conclusão

Bring-up do rádio **validado**. Hardware, firmware, antenas e protocolo
funcionam ponta a ponta. Liberado para o ensaio de alcance ao ar livre.

---

---

## Ensaio 01b — Bancada, curta distância (validação das ferramentas)

**Data:** 30/07/2026 · **Configuração:** idêntica ao ensaio 01
**Ambiente:** interno, placas próximas, sem obstrução relevante entre elas

| Métrica | Valor |
|---|---|
| Pacotes | 19/19 — **0% de perda** |
| RSSI médio | **−51,7 dBm** (−56,0 a −50,0) |
| SNR médio | +11,3 dB |
| Margem | 77 dB |
| **Assimetria** | **0,1 dB** |

### Leitura

Ensaio feito para validar as ferramentas de coleta, mas produziu dois resultados
técnicos que valem por si:

**As antenas estão boas.** Assimetria de **0,1 dB** entre o que cada lado ouve é
praticamente medida idêntica. Isso derruba com folga a hipótese de antena ou
conector defeituoso levantada no ensaio 01 — se houvesse problema em uma das
pontas, apareceria aqui como desequilíbrio.

**A hipótese das paredes ganha força.** Sem obstrução relevante, o enlace mede
−51,7 dBm; no ensaio 01, a ~10 m e através de paredes de alvenaria, media −77 a
−94 dBm. A diferença é consistente com atenuação por alvenaria.

Isso **não substitui** a medição de 10 m com visada limpa do ensaio 02 — a
distância aqui não foi controlada, então não dá para comparar diretamente com o
modelo de espaço livre. Mas remove a preocupação mais séria: o hardware está
saudável.

---

## Ensaio 02 — Percurso urbano noturno, 7 pontos

**Data:** 30/07/2026, 21:57 a 22:11 (local) · **Nós:** `HTC-01` (móvel) e `HTC-02` (fixo, área externa da casa)
**Configuração:** 916,8 MHz · SF9 · BW 125 kHz · CR 4/7 · 17 dBm · ToA 169 ms
**Condições:** noite, **sereno e chuva fina**, vegetação molhada
**Registro:** fotos do display com GPS no EXIF — sem log automático

Dados em `dados/ensaio02.geojson`, `.kml` e `-geo.csv`. Fotos originais em
`dados/fotos/ensaio02/`.

### Resultado

Distâncias medidas a partir de P0 (ponto de partida, próximo à casa).

| Ponto | Dist. | Alt. | RSSI méd | Faixa | Margem | Perda | Veredito | Ambiente |
|---|---|---|---|---|---|---|---|---|
| P0 | 0 m | 6,1 m | −85 | −96 a −82 | 44 dB | 0% | **APROVADO** | partida |
| P1 | 36 m | 9,6 m | −102 | −111 a −99 | 27 dB | 0% | **APROVADO** | alvenaria próxima |
| P2 | 90 m | 5,2 m | −116 | −133 a −114 | 13 dB | 3,7% | LIMITE | rua, alvenaria |
| P3 | 138 m | 5,6 m | −120 | −128 a −114 | 9 dB | 7,4% | **REPROVADO** | rua, alvenaria |
| P4 | 174 m | 6,7 m | −118 | −127 a −115 | 11 dB | 8,0% | **REPROVADO** | descampado com mato |
| P5 | 207 m | 16,7 m | −114 | −124 a −111 | 15 dB | 4,5% | LIMITE | **ponto mais alto** |
| P6 | 205 m | 17,4 m | −114 | −117 a −112 | 15 dB | **0%** | LIMITE | **ponto mais alto** |

### Achado principal: altura vence distância

Este é o resultado que mais importa para o projeto.

**P3/P4** ficam a ~156 m em média, a 6,2 m de altitude: RSSI médio −119 dBm, com
**7 a 8% de perda — reprovados**.

**P5/P6** ficam a ~206 m, **50 m mais longe**, a 17,0 m de altitude: RSSI médio
−114 dBm, e o P6 fechou **20/20 pacotes, zero perda**.

Ou seja: **+51 m de distância e +11 m de altura resultaram em +5 dB de ganho**.
Pelo modelo ajustado abaixo, os 51 m adicionais custariam ~3 dB; então a altura
sozinha entregou cerca de **8 dB — por 11 metros de elevação**.

Oito decibéis é muito: equivale a multiplicar a potência de transmissão por
seis, ou a subir dois níveis de spreading factor. Ganho que nenhum ajuste de
firmware entrega, e que se obtém apenas escolhendo onde instalar.

Isso confirma empiricamente a diretriz do roteiro — *altura de antena vale mais
que potência* — e tem consequência direta na fase 4: **a escolha do ponto do
gateway é a decisão de engenharia de maior impacto do sistema**, acima de
potência, antena ou spreading factor.

### Modelo de propagação ajustado

Regressão log-distância sobre P1–P4 (altitude entre 5 e 10 m, para não misturar
o efeito da altura):

```
RSSI = −63,3 − 25,7·log10(d)      expoente n = 2,57      resíduo RMS = 2,2 dB
```

Um resíduo de **2,2 dB com 4 pontos em ambiente real e chuva** é um ajuste
notavelmente bom. O expoente **n = 2,57** fica entre o espaço livre (2,0) e o
urbano denso (3,5–4,0) — coerente com área residencial de baixa densidade.

**Alcance previsto, mantendo ambos os nós baixos:**

| Margem alvo | Alcance |
|---|---|
| 20 dB (critério de aprovação) | **60 m** |
| 10 dB (limite operacional) | 147 m |
| 0 dB (enlace marginal) | 359 m |

### Leituras adicionais

**Obstrução domina a distância.** P3, a 138 m com alvenaria, mede **pior**
(−120 dBm) que P4, a 174 m em descampado (−118 dBm). Mais longe, sinal melhor. É
a alvenaria, não a distância, que condena o ponto.

**As medições são conservadoras.** Sereno e vegetação molhada atenuam. Vale
distinguir: a chuva em si, em 915 MHz, tem atenuação desprezível — mas **folhagem
molhada absorve bastante**, e o orvalho tem o mesmo efeito. Como o sistema precisa
funcionar exatamente durante a chuva, medir nessa condição é uma vantagem: os
números representam o caso degradado, não o melhor caso.

**A sensibilidade real é melhor que a tabela.** P2 registrou mínimo de
**−133 dBm**, abaixo da sensibilidade nominal de SF9 (−129 dBm), com o pacote
recebido. Isso é esperado — o LoRa demodula com SNR negativo — e significa que a
**margem exibida é conservadora**. O critério de 20 dB tem, portanto, folga
adicional embutida.

**Simetria excelente** em todo o percurso: assimetria de 1 a 4 dB. Nenhum
problema de antena em qualquer das pontas.

### Limitação — o que impede fechar a análise absoluta

A posição exata do `HTC-02` não foi registrada, então as distâncias são medidas
**a partir de P0**, não do nó fixo. O modelo relativo (n = 2,57) é robusto e não
depende disso, mas o termo absoluto fica comprometido: o intercepto de −63,3 dBm
a 1 m é cerca de 45 dB pior que o esperado em espaço livre, o que indica ou uma
distância adicional entre o `HTC-02` e P0, ou obstrução fixa na saída do nó fixo
(provavelmente a própria casa).

**Pendência P-008:** registrar a coordenada e a altura do `HTC-02` para
recalcular as distâncias reais. Com esse dado, o modelo passa a prever alcance
absoluto — e é o que permite calibrá-lo contra o MDE.

### Conclusão

Ensaio **válido e produtivo**. O sistema de medição funcionou ponta a ponta em
campo real: marcação de pontos, veredito automático e georreferenciamento por
foto. Sete pontos classificados sem nenhuma anotação manual de coordenada.

Para a operação, dois números orientam a fase 4: **n = 2,57** para o modelo de
cobertura, e **~8 dB de ganho por 11 m de elevação** para o posicionamento do
gateway.

---

## Próximos ensaios

Procedimento detalhado em [ROTEIRO_CAMPO.md](ROTEIRO_CAMPO.md).

- [x] **02** — Percurso urbano, 7 pontos até ~205 m. Modelo ajustado com
      n = 2,57; altura demonstrou valer ~8 dB por 11 m.
- [ ] **03** — **Prioritário.** Varredura SF7/SF9/SF12 no P6 (ponto alto, já
      caracterizado), comparando margem contra tempo no ar. SF12 acrescenta
      8 dB de sensibilidade sobre SF9 — pelo modelo ajustado, isso **dobra o
      alcance**, ao custo de ~6× mais tempo de rádio ligado.
- [ ] **02b** — Repetir P5/P6 com a coordenada do `HTC-02` registrada (P-008) e
      em tempo seco, para separar o efeito da vegetação molhada.
- [ ] **04** — Percurso com relevo e vegetação reais, no município-piloto
- [ ] **05** — Nó em posição de instalação candidata, 24 h contínuas

No ensaio 04 vale registrar coordenada de cada ponto: o resultado alimenta
diretamente a definição de onde ficam os gateways.
