# Modelo de propagação

Base de dimensionamento da rede: quantos gateways, onde, com qual spreading
factor e com que altura de instalação. Combina o ensaio próprio com resultados
publicados para os cenários que o projeto vai encontrar.

Ferramenta: `tools/alcance.py`. Dados do ensaio: [CAMPO.md](CAMPO.md).

---

## 1. Por que o cenário do projeto não é urbano

Área de risco geológico não é área densamente construída. É **encosta com mata**
— aclive e declive acentuados, vegetação de porte variado, ocupação esparsa e
frequentemente irregular. Isso inverte a hierarquia dos fatores de propagação:

| Fator | Peso em cidade densa | Peso em área de risco |
|---|---|---|
| Densidade de construção | dominante | secundário |
| **Relevo (aclive/declive)** | pouco | **dominante** |
| **Vegetação e folhagem** | pouco | **dominante** |
| Altura de instalação | importante | **crítica** |

E há um efeito favorável: **o relevo que cria o risco também ajuda o rádio.**
Um talude põe naturalmente o sensor e o gateway em cotas diferentes, o que é
exatamente a geometria que o enlace quer. O ensaio 02 mediu isso.

---

## 2. Modelo medido no ensaio 02

```
RSSI(d) = −48,1 − 32,8·log10(d)        n = 3,28        RMS = 2,2 dB
```

Cinco pontos, 14 a 175 m, altitude 5 a 10 m, 916,8 MHz, SF9, 17 dBm, sob sereno
e chuva fina. Decompondo em relação ao espaço livre:

```
perda total = FSPL(d) + 12,8·log10(d) + 33,4 dB
              ^espaço    ^excesso de      ^perda fixa
               livre      expoente         do ambiente
```

---

## 3. Confronto com a literatura — e uma coincidência reveladora

