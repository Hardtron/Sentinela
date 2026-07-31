# Prompt para geração do painel (Gemini)

Prompt autocontido — traz todos os números fechados para que o modelo não precise
inferir nem inventar dado. Atualizar quando novos ensaios entrarem.

Fonte dos dados: [CAMPO.md](CAMPO.md), [PROPAGACAO.md](PROPAGACAO.md),
[ANCORAGEM.md](ANCORAGEM.md), [CONFORMIDADE.md](CONFORMIDADE.md).

---

```
Você é um designer de informação técnica. Gere um PAINEL VISUAL em HTML único,
autocontido (CSS e JS embutidos, sem CDN, sem fontes externas), apresentando os
resultados de engenharia de um projeto de rede de sensores.

## CONTEXTO

Projeto "Sentinela": rede de sensores LoRa para monitoramento de áreas de risco
de deslizamento, destinada a prefeituras e defesa civil no Brasil. Mede chuva
acumulada, saturação do solo e inclinação de talude, e cruza esses dados com
base geoespacial de suscetibilidade e população exposta. É sistema de APOIO À
DECISÃO — não aciona evacuação de forma autônoma.

Hardware de desenvolvimento: Heltec WiFi LoRa 32 V2 (ESP32 + SX1276), operando
em 916,8 MHz, SF9, BW 125 kHz, 17 dBm.

Público do painel: diretoria técnica de uma empresa de geotecnologia, com
formação em engenharia e geoprocessamento. Devem sair sabendo o que foi medido,
o que se concluiu e o que isso muda no produto.

## DADOS MEDIDOS — use exatamente estes valores

### Ensaio de campo (7 pontos, percurso urbano noturno, sereno e chuva fina)

Nó fixo em quintal murado, antena vertical a 1,5 m do solo.

| Ponto | Distância | Altitude | RSSI médio | Margem | Perda | Veredito |
|-------|-----------|----------|------------|--------|-------|----------|
| P0 | 14 m | 6,1 m | -85 dBm | 44 dB | 0% | APROVADO |
| P1 | 42 m | 9,6 m | -102 dBm | 27 dB | 0% | APROVADO |
| P2 | 96 m | 5,2 m | -116 dBm | 13 dB | 3,7% | LIMITE |
| P3 | 143 m | 5,6 m | -120 dBm | 9 dB | 7,4% | REPROVADO |
| P4 | 175 m | 6,7 m | -118 dBm | 11 dB | 8,0% | REPROVADO |
| P5 | 194 m | 16,7 m | -114 dBm | 15 dB | 4,5% | LIMITE |
| P6 | 193 m | 17,4 m | -114 dBm | 15 dB | 0% | LIMITE |

Modelo de propagação ajustado (pontos de altitude 5–10 m):
RSSI = -48,1 - 32,8*log10(d), expoente n = 3,28, resíduo RMS = 2,2 dB

### Achado 1 — Altura vence distância

P3/P4: média 159 m de distância, 6,2 m de altitude → -119 dBm, 7-8% de perda.
P5/P6: média 194 m (35 m MAIS LONGE), 17,0 m de altitude → -114 dBm, P6 com 0%.

Contra o modelo, os pontos altos ficaram +9 dB acima do previsto — valor
idêntico nos dois, o que descarta coincidência.

O modelo de dois raios previa 20*log10(17,0/6,2) = +8,8 dB. Medido: +9 dB.

### Achado 2 — Validação cruzada com a literatura

| Cenário | Expoente n |
|---------|-----------|
| Espaço livre (teórico) | 2,00 |
| Visada limpa, 923 MHz (literatura) | 2,31 |
| Floresta tropical, 923 MHz (literatura) | 3,22 |
| NOSSO ENSAIO — alvenaria esparsa | 3,28 |
| Vegetação densa / dossel alto | ~4,0 |

Conclusão: alvenaria esparsa e mata atenuam de forma comparável — ambos são
meios com obstruções distribuídas. Os dados urbanos servem como proxy do
cenário de encosta com mata.

### Achado 3 — Vento inviabiliza haste alta com inclinômetro

Deflexão angular no topo, vento de 72 km/h:

| Perfil | 1,5 m | 3 m | 4 m |
|--------|-------|-----|-----|
| Eletroduto 3/4" galvanizado | 0,08° | 0,68° | 1,61° |
| Eletroduto 1" galvanizado | 0,04° | 0,35° | 0,83° |
| Tubo 1.1/2" galvanizado | 0,02° | 0,17° | 0,39° |
| Tubo 2" galvanizado | 0,01° | 0,09° | 0,21° |
| PVC 50 mm | 1,19° | 9,52° | 22,58° |

O movimento lento (creep) que o sistema precisa detectar é de 0,1° a 0,5°.
Uma haste de 4 m produz 0,2° a 1,6° só de vento — encobre ou imita o sinal.

SOLUÇÃO ADOTADA: separar funções. Inclinômetro na BASE ENGASTADA (deflexão nula
por definição), antena no topo a 1,5 m. PVC descartado como elemento estrutural.

### Achado 4 — Onde investir altura

Em rampa uniforme, a folga da linha de visada no meio do vão vale
(h_sensor + h_gateway)/2 - h_vegetação. O desnível do terreno SE CANCELA.
Quem ajuda é o perfil côncavo; o convexo atrapalha.

Como as duas alturas têm o mesmo peso e o gateway é um para muitos nós:
+1 m no gateway equivale a +1 m em CADA sensor. Rede de 20 nós → 20x mais barato.

Altura de antena necessária no sensor (vegetação de 3 m):

| Vão | Gateway 6 m | Gateway 10 m | Gateway 15 m | Gateway 20 m |
|-----|-------------|--------------|--------------|--------------|
| 200 m | 4,9 m | 0,9 m | dispensa | dispensa |
| 500 m | 7,7 m | 3,7 m | dispensa | dispensa |
| 1000 m | 10,8 m | 6,8 m | 1,8 m | dispensa |
| 2000 m | 15,3 m | 11,3 m | 6,3 m | 1,3 m |

Alternativa: antena Yagi de 9 dBi no gateway rende o mesmo que haste de 4 m no
sensor, sem estrutura, sem vento e sem captor de raio sobre o talude.

### Spreading factor: alcance contra autonomia

| SF | Sensibilidade | Tempo no ar (11 bytes) | Custo relativo |
|----|---------------|------------------------|----------------|
| SF7 | -123,0 dBm | 41 ms | 1,0x |
| SF9 | -129,0 dBm | 169 ms | 4,1x |
| SF10 | -132,0 dBm | 289 ms | 7,0x |
| SF12 | -136,0 dBm | 1155 ms | 28,2x |

SF7 → SF12 rende 14 dB ao custo de 28x mais tempo de rádio ligado.
Uma haste rende 9 dB ao custo de ZERO energia.

### Alcance previsto (margem 20 dB, SF9, sensor a 1,4 m)

| Cenário | Nó fixo confinado (33 dB) | Gateway bem instalado (15 dB) |
|---------|---------------------------|-------------------------------|
| Visada limpa | 434 m | 2.713 m |
| Mata / alvenaria esparsa | 72-78 m | 262-291 m |
| Vegetação densa | 33 m | 96 m |

### Custo comparado (por nó)

- Estrutura de ancoragem do Sentinela: ~R$ 300
- Referência internacional SitkaNet (Alasca): US$ 940
- Soluções geotécnicas tradicionais: US$ 8.000 a 10.000 por sítio

### Lições de campo de projetos anteriores (SitkaNet)

- Falhas de transmissão correlacionaram com CHUVA INTENSA — o enlace degrada
  exatamente durante o evento que o sistema existe para monitorar
- Acelerômetro usado como detector de vibração gerou falsos alarmes e foi
  desativado
- Bateria durou 2-3 meses contra mais de 6 previstos
- Apenas 12 de 18 sensores de umidade forneceram dado confiável
- Alcance real de 2 a 2,5 km, somente com visada limpa

### Conformidade regulatória (Brasil)

- Homologação Anatel é OBRIGATÓRIA para comercialização (Lei 9.472/1997 e
  Resolução 715/2019) — processo de meses, entra no cronograma e no preço
- Faixas permitidas: 902-907,5 MHz e 915-928 MHz. A janela 907,5-915 MHz NÃO é
  permitida (Resolução Anatel 680/2017)
- Lei 12.608/2012 institui a Política Nacional de Proteção e Defesa Civil
- ABNT NBR 11682 (estabilidade de encostas) exige responsável técnico com ART
- ABNT NBR 5419 (proteção contra descargas) — haste metálica em encosta é captor
- LGPD aplicável ao cruzamento com dados de população exposta

## ESTRUTURA DO PAINEL

1. Cabeçalho com o nome do projeto e uma frase de posicionamento
2. Faixa de números-chave: n = 3,28 | +9 dB por 11 m | RMS 2,2 dB | 7 pontos
3. Ensaio de campo: tabela dos 7 pontos + gráfico RSSI x distância, destacando
   visualmente que P5/P6 estão acima da curva apesar de mais distantes
4. Validação cruzada com a literatura: gráfico de barras dos expoentes,
   destacando a proximidade entre 3,28 (nosso) e 3,22 (floresta tropical)
5. O conflito vento x medição: gráfico comparando deflexão por altura e material
   contra a faixa do creep (0,1-0,5°), deixando claro onde a haste inviabiliza
6. Diagrama do nó: estaca cravada, inclinômetro na base, antena a 1,5 m
7. Tabela de decisão de altura (vão x altura do gateway)
8. Trade-off spreading factor: alcance contra tempo no ar
9. Comparativo de custo
10. Conformidade: lista objetiva, destacando a homologação Anatel como condição
11. Próximos passos

## DIRETRIZES VISUAIS

- Idioma: português do Brasil
- Densidade alta de informação, estética de relatório de engenharia — não de
  apresentação comercial. Sem gradientes chamativos, sem ícones decorativos
- Paleta sóbria, com uma cor de destaque para os achados principais. Use
  vermelho/âmbar/verde apenas para os vereditos REPROVADO/LIMITE/APROVADO
- Gráficos em SVG puro, desenhados no próprio HTML. Não use bibliotecas
- Layout responsivo em CSS Grid; tabelas largas com rolagem horizontal própria
- Suporte a tema claro e escuro via prefers-color-scheme
- Cada seção deve ter uma frase curta de interpretação — o número sozinho não
  comunica

## RESTRIÇÕES

- NÃO invente dados, medições ou fontes. Use apenas os valores acima
- NÃO arredonde de forma que altere a conclusão
- Onde algo é estimativa ou vem da literatura, rotule como tal
- Deixe explícito no rodapé que é sistema de apoio à decisão, que não substitui
  o julgamento técnico da defesa civil nem aciona evacuação automaticamente
- O painel precisa funcionar aberto direto do arquivo, sem servidor
```
