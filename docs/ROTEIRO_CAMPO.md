# Roteiro do ensaio de campo

Procedimento para levantar a **curva alcance × spreading factor** — o número que
dimensiona quantos gateways por município e, portanto, o custo de implantação.
É o critério de saída da Fase 0.

Os resultados vão para [CAMPO.md](CAMPO.md).

---

## 1. Antes de sair

### Verificação obrigatória

- [ ] **Antena parafusada nas duas placas.** Transmitir sem antena degrada o PA
      do SX1276 (armadilha A-003). Conferir fisicamente, não de memória.
- [ ] Firmware atual gravado nas duas — `HTC-01` como `node_dev` (PINGER) e
      `HTC-02` como `node_range` (PONGER).
- [ ] Alimentação resolvida nas duas (ver §2).
- [ ] Trena, aplicativo de GPS e algo para anotar. O celular serve para as três
      coisas, e a foto da tela substitui a anotação manual.

### Confirmação de que o par está vivo

Ligue as duas lado a lado, a 2–3 m, e confirme na tela do PINGER:

- página **ENLACE** com RSSI forte e barra de margem cheia
- contador de pacotes subindo **sem perda**

Só saia depois disso. Descobrir problema de par a 300 m de casa custa a
caminhada de volta.

---

## 2. Alimentação

### Opção A — Power bank USB (custo zero, recomendada para começar)

Qualquer power bank alimenta a placa pela USB. **Ressalva conhecida:** muitos
power banks se desligam sozinhos quando o consumo é baixo, e a Heltec puxa pouco
— tipicamente algumas dezenas de mA. Se a placa apagar sozinha depois de alguns
minutos, é isso, não é defeito.

Teste antes de sair: deixe a placa ligada no power bank por 10 minutos parada.
Se sobreviver, serve para o ensaio.

### Opção B — Bateria LiPo no conector JST

A Heltec V2 tem conector de bateria e carregador integrado. Três cuidados que
evitam dano à placa:

1. **Conector JST 1,25 mm (tipo SH), 2 vias** — não é o JST-PH 2,0 mm que vem na
   maioria das baterias de hobby. Conferir antes de comprar.
2. **Polaridade.** Não há padronização entre fabricantes de bateria. **Confirmar
   com multímetro qual pino é positivo antes de conectar.** Inverter a
   polaridade danifica a placa.
3. **Célula LiPo de 3,7 V** com proteção. Algo entre 1000 e 2000 mAh dá horas
   de ensaio com folga.

> Enquanto a leitura de tensão não for calibrada (pendência P-005), a indicação
> na tela vem rotulada como `nc` e serve apenas como tendência. Não tire
> conclusão de autonomia a partir dela.

### Opção C — Carregador de celular

Funciona e foi o usado no ensaio 01. Serve para o **nó fixo**, que não se move.

---

## 3. Papéis dos nós

**O operador caminha com o PINGER (`HTC-01`).** Isso não é arbitrário: só o
PINGER sabe quantos pacotes **não** foram respondidos, porque é ele quem conta
os envios. O PONGER só enxerga o que chegou — ele não tem como saber o que se
perdeu.

**O PONGER (`HTC-02`) fica fixo**, no ponto que simula o gateway. Posicione-o
como um gateway real ficaria: **o mais alto possível** e longe de massas
metálicas. Altura de antena vale mais que potência — cada metro de elevação
compra mais alcance do que qualquer ajuste de firmware.

Anote a altura do PONGER. Ela vai junto com o resultado, senão os números não
são comparáveis entre ensaios.

---

## 4. Uso do botão PRG

Um botão, duas funções:

| Ação | Efeito |
|---|---|
| **Toque curto** | Passa para a próxima página |
| **Toque longo (>1 s)** | **Marca novo ponto de medição** — zera as estatísticas e pisca o LED confirmando |

As cinco páginas: **ENLACE** (RSSI grande e barra de margem) · **PONTO**
(resumo consolidado) · **HISTORICO** (gráfico) · **RADIO** (parâmetros) ·
**SISTEMA** (saúde).

A página **PONTO** é a que se fotografa antes de sair de cada local.

---

## 5. Procedimento em cada ponto

1. Chegue ao ponto e **pare de caminhar**. Medir andando mistura
   multipercurso com deslocamento e suja o dado.
2. **Toque longo no PRG** para marcar o novo ponto. O LED confirma.
3. Segure a placa **na altura do peito, antena vertical, afastada do corpo**.
   O corpo humano absorve bem em 915 MHz — encostar a placa no peito derruba
   vários dB e inventa uma atenuação que não existe no cenário real.
4. **Aguarde no mínimo 20 pacotes.** A 3 s por ping, é 1 minuto parado. Menos
   que isso não distingue sinal ruim de desvanecimento momentâneo.
5. Abra a página **PONTO** e fotografe. Registre também a coordenada GPS e a
   distância.
6. Caminhe até o próximo ponto.

