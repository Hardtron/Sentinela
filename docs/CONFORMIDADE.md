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

**[VERIFICAR]** Os valores numéricos da Tabela I do regulamento e a verificação
de que a combinação transmissor + antena escolhida atende ao limite de
intensidade de campo. Isso é ensaio de laboratório, não cálculo de planilha.

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

**[VERIFICAR]** Requisitos metrológicos aplicáveis aos instrumentos —
especialmente pluviômetro, se houver exigência do Inmetro ou de padrão
INMET/CEMADEN para que o dado seja aceito oficialmente.

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
| C-01 | Consultar OCD sobre homologação Anatel e aproveitamento de módulo homologado | **Antes da fase 4** | OCD |
| C-02 | Confirmar limites da Tabela I (Res. 680) para o conjunto rádio + antena | Fase 4 | Laboratório |
| C-03 | Definir responsável técnico geotécnico (ART) para os pontos de instrumentação | Fase 4 | Eng. geotécnico |
| C-04 | Análise LGPD do cruzamento com população exposta | Fase 3 | Jurídico |
| C-05 | Verificar exigência metrológica para o pluviômetro | Fase 1 | Inmetro/INMET |
| C-06 | Avaliar integração com S2ID/CEMADEN e adoção de SensorThings API | Fase 3 | Projeto |
| C-07 | Projeto de SPDA e aterramento conforme NBR 5419 | Fase 4 | Eng. eletricista |

**Fontes:**
[Resolução Anatel nº 680/2017](https://informacoes.anatel.gov.br/legislacao/resolucoes/2017/936resolucao-680) ·
[Ato nº 14448/2017](https://informacoes.anatel.gov.br/legislacao/atos-de-certificacao-de-produtos/2017/1139-) ·
[Resolução Anatel nº 715/2019](https://informacoes.anatel.gov.br/legislacao/resolucoes/2019/1350-resolucao-715)
