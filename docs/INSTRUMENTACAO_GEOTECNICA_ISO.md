# Instrumentação geotécnica e caminho de conformidade

Arquitetura normativa do produto Sentinela para medição de deslocamentos em
taludes. Este documento substitui a barra superficial como instrumento
geotécnico primário e separa três coisas que não podem ser confundidas:

1. **instrumento de medição geotécnica**;
2. **aquisição, armazenamento e telemetria Sentinela**;
3. **interpretação e decisão da Defesa Civil**.

> **Estado em 02/08/2026:** `ALVO DE CONFORMIDADE — NÃO CERTIFICADO`.
> Nenhum hardware atual do repositório foi avaliado ou certificado segundo a
> ISO 18674-3. A Heltec V2 e a barra superficial permanecem protótipos de P&D.

## 1. O que a ISO 18674-3 muda no produto

A ISO 18674-3:2017, com a Emenda 1:2020, especifica a medição de
**deslocamentos transversais a uma linha** por inclinômetros. Seu escopo inclui
taludes naturais, cortes, aterros e a identificação/monitoração de planos ativos
de cisalhamento. A ISO 18674-1:2015 contém as regras gerais da instrumentação
geotécnica em campo.

Uma barra curta com um único acelerômetro superficial mede a **rotação local da
barra**. Ela não reconstrói o perfil de deslocamento ao longo de uma linha e não
localiza um plano de cisalhamento. Logo:

- continua útil para estudar instalação, deriva, rádio e detecção auxiliar;
- não pode ser denominada “inclinômetro conforme ISO 18674-3”;
- não pode ser o canal geotécnico primário de um produto que faça essa alegação.

O produto-alvo precisa de uma linha de medição vertical em furo revestido e de
um método de referência definido pelo projeto geotécnico. Uma cadeia de
inclinômetros *in-place* (IPI) biaxiais mede ângulo em diversos trechos e permite
calcular o perfil de deslocamento. Não se presume que o fundo seja estável: a
referência, o comprimento do furo e a zona instrumentada são decisões do
responsável geotécnico, registradas no projeto e no comissionamento.

## 2. Arquitetura-alvo

```text
   TALUDE / FURO INCLINOMÉTRICO               UNIDADE SENTINELA

   tampa e referência topográfica             antena homologável
              │                                      │
   casing com ranhuras A/B       RS-485       ┌──────┴─────────────┐
              │═══════════════════════════════│ isolação/proteção  │
       IPI biaxial serializado                │ aquisição Modbus   │
              │                               │ relógio + memória  │
       junta/segmento conhecido               │ LoRa + diagnóstico │
              │                               └──────┬─────────────┘
       IPI biaxial serializado                       │
              │                                      ▼
       ... perfil instrumentado              bridge / MQTT / banco
              │                                      │
       referência definida no projeto                ▼
                                              perfil + evidência
```

### Camada IG — instrumento geotécnico

- casing inclinometricamente compatível, com ranhuras/eixos identificados;
- cadeia biaxial de segmentos IPI, com comprimento conhecido;
- sensores individualmente serializados e calibrados;
- temperatura por segmento quando fornecida pelo sistema;
- cabo, conectores, suspensão, terminador e proteção de boca do furo;
- documentação de instalação, orientação, calibração e redução de dados;
- método independente de verificação do perfil e do datum.

### Camada DAQ — aquisição Sentinela

- mestre RS-485/Modbus compatível com o instrumento selecionado;
- isolamento galvânico e proteção contra surtos dimensionados por profissional;
- alimentação separada e monitorada para a cadeia;
- relógio e qualidade temporal explícitos;
- armazenamento não volátil do perfil completo antes da transmissão;
- leitura bruta de registradores preservada juntamente com valor convertido;
- fila *store-and-forward* e identificação de lacunas de sequência;
- firmware e parâmetros com versão, hash e trilha de alteração.

### Camada COM — comunicação

LoRa não pode reduzir o perfil a um único ângulo sem preservar o dado completo.
A unidade pode transmitir os segmentos em quadros versionados, com manifesto,
sequência e integridade, ou usar um enlace de maior capacidade. Um resumo por
rádio nunca substitui o arquivo bruto armazenado.

### Camada APP — interpretação

O backend calcula deslocamentos somente com algoritmo versionado e verificado
contra vetores de referência. Baseline, datum, orientação A/B, comprimento dos
segmentos, incerteza e qualidade acompanham o resultado. Limiar e significado
geotécnico permanecem sob responsabilidade profissional e institucional.

