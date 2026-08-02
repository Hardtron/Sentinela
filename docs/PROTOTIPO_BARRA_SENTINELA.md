# Protótipo da Barra Sentinela

Especificação de engenharia para construir e ensaiar o primeiro conjunto de
sensoriamento local do Sentinela. Este documento organiza o que pode ser feito
com a base atual; ele **não é projeto executivo de instalação em área de risco**.

> **Estado:** `PROTOTIPO / NÃO DECISÓRIO`
> **Placa central:** Heltec WiFi LoRa 32 V2, a "placa LoRa" já inventariada em
> [HARDWARE.md](HARDWARE.md).
> **Recorte:** bancada e piloto observacional controlado em Caraguatatuba.
> **Regra:** nenhum valor coletado por este protótipo gera, sozinho, nível de
> risco, alarme público, evacuação ou diagnóstico de estabilidade.

> **Reclassificação — ADR-010.** Este conjunto é um sensor superficial auxiliar
> e bancada de aquisição; **não é o instrumento geotécnico principal e não é
> compatível, por si, com a ISO 18674-3**. A arquitetura normativa do produto é
> a cadeia IPI em furo revestido descrita em
> [INSTRUMENTACAO_GEOTECNICA_ISO.md](INSTRUMENTACAO_GEOTECNICA_ISO.md). O P0/P1
> permanece útil para validar rádio, energia, vedação, integração e comparação
> com o instrumento de referência.

## 1. Proveniência e limites

Este documento usa as marcas de [REFERENCIAS.md](REFERENCIAS.md): **[M]** medido
pelo projeto, **[N]** norma, **[L]** literatura revisada, **[G]** fonte
governamental e **[E]** decisão de engenharia para o protótipo. Uma decisão
**[E]** precisa ser validada; ela não pode ser promovida a critério geotécnico.

As referências que limitam o desenho são:

- **ISO 18674-1**: regras gerais para instrumentação geotécnica em campo **[N]**;
- **ISO 18674-3:2017**: inclinômetros medem deslocamentos ao longo de uma linha;
  a edição foi confirmada pela ISO em 2023 **[N]**;
- **ISO 18674-4:2020**: piezômetros medem pressão de água e nível piezométrico em
  solo saturado, inclusive em taludes **[N]**;
- **ISO 17892-1:2014**, confirmada em 2025: método de referência por secagem em
  estufa para teor de água em amostras de solo **[N]**;
- o CEMADEN trata chuva e umidade do solo como variáveis complementares e usa
  sensores em diferentes camadas, chegando a 3 m em sua RedeGeo **[G]**;
- a literatura distingue o **gatilho meteorológico** do **estado hidrológico**
  da encosta e mostra que incorporar umidade antecedente pode melhorar modelos
  baseados só em chuva **[L]**.

