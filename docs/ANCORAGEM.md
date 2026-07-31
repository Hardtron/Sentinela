# Ancoragem e instalação do nó de campo

Projeto padronizado de como o dispositivo se fixa no talude. Responde às quatro
questões abertas: como ancorar, se a haste de 4 m é mesmo necessária em encosta,
que material usar e como manter a instalação simples sem comprometer a leitura.

Dimensionamento: `tools/haste.py`. Propagação: [PROPAGACAO.md](PROPAGACAO.md).

> **Proveniência.** Números e afirmações neste documento seguem a política de
> [REFERENCIAS.md](REFERENCIAS.md): **[M]** medido em ensaio próprio, **[N]**
> norma, **[L]** literatura revisada, **[G]** fonte governamental, **[E]**
> estimativa própria derivada, **[?]** pendente de referência.

---

## 1. O conflito central

O nó tem duas funções que pedem coisas opostas:

| Função | O que ela quer |
|---|---|
| **Rádio** | Antena **alta**, acima da vegetação |
| **Inclinômetro** | Estrutura **rígida e solidária ao solo** que se quer medir |

Uma haste alta balança. E se o inclinômetro estiver nela, o balanço vira leitura
de movimento — falso positivo no sensor que existe justamente para detectar
movimento.

**Quanto isso pesa, em número.** Vento conforme **ABNT NBR 6123** **[N]**:
velocidade básica V₀ = 40 m/s (estimativa para o litoral paulista,
**[CONFIRMAR]** na isopleta — a norma dá de 30 a 48 m/s no país), categoria III
e fator topográfico S₁ = 1,15 para encosta. A velocidade característica resulta
em **35,8 m/s a 1,5 m** e 39,5 m/s a 4 m.

Deflexão angular no topo **[E]** — viga engastada, pressão dinâmica uniforme:

| Perfil | 1,5 m | 3 m | 4 m |
|---|---|---|---|
| Eletroduto 3/4" galv. | 0,27° | 2,49° | **6,26°** |
| Eletroduto 1" galv. | 0,14° | 1,29° | **3,23°** |
| Tubo 1.1/2" galv. | **0,07°** | 0,61° | 1,54° |
| Tubo 2" galv. | **0,04°** | 0,33° | 0,83° |
| PVC 50 mm | 3,81° | 34,99° | 87,86° |

> **Correção registrada.** A versão anterior deste documento usava 20 m/s, valor
> arbitrário e não normativo, e subestimava as deflexões em cerca de 3×. Ver
> [REFERENCIAS.md](REFERENCIAS.md) §3, revisão R1.