## 3. Estratégia de hardware

### 3.1 Primeiro produto: integrar instrumento comercial

O caminho de menor risco é adquirir um sistema IPI comercial completo e usar o
Sentinela como datalogger/telemetria. Isso preserva o objetivo de produto e
evita declarar que um MEMS montado internamente já satisfaz uma norma de sistema
de medição.

Referências técnicas encontradas — **não homologadas automaticamente pelo
Sentinela**:

| Sistema | Evidência pública do fabricante | Uso na seleção |
|---|---|---|
| GEOKON 6180 | cadeia biaxial endereçável, casing ranhurado, RS-485/Modbus RTU, segmentos serializados/calibrados | referência funcional e candidato a RFI |
| Sisgeo S411/S412 digital | cadeia IPI suspensa em casing, biaxial/uniaxial, Modbus RS-485 | candidato a RFI e comparação de integração |
| RST MEMS Digital IPI | cadeia IPI digital com RS-485 e manual de instalação | candidato a RFI e comparação de suporte |

Ficha técnica ou ISO 9001 do fabricante **não prova conformidade do produto com
a ISO 18674-3**. Antes da compra, o fornecedor deve responder documentalmente:

1. declaração explícita de conformidade, ou matriz de atendimento, à ISO
   18674-1 e ISO 18674-3:2017+Amd 1:2020;
2. escopo exato: sonda, cadeia IPI, casing, instalação, logger e software;
3. certificado de calibração individual, incerteza e rastreabilidade;
4. laboratório emissor e seu escopo ISO/IEC 17025/RBC ou reconhecimento ILAC;
5. faixa calibrada, resolução, exatidão, repetibilidade, deriva térmica e
   estabilidade de longo prazo, com condições de ensaio;
6. materiais, vedação, conectores, limites ambientais e manutenção;
7. protocolo completo, mapa de registradores e política de compatibilidade;
8. procedimento de instalação, verificação, redução de dados e recalibração;
9. prazo de suporte, disponibilidade de peças e controle de revisão;
10. referências de uso em taludes e contato técnico no Brasil.

Se o fornecedor não comprovar o item 1, o produto pode ser avaliado, mas não
ser anunciado como conforme à ISO.

### 3.2 Hardware próprio: trilha de P&D separada

ADXL355 e SCL3300-D01 continuam úteis para desenvolver eletrônica, algoritmos e
um sensor auxiliar. Para se tornarem o instrumento primário, seria necessário
projetar e qualificar o **sistema inteiro**: encapsulamento, segmentos, juntas,
engate ao casing, calibração, modelo térmico, comunicação, instalação, redução
de dados e estabilidade. Essa trilha não bloqueia a integração comercial, mas
não herda conformidade do componente MEMS.

### 3.3 Placa controladora

A Heltec WiFi LoRa 32 V2 fica restrita a bancada e piloto de integração. A placa
de produto deve partir do alvo STM32WLE5/RAK3172 da ADR-004, sujeito a:

- consulta a OCD e homologação do produto final pela Anatel;
- RS-485 isolado, terminação configurável e proteção contra transientes;
- fonte da cadeia separada, protegida e monitorada;
- memória não volátil com detecção de corrupção e dimensionamento de retenção;
- relógio com estado de sincronização e estratégia de continuidade;
- *secure boot*, firmware assinado, identidade única e proteção de chaves;
- conectores de serviço sem abrir a vedação principal, quando tecnicamente
  possível;
- projeto para ensaios de EMC, segurança elétrica e ambiente desde o layout.

Nenhuma dessas funções será simulada na Heltec para alegar prontidão do produto.

## 4. Requisitos do subsistema inclinômetro

Identificadores `GI-*` são requisitos do produto; limites numéricos serão
preenchidos somente pela norma licenciada, pelo projeto do sítio ou pelo plano
de ensaio aprovado.

