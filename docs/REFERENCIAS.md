# Política de proveniência e bibliografia

Este projeto produz informação usada para decidir sobre risco à vida, tem órgão
público como cliente e pode gerar propriedade intelectual. Nada aqui pode
depender de afirmação sem lastro.

Vale também como salvaguarda de habilitação: a camada de geologia, geotecnia e
geografia **não** é assinada pela equipe do projeto
([RESPONSABILIDADE_TECNICA.md](RESPONSABILIDADE_TECNICA.md)). Ela entra
exclusivamente como **referência a estudo publicado, norma ou fonte
institucional** — e por isso precisa estar sempre rastreável até a origem.

---

## 1. Regra

**Todo número, limiar ou afirmação técnica na documentação precisa cair em uma
destas categorias, e estar marcado como tal:**

| Marca | Categoria | Exigência |
|---|---|---|
| **[M]** | **Medido** — ensaio próprio | Dado bruto versionado no repositório, com método descrito |
| **[N]** | **Norma** — ABNT, Anatel, ITU, INMETRO | Número e ano da norma, artigo ou tabela quando aplicável |
| **[L]** | **Literatura** — publicação revisada por pares, tese, relatório institucional | Autor, ano, veículo e link ou DOI |
| **[G]** | **Fonte governamental** — CEMADEN, INPE, IPT, IBGE, INMET | Órgão e link |
| **[E]** | **Estimativa própria** — cálculo derivado de [M], [N], [L] ou [G] | Método explícito e insumos identificados |
| **[?]** | **Sem referência** | **Não pode permanecer.** Ou se acha a fonte, ou se remove |

**Regra dura:** afirmação de domínio geológico, geotécnico ou geográfico **nunca**
recebe [E]. Só pode ser [L], [N] ou [G]. Se não houver fonte, a afirmação sai da
documentação.

**Regra de escrita:** onde o texto disser "tipicamente", "da ordem de" ou
"costuma ser", tem que haver fonte ao lado. Sem ela, é opinião com aparência de
dado — o pior tipo de conteúdo num documento que pode ir a juízo ou a exame de
patente.

---

## 2. Por que isso importa para patente

Documentação rigorosa serve a três funções simultâneas:

1. **Estado da técnica.** Para sustentar novidade e atividade inventiva é
   preciso demonstrar o que já existia. A bibliografia é a base dessa
   demonstração.
2. **Data e autoria.** O histórico do repositório registra quando cada
   contribuição apareceu e por quem — com decisões justificadas, não só código.
3. **Suficiência descritiva.** Pedido de patente precisa descrever a invenção de
   forma que um técnico no assunto a reproduza. É exatamente o que esta
   documentação faz.

**Consequência prática:** separar com clareza **o que é nosso** (medições,
método, arquitetura, decisões de projeto) do **que é estado da técnica**
(literatura, normas). Essa fronteira é a primeira coisa examinada.

**[VERIFICAR]** com agente de propriedade industrial (INPI) antes de qualquer
divulgação pública ampla — publicar antes de depositar pode comprometer a
novidade. O repositório é privado, o que preserva a opção.

---

## 3. Registro de revisões — correções feitas por esta política

Auditoria de 31/07/2026, aplicando a regra retroativamente.

### R1 — Velocidade do vento estava fora da norma **[corrigido]**

`tools/haste.py` e `ANCORAGEM.md` usavam **20 m/s** como referência de vento,
valor **arbitrário e não normativo**, escolhido sem fonte.

