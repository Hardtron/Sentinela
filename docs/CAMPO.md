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

## Próximos ensaios

Procedimento detalhado em [ROTEIRO_CAMPO.md](ROTEIRO_CAMPO.md).

- [ ] **02** — Linha de visada ao ar livre: 10 m → 25 m → 50 m → 100 m, SF9.
      A casa a 100 m na mesma rua é o ponto final. **A leitura de 10 m com
      visada limpa resolve a pendência do ensaio 01.**
- [ ] **03** — Varredura SF7/SF9/SF12 no ponto de 100 m, comparando margem e ToA
- [ ] **04** — Percurso com relevo e vegetação reais, no município-piloto
- [ ] **05** — Nó em posição de instalação candidata, 24 h contínuas

No ensaio 04 vale registrar coordenada de cada ponto: o resultado alimenta
diretamente a definição de onde ficam os gateways.
