# Conformidade normativa

O Sentinela é destinado a uso por órgãos públicos — prefeituras, defesa civil,
possivelmente institutos, universidades e forças armadas. Isso eleva a barreira:
o que em um protótipo de bancada seria detalhe, em produto vendido ao poder
público é requisito de habilitação.

> **Este documento não é parecer jurídico.** Ele mapeia o que se aplica e o que
> precisa ser confirmado por profissional habilitado (engenheiro com ART,
> Organismo de Certificação Designado, assessoria jurídica). Os itens marcados
> **[VERIFICAR]** são exatamente os que não devem ser assumidos como resolvidos.

---

## 1. Telecomunicações — o ponto mais crítico

> **Controle regulatório — consulta de 02/08/2026.** A Resolução 715/2019
> recebeu alterações pela Resolução 780/2025, e a própria página oficial
> registra suspensão parcial de efeitos pelo Acórdão 58/2026. As referências
> históricas abaixo continuam úteis para o protótipo, mas o enquadramento,
> procedimento, marcação e atos técnicos do produto final devem ser obtidos da
> versão consolidada da Anatel e confirmados por OCD antes do layout final.
> Não congelar o dossiê com base apenas na redação de 2019/2017.

### 1.1 Faixa de operação

O equipamento opera como **radiação restrita** sob a
[Resolução Anatel nº 680/2017](https://informacoes.anatel.gov.br/legislacao/resolucoes/2017/936resolucao-680),
com requisitos técnicos no
[Ato nº 14448/2017](https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2017/1139-).

Faixas permitidas na região de 900 MHz: **902–907,5 MHz e 915–928 MHz**.
A janela **907,5–915 MHz não é permitida** no Brasil.

O regulamento estabelece limites de **intensidade de campo medida a 3 m**, não
de potência no conector. A emissão de pico não pode exceder o valor médio
especificado em mais de 20 dB, e emissões fora da faixa devem ser atenuadas em
pelo menos 50 dB do nível da fundamental.

**Decisão do projeto:** operação em 915–928 MHz. P2P em 916,8 MHz; LoRaWAN em
AU915 sub-banda 2 (canais 8–15, 916,8–918,2 MHz). Ver ADR-003.

**Tabela I do Ato nº 14.448/2017 — resolvido [N].** Texto integral obtido em
31/07/2026. Para 915–928 MHz: intensidade de campo da fundamental **50 mV/m**
a 3 m; harmônicos **500 µV/m** a 3 m. Mesmos valores para 902–907,5 MHz.

Fecha a maior parte do item C-02. O que permanece pendente é só a
**verificação laboratorial formal** — a norma exige medição por OCD para
homologar, cálculo não substitui o ensaio — mas o dimensionamento de engenharia
já pode ser feito com os números reais, não mais por suposição.

### 1.1.1 Ganho de antena — a regra que decide quantos dBi usar

Achado direto do texto do Ato, item 10 (**Equipamentos Utilizando Tecnologia de
Espalhamento Espectral ou outras Tecnologias de Modulação Digital**) — LoRa
(CSS) se enquadra aqui pela própria definição de espalhamento espectral do
documento (item 3.1.9) **[N]**:

> *"Equipamentos [...] que façam uso de antenas de transmissão com ganho
> direcional superior a 6 dBi[,] devem ter a potência de pico máxima na saída
> do transmissor reduzida [...] pela quantidade em dB que o ganho direcional da
> antena exceder a 6 dBi."* — item 10.5

Ou seja: **6 dBi é o ganho de referência**. Até esse valor, potência plena, sem
redução. Acima, a potência conduzida tem que cair na mesma proporção em dB que
o ganho excede 6 dBi.

**Consequência matemática, e é o que resolve a pergunta de quantos dBi
comprar:** como a redução exigida cancela exatamente o ganho extra, o **EIRP
máximo legal fica constante em `potência_conduzida + 6 dBi`, qualquer que seja
o ganho da antena acima de 6 dBi.** Antena de 9, 12 ou 15 dBi não aumenta o
alcance de transmissão além do que uma antena de 6 dBi já entrega na potência
máxima — a diferença tem que ser devolvida em potência.

| Configuração | Conduzido | Ganho | Redução exigida | **EIRP legal** |
|---|---|---|---|---|
| Atual (2 dBi, sem redução) | 17 dBm | 2 dBi | nenhuma | **19 dBm** (~79 mW) |
| **Alvo — 6 dBi, sem redução** | 17 dBm | 6 dBi | nenhuma | **23 dBm** (~200 mW) |
| Hipotético 9 dBi | 14 dBm (17−3) | 9 dBi | 3 dB | 23 dBm — **igual ao de 6 dBi** |
| Máximo do chip **[N]** | +20 dBm | 6 dBi | nenhuma | ~26 dBm — ainda dentro do teto de 30 dBm (item 10.3.2) |

**Resposta prática:** subir de 2 para 6 dBi dá **+4 dB de EIRP de graça**, só
trocando a antena, sem tocar no firmware — ganho equivalente a mais que dobrar
a potência de transmissão. **Acima de 6 dBi não há mais ganho de alcance em
transmissão** — o que sobra é ganho de **recepção**, porque a regra do EIRP
governa apenas o que se transmite, não a sensibilidade de quem escuta. Antena
de 9 dBi ouve 3 dB melhor que uma de 6 dBi, com zero penalidade — só não
transmite mais longe.

**Isso orienta onde investir cada dBi:**

- **Atalaia (transmite e recebe, cobertura em várias direções):** manter **até
  6 dBi**, preferencialmente omnidirecional. Acima disso não ganha alcance de
  uplink e ainda exige reduzir potência.
- **Farol/gateway (ouve muitas Atalaias, direção conhecida):** antena acima de
  6 dBi **vale a pena para a recepção**, mesmo sem ganho na transmissão — foi
  exatamente o que o SitkaNet fez com a Yagi de 9 dBi no hub
  (ANCORAGEM.md §7).
- **Não há limite físico do conector** — o SMA/u.FL aceita qualquer antena de
  50 Ω. O limite é inteiramente regulatório, não de hardware.

**[?]** Confirmar com o OCD, no processo de homologação (C-01), a
classificação exata do produto sob o item 10 e a leitura de "ganho direcional"
para antena omnidirecional simples — a norma fala em "ganho direcional", termo
que tecnicamente se refere a diretividade e pode ter leitura específica do
examinador.

### 1.2 Homologação — impacto direto no plano de produto

Este é o achado de maior consequência para a proposta comercial.

**A homologação Anatel é condição obrigatória para comercialização e uso** de
produtos de telecomunicações no país, conforme a Lei nº 9.472/1997 (Lei Geral
de Telecomunicações) e a
[Resolução nº 715/2019](https://informacoes.anatel.gov.br/legislacao/resolucoes/2019/1350-resolucao-715).
O produto precisa passar por avaliação de conformidade, com Certificado de
Conformidade Técnica emitido por **Organismo de Certificação Designado (OCD)** e
registro no sistema Mosaico da Anatel.

Consequências práticas:

- Protótipo em bancada e piloto de pesquisa: sem problema.
- **Vender o dispositivo a uma prefeitura: exige homologação.** Não é etapa
  opcional nem contornável por se tratar de órgão público — ao contrário, a
  contratação pública tende a exigir a comprovação.
- Prazo e custo de homologação precisam entrar no cronograma e no preço. É
  processo de meses, não de semanas.

**Mitigação que orienta a escolha de hardware:** partir de um **módulo de rádio
já homologado** reduz substancialmente o escopo de ensaios. Isso reforça a
escolha do RAK3172 (ADR-004) sobre soluções montadas do zero — mas atenção,
**módulo homologado não dispensa automaticamente a homologação do produto
final**.

**[VERIFICAR]** Com um OCD: (a) qual categoria de produto se aplica;
(b) o que exatamente é aproveitado de um módulo já homologado; (c) custo e
prazo. Esta é a primeira consulta técnica externa que o projeto deve fazer, e
deve acontecer **antes** da fase 4.

---

## 2. Proteção e Defesa Civil

**Lei nº 12.608/2012** institui a Política Nacional de Proteção e Defesa Civil
(PNPDEC) e o SINPDEC, atribuindo aos municípios competências de monitoramento
de riscos e alerta à população. É a base legal que dá função ao produto — e
também o que define quem é a autoridade do alerta.

Implicação de projeto, já refletida em RC-00: o sistema **apoia** a decisão do
órgão de defesa civil. A autoridade do alerta à população é do poder público.
Um produto que se apresentasse como acionador autônomo de evacuação assumiria
responsabilidade que não lhe cabe.

**[VERIFICAR]** Integração com o **S2ID** (Sistema Integrado de Informações
sobre Desastres) e com os protocolos do CEMADEN — tanto para consumir alertas
quanto para eventual envio de dados.

---

## 3. Geotecnia e instrumentação

**ABNT NBR 11682 — Estabilidade de encostas.** Norma de referência para
estabilidade de taludes, incluindo diretrizes de instrumentação e monitoramento.
Deve orientar onde e como instrumentar, e o laudo que acompanha a instalação.

Ponto que não é negociável: **a definição dos pontos de instrumentação e a
interpretação geotécnica exigem profissional habilitado, com ART.** O Sentinela
fornece o dado; a leitura geotécnica é responsabilidade de engenheiro
geotécnico. Isso protege o projeto e é o que torna o produto defensável.

### 3.1 Inclinometria — arquitetura corrigida pela ADR-010

A [ISO 18674-3:2017](https://www.iso.org/standard/69207.html), com a
[Emenda 1:2020](https://www.iso.org/standard/78218.html), trata da medição de
deslocamentos transversais ao longo de uma linha por inclinômetros. O escopo
inclui taludes e identificação/monitoração de planos ativos de cisalhamento. As
regras gerais estão na
[ISO 18674-1:2015](https://www.iso.org/standard/63168.html).

**Consequência:** a barra superficial com um único MEMS não atende ao objeto da
norma. O produto-alvo passa a ter cadeia IPI biaxial em casing instalado em
furo; a unidade Sentinela adquire e transmite o perfil. Ver a matriz completa,
hardware, FAT/SAT e RFI em
[INSTRUMENTACAO_GEOTECNICA_ISO.md](INSTRUMENTACAO_GEOTECNICA_ISO.md).

O primeiro produto deve integrar instrumento comercial com documentação e
calibração verificáveis. ADXL355/SCL3300 permanecem P&D auxiliar. Nenhuma
alegação `CONFORME ISO 18674-3` é permitida antes de:

1. adquirir o texto integral da norma e sua emenda;
2. produzir matriz cláusula → requisito → ensaio → evidência;
3. validar instrumento, casing, instalação, referência e redução de dados;
4. obter avaliação/certificados externos dentro do escopo aplicável;
5. ter projeto geotécnico e ART do sítio.

### 3.2 Metrologia

A [ISO/IEC 17025:2017](https://www.iso.org/standard/66912.html) estabelece
competência de laboratórios de ensaio e calibração. No Brasil, a
[RBC/Inmetro](https://www.gov.br/inmetro/pt-br/centrais-de-conteudo/sistemas/rbc)
lista laboratórios acreditados. A acreditação é do laboratório **e de seu
escopo**; não certifica automaticamente o sensor.

Cada segmento IPI precisa de identificação e certificado de calibração com
incerteza/rastreabilidade. O escopo do laboratório deve cobrir efetivamente a
grandeza e faixa contratadas. Certificado de componente fora do escopo não
valida a cadeia montada.

### 3.3 Produto eletrônico

Normas candidatas, sujeitas à definição de aplicabilidade pelo laboratório:

| Referência | Objeto | Uso previsto |
|---|---|---|
| IEC 61326-1:2020 | emissões e imunidade EMC de equipamento de medição/controle | ensaio da DAQ completa |
| IEC 61010-1:2010+A1:2016 | segurança elétrica de medição/controle | análise e ensaio conforme classificação final |
| IEC 60529 | código IP | caixa montada com tampa, respiro, conectores e prensa-cabos |
| IEC 60068-2-6 / -2-27 | vibração e choque | transporte, instalação e operação |
| IEC 60068-2-14 / -2-78 | temperatura e calor úmido | ambiente externo costeiro, com severidade definida pelo perfil real |
| IEC 62133-2 | segurança de bateria de lítio portátil | confirmar aplicabilidade ao pack final |
| ONU 38.3 | transporte de bateria de lítio | relatório/resumo do tipo de bateria transportado |

Não se escolhem severidades ambientais por conveniência. Elas derivam do
perfil de uso, transporte, armazenamento e instalação e ficam congeladas antes
do ensaio.

### 3.4 Cibersegurança e qualidade

- IEC 62443-4-1 é o alvo de processo para requisitos, projeto seguro,
  verificação, gestão de vulnerabilidades, atualizações e fim de vida;
- IEC 62443-4-2 só entra como alvo de componente depois que o órgão/arquitetura
  definir o nível de capacidade de segurança pretendido;
- ISO 9001 é certificação do sistema de gestão da organização, não do sensor e
  não substitui ensaio do produto. A edição 2015 está em revisão; confirmar a
  edição vigente quando o processo de certificação começar.
- [ISO/IEC 27001:2022](https://www.iso.org/standard/27001) é um sistema de
  gestão de segurança da informação da organização; complementa, mas não
  substitui, os requisitos de produto da IEC 62443.
- [ISO 22320:2018](https://www.iso.org/standard/67851.html) pode orientar
  papéis, responsabilidades e cooperação na gestão do incidente. A
  [ISO 22324:2022](https://www.iso.org/standard/84559.html) orienta o uso de
  cores em alertas. Ambas dependem do protocolo do órgão e não autorizam o
  projeto a inventar severidades ou comandos.
- A série [IEC 61508](https://webstore.iec.ch/en/publication/22273) só entra no
  escopo se uma futura versão executar função elétrica/eletrônica relacionada
  à segurança. O posicionamento atual é apoio à decisão; não declarar SIL nem
  conformidade funcional por analogia.

---

## 4. Instalação em campo

- **ABNT NBR 5419** — proteção contra descargas atmosféricas. Sensor em encosta,
  com mastro e antena, em região de tempestade, é alvo. Aterramento e proteção
  contra surto são requisito de projeto, não acessório.
- **ABNT NBR 5410** — instalações elétricas de baixa tensão, onde aplicável.
- **NR-35 (trabalho em altura)** e **NR-10 (segurança em eletricidade)** —
  aplicáveis à equipe de instalação e manutenção em talude.
- Licenciamento e autorização de acesso ao local de instalação, especialmente em
  área de preservação ou propriedade privada. **[VERIFICAR]** caso a caso.

---

## 5. Dados e software

**LGPD (Lei nº 13.709/2018).** O sistema em si mede grandezas físicas, que não
são dados pessoais. Mas o cruzamento previsto na fase 3 — população exposta,
cadastro de edificações — **envolve dados pessoais**. Requer base legal
adequada, minimização e controle de acesso. É provável que se enquadre em
execução de políticas públicas, mas isso precisa de análise formal.

**[VERIFICAR]** Com a assessoria jurídica: base legal, necessidade de DPIA, e
papel de controlador/operador entre a empresa e o município.

**INDE — Infraestrutura Nacional de Dados Espaciais** (Decreto nº 6.666/2008) e
o Perfil MGB de metadados. Dado geoespacial produzido para o poder público deve
seguir os padrões de metadados brasileiros para ser interoperável e reutilizável.

**Padrões OGC** — WMS, WFS e, para telemetria, **SensorThings API**. Adotar
padrão aberto em vez de formato proprietário é o que permite integração com
plataformas existentes, incluindo o TerraMA² do INPE.

**Acessibilidade** — sistemas de governo devem seguir o **eMAG/WCAG**.
Aplicável ao painel, se ele for exposto a usuário do poder público.

---

## 6. Contratação pública

**Lei nº 14.133/2021** rege as licitações. Dois efeitos sobre a engenharia:

1. **Especificação sem direcionamento.** Descrever o produto por desempenho e
   norma, não por marca, facilita a contratação — e o uso de padrões abertos
   (OGC, LoRaWAN) ajuda a demonstrar que não há aprisionamento de fornecedor.
2. **Comprovação documental.** Homologação Anatel, ART do responsável técnico e
   atestados são o que habilita. Vale montar o dossiê desde já, em vez de
   correr atrás na véspera do edital.

---

## Resumo do que precisa de ação

| # | Item | Quando | Quem |
|---|---|---|---|
| C-01 | Consultar OCD sobre regulamentação consolidada, modelo de avaliação e aproveitamento de módulo homologado | **Antes do layout final** | OCD |
| ~~C-02~~ | ~~Tabela I e regra de ganho de antena~~ | **Resolvida em 31/07/2026** — texto integral do Ato 14448 obtido; verificação laboratorial formal segue pendente para homologação | Laboratório |
| C-03 | Definir responsável técnico geotécnico (ART) para os pontos de instrumentação | Fase 4 | Eng. geotécnico |
| C-04 | Análise LGPD do cruzamento com população exposta | Fase 3 | Jurídico |
| C-05 | Verificar exigência metrológica para o pluviômetro | Fase 1 | Inmetro/INMET |
| C-06 | Avaliar integração com S2ID/CEMADEN e adoção de SensorThings API | Fase 3 | Projeto |
| C-07 | Projeto de SPDA e aterramento conforme NBR 5419 | Fase 4 | Eng. eletricista |
| C-08 | Definir as responsabilidades técnicas por camada — ver [RESPONSABILIDADE_TECNICA.md](RESPONSABILIDADE_TECNICA.md) | **Antes do piloto** | Projeto |
| C-09 | Adquirir ISO 18674-1, ISO 18674-3 e Amd 1 e elaborar matriz cláusula a cláusula | **Antes de congelar o instrumento** | Produto + geotécnico |
| C-10 | Emitir RFI para IPI comercial e exigir declaração/matriz ISO, calibração e protocolo | **Agora** | Suprimentos + produto |
| C-11 | Selecionar laboratório ISO/IEC 17025 com escopo angular/deslocamento adequado | Antes do FAT | Metrologia |
| C-12 | Definir com laboratório o plano IEC 61326, 61010, 60529 e 60068 | Antes do layout final | Hardware + laboratório |
| C-13 | Confirmar IEC 62133-2 e ONU 38.3 para o pack final | Antes de transportar/vender | Hardware + laboratório/logística |
| C-14 | Definir escopo IEC 62443 e política institucional de cibersegurança | Antes do piloto operacional | Produto + órgão piloto |
| C-15 | Alinhar papéis, fluxo de incidente e semântica de cores às ISO 22320/22324, sem criar níveis | Antes do painel operacional | Órgão piloto + produto |
| C-16 | Avaliar formalmente IEC 61508 se o escopo passar a executar função de segurança | Antes de qualquer automação decisória | Segurança funcional + instituição |

**Fontes:**
[Resolução Anatel nº 680/2017](https://informacoes.anatel.gov.br/legislacao/resolucoes/2017/936resolucao-680) ·
[Ato nº 14448/2017](https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2017/1139-) ·
[Resolução Anatel nº 715/2019](https://informacoes.anatel.gov.br/legislacao/resolucoes/2019/1350-resolucao-715)