### O que anotar em cada ponto

| Campo | Onde obtém |
|---|---|
| Nº do ponto | Tela (cabeçalho `P<n>`) |
| Coordenada GPS | Celular |
| Distância ao PONGER | Aplicativo de mapa ou trena |
| Pacotes recebidos / enviados | Página PONTO |
| Perda % | Página PONTO |
| RSSI médio, mín e máx | Página PONTO |
| Margem | Página PONTO |
| Obstruções entre os nós | Observação — casas, muros, vegetação, relevo |
| Altura da placa e do PONGER | Fita métrica ou estimativa |

A coluna de **obstruções é a mais importante** e a mais esquecida. Sem ela, dois
pontos à mesma distância com resultados opostos viram contradição inexplicável.

---

## 6. Sequência recomendada

### Ensaio 02 — Linha de visada, SF9

Objetivo duplo: medir alcance e **resolver a pendência do ensaio 01** — a
atenuação medida ficou 45 a 60 dB acima do esperado para espaço livre, o que é
compatível com as paredes de alvenaria daquele teste, mas precisa ser confirmado
sem obstrução.

Pontos sugeridos, com visada limpa: **10 m → 25 m → 50 m → 100 m**.

> **A leitura decisiva é a de 10 m com visada limpa.** Se o RSSI ali ficar entre
> −30 e −45 dBm, as paredes explicavam tudo e o hardware está saudável. Se
> continuar perto de −80 dBm sem obstrução alguma, o problema é antena ou
> conector — e aí o ensaio para e o defeito é investigado antes de qualquer
> caminhada longa.

A casa a **100 m na mesma rua** é o ponto final ideal deste ensaio: distância
conhecida, acesso garantido e obstrução representativa de área urbana.

### Ensaio 03 — Varredura de spreading factor

No ponto de 100 m, sem mover nada, repita a medição em SF7, SF9 e SF12.

Trocar o SF exige regravar as duas placas alterando `LORA_SF` em
`board_heltec_v2.h`. Regrave as duas — SF diferente entre os nós não fecha
enlace, e esse é um erro fácil de cometer e difícil de diagnosticar em campo.

O que se compara:

| SF | Sensibilidade | Tempo no ar (11 bytes) | Efeito |
|---|---|---|---|
| SF7 | −123 dBm | ~50 ms | Rápido, menor alcance, menos ocupação de canal |
| SF9 | −129 dBm | ~169 ms | Referência atual |
| SF12 | −137 dBm | ~1,1 s | Máximo alcance, ocupa muito o canal e gasta muito mais |

A comparação de margem contra tempo no ar é o que define o SF de operação.
**Maior alcance não é gratuito:** SF12 multiplica por vinte o tempo de rádio
ligado, o que impacta diretamente a autonomia do nó a bateria e limita quantos
nós cabem no canal.

### Ensaio 04 — Relevo real, no piloto

Feito no município-piloto, com encosta e vegetação reais. Aqui a coordenada de
cada ponto é obrigatória: o resultado alimenta diretamente a decisão de onde
instalar os gateways.

Priorize o cenário verdadeiro: **nó embaixo, na encosta; gateway em ponto alto.**
É essa geometria que a operação terá.

### Ensaio 05 — Estabilidade

Nó parado em posição candidata, 24 h contínuas. Mede o que o teste rápido não
vê: variação térmica ao longo do dia, chuva, movimento de vegetação e
interferência em horários diferentes.

---

## 7. Interpretação

**Margem de enlace** é o número que decide, não o RSSI absoluto. Ela aparece
pronta na tela: distância entre o RSSI recebido e a sensibilidade do SF em uso.

| Margem | Leitura |
|---|---|
| **> 20 dB** | Confortável. Suporta chuva, vegetação úmida e variação sazonal |
| **10 a 20 dB** | Aceitável, mas sem folga para degradação |
| **< 10 dB** | **Não instalar.** Cai na primeira chuva forte |

A recomendação de manter 20 dB de margem não é conservadorismo gratuito: chuva
intensa e folhagem molhada atenuam, e **é exatamente durante a chuva forte que o
sistema precisa funcionar.** Um enlace dimensionado no limite em dia de sol
falha justamente no evento que ele existe para monitorar.

**Perda de pacotes** acima de 5% em ponto parado desqualifica o local, mesmo com
RSSI aparentemente bom — indica interferência ou desvanecimento profundo.

**Assimetria** entre RSSI local e remoto acima de ~10 dB merece investigação:
antena, obstrução próxima a um dos nós, ou ruído local em um dos lados.

---

## 8. Segurança

- Encosta instável é o objeto do projeto, não o lugar do teste. **Não caminhe em
  talude com sinal de instabilidade** para posicionar sensor.
- Ensaio em dia de chuva forte em área de risco: não fazer.
- Propriedade privada exige autorização prévia do morador.
- Ensaio 04, em campo real, não deve ser feito sozinho.
