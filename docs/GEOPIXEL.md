# Contexto Geopixel e proposta de valor

Análise feita a partir das duas páginas públicas do produto Geopixel Monitor,
em 30/07/2026. É leitura **externa**, baseada em material de divulgação — a
arquitetura real do produto pode conter coisas que a página não mostra. Tratar
como hipótese a validar internamente, não como diagnóstico fechado.

- https://geopixelsistemas.com.br/monitoramento-climatico/index.html
- https://caraguatatuba.geopixel.com.br/monitor/

---

## 1. O que a plataforma já entrega

**Monitoramento climático e de riscos territoriais para gestão municipal.**
Acompanha chuva intensa, inundação, deslizamento, queimada, onda de calor,
vendaval, granizo e geada.

**Base tecnológica:** sensoriamento remoto (satélite, drone, aeronave), SIG,
análise de relevo, cobertura vegetal e uso do solo.

**Fontes de dados:** INMET, CEMADEN, ANA, INPE, mais dados próprios.

**Parceria relevante:** INPE e **TerraMA²** — a plataforma livre do INPE para
alerta de desastres naturais.

**Funcionalidades observadas na instância de Caraguatatuba:**

- Mapas de risco interativos e camadas territoriais
- Exportação de feições em **CSV e KML**, com seleção por caixa
- **Módulo de Vistoria** — solicitação de vistoria em ponto específico, com
  acompanhamento de status (solicitada, programada, finalizada)
- **Sistema de Alertas** — data de emissão, identificação da área de risco,
  status, duração e mensagem personalizada
- **Meteograma**
- Interface em português, espanhol e inglês

**Público:** prefeituras, gestores municipais e defesa civil — exatamente o
público do Sentinela.

---

## 2. A lacuna estrutural

A plataforma é forte onde os dados são **regionais e remotos**. E é justamente
aí que está o limite físico:

**Resolução espacial.** Satélite e modelo meteorológico enxergam o município ou
a bacia. A rede do CEMADEN tem pluviômetros esparsos — o mais próximo pode estar
a quilômetros e do outro lado de um divisor de águas. Mas o deslizamento não
acontece no município: acontece **naquele talude**, sobre aquelas casas. Chuva
convectiva de verão na Serra do Mar varia drasticamente em poucos quilômetros.

**Grandeza observável.** Sensoriamento remoto não mede o que de fato antecede a
ruptura: **poropressão, saturação do solo e deslocamento milimétrico**. Ele
infere a partir de proxies. Interferometria de satélite mede deslocamento, mas
com revisita de dias — tarde demais para um evento que se desenvolve em horas.

**Latência.** Modelo e satélite têm ciclo de atualização. Encosta em ruptura
não espera a próxima passagem.

**Consequência operacional — e é aqui que dói:** alerta baseado em previsão
regional gera **falso positivo**. A defesa civil é acionada, evacua, não
acontece nada. Repetido algumas vezes, a população para de responder. O custo
não é o do alerta errado: é o do alerta **certo** que será ignorado depois.

---

## 3. Onde o Sentinela encaixa

O Sentinela não compete com o que a Geopixel tem — ele fornece a camada que
falta: **medição in situ, no talude específico, em tempo quase real.**

```
Satélite / modelo / INMET / CEMADEN   →  risco regional, horas a dias
                 ↓
          Geopixel Monitor            →  território, cadastro, exposição
                 ↓
       SENTINELA (camada de campo)    →  aquele talude, agora
```

É a diferença entre *"há risco alto de deslizamento na região"* e *"o talude do
Setor 3 acumulou 180 mm em 72 h, o solo está saturado nas três profundidades e a
inclinação derivou 0,4° nas últimas 6 horas"*.

---

## 4. Insights de produto

### 4.1 Verdade de campo reduz o falso positivo

O uso mais valioso do sensor não é disparar alerta sozinho — é **confirmar ou
desmentir** o alerta regional. O modelo diz que há risco; o sensor diz se aquele
talude específico está de fato saturado e se movendo. Isso converte alerta
genérico em alerta qualificado, e **preserva a credibilidade**, que é o ativo
mais frágil da defesa civil.

### 4.2 O módulo de Vistoria fecha o ciclo — nos dois sentidos

Hoje a vistoria parece ser demandada manualmente. Com a rede de sensores:

- **Sensor → vistoria:** deriva de inclinação prioriza automaticamente qual
  talude inspecionar. A equipe, que é escassa, vai onde o dado aponta.
- **Vistoria → sensor:** o laudo de campo rotula o que o sensor mediu, criando
  o conjunto de dados que **calibra os limiares locais**.

Esse segundo sentido é o mais subestimado: transforma um módulo operacional já
existente em fonte de dado rotulado.

### 4.3 Limiares locais viram ativo proprietário