Links verificáveis estão no [Anexo A](#anexo-a--fontes-primarias-e-literatura).

## 2. O que o protótipo precisa provar

O protótipo só avança de fase quando produzir evidência para estas perguntas:

1. a placa lê cada sensor, preserva unidade, identidade, instante, qualidade e
   versão de calibração;
2. a leitura de inclinação permanece estável diante de ciclo térmico, vento e
   manutenção, ou esses efeitos ficam identificáveis nos dados;
3. as sondas de umidade respondem ao solo local e podem ser comparadas com
   amostras de referência, sem converter leitura bruta em saturação por palpite;
4. bateria, rádio, bridge, MQTT, ingestor, banco e painel preservam a leitura e
   sua proveniência de ponta a ponta;
5. falha, desconexão, valor fora do domínio ou calibração ausente aparecem como
   `SEM_DADO`/inválido, nunca como condição normal;
6. instalação, manutenção e retirada podem ser feitas sem introduzir um risco
   maior que o benefício do ensaio.

Alcance de rádio, autonomia, repetibilidade, proteção ambiental e estabilidade
**serão resultados medidos**, não especificações presumidas.

## 3. Arquitetura física recomendada

O conjunto tem dois elementos independentes:

```text
                       MASTRO DE SERVIÇO
                    antena LoRa vertical
                            │
                 ┌──────────┴──────────┐
                 │ caixa: Heltec,      │
                 │ energia e interfaces│
                 └──────────┬──────────┘
                            │ cabos com laço de gotejamento
                            │
             separação mecânica — não usar tirante comum
                            │
  encosta  ────────────────┼────────────────────────────
              cabeçote selado da BARRA DE MEDIÇÃO
              inclinômetro solidário à barra; eixos marcados
                            │
                            │ barra no horizonte investigado
                    ────────┼────────  sonda de umidade A
                            │
                    ────────┼────────  sonda de umidade B
                            │
                    ────────┼────────  sonda opcional C
                            │
                 profundidades definidas pelo perfil do sítio
```

### Por que separar

Uma antena ganha enlace quando sobe; um inclinômetro perde confiabilidade se o
mesmo elemento alto flexiona com vento ou manutenção. O sensor de inclinação
deve ficar no cabeçote curto, diretamente acoplado à barra de medição. O mastro
leva apenas rádio, caixa, energia e, opcionalmente, um segundo sensor usado para
**quantificar interferência do próprio mastro**, nunca movimento do solo **[E]**.

Um único acelerômetro fixado na superfície não equivale ao inclinômetro em furo
da ISO 18674-3. Ele mede a rotação local do conjunto ao qual está acoplado. Essa
diferença deve acompanhar o nome da grandeza no firmware, banco e painel.

## 4. Geometria para começar — sem transformá-la em prescrição de campo

O repositório já dimensionou um corpo de ensaio em tubo de aço galvanizado a
fogo, 1 1/2 polegada (48,3 mm), parede de 3 mm e 2,5 m de comprimento total
([ANCORAGEM.md](ANCORAGEM.md)). Essa geometria fica preservada como **corpo de
prova mecânico P1 [E]**, pois permite iniciar ensaios comparáveis. Ela não define
a profundidade correta de uma instalação geotécnica.

| Elemento | Geometria inicial do protótipo | O que ainda decide o campo |
|---|---|---|
| Barra de medição | tubo 48,3 × 3 mm; peça de até 2,5 m **[E]** | comprimento útil e método de acoplamento após perfil pedológico/geotécnico |
| Trecho acima do solo | o menor que permita cabeçote, conexão e manutenção **[E]** | proteção contra impacto e acesso seguro |
| Profundidade enterrada | **não fixada** | horizonte investigado, interface entre materiais e mecanismo de movimento |
| Mastro de serviço | corpo separado; 1,5 m livre pode ser ensaiado como a hipótese já calculada no projeto **[E]** | altura final pelo perfil de enlace e verificação estrutural da edição vigente da ABNT NBR 6123 |
| Caixa | dimensionar depois de montar bornes, fonte e raio de curvatura dos cabos | ensaio do conjunto montado segundo o código IP; não basta a etiqueta da caixa |
| Sondas de umidade | em horizontes diferentes, não em "profundidades padrão" | profundidades e quantidade após descrição do perfil e objetivo de medição |

Os 0,8–1,2 m anteriormente citados em ANCORAGEM.md são **hipótese histórica de
protótipo**, não faixa validada para Caraguatatuba. O próprio CEMADEN escolhe e
caracteriza os locais com especialistas e mede várias camadas. A posição final
precisa de geólogo ou engenheiro geotécnico habilitado e do registro de sua
decisão.

## 5. Eletrônica e sensores

### 5.1 Núcleo já disponível

| Item | Uso no protótipo | Limite conhecido |
|---|---|---|
| Heltec WiFi LoRa 32 V2 | controlador, aquisição e enlace LoRa | consumo em repouso já documentado como inadequado à versão final de campo |
| Antena LoRa | enlace de ensaio | nunca energizar transmissão sem antena compatível instalada |
| Célula NCR18650B | ensaio de energia | precisa proteção, fixação, fusível e medição real de autonomia |
| I2C externo GPIO 22/23 | sensores ambientais/triagem | validar conflito, comprimento, pull-ups e imunidade antes de campo |
| SPI | sensor de inclinação de referência | definir chip-select dedicado e validar coexistência com rádio/display |

A Heltec V2 é adequada ao P0/P1, mas a aprovação do sensor não aprova essa placa
como nó final. A próxima revisão de hardware continua condicionada à medição de
consumo e à ADR-004.

### 5.2 Seleção recomendada

| Grandeza | Opção para o protótipo | Decisão e justificativa |
|---|---|---|
| Inclinação/rotação local | **ADXL355** em placa de avaliação | permanece a primeira candidata do projeto: baixo ruído e deriva, SPI/I2C, temperatura e autoteste; comparar a saída térmica antes de aceitar **[E]** |
| Inclinação de referência | **Murata SCL3300-D01** em placa de avaliação | canal comparativo opcional: inclinômetro dedicado, saída angular e SPI; útil para separar erro do algoritmo do erro mecânico **[E]** |
| Umidade volumétrica/temperatura/EC | **TEROS 12** como instrumento de referência | sonda de campo encapsulada, DDI/SDI-12 e cabo; exige contato correto e calibração específica do solo **[E]** |
| Ambiente interno da caixa | **SHT41** | mede temperatura/umidade do invólucro para diagnosticar condensação e deriva; não representa o microclima externo **[E]** |
| Pressão de poros | não comprar no P0 | piezometria é fase própria, com projeto e instalação segundo ISO 18674-4 **[N]** |

Não há substituição automática do ADXL355 pelo SCL3300. A decisão de compra é:

- adquirir primeiro uma montagem rastreável do ADXL355;
- se o orçamento permitir, usar SCL3300 como referência A/B no mesmo gabarito;
- escolher depois de comparar ruído, deriva térmica, repetibilidade, consumo,
  integração e disponibilidade — não pela resolução de catálogo isolada.

Para umidade, o TEROS 12 é a referência de validação. Sensores capacitivos de
baixo custo podem ser comparados lado a lado, mas não substituem a referência
até reproduzirem os ciclos de laboratório e campo dentro de critérios definidos
antes do teste. O fabricante declara alimentação de 4–15 V e DDI/SDI-12; logo a
Heltec requer fonte comutada e interface elétrica próprias. **Não conectar a
sonda diretamente a GPIO de 3,3 V.**

### 5.3 Módulos auxiliares necessários

- fonte elevadora/comutada compatível com a sonda escolhida, desligável pelo
  ESP32 e dimensionada a partir do consumo medido;
- interface SDI-12 com níveis elétricos documentados e proteção contra
  transientes;
- fusível substituível, proteção de polaridade e TVS dimensionados por projeto
  elétrico;
- borne identificado e desconectável para cada sonda;
- medição de tensão da bateria calibrada e, se possível, corrente do conjunto;
- prensa-cabos compatíveis, respiro de membrana e laços de gotejamento;
- cabo de ligação flexível entre barra e caixa, sem transmitir esforço do
  mastro ao cabeçote de medição;
- etiqueta externa e interna com `node_id`, placa, revisão, lote, calibrações e
  QR/código para o snapshot de comissionamento.

## 6. Montagem mecânica

### 6.1 Barra e cabeçote de medição

1. Marcar no tubo o eixo longitudinal, o sentido de maior declive e uma escala
   de profundidade permanente.
2. Fixar o sensor em berço rígido, sem espuma compressível, dentro de cabeçote
   selado e removível. Registrar foto da orientação dos eixos.
3. Manter a parte livre da barra curta e sem caixa, painel solar ou antena.
4. Fazer a saída do cabo com alívio de tração; o cabo não pode puxar a barra.
5. Não usar concreto no P1 antes de comparar métodos de acoplamento. Qualquer
   método definitivo depende da investigação do sítio e do mecanismo que se
   pretende observar.

### 6.2 Sondas de umidade

1. Abrir perfil de inspeção apenas com procedimento e autorização de campo.
2. Descrever e fotografar horizontes antes de escolher pontos de leitura.
3. Inserir as hastes da sonda completamente em solo representativo, evitando
   bolsões de ar; seguir o manual do fabricante.
4. Preferir inserção lateral em face de solo não revolvido. Reconstituir o
   perfil na ordem dos horizontes e registrar o método.
5. Não encostar a sonda no tubo metálico. Afastamento e volume de influência
   serão os do manual/ensaio do sensor, não um número inventado.
6. Identificar cada canal por sensor, número de série, profundidade real e
   horizonte — nunca apenas `umidade_1`, `umidade_2`.

### 6.3 Mastro, caixa e antena

1. Instalar o mastro fora do elemento de medição e sem tirante compartilhado.
2. Fixar a caixa em altura acessível sem trabalho em altura; entradas de cabo
   pela face inferior e com laço de gotejamento.
3. Manter a antena vertical e instalar a antena antes de qualquer transmissão.
4. Determinar altura pelo perfil do enlace de [PROPAGACAO.md](PROPAGACAO.md),
   depois verificar estrutura e fundação pela norma vigente.
5. Tratar "IP67" como requisito de ensaio do conjunto completo — caixa, tampa,
   respiro, conectores e prensa-cabos — conforme IEC 60529 **[N]**.

## 7. Procedimento de instalação P1

O P1 é um piloto **observacional e controlado**, fora de uma decisão operacional.

1. **Autorizações e responsáveis:** registrar proprietário, responsável pelo
   ensaio e profissional que aprovou o ponto. Fazer análise preliminar de risco,
   localizar interferências enterradas e definir rota de acesso.
2. **Caracterização:** registrar coordenadas, topografia, cobertura, drenagem,
   intervenções antrópicas, perfil de solo e histórico disponível. A escolha de
   horizonte é geotécnica, não eletrônica.
3. **Enlace antes de escavar:** ensaiar rádio com antena, potência e firmware
   registrados; não transformar ensaio interno ou de visada em prova de campo.
4. **Sondas:** instalar conforme §6.2, fotografar cada profundidade e coletar
   amostras pareadas para a campanha de calibração.
5. **Barra:** instalar pelo método experimental aprovado, registrar profundidade
   real, resistência/encontros, verticalidade/orientação e qualquer pré-furo.
6. **Cabeçote:** montar o sensor, conferir eixos, autoteste, temperatura e
   leitura bruta antes de fechar.
7. **Mastro:** instalar separadamente e executar o teste de interferência:
   tocar/manter o mastro, abrir a caixa e aplicar vento controlado sem tocar a
   barra; registrar o que aparece no canal de medição.
8. **Elétrica:** testar polaridade, isolação, corrente em repouso/medição/TX,
   bateria e falhas de sonda antes de energização contínua.
9. **Cadeia completa:** observar o mesmo identificador e instante em nó, Farol,
   bridge, MQTT, ingestor, banco e painel. Falta em qualquer elo impede aprovar.
10. **Baseline:** coletar período suficiente para caracterizar repetibilidade e
    ciclo térmico. A duração será definida antes do ensaio a partir da taxa de
    amostragem e do ambiente; este documento não inventa uma duração universal.
11. **Snapshot:** concluir o checklist, anexar fotos, versões, calibrações,
    medições de energia/enlace e hash do pacote de evidência contextual.

## 8. Contrato mínimo de dados do protótipo

O protocolo atual não deve reduzir 2–3 profundidades a um único valor ambíguo.
A próxima versão do quadro de sensores deve preservar:

```text
schema_version
node_id / hardware_revision / firmware_version
sample_id / boot_id / sequence
measured_at / received_at / clock_quality
battery_voltage + calibration_id + valid
radio_rssi / radio_snr / gateway_id
sensors[]:
  sensor_id / serial / model / channel
  measurand / raw_value / raw_unit
  calibrated_value / unit / valid / quality_flags
  calibration_id / calibration_status
  depth_m / horizon_id / axis_orientation
```

`depth_m`, `horizon_id` e `axis_orientation` são metadados de instalação; não
devem ser aceitos de um pacote que possa alterá-los silenciosamente. Mudança
exige nova revisão de comissionamento. A ausência de calibração mantém o valor
bruto disponível, mas o valor físico fica nulo ou explicitamente experimental.

## 9. Campanha de validação

Definir o critério e congelar sua versão **antes** de executar cada ensaio. A
tabela descreve a evidência exigida, não cria limites de aprovação.

| Etapa | Ensaio | Evidência mínima | Proíbe concluir |
|---|---|---|---|
| P0.1 | identificação elétrica e barramentos | fotos, números de série, pinagem, consumo e firmware | prontidão de campo |
| P0.2 | inclinação em gabarito | posições repetidas, subida/descida, temperatura, bruto e processado | limiar de movimento |
| P0.3 | deriva térmica | sensor imóvel durante ciclo térmico medido | compensação universal |
| P0.4 | umidade em solo local | leitura bruta, amostra, massa úmida/seca, densidade quando aplicável e calibração versionada | "saturado" por porcentagem bruta |
| P0.5 | falhas | desconexão, curto/valor impossível, reboot e fila offline | substituir ausência por zero |
| P0.6 | energia | corrente por estado e autonomia observada | autonomia anual extrapolada sem modelo validado |
| P0.7 | rádio | sequência, perda, RSSI/SNR, configuração e geometria | cobertura municipal |
| P0.8 | ponta a ponta | quadro original e registros equivalentes em todos os elos | sucesso por USB apenas |
| P1.1 | acoplamento mecânico | resposta da barra a ação conhecida e resposta cruzada do mastro | deslocamento real de talude |
| P1.2 | ambiente | ingresso, condensação, temperatura e corrosão após montagem | grau IP certificado sem ensaio apropriado |
| P1.3 | solo controlado | ciclos de molhagem/secagem e amostras de referência | limiar operacional |
| P1.4 | piloto observacional | série contínua, manutenção, ocorrências e ausências | alerta público ou certificação |

### Calibração de umidade

O TEROS 12 fornece leitura volumétrica segundo calibrações declaradas pelo
fabricante, mas o solo local, a densidade e a instalação alteram a resposta. A
campanha deve:

1. manter rastreabilidade de cada sonda e amostra;
2. cobrir ciclos de umedecimento e secagem do solo representativo;
3. comparar com teor de água por secagem conforme ISO 17892-1 e registrar o
   método usado para converter, quando necessário, massa em volume;
4. ajustar e validar em conjuntos de dados separados;
5. preservar curva, resíduos, domínio válido e versão;
6. nunca extrapolar além do domínio ensaiado sem marcar a leitura inválida.

### Inclinação e movimento

Calibrar ângulo em gabarito não calibra o acoplamento solo–barra. São dois
ensaios distintos. O P0 mede sensor/eletrônica; o P1 mede a montagem. Para
movimento subsuperficial ao longo de uma linha, o caminho de referência é um
inclinômetro geotécnico instalado segundo projeto compatível com ISO 18674-3,
não uma alegação estendida ao MEMS superficial.

## 10. Segurança

- não trabalhar na encosta durante chuva, alerta vigente ou condição não
  inspecionada;
- não transmitir RF sem antena conectada;
- não abrir/manipular bateria de lítio danificada e não operar célula sem
  proteção elétrica e mecânica;
- consultar a versão vigente das NR-10 e NR-35 e aplicar somente quando o
  trabalho correspondente existir;
- não criar aterramento isolado ou SPDA improvisado. A avaliação de risco de
  descargas e a solução conforme a edição vigente do conjunto ABNT NBR 5419 são
  responsabilidade de profissional habilitado;
- não elevar a barra de medição para ganhar rádio. Aumentar primeiro a altura
  do gateway ou instalar mastro de serviço projetado separadamente;
- interromper o ensaio diante de água na caixa, aquecimento, bateria deformada,
  cabo tracionando a barra, corrosão, leitura saturada persistente ou estrutura
  instável.

## 11. Critérios de saída por fase

### P0 — bancada

- sensores identificados e lidos sem perda de identidade/unidade;
- falhas aparecem explicitamente;
- repetibilidade, deriva térmica e consumo foram medidos;
- calibração de umidade possui dados brutos, amostras e versão;
- quadro versionado percorre um ambiente de teste de ponta a ponta;
- nenhuma informação de teste foi misturada a dados operacionais.

### P1 — instalação controlada

- ponto e horizontes aprovados por responsável competente;
- barra e mastro mecanicamente independentes e interferência medida;
- conjunto ambiental e energia passaram pelos critérios previamente aprovados;
- snapshots de instalação, parâmetros e evidência são recuperáveis;
- série observacional registra manutenção, falha e ausência;
- conclusão permanece `EXPERIMENTAL`, sem limiar decisório.

### Só depois do P1

Limiar, janela, regra de fusão, localização em área de risco, protocolo de
incidente, responsabilidade por alerta, periodicidade de manutenção e projeto
executivo exigem, conforme o item: validação estatística local, literatura,
profissional habilitado, Defesa Civil e/ou norma vigente.

## 12. Lista de aquisição — ordem recomendada

1. obter RFI e proposta de uma cadeia IPI comercial, casing e documentação de
   calibração/conformidade para o canal geotécnico principal;
2. placa de avaliação ADXL355 e materiais do gabarito de inclinação, somente
   para o canal superficial auxiliar/P&D;
3. uma sonda TEROS 12 de referência, interface SDI-12 e fonte protegida para
   fechar o canal completo antes de multiplicar unidades;
4. as demais sondas para o perfil de 2–3 profundidades já decidido em
   [SENSORES.md](SENSORES.md), depois da validação do primeiro canal;
5. SHT41 para diagnóstico interno da caixa;
6. SCL3300-D01 em placa de avaliação, se aprovado o ensaio comparativo;
7. caixa, prensa-cabos e conectores definitivos apenas após o envelope elétrico;
8. material do corpo de prova de 2,5 m e mastro separado;
9. instrumentação/laboratório para massas, temperatura, corrente e gabarito.

Marca e modelo são referências técnicas, não fornecedores exclusivos. Antes da
compra devem ser registrados: revisão da ficha, disponibilidade, autenticidade,
prazo, custo total, interface, tensão e condição de calibração.

## Anexo A — fontes primárias e literatura

- [ISO 18674-1:2015 — regras gerais de instrumentação geotécnica](https://www.iso.org/standard/63168.html)
- [ISO 18674-3:2017 — inclinômetros](https://www.iso.org/standard/69207.html)
- [ISO 18674-4:2020 — piezômetros](https://www.iso.org/standard/73819.html)
- [ISO 17892-1:2014 — teor de água por secagem](https://www.iso.org/standard/55243.html)
- [IEC 60529 — código IP](https://webstore.iec.ch/en/publication/2452)
- [CEMADEN — objetivos de pesquisa em geologia](https://www.gov.br/cemaden/pt-br/assuntos/pesquisa/4-geologia)
- [CEMADEN — RedeGeo, chuva e umidade até 3 m](https://www.gov.br/cemaden/pt-br/assuntos/noticias-cemaden/redegeo-e-informacoes-sobre-umidade-de-solo-das-encostas-para-prevencao-de-deslizamentos-sao-apresentadas-pelo-cemaden)
- [CEMADEN — treinamento técnico e manutenção das PCDs Geo](https://www.gov.br/cemaden/pt-br/assuntos/noticias-cemaden/defesas-civis-do-rj-recebem-treinamento-do-cemaden-mcti-sobre-dados-das-pcds-geo-e-o-sistema-de-monitoramento-de-riscos-de-deslizamentos)
- [Bogaard & Greco (2018) — gatilho meteorológico e causa hidrológica](https://doi.org/10.5194/nhess-18-31-2018)
- [Halter et al. (2025) — umidade in situ em alerta baseado em precipitação](https://doi.org/10.1007/s10346-025-02599-4)
- [SitkaNet (2022) — rede LoRa de baixo custo em campo](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/)
- [Analog Devices — ADXL355](https://www.analog.com/en/products/adxl355.html)
- [Murata — SCL3300-D01](https://www.murata.com/en-us/products/sensor/overview/item/scl3300-d01)
- [METER Group — manual TEROS 11/12](https://publications.metergroup.com/Manuals/20587_TEROS11-12_Manual_Web.pdf)
- [MTE — NR-10 vigente](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/norma-regulamentadora-no-10-nr-10)
- [MTE — NR-35 vigente](https://www.gov.br/trabalho-e-emprego/pt-br/acesso-a-informacao/participacao-social/conselhos-e-orgaos-colegiados/comissao-tripartite-partitaria-permanente/normas-regulamentadora/normas-regulamentadoras-vigentes/norma-regulamentadora-no-35-nr-35)