| ID | Requisito | Evidência de aceitação |
|---|---|---|
| GI-01 | medir as duas componentes transversais à linha vertical | matriz ISO e relatório de ensaio |
| GI-02 | reconstruir o perfil por segmentos de comprimento conhecido | vetores de referência e comparação independente |
| GI-03 | preservar eixo A/B, sentido, datum e orientação em campo | levantamento, fotos e ficha de instalação |
| GI-04 | identificar individualmente sensor, casing, cabo, logger e revisão | registro de ativos e certificados |
| GI-05 | manter calibração e incerteza rastreáveis por segmento | certificado dentro do escopo ISO/IEC 17025 |
| GI-06 | registrar temperatura e compensação exatamente como declaradas | bruto, corrigido, versão e relatório térmico |
| GI-07 | preservar registradores brutos antes de qualquer transformação | arquivo bruto imutável e hash |
| GI-08 | tornar ausência, saturação, falha ou fora de faixa explicitamente inválidos | ensaio de injeção de falhas |
| GI-09 | detectar segmento ausente, duplicado, fora de ordem ou com identidade trocada | FAT automatizado |
| GI-10 | não recalcular silenciosamente histórico após mudança de algoritmo/calibração | revisão imutável e reprocessamento versionado |
| GI-11 | comparar o perfil automatizado com método independente previsto no plano | relatório de comissionamento/SAT |
| GI-12 | definir referência e zona instrumentada por projeto geotécnico | ART, projeto e as-built |
| GI-13 | operar apenas dentro do domínio ambiental qualificado | relatório IEC/condição de instalação |
| GI-14 | manter perfil completo durante perda de enlace | ensaio store-and-forward |
| GI-15 | não emitir regra decisória sem versão aprovada e evidência associada | teste de contrato e auditoria |

## 5. Modelo de dados requerido

O quadro compacto atual não comporta uma cadeia IPI. A versão seguinte precisa
representar ao menos:

```text
instrument_system
  system_id, manufacturer, model, revision, serial
  conformity_claim, conformity_scope, document_revision

installation
  installation_id, borehole_id, site_id
  casing_model, casing_serial, axis_azimuth, reference_method
  top_elevation, installed_at, responsible_art, as_built_revision

segment
  segment_id, serial, address, order, length, depth_top, depth_bottom
  axes, calibration_id, calibration_status

profile_sample
  schema_version, sample_id, measured_at, clock_quality
  logger_id, firmware_version, parameter_snapshot_id
  complete, expected_segments, received_segments, quality_flags

segment_reading[]
  segment_id, raw_registers, angle_a, angle_b, temperature
  units, valid, quality_flags, calibration_id

derived_profile
  algorithm_version, baseline_id, reference_method
  displacement_a[], displacement_b[], uncertainty, quality_flags
```

Dados de instalação não podem ser alterados por telemetria de rotina. Mudança
de posição, sensor, endereço ou calibração cria nova revisão e encerra a
validade da configuração anterior a partir do instante documentado.

## 6. FAT, SAT e comissionamento

### FAT — aceitação em fábrica/bancada

- conferir certificado e número de série de cada segmento;
- verificar cadeia completa, endereços, ordem, orientação e terminador;
- registrar registradores brutos em posições conhecidas e temperatura medida;
- repetir sequência de posições nos sentidos A/B e retorno, conforme plano
  extraído da norma e do fabricante;
- interromper, inverter e remover segmentos para provar detecção de falha;
- validar queda/retorno de energia, relógio, memória e fila offline;
- verificar redução de dados contra cálculo independente e vetores congelados;
- ensaiar versões de firmware e configuração exatamente candidatas ao campo.

### SAT — aceitação no sítio

- confrontar furo, casing, orientação, profundidades e datum com o projeto;
- fazer verificações pré-instalação indicadas pelo fabricante;
- registrar sequência/posição real dos segmentos e fotos do as-built;
- conferir perfil inicial e método independente de referência;
- observar assentamento/baseline pelo período definido pelo geotécnico;
- testar a cadeia completa até banco e snapshot, sem abrir alarme operacional;
- documentar toda não conformidade, reparo e repetição de ensaio.

### Operação

- plano de inspeção, verificação e recalibração definido antes do piloto;
- comparação periódica com referência independente definida pelo projeto;
- controle de deriva, temperatura, movimentação da boca do furo e integridade
  do casing;
- preservação do histórico bruto e de toda mudança de algoritmo;
- alarmes de saúde do instrumento separados de indicação geotécnica.

## 7. Matriz de normas e certificações

“Aplicável” não significa “certificado”. O escopo final deve ser confirmado por
laboratório, OCD e responsáveis técnicos antes de congelar o projeto.