A [ABNT NBR 6123](https://www.abntcatalogo.com.br/) define a velocidade básica
V₀ como a média sobre 3 s excedida uma vez a cada 50 anos, a 10 m em terreno
aberto, com isopletas de **30 a 48 m/s** no território nacional.

Aplicando V₀ = 40 m/s (estimativa para o litoral paulista, **[CONFIRMAR]** na
isopleta), categoria III e S₁ = 1,15 para encosta, a velocidade característica a
1,5 m é de **35,8 m/s** — quase o dobro do valor antes usado, e a força varia com
o quadrado.

**Efeito:** as deflexões publicadas antes desta revisão estavam **subestimadas
em cerca de 3×**. Números corrigidos em ANCORAGEM.md §1.

**A conclusão qualitativa não mudou — ficou mais forte.** Haste alta com
inclinômetro no topo já era inviável a 20 m/s; com a velocidade normativa é
inviável por margem muito maior. E o eletroduto 3/4", antes aceitável a 1,5 m
(0,08°), passa a 0,27° e sai da recomendação.

### R2 — Limiar de creep de "0,1 a 0,5°" não tinha fonte **[corrigido]**

O texto afirmava que o movimento a detectar seria "da ordem de 0,1 a 0,5°",
número sem origem identificável.

A literatura consultada é explícita em que **limiares de alerta por inclinação
são específicos do sítio**, definidos a partir da geologia e das condições
locais, não universais
([Natural Hazards, 2022](https://link.springer.com/article/10.1007/s11069-022-05383-y)).

**Correção:** a afirmação foi substituída. O projeto **não define limiar** — isso
é atribuição de engenheiro geotécnico por sítio (RESPONSABILIDADE_TECNICA.md §5).
O que o projeto especifica é **capacidade de medição**: resolução do sensor e
ruído estrutural suficientemente baixos para que qualquer limiar plausível seja
detectável.

Referência de capacidade: inclinômetros MEMS de instrumentação apresentam
resolução da ordem de **0,0025°**
([ESS Earth Sciences](https://www.essearth.com/product/geostring-in-place-mems-inclinometer/),
[Sisgeo](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/)).

### R3 — Profundidade de ruptura precisava de fonte **[corrigido]**

A afirmação de que deslizamentos rasos rompem "entre 1 e 3 m" era plausível, mas
não estava referenciada — e é afirmação de domínio geotécnico, que pela regra
acima não admite [E].

Substituída por descrição referenciada do mecanismo, em ANCORAGEM.md §3.

### R4 — Custos de materiais são estimativa, e passam a ser marcados **[corrigido]**

Valores em reais de tubos, sensores e caixas eram estimativas de mercado sem
cotação. Passam a ser marcados **[E]**, com a ressalva de que precisam de cotação
formal antes de compor proposta comercial.

### R5 — Tabela I e regra de ganho de antena, antes `[VERIFICAR]` **[resolvido]**

CONFORMIDADE.md §1.1 marcava como `[VERIFICAR]` os valores numéricos da
Tabela I do Ato 14448/2017 e a relação entre ganho de antena e potência de
transmissão. O texto integral do Ato foi obtido em 31/07/2026 e ambos os
pontos foram resolvidos com o valor primário da norma: Tabela I confirma
50 mV/m (fundamental) a 3 m para 915–928 MHz; item 10.5 estabelece **6 dBi**
como ganho de antena de referência, com redução de potência dB-a-dB acima
disso — o que implica EIRP de transmissão constante além de 6 dBi,
independente do ganho usado. Verificação laboratorial formal para homologação
continua pendente, mas o dimensionamento de engenharia deixa de ser suposição.

### R6 — Bobina identificada como antena WiFi/BT, não LoRa **[novo]**

Fotos reais de uma das placas mostraram uma bobina de cobre soldada perto do
PRG. Identificada como a antena de 2,4 GHz do WiFi/Bluetooth do ESP32, com
base na documentação oficial da Heltec para a mesma família de placas e no
dimensionamento físico incompatível com 915 MHz. Sem relação com o rádio LoRa
— ver HARDWARE.md. Marcada **[E]** por não haver datasheet da V2 com o
componente explicitamente rotulado (só V3/V4, mesmo fabricante e convenção).

---

## 4. Bibliografia por área

### 4.1 Deslizamentos e mecanismo de ruptura

- **Tatizana, C. et al. (1987)** — curva de correlação entre chuva acumulada em
  24 h e 72 h e ocorrência de escorregamentos na Serra do Mar. É a referência
  fundacional brasileira do tema e base de sistemas operacionais de alerta.
  [contexto e discussão](https://www.researchgate.net/profile/Rodolfo-Mendes-2/publication/349413120_Proposicao_de_limiares_criticos_ambientais_para_uso_em_sistema_de_alertas_de_deslizamentos/links/602ed1b34585158939b4703a/Proposicao-de-limiares-criticos-ambientais-para-uso-em-sistema-de-alertas-de-deslizamentos.pdf) · **[L]**
- **Deslizamentos translacionais rasos na Serra do Mar — diagnóstico do
  fenômeno.** Mobilizam quase exclusivamente o horizonte superior do solo
  superficial; a ruptura ocorre predominantemente no **contato entre solo
  residual e solo saprolítico**, e a mobilização de saprólito ocorre sobretudo
  na "raiz" (zona de início) do escorregamento, onde a profundidade é maior que
  no corpo.
  [SIGESP, 2023](https://www.sigesp.org.br/images/SIGESP/conteudo/documentos/Artigos/2023/OS%20DESLIZAMENTOS%20TRANSLACIONAIS%20RASOS%20NATURAIS%20NAS%20ENCOSTAS%20DA%20SERRA%20DO%20MAR%20%20DIAGNSTICO%20DO%20FENMENO.pdf) · **[L]**
- **Propriedades físicas do solo e estabilidade de encostas na Serra do Mar.**
  Textura, estrutura e porosidade afetam a permeabilidade e o mecanismo de
  ruptura.
  [Revista do Depto. de Geografia, USP](https://revistas.usp.br/rdg/article/view/188406) · **[L]**
- **Condutividade hidráulica saturada e escorregamentos rasos na Serra do Mar.**
  Ruptura por poropressão positiva com fluxo paralelo à encosta sobre horizonte
  menos permeável.
  [SINAGEO](https://sinageo.org.br/2012/trabalhos/1/1-477-58.html) · **[L]**

### 4.2 Monitoramento e limiares operacionais

- **CEMADEN** — monitoramento baseado em previsão meteorológica, **limiares de
  chuva acumulada em 24 h e 72 h por município** e vistorias de campo. Umidade do
  solo monitorada **até 3,0 m de profundidade**.
  [Cemaden/MCTI](https://www.gov.br/cemaden/pt-br) · **[G]**
- **Limiares de alerta por inclinação são específicos do sítio** — não há valor
  universal; dependem de geologia e condições locais.
  [Natural Hazards, Springer, 2022](https://link.springer.com/article/10.1007/s11069-022-05383-y) · **[L]**
- **SitkaNet** — rede distribuída de baixo custo para monitoramento de
  deslizamentos. Ancoragem por ponteira cravada a ~0,95 m, custo ~US$ 940/nó,
  instalação em menos de um dia com duas pessoas, alcance LoRa de 2–2,5 km só
  com visada. Falhas de transmissão correlacionadas com chuva intensa;
  acelerômetro por limiar gerou falsos alarmes e foi desativado.
  [Sensors, 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/) · **[L]**
- **Rede geossensorial IoT para LEWS de baixo custo.**
  [Sensors, 2021](https://doi.org/10.3390/s21082609) · **[L]**
- **Inclinômetros MEMS in-place** — resolução da ordem de 0,0025°.
  [Sisgeo](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/) ·
  [ESS](https://www.essearth.com/product/geostring-in-place-mems-inclinometer/) · **[L]**

### 4.3 Propagação LoRa

- **Comparação experimental e modelagem empírica de perda de percurso em visada
  e em floresta a 923 MHz.** Expoente n = 2,31 em visada e **n = 3,22 em
  floresta tropical**.
  [Sensors, 2026](https://doi.org/10.3390/s26103192) · **[L]**
- **Avaliação de desempenho de LoRa 920 MHz em área florestada montanhosa.**
  RSSI médio −100 dBm, alcance máximo ~250 m; com dossel acima de ~23 m o sinal
  passa a depender de difração e o RSSI cai para −120 a −127 dBm.
  [Electronics, 2021](https://doi.org/10.3390/electronics10040502) · **[L]**
- **Revisão crítica dos modelos de propagação empregados em sistemas LoRa.**
  [Sensors, 2024](https://www.mdpi.com/1424-8220/24/12/3877) · **[L]**
- **Modelo de perda multiparede a 433 MHz caracterizando influência de
  folhagem.** n = 2,34 em visada, 125–250 kHz.
  [Sensors, 2022](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9317254/) · **[L]**
- **Propagação de enlaces LoRa P2P para IoT.**
  [Sensors, 2021](https://www.mdpi.com/1424-8220/21/20/6872) · **[L]**

### 4.4 Normas técnicas

- **ABNT NBR 6123** — Forças devidas ao vento em edificações. Velocidade básica
  V₀, isopletas de 30 a 48 m/s, fatores S₁, S₂ e S₃. · **[N]**
- **ABNT NBR 11682** — Estabilidade de encostas. · **[N]**
- **ABNT NBR 5419** — Proteção contra descargas atmosféricas. · **[N]**
- **ABNT NBR 5410** — Instalações elétricas de baixa tensão. · **[N]**
- **NR-35** — Trabalho em altura · **NR-10** — Segurança em eletricidade. · **[N]**

### 4.5 Telecomunicações e regulação

- [Resolução Anatel nº 680/2017](https://informacoes.anatel.gov.br/legislacao/resolucoes/2017/936resolucao-680) — radiação restrita. · **[N]**
- [Ato Anatel nº 14448/2017](https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2017/1139-) — requisitos técnicos.
  **Texto integral obtido em 31/07/2026.** Tabela I (915–928 MHz: 50 mV/m
  fundamental, 500 µV/m harmônicos a 3 m) e item 10.5 (antena de referência
  6 dBi para equipamentos de espalhamento espectral, com redução de potência
  dB-a-dB acima disso) — base do CONFORMIDADE.md §1.1.1. · **[N]**
- [Resolução Anatel nº 715/2019](https://informacoes.anatel.gov.br/legislacao/resolucoes/2019/1350-resolucao-715) — avaliação de conformidade e homologação. · **[N]**
- **Semtech SX1276 datasheet** — sensibilidade por spreading factor. **[?]**
  Ainda não citado formalmente; os valores em uso vêm de tabela do fabricante e
  precisam do link do documento oficial. · **[?]**
- **Heltec — documentação oficial WiFi LoRa 32.**
  [Pinout V2 (PDF)](https://resource.heltec.cn/download/WiFi_LoRa_32/WIFI_LoRa_32_V2.pdf) ·
  [docs.heltec.org (V3/V4)](https://docs.heltec.org/en/node/esp32/wifi_lora_32/index.html) —
  usado para identificar a bobina de antena WiFi/BT (HARDWARE.md). · **[L]**

### 4.6 Legislação e habilitação

- [Lei nº 12.608/2012](https://www.planalto.gov.br/ccivil_03/_ato2011-2014/2012/lei/l12608.htm) — PNPDEC. · **[N]**
- [Lei nº 13.709/2018](https://www.planalto.gov.br/ccivil_03/_ato2015-2018/2018/lei/l13709.htm) — LGPD. · **[N]**
- [Lei nº 14.133/2021](https://www.planalto.gov.br/ccivil_03/_ato2019-2022/2021/lei/l14133.htm) — Licitações. · **[N]**
- [Decreto nº 90.922/1985](https://www2.camara.leg.br/legin/fed/decret/1980-1987/decreto-90922-6-fevereiro-1985-441525-publicacaooriginal-1-pe.html) — técnicos industriais. · **[N]**
- [Resolução CFT nº 120/2020](https://www.crtsp.gov.br/wp-content/uploads/2020/12/RESOLUCAO-no-120.2020-Define-as-Atribuicoes-do-Tecnico-em-Mecatronica.pdf) — atribuições do Técnico em Mecatrônica. · **[N]**
- [Lei nº 6.664/1979](https://planalto.gov.br/ccivil_03/leis/1970-1979/L6664.htm) — profissão de Geógrafo. · **[N]**

---

## 5. O que ainda falta referenciar

| ID | Item | Situação |
|---|---|---|
| B-01 | Datasheet oficial Semtech SX1276 — sensibilidade por SF | **[?]** citar documento |
| B-02 | Isopleta da NBR 6123 para o litoral paulista — V₀ exato | **[CONFIRMAR]** |
| B-03 | Atenuação por vegetação — buscar recomendação ITU-R P.833 | **[?]** |
| B-04 | Atenuação por chuva em 900 MHz — ITU-R P.838 | **[?]** |
| B-05 | Coeficiente de arrasto de cilindro (Cd = 1,2) — citar norma ou referência | **[?]** |
| B-06 | Deriva térmica de acelerômetros MEMS — citar datasheet ou publicação | **[?]** |
| B-07 | Custos de materiais — substituir estimativa por cotação formal | **[E]** → cotar |
| B-08 | Desastre de Caraguatatuba de 1967 — citar fonte ao mencionar | **[?]** |

Itens **[?]** não podem ir para proposta comercial nem para pedido de patente
sem resolução.
