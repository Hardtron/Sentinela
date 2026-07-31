# Saúde da frota e manutenção preditiva

Como o sistema descobre sozinho que um dispositivo precisa de visita — e o que
exatamente precisa ser feito lá — sem que ninguém vá conferir.

> **Proveniência.** Segue a política de [REFERENCIAS.md](REFERENCIAS.md):
> **[M]** medido, **[N]** norma, **[L]** literatura, **[G]** governamental,
> **[E]** estimativa própria derivada, **[?]** pendente.

---

## 1. Nomenclatura

O sistema precisava de nome próprio para o dispositivo de campo. Adotado:

| Termo | O que é |
|---|---|
| **Sentinela** | O sistema completo — rede, backend e plataforma |
| **Atalaia** | **O dispositivo instalado no talude**: haste, sensores, rádio e energia |
| **Farol** | O gateway, em ponto alto, que congrega as Atalaias de uma área |
| **Vigília** | Uma campanha de monitoramento ativa sobre um conjunto de taludes |

*Atalaia* é o posto elevado de onde se vigia — palavra portuguesa que descreve
exatamente o objeto: uma haste erguida sobre a encosta, observando. Tem a
vantagem de ser específica (não se confunde com "nó", "sensor" ou "estação",
que são genéricos), pronunciável em campo e apropriável como marca.

Identificação individual: `ATL-<município>-<sequencial>`, por exemplo
`ATL-CGB-014`. O Farol correspondente: `FAR-CGB-01`.

---

## 2. Por que isto é o problema econômico central

Um sistema de 50 Atalaias espalhadas por encostas tem custo de equipamento
relativamente baixo e **custo de operação dominado por visitas de campo**. Cada
visita a talude significa deslocamento, dupla de técnicos, acesso difícil e, com
frequência, NR-35.

Manutenção por **calendário** — visitar todas a cada N meses — desperdiça a
maior parte das visitas em dispositivos que estavam bem, e ainda assim deixa
passar a que falhou logo depois da última visita.

Manutenção por **condição** inverte isso: visita-se quem dá sinal. O sistema já
tem um canal de rádio operando e uma placa medindo tensão — a informação para
decidir está disponível de graça, se for tratada.

**E há o requisito que vem de cima:** Atalaia fora do ar significa **talude sem
monitoramento**. Não é indisponibilidade de serviço, é lacuna de cobertura num
sistema de alerta de risco à vida. A manutenção aqui é parte da função, não
suporte pós-venda.

---

## 3. A bateria e o painel solar como instrumento de diagnóstico

Esta é a ideia central do documento: **a curva diária de carga solar é uma
assinatura**, e mudanças nela revelam o que está acontecendo fisicamente no
local — sem sensor adicional.

### Grandezas registradas por dia

| Símbolo | Grandeza | O que carrega de informação |
|---|---|---|
| `E_dia` | Energia colhida no dia (mAh ou Wh) | Saúde geral da captação |
| `t_ini`, `t_fim` | Início e fim da janela de carga | Sombreamento e horizonte |
| `I_pico` | Corrente máxima de carga | Capacidade instantânea do painel |
| `V_min` | Tensão mínima (fim da madrugada) | Reserva efetiva da bateria |
| `DoD` | Profundidade de descarga noturna | Consumo do dispositivo |
| `V_fim` | Tensão ao encerrar a carga | Resistência interna da bateria |

### Assinaturas — o que cada padrão significa **[E]**

| Padrão observado | Diagnóstico provável | Ação |
|---|---|---|
| `E_dia` cai **gradualmente** por semanas, janela inalterada | **Sujeira acumulada no painel** | Limpeza |
| Janela **encurta progressivamente**, sempre no mesmo horário do dia | **Vegetação crescendo e sombreando** | Poda |
| `E_dia` cai **abruptamente** para perto de zero | Painel desconectado, danificado ou coberto | Visita urgente |
| Queda de um dia só, com recuperação | Evento pontual — folha, dejeto de ave, nuvem | Registrar, não agir |
| `E_dia` normal mas `V_min` cai mais a cada noite | **Bateria degradando** | Trocar bateria |
| `DoD` aumenta sem mudança em `E_dia` | **Consumo anômalo** — sensor travado, rádio retransmitindo | Diagnóstico remoto |
| `V_fim` sobe rápido com `E_dia` baixa | Resistência interna alta, bateria no fim da vida | Trocar bateria |