Limiares de chuva crítica publicados são regionais e genéricos. Uma série
temporal local, por talude, ao longo de anos, correlacionada com eventos e
vistorias reais, permite calibrar limiares **daquela encosta**. Esse conjunto é
difícil de replicar, melhora com o tempo e é o tipo de coisa que rende
publicação conjunta com universidade — reforçando a credibilidade institucional
junto ao poder público.

### 4.4 O meteograma passa a ter dado observado

Hoje o meteograma tende a exibir previsão de modelo. Com estação própria no
ponto, ele passa a mostrar **observado versus previsto** — e o histórico de
acerto do modelo naquele local. Para um técnico de defesa civil, saber que o
modelo vem superestimando a chuva naquele setor muda a decisão.

### 4.5 Integração barata pelos caminhos que já existem

A instância já exporta **CSV e KML**. Se o Sentinela publicar nesses formatos e
em **OGC SensorThings API**, a integração usa trilhos existentes. E o TerraMA²,
sendo aberto e já em parceria, é ponto natural de entrada de uma nova fonte de
dados — em vez de construir integração proprietária.

### 4.6 Caraguatatuba é o piloto certo

A instância existente é de Caraguatatuba — litoral norte paulista, encosta da
Serra do Mar, uma das regiões de maior suscetibilidade a deslizamento do país, e
palco de um dos maiores desastres de movimento de massa da história brasileira,
em 1967. Há relevo crítico, ocupação em encosta, chuva orográfica intensa e uma
prefeitura que **já é cliente e já usa a plataforma**.

Ou seja: o piloto não precisa de venda nova nem de integração do zero. Precisa
de alguns nós instrumentando taludes já mapeados como de risco pela própria
plataforma.

### 4.7 Mudança no modelo de negócio

Este é o ponto de maior efeito sobre o valor do produto final.

| | Hoje | Com o Sentinela |
|---|---|---|
| Natureza | Software e integração de dados de terceiros | Solução completa: hardware + software + operação |
| Receita | Licença/serviço | Licença + equipamento + **recorrência** de telemetria, manutenção e calibração |
| Dado | Majoritariamente público, disponível a qualquer concorrente | **Proprietário**, gerado pela própria rede |
| Barreira | Integração e interface, replicáveis | Rede física instalada e série histórica local |
| Posição | Fornecedor de sistema | Operador de infraestrutura de monitoramento |

O ponto estratégico: **uma plataforma que só integra dados públicos é, em
princípio, replicável por um concorrente com bons desenvolvedores.** Uma rede
física instalada em encostas, com anos de série local calibrada, não é. O
hardware não vale pelo hardware — vale por criar dado que ninguém mais tem.

### 4.8 O mesmo tronco serve a outros riscos da carteira

A plataforma já monitora queimada, inundação e onda de calor. A mesma malha de
nós, trocando o conjunto de sensores, atende:

- **Inundação** — régua de nível em curso d'água, com o mesmo transporte
- **Queimada** — temperatura, umidade e índice de risco de fogo in situ
- **Onda de calor** — temperatura e umidade em pontos urbanos, incluindo ilhas
  de calor, que é tema geoespacial clássico

Um investimento de plataforma, vários produtos verticais. Isso muda
substancialmente o retorno do esforço de engenharia.

---

## 5. O que isso exige do projeto

Consequências que já entram nas decisões técnicas:

1. **Padrões abertos desde o começo** (OGC SensorThings, CSV/KML, metadados
   INDE) — integração e não-aprisionamento são argumento de venda pública
   (ver CONFORMIDADE.md §5 e §6).
2. **Homologação Anatel entra no cronograma comercial** — é condição para
   vender equipamento, e o prazo é de meses (CONFORMIDADE.md §1.2, item C-01).
3. **O nó precisa ser barato e durar anos**, senão o modelo de implantação em
   escala não fecha — o que sustenta ADR-004 (STM32WLE5).
4. **Vistoria e sensor devem ser desenhados como um ciclo**, não como módulos
   separados.

---

## 6. Para validar internamente

Perguntas que só a empresa responde, e que mudam a proposta:

- A plataforma já ingere alguma fonte de sensor em campo, ou é toda de dados
  remotos e de terceiros?
- Qual o formato e a via de ingestão do TerraMA² na integração atual?
- O módulo de Vistoria tem API, ou a priorização teria que ser manual no início?
- Existe demanda ou reclamação registrada de cliente sobre **falso positivo** de
  alerta? Se existir, é a porta de entrada mais forte da proposta.
- Há apetite para hardware, com o que ele implica — estoque, garantia,
  assistência, homologação?

Essa última é a pergunta de fundo: passar a vender equipamento muda a operação
da empresa, não só o produto. Vale entrar na apresentação de forma explícita, em
vez de deixar aparecer depois como surpresa.