| Referência | Objeto | Natureza para o Sentinela | Estado |
|---|---|---|---|
| ISO 18674-1:2015 | regras gerais de monitoramento geotécnico | alvo normativo do sistema de medição | texto integral/licença e matriz pendentes |
| ISO 18674-3:2017+Amd 1:2020 | deslocamentos transversais por inclinômetros | alvo normativo obrigatório para a alegação pretendida | arquitetura alinhada; avaliação pendente |
| ISO 18674-4:2020 | piezômetros | aplicável quando entrar pressão de poros | fora do primeiro escopo |
| ABNT NBR 11682, edição vigente | estabilidade de encostas | projeto/aplicação e interpretação | profissional/ART pendentes |
| ISO/IEC 17025:2017 | competência de laboratórios | calibração e ensaios com rastreabilidade | contratar laboratório com escopo adequado |
| IEC 61326-1:2020 | EMC de equipamento de medição/controle | alvo de ensaio da unidade DAQ | perfil e laboratório pendentes |
| IEC 61010-1:2010+A1:2016 | segurança de equipamento de medição/controle | aplicabilidade/escopo a confirmar com laboratório | análise pendente |
| IEC 60529 | código IP | ensaio do conjunto montado | severidade definida pelo ambiente/projeto |
| IEC 60068-2-6 / -2-27 | vibração e choque | qualificação de transporte/uso | severidades pendentes do perfil ambiental |
| IEC 60068-2-14 / -2-78 | variação térmica e calor úmido | qualificação costeira/externa | usar edições vigentes; perfil pendente |
| IEC 62133-2 | segurança de bateria de lítio portátil | aplicabilidade ao pack final a confirmar | célula de bancada não aprova o pack |
| ONU 38.3 | transporte de bateria de lítio | obrigatório quando o tipo for transportado no escopo aplicável | resumo de ensaio do pack/célula pendente |
| Res. Anatel 715/2019 e atos vigentes | produto de telecomunicações | homologação legal para uso/comercialização no Brasil | consultar OCD antes do layout final |
| IEC 62443-4-1 | ciclo de desenvolvimento seguro | alvo de processo, certificação opcional | incorporar requisitos desde o projeto |
| IEC 62443-4-2 | requisitos técnicos de componente IACS | somente após definir contexto e SL-C alvo | decisão institucional pendente |
| ISO/IEC 27001:2022+Amd 1:2024 | sistema de gestão de segurança da informação | certificação organizacional, complementar ao produto | avaliar na operação institucional |
| ISO 22320:2018 | gestão de incidentes, papéis e cooperação | orientação para protocolo operacional, não certificação do sensor | alinhar com o órgão piloto |
| ISO 22324:2022 | uso de cores em alertas | orientação para painel/alerta formal; não cria severidades | depende de protocolo institucional |
| IEC 61508:2010 | segurança funcional E/E/PE | somente se futura versão executar função de segurança | fora do escopo decisório atual; avaliar antes de mudar a alegação |
| ISO 9001 | sistema de gestão da qualidade | certificação organizacional, não do sensor | decidir na industrialização; versão em revisão |

### O que é obrigatório e o que é voluntário

- A homologação Anatel é requisito legal brasileiro para comercialização e uso
  de produto de telecomunicações, conforme o enquadramento final.
- ART, normas de projeto e regras de segurança aplicam-se ao serviço/instalação
  conforme a atividade e o local.
- ISO 18674-3 é uma norma técnica voluntária salvo contrato, edital ou regra que
  a incorpore; ao declarar conformidade, porém, a empresa assume o dever de
  demonstrá-la no escopo alegado.
- ISO/IEC 17025 acredita o laboratório e seu escopo, não “certifica o sensor”.
- ISO 9001 certifica o sistema de gestão da organização, não o desempenho deste
  instrumento.
- ISO/IEC 27001 certifica o sistema de gestão de segurança da informação da
  organização; IEC 62443 orienta o processo/componente industrial. Nenhuma das
  duas prova desempenho geotécnico.
- ISO 22320 e ISO 22324 não autorizam criar níveis, cores ou comandos. Elas só
  podem orientar o protocolo formal definido pela instituição.
- IEC 61508 não é adotada por analogia. Ela deve ser avaliada se o escopo mudar
  de apoio à decisão para uma função elétrica/eletrônica relacionada à segurança.

## 8. Dossiê técnico do produto

Cada revisão candidata precisa conter:

1. definição de uso, usuários, ambiente, limites e alegações permitidas;
2. matriz requisito → projeto → ensaio → evidência → responsável;
3. desenhos, BOM, fornecedores aprovados e controle de substituição;
4. análise de riscos de hardware, firmware, medição, instalação e cibersegurança;
5. código, toolchain, SBOM, parâmetros, testes e procedimento de liberação;
6. certificados de calibração e relatórios de laboratório;
7. relatórios FAT/SAT, as-built, baseline e manutenção;
8. manual de instalação, operação, falha segura e descarte;
9. homologação Anatel, marcação e documentação de bateria aplicáveis;
10. registro de não conformidades, ações corretivas e mudanças.

Status permitidos para qualquer alegação:

`NAO_AVALIADO` → `EM_DESENVOLVIMENTO` → `ENSAIO_INTERNO` →
`ENSAIO_TERCEIRO` → `CONFORME` ou `NAO_CONFORME`.

Somente relatório ou certificado dentro de escopo autoriza `CONFORME`.

## 9. Plano de execução

### Pode começar sem conta ou compra

1. adotar esta arquitetura e reclassificar a barra superficial;
2. preparar RFI técnico para três fornecedores IPI;
3. desenhar a DAQ com RS-485 isolado e armazenamento do perfil completo;
4. especificar o contrato de dados multiponto e os vetores de redução;
5. criar matriz de riscos, rastreabilidade e dossiê por revisão;
6. consultar laboratórios sobre escopo de calibração angular/deslocamento, EMC,
   segurança, IP e ambiente.

### Exige contratação, cadastro ou responsável externo

1. adquirir cópias licenciadas da ISO 18674-1, ISO 18674-3 e Emenda 1 e das
   normas ABNT/IEC selecionadas;
2. contratar engenheiro geotécnico/geólogo para projeto do furo e ART;
3. obter propostas e documentação dos fornecedores IPI;
4. contratar laboratório acreditado cujo **escopo** cubra o ensaio/calibração;
5. abrir processo com OCD/Anatel depois de congelar rádio, antena e invólucro;
6. definir com o órgão piloto requisitos de cibersegurança, retenção, operação e
   regra de decisão.

## 10. Fontes primárias

- [ISO 18674-1:2015](https://www.iso.org/standard/63168.html)
- [ISO 18674-3:2017](https://www.iso.org/standard/69207.html)
- [ISO 18674-3:2017/Amd 1:2020](https://www.iso.org/standard/78218.html)
- [ISO 18674-4:2020](https://www.iso.org/standard/73819.html)
- [ISO/IEC 17025:2017](https://www.iso.org/standard/66912.html)
- [Inmetro — Rede Brasileira de Calibração](https://www.gov.br/inmetro/pt-br/centrais-de-conteudo/sistemas/rbc)
- [IEC 61326-1:2020](https://webstore.iec.ch/en/publication/67782)
- [IEC 61010-1](https://webstore.iec.ch/en/publication/4279)
- [IEC 60529](https://webstore.iec.ch/en/publication/2452)
- [IEC 60068-2-6:2007](https://webstore.iec.ch/en/publication/544)
- [IEC 60068-2-27:2008](https://webstore.iec.ch/en/publication/514)
- [IEC 60068-2-14:2023](https://webstore.iec.ch/en/publication/71503)
- [IEC 62133-2](https://webstore.iec.ch/en/publication/32662)
- [ONU — Manual de Ensaios e Critérios, Rev. 8 e Emenda 1](https://unece.org/transport/dangerous-goods/rev8-files)
- [Anatel — certificação de produtos](https://www.gov.br/anatel/pt-br/regulado/certificacao-de-produtos)
- [IEC 62443-4-1](https://webstore.iec.ch/en/publication/33615)
- [IEC 62443-4-2](https://webstore.iec.ch/en/publication/34421)
- [ISO/IEC 27001:2022](https://www.iso.org/standard/27001)
- [ISO 22320:2018](https://www.iso.org/standard/67851.html)
- [ISO 22324:2022](https://www.iso.org/standard/84559.html)
- [IEC 61508:2010](https://webstore.iec.ch/en/publication/22273)
- [GEOKON 6180](https://www.geokon.com/6180)
- [Sisgeo IPI MEMS](https://sisgeo.com/products/ipi-in-place-inclinometers/mems-in-place-inclinometers/)
- [RST MEMS IPI — manual](https://rstinstruments.com/wp-content/uploads/ICM0062K-MEMS-In-Place-Inclinometer-System-Instruction-Manual.pdf)