**Por que sombra e sujeira se distinguem:** sujeira reduz a captação de forma
aproximadamente uniforme ao longo do dia; sombra atua em **janela horária
específica**, que se desloca com a estação. É a forma da curva, não o valor
médio, que separa as duas — e é por isso que registrar `t_ini` e `t_fim` importa
tanto quanto registrar `E_dia`.

Sombreamento **parcial** merece nota: em painel com células em série, sombrear
uma fração pequena derruba a corrente de forma desproporcional. A queda é maior
que a área sombreada sugere — o que torna a detecção mais fácil, não menos.

### O conceito de referência

Na indústria fotovoltaica, a métrica usada é o **Performance Ratio** — razão
entre a saída real e a esperada — e a detecção de sujeira normalmente exige um
**painel de referência limpo** ao lado do sujo, ou um sensor óptico dedicado
([Seven Sensor](https://www.sevensensor.com/what-is-a-soiling-sensor-and-how-it-does-work/),
[detecção orientada a dados](https://arxiv.org/pdf/2301.12939)) **[L]**. O ganho
operacional documentado é substituir limpeza por calendário — duas ou três vezes
ao ano — por limpeza acionada pela perda medida **[L]**.

Ambas as soluções convencionais custam caro por ponto, e o projeto tem dezenas
de pontos.

---

## 4. Referência distribuída — a rede como sensor de referência

**A solução que adotamos evita o painel de referência: usa as Atalaias vizinhas
como referência mútua.** **[E]**

Atalaias de uma mesma vigília estão sob a mesma condição de céu. Então, para
cada dia:

```
razao_i = E_dia(Atalaia_i) / mediana(E_dia de todas as Atalaias do Farol)
```

- Se **todas** caem juntas → foi o tempo. Não há falha, não há visita.
- Se **uma** cai e as outras não → o problema é local: sujeira, sombra ou
  hardware. **É esse o gatilho de manutenção.**

A mediana é deliberada: resiste a valores extremos, então uma Atalaia com
problema não contamina a própria referência.

O que isso resolve, e que é o ponto:

1. **Elimina a variável climática sem instrumento adicional.** Semana nublada
   derruba todo mundo — e não gera alarme falso, que é o modo de falha típico de
   limiar absoluto.
2. **Custo marginal zero.** Nenhum painel de referência, nenhum sensor óptico. A
   informação já trafega.
3. **Melhora conforme a rede cresce.** Mais Atalaias, mediana mais robusta.
4. **Normaliza a instalação.** Atalaias com orientação e inclinação diferentes
   convergem, porque o que se acompanha é a **razão de cada uma consigo mesma ao
   longo do tempo**, não o valor absoluto entre elas.

> **Nota de propriedade intelectual.** O uso da mediana da própria frota como
> referência de irradiância para separar perda local (sujeira/sombra) de
> variação climática, dispensando painel de referência, é candidato a
> reivindicação. **Não divulgar antes de consultar o INPI** — REFERENCIAS.md §2.

**Refinamento posterior:** cruzar com irradiância de fonte externa (INMET,
satélite) melhora a estimativa quando há poucas Atalaias por Farol. Fica como
evolução, não como dependência — o método não pode precisar de internet de
terceiros para funcionar.

---

## 5. Taxonomia de alarmes

Alarme sem ação definida vira ruído, e ruído faz a equipe ignorar o painel. Cada
alarme aqui tem **severidade, gatilho e ação**.

### Severidades

| Nível | Significado | Resposta esperada |
|---|---|---|
| **CRÍTICO** | Talude sem monitoramento **agora** | Imediata — há lacuna de cobertura |
| **URGENTE** | Falha iminente, dias de margem | Próxima janela de campo, com prioridade |
| **ATENÇÃO** | Degradação em curso, semanas de margem | Agendar na próxima rota |
| **INFO** | Registro, sem ação | Nenhuma |

### Catálogo

**Comunicação**

| Alarme | Gatilho | Severidade |
|---|---|---|
| Atalaia silenciosa | Sem pacote além de 3 heartbeats consecutivos | **CRÍTICO** |
| Enlace degradando | Margem média cai abaixo de 10 dB por 7 dias | ATENÇÃO |
| Perda crescente | Perda acima de 5% em média móvel de 24 h | ATENÇÃO |
| Farol fora do ar | Gateway sem contato | **CRÍTICO** — afeta todas as Atalaias |

**Energia**

| Alarme | Gatilho | Severidade |
|---|---|---|
| Bateria crítica | Autonomia projetada abaixo de 48 h | **URGENTE** |
| Sem captação | `E_dia` perto de zero com vizinhas normais | **URGENTE** |
| Captação reduzida | `razao_i` abaixo de 0,75 por 7 dias, janela normal | ATENÇÃO — limpeza |
| Sombreamento crescente | Janela de carga encurta de forma monotônica por 14 dias | ATENÇÃO — poda |
| Bateria em fim de vida | `V_min` em queda monotônica com `E_dia` estável | ATENÇÃO — troca |
| Consumo anômalo | `DoD` acima do histórico com `E_dia` estável | **URGENTE** — investigar remoto |

**Sensores**

| Alarme | Gatilho | Severidade |
|---|---|---|
| Sensor sem resposta | Sem leitura válida em 3 ciclos | **URGENTE** |
| Leitura travada | Valor idêntico além do plausível para a grandeza | **URGENTE** — pior que ausente (RC-07) |
| Fora de faixa | Além do intervalo físico do sensor | **URGENTE** |
| Deriva suspeita | Divergência crescente de sensor redundante | ATENÇÃO |
| Pluviômetro mudo | Sem pulso durante chuva reportada pelas vizinhas | **URGENTE** |

**Integridade física**

| Alarme | Gatilho | Severidade |
|---|---|---|
| **Umidade interna** | Umidade dentro do invólucro acima do limiar | **URGENTE** — vedação comprometida |
| Impacto | Aceleração acima do limiar sem chuva associada | **URGENTE** — vandalismo, queda de galho |
| Inclinação anômala sem chuva | Variação sem precipitação nas vizinhas | **URGENTE** — verificar antes de tratar como movimento |
| Temperatura interna alta | Acima do limite dos componentes | ATENÇÃO |

**Sistema**

| Alarme | Gatilho | Severidade |
|---|---|---|
| Reinícios frequentes | Mais de 3 em 24 h | **URGENTE** |
| Watchdog disparado | Qualquer ocorrência | ATENÇÃO |
| Memória degradando | Heap livre em queda monotônica | ATENÇÃO — vazamento |
| Relógio à deriva | Divergência além do tolerável | ATENÇÃO |

> **A umidade dentro do invólucro é o alarme de melhor retorno do catálogo.**
> Custa um sensor barato, e detecta falha de vedação **antes** de a água
> destruir a eletrônica — transformando uma perda total em uma troca de anel de
> vedação. Vale também como evidência para garantia.

---

## 6. Índice de saúde da Atalaia

Número de 0 a 100 para priorizar rota de manutenção. Não substitui os alarmes —
serve para ordenar o que já está sinalizado. **[E]**

| Componente | Peso | Entra com |
|---|---|---|
| Comunicação | 30 | Entrega de heartbeat, margem, perda |
| Energia | 30 | Razão de captação, autonomia projetada, saúde da bateria |
| Sensores | 25 | Fração de sensores válidos, deriva |
| Integridade | 15 | Umidade interna, temperatura, reinícios |

Faixas: **90–100** saudável · **70–89** observar · **50–69** agendar ·
**abaixo de 50** intervir.

Regra que evita o erro clássico do índice agregado: **qualquer alarme CRÍTICO
zera o índice**, independentemente do restante. Uma Atalaia muda com bateria
cheia e sensores perfeitos não é uma Atalaia 70% saudável — ela é inútil.

---

## 7. Roteirização da manutenção

Com dispositivos em encostas de acesso difícil, o custo é o deslocamento — não a
intervenção. Então o sistema deve **agrupar**, não apenas listar.

A saída útil é uma **rota**, com os dispositivos ordenados por proximidade
geográfica e prioridade combinadas, e para cada um a **lista do que fazer**,
derivada dos alarmes: limpar painel, podar vegetação, trocar bateria, verificar
vedação, recalibrar.

Isso é problema geoespacial, e cai naturalmente no PostGIS já previsto
(ADR-005): as Atalaias são pontos, o acesso é rede, e a rota é consulta.

**Consequência operacional:** uma visita programada por degradação lenta
(limpeza, poda) deve **arrastar consigo** as intervenções de baixa prioridade
das Atalaias próximas. Trocar uma bateria que ainda tem dois meses custa quase
nada se a equipe já está a 30 metros; custa uma expedição inteira depois.

---

## 8. Telemetria necessária

O que o firmware precisa passar a transmitir, além do que já mede.

**Em cada pacote de saúde** (baixa frequência, agregado no dispositivo):

```
tensao_bateria, corrente_carga, energia_dia, janela_carga_ini, janela_carga_fim,
tensao_minima_24h, profundidade_descarga, temperatura_interna,
umidade_interna, reinicios, watchdogs, heap_livre, rssi_ultimo, perda_24h,
sensores_validos (bitmap), versao_firmware
```

Três decisões de projeto que decorrem disso:

**Agregar no dispositivo, não no servidor.** Enviar amostra de tensão a cada
minuto consumiria o orçamento de rádio inteiro. O dispositivo calcula `E_dia`,
janela e `DoD` localmente e envia o resumo — cabe em poucos bytes por dia. É a
mesma lógica que já rege o payload (`lib/proto/`).

**Persistir o histórico local.** Guardar em NVS os últimos 30 dias de resumo
diário permite reconstruir tendência mesmo depois de período sem enlace — e é
o que torna o diagnóstico possível após uma falha de comunicação prolongada
(RC-06).

**Bitmap de validade por sensor.** Sensor falho precisa ser distinguível de
leitura válida no próprio payload, não inferido no servidor (RC-07).

---

## 9. O que implementar, e quando

| Item | Fase | Depende de |
|---|---|---|
| Telemetria de saúde no payload | 1 | `lib/proto/` |
| Agregação diária de energia em NVS | 1 | — |
| Sensor de umidade interna ao invólucro | 1 | Escolha do invólucro |
| Detecção de sensor travado e fora de faixa | 1 | — |
| Catálogo de alarmes no ingestor | 2 | Backend |
| Referência distribuída entre Atalaias | 3 | Vários dispositivos operando |
| Índice de saúde e painel de frota | 3 | Backend |
| Roteirização geoespacial | 3 | PostGIS |
| Validação das assinaturas em campo | 5 | Operação real |

**Ponto honesto sobre maturidade:** as assinaturas da §3 são **derivadas de
princípio físico e da literatura fotovoltaica, ainda não validadas em campo neste
projeto** **[E]**. Os limiares numéricos (0,75 de razão, 7 dias, 14 dias) são
pontos de partida e **precisam ser calibrados com a operação real** antes de
virarem gatilho automático de despacho de equipe. Até lá, devem gerar sugestão
para o operador, não ordem de serviço.

**Fontes:**
[Soiling sensor — princípio de medição](https://www.sevensensor.com/what-is-a-soiling-sensor-and-how-it-does-work/) ·
[Detecção de sujeira orientada a dados em módulos PV](https://arxiv.org/pdf/2301.12939) ·
[Monitoramento remoto e Performance Ratio](https://www.carolinasolarcare.com/remote-monitoring-for-solar-panel-efficiency-optimize-performance/) ·
[SitkaNet — falhas de campo em rede de baixo custo](https://pmc.ncbi.nlm.nih.gov/articles/PMC9041236/)