| Cenário | Expoente n | Fonte |
|---|---|---|
| Espaço livre (teórico) | 2,00 | — |
| Visada limpa, 923 MHz | 2,31 | [Sensors 2026](https://doi.org/10.3390/s26103192) |
| Palmeiral, visada, 433 MHz | 2,34 | [Sensors 2022](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9317254/) |
| **Floresta tropical, 923 MHz** | **3,22** | [Sensors 2026](https://doi.org/10.3390/s26103192) |
| **Nosso ensaio 02 — alvenaria esparsa** | **3,28** | medido |
| Vegetação densa / dossel alto | ~4,0 | estimado da literatura |

**O paralelo é o achado mais útil desta análise.** Nosso ambiente urbano de baixa
densidade produziu n = 3,28; floresta tropical medida com o mesmo tipo de rádio
produziu n = 3,22. Praticamente idênticos.

Duas consequências práticas:

1. **Alvenaria esparsa e mata atenuam de forma comparável.** Isso não é
   coincidência conceitual: ambos são meios com obstruções distribuídas que
   espalham e absorvem, em vez de bloquear em um ponto.
2. **Nossos dados urbanos servem como proxy razoável para o cenário de encosta
   com mata.** Podemos dimensionar antes de ter acesso ao talude real, e depois
   confirmar. Isso destrava o planejamento.

O que **não** está coberto pelo nosso ensaio, e a literatura alerta: com
**dossel acima de ~23 m** o sinal passa a depender de difração e o RSSI cai para
a faixa de **−120 a −127 dBm**, com alcance máximo em torno de **250 m** em área
florestada montanhosa ([Electronics 2021](https://doi.org/10.3390/electronics10040502)).
Nossos P3/P4 mediram −118 a −120 dBm — exatamente essa faixa. Para mata alta,
usar n = 4,0.

Para referência de dispersão: estudos de cobertura relatam de **50 a 90 m** em
vegetação densa a 868 MHz, **232 m** em terreno florestal e até **1 km** em
floresta junto a lago, onde há visada sobre a água. A variabilidade é enorme e
depende mais do perfil do que da distância — motivo pelo qual o ensaio de campo
não é substituível por catálogo.

---

## 4. A perda fixa de 33 dB é a maior incerteza — e a maior oportunidade

Os 33,4 dB de perda fixa vêm do ambiente imediato do nó fixo: quintal murado,
antena baixa e possível polarização cruzada (CAMPO.md). **Um gateway bem
instalado — poste ou torre, antena vertical, sem obstrução imediata — elimina a
maior parte disso.**

O efeito no alcance é dramático, porque a perda fixa entra linearmente na
equação enquanto a distância entra pelo logaritmo:

**Alcance para margem de 20 dB, SF9, sensor a 1,4 m:**

| Cenário | Com 33 dB de perda fixa | Com 15 dB (gateway limpo) |
|---|---|---|
| Visada limpa | 434 m | **2.713 m** |
| Alvenaria esparsa / mata | 72–78 m | **262–291 m** |
| Vegetação densa | 33 m | **96 m** |

Reduzir a perda fixa de 33 para 15 dB multiplica o alcance por ~3,6. É o ganho
mais barato disponível: depende de escolher o local e orientar a antena, não de
comprar nada.

**Por isso o P-009 (teste de polarização e altura do nó fixo) é prioritário sobre
qualquer outro ensaio.** Ele pode reclassificar todo o dimensionamento.

---

## 5. Altura: o modelo de dois raios funciona

O ensaio validou o modelo empiricamente. Elevar de 6,2 m para 17,0 m:

- previsto por dois raios: 20·log10(17,0/6,2) = **+8,8 dB**
- medido no P5 e no P6: **+9 dB nos dois**

Com isso, dá para dimensionar haste com confiança. Ganho em relação à referência
de 1,4 m (placa na mão):

| Altura da antena | Ganho | Alcance relativo (n = 3,28) |
|---|---|---|
| 1,4 m (no solo) | referência | 1,0× |
| 2 m | +3,1 dB | 1,2× |
| **3 m** | **+6,6 dB** | **1,6×** |
| **4 m** | **+9,1 dB** | **1,9×** |
| 6 m | +12,6 dB | 2,4× |
| 8 m | +15,1 dB | 2,9× |

**Ponto de diminuição de retorno:** o ganho é logarítmico, então os primeiros
metros valem muito mais. De 1,4 m para 4 m ganham-se 9 dB; de 4 m para 8 m,
apenas 6 dB adicionais — com muito mais custo estrutural, exposição ao vento e
risco de raio.

### Recomendação para o nó de campo

**Haste de 3 a 4 m acima do solo** é o ponto ótimo de custo-benefício:

- entrega 6,6 a 9,1 dB — equivalente a dois ou três spreading factors, **de graça
  em consumo**
- tira a antena da vegetação rasteira, que é o que mais absorve perto do solo
- mantém-se dentro do que um poste, estaca reforçada ou varão de aço galvanizado
  suporta sem estaiamento elaborado
- permanece acessível para manutenção sem equipamento de altura (relevante para
  NR-35)

Acima de 4 m, o custo estrutural e o de proteção contra descarga atmosférica
(NBR 5419) crescem mais rápido que o ganho de rádio.

> Atenção de projeto: haste metálica em encosta exposta é captor de descarga.
> O SPDA passa a ser obrigatório, não opcional — ver CONFORMIDADE.md §4, item
> C-07. E a haste **não pode comprometer a medição**: o inclinômetro mede o
> movimento do talude, então a haste precisa estar solidária ao solo que se quer
> medir, e ser rígida o suficiente para não oscilar com vento — oscilação de
> haste vira falso movimento.

---

## 6. Zona de Fresnel — quanta folga o enlace precisa

A haste não serve apenas para "subir": ela precisa liberar a **primeira zona de
Fresnel**, o volume elipsoidal em torno da linha reta entre as antenas. Obstáculo
dentro de 60% desse raio já atenua de forma apreciável.

Raio no meio do vão, a 916,8 MHz:

| Distância | Raio F1 | 60% de F1 |
|---|---|---|
| 100 m | 2,9 m | 1,7 m |
| 200 m | 4,0 m | 2,4 m |
| 500 m | 6,4 m | 3,8 m |
| 1.000 m | 9,0 m | 5,4 m |
| 2.000 m | 12,8 m | 7,7 m |

Leitura prática: para um enlace de 200 m, é preciso **2,4 m de folga no meio do
caminho**. Com sensor a 1,4 m e gateway a 10 m, a linha passa a ~5,7 m no ponto
médio — folgado em terreno plano, mas **insuficiente se houver arbusto de 4 m no
meio**, e é isso que acontece em encosta com mata.

**Aqui o relevo trabalha a favor.** Em declive, a linha entre um sensor na
encosta e um gateway em cota alta passa **acima** do terreno intermediário por
construção geométrica. A folga de Fresnel vem do desnível, não da haste. É por
isso que o cenário de área de risco é, em propagação, mais favorável do que o
número de vegetação isolado sugere.

---

## 7. Spreading factor: alcance contra autonomia

| SF | Sensibilidade | Ganho sobre SF7 | Tempo no ar (11 B) | Custo relativo |
|---|---|---|---|---|
| SF7 | −123,0 dBm | — | 41 ms | 1,0× |
| SF9 | −129,0 dBm | +6 dB | 169 ms | 4,1× |
| SF10 | −132,0 dBm | +9 dB | 289 ms | 7,0× |
| **SF12** | **−137,0 dBm** | **+14 dB** | 1.155 ms | **28,2×** |

SF12 acrescenta 14 dB sobre SF7 — pelo modelo com n = 3,28, isso **multiplica o
alcance por 2,7**. Mas custa **28× mais tempo de rádio ligado**, o que ataca
diretamente os dois recursos escassos do projeto: bateria e ocupação de canal.

**Comparação que decide o desenho:** subir de SF7 para SF12 rende 14 dB ao custo
de 28× de energia de transmissão. Uma haste de 4 m rende 9 dB ao custo de **zero
energia**. Elevar a antena é quase sempre a troca melhor — e as duas se somam.

Regra de projeto: **primeiro resolva altura e posicionamento; use SF alto só
para o que sobrar.** ADR futuro deve fixar SF9 ou SF10 como padrão, com SF12
reservado a nós isolados, e deixar o ADR do LoRaWAN ajustar automaticamente
quando a rede migrar (ADR-001).

---

## 8. Como calibrar isto contra o terreno

O objetivo final é predizer cobertura **sem medir cada ponto** (ROTEIRO_CAMPO.md
§4.2):

1. Pontos medidos e georreferenciados — feito, ensaio 02.
2. **MDE** da área, mais camada de vegetação quando disponível.
3. Extrair o **perfil de terreno** entre gateway e cada ponto, e computar a
   obstrução de Fresnel ao longo dele.
4. Ajustar o expoente e a perda por obstrução aos dados medidos.
5. Rodar o modelo calibrado sobre a malha do município e gerar o **mapa de
   cobertura previsto**.
6. Ir a campo apenas para confirmar os pontos críticos e as discordâncias.

Esse é o passo que transforma trabalho de campo, que não escala, em modelo, que
escala — e é onde a competência em geoprocessamento do projeto entra
(GEOPIXEL.md §4).

---

## 9. Números para levar para a fase 4

| Parâmetro | Valor | Origem |
|---|---|---|
| Expoente, alvenaria esparsa / mata | **n = 3,28** | ensaio 02 |
| Expoente, visada limpa | n = 2,31 | literatura |
| Expoente, vegetação densa / dossel alto | n = 4,0 | literatura |
| Ganho por elevação | **dois raios, +6 dB por dobra** | validado no ensaio 02 |
| Haste recomendada no sensor | **3 a 4 m** | §5 |
| Margem mínima de projeto | 20 dB | ROTEIRO_CAMPO.md §7 |
| Perda fixa a investigar | 33,4 dB | P-009 |

**Fontes:**
[Experimental Comparison and Empirical Path Loss Modeling of LoRa in Line-of-Sight and Forest Environments at 923 MHz](https://doi.org/10.3390/s26103192) ·
[Performance Evaluation of LoRa 920 MHz in a Hilly Forested Area](https://doi.org/10.3390/electronics10040502) ·
[A Critical Review of the Propagation Models Employed in LoRa Systems](https://www.mdpi.com/1424-8220/24/12/3877) ·
[A Multiwall Path-Loss Prediction Model Using 433 MHz LoRa-WAN to Characterize Foliage's Influence](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9317254/) ·
[A Propagation Study of LoRa P2P Links for IoT Applications](https://www.mdpi.com/1424-8220/21/20/6872)