**Sobre o que se compara.** O projeto **não define limiar de alerta por
inclinação** — a literatura é explícita em que esses limiares são **específicos
do sítio**, definidos a partir da geologia e das condições locais
([Natural Hazards, 2022](https://link.springer.com/article/10.1007/s11069-022-05383-y))
**[L]**, e sua definição é atribuição de engenheiro geotécnico
(RESPONSABILIDADE_TECNICA.md §5).

O que cabe ao projeto especificar é **capacidade de medição**: instrumentos MEMS
de instrumentação geotécnica apresentam resolução da ordem de **0,0025°**
([Sisgeo](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/),
[ESS](https://www.essearth.com/product/geostring-in-place-mems-inclinometer/))
**[L]**. O **ruído estrutural precisa ficar muito abaixo de qualquer limiar
plausível** — e é isso que a tabela avalia.

Conclusões:

- **Haste de 3 a 4 m com inclinômetro no topo é inviável.** Deflexões de 0,8° a
  6,3° são ordens de grandeza acima da resolução do instrumento e comprometem
  qualquer limiar razoável.
- **A 1,5 m, tubo de 1.1/2" ou 2" fica em 0,04–0,07°** — margem aceitável, ainda
  que não desprezível. O eletroduto 3/4" **sai da recomendação**: 0,27° a 1,5 m
  é alto demais.
- **PVC está descartado como elemento estrutural.** 3,81° já a 1,5 m. Serve como
  conduíte ou proteção, nunca como haste.

---

## 2. A solução: separar as duas funções

**O inclinômetro fica embaixo, junto ao solo. A antena fica em cima.** O rádio
não se importa com oscilação — alguns centímetros de balanço não alteram o
enlace. O inclinômetro se importa muito.

```
        ┌── antena no topo do invólucro (1,5 m)
        │
   ═════╪═════  invólucro IP67 com eletrônica e rádio
        │
        │       tubo de aço galvanizado 1.1/2"
        │
   ─────┼─────  solo
        ▓       ← INCLINÔMETRO AQUI, na base, dentro do tubo
        ▓
        ▓       trecho cravado, 0,8 a 1,2 m
        ▓
```

Com o sensor de inclinação na base engastada, a deflexão do vento é **zero por
definição** — o engaste não gira, quem gira é o topo livre. O que a base mede é
apenas a rotação do bloco de solo em que está cravada, que é exatamente o
fenômeno de interesse.

Se um vão específico exigir antena mais alta que 1,5 m, a saída **não** é
alongar esta haste: é um **mastro separado**, estaiado, mecanicamente
independente do tubo de medição, ligado por cabo coaxial. Assim o mastro pode
balançar à vontade sem contaminar a leitura.

---

## 3. Profundidade de ancoragem — e um contra-senso importante

A intuição diz "quanto mais fundo, mais firme, melhor". **Aqui é o contrário** —
e a razão está no mecanismo descrito na literatura.

**O que a literatura estabelece [L]:** o tipo predominante de escorregamento
natural na Serra do Mar, por distribuição e frequência, é o **translacional
raso**. Esses movimentos **mobilizam quase exclusivamente o horizonte superior
do solo superficial**, e a ruptura ocorre predominantemente no **contato entre
solo residual e solo saprolítico**, onde há descontinuidade pedológica marcada.
A mobilização de material saprolítico ocorre sobretudo na "raiz" — a zona de
início —, onde a profundidade atingida é maior que no corpo do escorregamento
([SIGESP, 2023](https://www.sigesp.org.br/images/SIGESP/conteudo/documentos/Artigos/2023/OS%20DESLIZAMENTOS%20TRANSLACIONAIS%20RASOS%20NATURAIS%20NAS%20ENCOSTAS%20DA%20SERRA%20DO%20MAR%20%20DIAGNSTICO%20DO%20FENMENO.pdf)).

O mecanismo: a ruptura se dá por **poropressão positiva**, com fluxo de água
paralelo à encosta sobre um horizonte menos permeável
([SINAGEO](https://sinageo.org.br/2012/trabalhos/1/1-477-58.html)) **[L]**. Como
referência operacional, o **CEMADEN monitora umidade do solo até 3,0 m de
profundidade** **[G]**.

**Consequência para a instrumentação [E]:** se a estaca for cravada **abaixo** da
superfície de ruptura, fica ancorada no material que não se move — e o sensor
deixa de registrar o deslocamento justamente quando ele ocorre. A estaca precisa
estar **dentro do horizonte superficial mobilizável**.

Profundidade cravada de **0,8 a 1,2 m** é o ponto de partida adotado: fica no
horizonte superficial descrito pela literatura, dá estabilidade ao tubo curto e
coincide com a faixa validada em campo pelo SitkaNet, que crava até ~0,95 m ou
até a interface solo-rocha **[L]**.

> **Esta é decisão geotécnica, não de instrumentação.** A profundidade correta
> depende do perfil pedológico do talude — em particular da posição do contato
> solo residual/saprolítico — e **deve ser definida por engenheiro geotécnico ou
> geólogo habilitado, com ART, para cada sítio**
> (RESPONSABILIDADE_TECNICA.md §5). O valor acima é ponto de partida de projeto
> ancorado em literatura, **não prescrição de engenharia**.

Corolário de leitura: com essa geometria, o nó mede **rotação do bloco
superficial**. Movimento profundo exige inclinômetro em furo revestido, que é
outra ordem de custo — reservado a taludes críticos já classificados.

---

## 4. Como ancorar: ponteira cravada, sem concreto

O método validado em campo pelo [SitkaNet](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/)
— rede de monitoramento de deslizamentos no Alasca — é o mais adequado:

> A ponteira (*well point*) é cravada no solo com **capacete de cravação e
> marreta**, até ~0,95 m ou até encontrar a interface solo-rocha. O invólucro é
> preso ao tubo por abraçadeiras tipo U. Instalação completa em **menos de um
> dia, com duas pessoas** — metade do tempo e do pessoal dos sistemas
> tradicionais.

Por que cravar e não concretar:

- **Sem cura.** Instala e mede no mesmo dia; concreto exige retorno.
- **Sem água nem betoneira** em local de acesso difícil — que é a regra em
  encosta.
- **Reversível.** O nó pode ser realocado se o ponto se mostrar ruim, o que é
  comum nas primeiras campanhas.
- **Acoplamento melhor ao solo superficial.** Bloco de concreto cria uma inércia
  própria e responde ao movimento de forma diferente do solo ao redor —
  exatamente o que não se quer num sensor de rotação.
- **Menor impacto**, relevante em área de preservação.

Complementos quando o solo for muito mole ou muito duro:

| Situação | Solução |
|---|---|
| Solo mole, estaca "afunda" | Ponteira mais longa (1,5 m) ou aleta soldada na base |
| Rocha/matacão raso | Reposicionar o ponto; cravar em matacão não mede o talude |
| Solo muito duro | Pré-furo com trado manual, cravando em seguida |
| Encosta muito íngreme | Estaca inclinada é aceitável: o que importa é a **variação** do ângulo, não o valor absoluto |

---

## 5. Material: tubo de aço galvanizado 1.1/2"

**Recomendação: tubo de aço carbono galvanizado a fogo, 1.1/2" (48,3 mm),
parede 3 mm, comprimento total 2,5 m** — cerca de 1 m cravado e 1,5 m livre.

| Critério | Avaliação |
|---|---|
| Deflexão a 1,5 m, Vk = 35,8 m/s (NBR 6123) | **0,07°** **[E]** |
| Custo | ~R$ 45/m → **~R$ 110 por nó** **[E]** — cotar (B-07) |
| Massa (2,5 m) | ~8,4 kg — carregável por uma pessoa em trilha |
| Disponibilidade | Qualquer depósito de construção ou serralheria |
| Durabilidade | Galvanização a fogo: décadas em exposição externa |
| Usinagem | Corta e fura com ferramenta comum |

Descartados e por quê:

- **PVC** — 3,81° de deflexão a 1,5 m, degrada com UV. Só como conduíte interno.
- **Eletroduto 3/4"** — 0,27° a 1,5 m. Foi cogitado pelo custo, mas sai da
  recomendação após a correção da velocidade normativa (REFERENCIAS.md R1).
- **Alumínio** — leve, mas 3× menos rígido que o aço e mais caro.
- **Fibra de vidro** — não conduz (bom para raio), mas custo e disponibilidade
  ruins no Brasil. Reavaliar se SPDA se tornar problema crítico.
- **Bambu tratado** — custo quase nulo, mas variabilidade mecânica e durabilidade
  incompatíveis com instrumentação que precisa de repetibilidade por anos.

---

## 6. A haste de 4 m é necessária em encosta? Quase nunca

Esta era a dúvida central, e a geometria responde.

**Derivação.** Num perfil de rampa uniforme entre sensor e gateway, a folga da
linha de visada sobre a vegetação, no meio do vão, vale:

```
folga = (h_sensor + h_gateway) / 2  −  h_vegetação
```

O desnível do terreno **se cancela**. O que sobra é a **média das alturas de
antena**. Requisito: folga ≥ 60% do raio da primeira zona de Fresnel.

**Altura de antena necessária no sensor**, para vegetação de 3 m:

| Vão | gw 6 m | gw 10 m | gw 15 m | gw 20 m | gw 30 m |
|---|---|---|---|---|---|
| 200 m | 4,9 m | 0,9 m | — | — | — |
| 500 m | 7,7 m | 3,7 m | — | — | — |
| 1.000 m | 10,8 m | 6,8 m | 1,8 m | — | — |
| 2.000 m | 15,3 m | 11,3 m | 6,3 m | 1,3 m | — |

"—" significa que a altura do gateway já resolve: **o sensor pode ficar baixo,
sem haste**.

**Conclusão direta:** com gateway a 15 m ou mais — poste, torre leve, laje ou
ponto alto do terreno — o sensor **não precisa de haste alta** em vãos de até
1 km. A haste de 4 m só se justifica quando o gateway é baixo, que é o cenário a
evitar de qualquer forma.

### E o aclive/declive, ajuda ou não?

Depende do **formato** do perfil, não da inclinação:

- **Rampa uniforme** — o desnível se cancela, como na derivação. Não ajuda nem
  atrapalha.
- **Perfil côncavo** (encosta que suaviza na base, forma de anfiteatro — comum na
  porção inferior de cicatrizes de deslizamento) — a linha reta passa **acima**
  do terreno. **Ajuda, e pode dispensar a haste.**
- **Perfil convexo** (crista, quebra de relevo entre os dois pontos) — a linha
  passa **abaixo** do terreno intermediário. **Atrapalha**, e nenhuma haste
  razoável resolve: é caso de mudar o ponto do gateway ou usar repetidor.

Por isso o perfil extraído do **MDE** é o que decide caso a caso, e não uma regra
única (PROPAGACAO.md §8).

---

## 7. Onde investir altura: no gateway, sempre

Como a folga depende da **média** das duas alturas, um metro no gateway vale
exatamente o mesmo que um metro no sensor. Mas o gateway é **um para muitos**:

| Rede | Efeito de +1 m no gateway |
|---|---|
| 10 nós | equivale a +1 m em cada um dos 10 sensores |
| 50 nós | equivale a +1 m em cada um dos 50 sensores |

**Regra de projeto: elevar o gateway até o limite estrutural e orçamentário
primeiro. Só depois considerar haste no sensor.** Isso reduz custo, reduz
manutenção em campo e tira estrutura alta de cima do talude instável — onde ela
é justamente mais problemática.

### Alternativa que dispensa altura no sensor

O SitkaNet usou **antena Yagi direcional de 9 dBi no hub**. Nove decibéis é o
mesmo ganho de uma haste de 4 m no sensor — porém **sem estrutura, sem vento e
sem captor de raio no nó de campo**.

O custo é a direcionalidade: exige que os nós estejam num setor definido. **É
exatamente o caso de uma encosta monitorada**, que ocupa um setor angular
estreito visto do gateway. Vale como padrão de projeto.

---

## 8. Lições de campo de quem já fez

Do SitkaNet e das referências de LEWS de baixo custo, o que muda decisões aqui:

**Falhas de transmissão correlacionaram com chuva intensa.** É a confirmação mais
importante: o enlace degrada exatamente durante o evento que o sistema existe
para monitorar. **Sustenta a margem de 20 dB** e reforça o buffer local com
retransmissão (RC-05, RC-06).

**O acelerômetro gerou múltiplos alarmes falsos e foi desativado.** Usaram limiar
de 3 G para detectar evento. Confirma o que já está em SENSORES.md: acelerômetro
como **detector de vibração** é fonte de falso positivo; como **inclinômetro**,
medindo deriva lenta com confirmação temporal, é outra coisa. Nosso desenho já
segue o segundo caminho (RC-09).

**Bateria durou 2–3 meses contra >6 previstos**, por temperatura. No nosso clima
o efeito é menor, mas a lição vale: **dimensionar autonomia pelo pior caso
térmico**, não pelo nominal do fabricante.

**Só 12 de 18 sensores de umidade deram dado confiável.** Redundância de marca e
profundidade não é luxo — é o que salva a campanha (RC-07).

**Alcance real: 2–2,5 km apenas com visada limpa**, limitado por topografia,
umidade do ar e densidade florestal. Coerente com o nosso modelo e com a
literatura de mata (PROPAGACAO.md §3).

**Custo:** ~US$ 940 por nó, contra US$ 8.000–10.000 das soluções tradicionais.
Nossa estrutura de ancoragem fica em **~R$ 200 por nó**, o que mantém o alvo de
custo agressivo.

---

## 9. Kit padrão de instalação

Materiais por nó:

| Item | Especificação | Custo aprox. |
|---|---|---|
| Tubo | Aço galv. a fogo 1.1/2", 3 mm, 2,5 m | R$ 110 |
| Ponteira | Bisel na base ou aleta soldada | R$ 20 |
| Abraçadeiras | Tipo U, 2 unidades | R$ 15 |
| Invólucro | Caixa IP67 com prensa-cabos | R$ 80–150 |
| Aterramento | Cabo de cobre + haste (NBR 5419) | R$ 60 |
| **Total estrutura** | | **~R$ 300** **[E]** |

Todos os valores acima são **estimativa de mercado sem cotação formal** — item
B-07 em REFERENCIAS.md. Não usar em proposta comercial antes de cotar.

Ferramenta compartilhada pela equipe: marreta, capacete de cravação (reutilizável),
trado manual, nível de bolha, trena, GPS.

### Procedimento

1. **Escolher o ponto** — geotécnico define o local; `tools/alcance.py` e o
   modelo do MDE indicam se o enlace fecha.
2. **Verificar o enlace antes de instalar** — levar o nó com o firmware de campo
   e confirmar veredito **APROVADO** na posição pretendida (ROTEIRO_CAMPO.md).
   Instalar primeiro e testar depois é retrabalho garantido.
3. **Cravar o tubo** com capacete e marreta, 0,8 a 1,2 m, até resistência firme.
4. **Conferir a prumada** — o valor absoluto não importa, mas registrar o ângulo
   inicial como referência de calibração.
5. **Fixar o invólucro** com as abraçadeiras, antena na vertical, apontada para
   cima.
6. **Aterrar** conforme NBR 5419.
7. **Registrar**: coordenada, altitude, ângulo inicial, foto do conjunto e do
   entorno, e o veredito de enlace medido.
8. **Confirmar o primeiro pacote** no gateway antes de deixar o local.

### O que padronizar e o que não

**Padronizar:** tubo, invólucro, altura livre de 1,5 m, procedimento de cravação,
ficha de registro.

**Não padronizar:** profundidade final e escolha do ponto. Dependem do perfil do
talude e são decisão de engenheiro geotécnico por sítio.

---

## 10. Pendências abertas deste projeto

| ID | Item |
|---|---|
| A-01 | Definir a fixação do sensor de inclinação **na base do tubo** — acoplamento rígido e repetível, sem folga |
| A-02 | Ensaiar cravação em solo real da região: profundidade alcançável e esforço |
| A-03 | Especificar SPDA proporcional — haste de 1,5 m em encosta exposta ainda é captor (C-07) |
| A-04 | Avaliar Yagi 9 dBi no gateway como padrão, medindo o ganho real |
| A-05 | Definir o mastro separado para os casos que exigirem antena acima de 1,5 m |

**Fontes:**
[SitkaNet: a low-cost, distributed sensor network for landslide monitoring](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/) ·
[IoT Geosensor Network for Cost-Effective Landslide Early Warning Systems](https://doi.org/10.3390/s21082609) ·
[Prototype of an IoT-Based Low-Cost Sensor Network for Hydrological Monitoring of Landslide-Prone Areas](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9964066/) ·
[Slope Inclinometers for Landslides — Geoengineer](https://www.geoengineer.org/education/instrumentation/slope-inclinometers) ·
[MEMS in-place inclinometers](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/)
