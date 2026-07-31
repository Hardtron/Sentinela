# Frente 3 — Concorrência e originalidade

O objetivo declarado desta análise: **evitar desenvolver o que já existe e já é
sólido.** Este documento é deliberadamente desfavorável ao projeto — é assim que
ele presta serviço.

> **Proveniência.** Segue [REFERENCIAS.md](REFERENCIAS.md). Preços marcados
> **[E]** são estimativa; o setor **não publica tabela**.

---

## 1. O que já existe, e é sólido

### Instrumentação geotécnica sem fio — internacional

| Empresa | Produto | Posição |
|---|---|---|
| **Worldsensing** | Tiltmeter sem fio, rede LoRa própria | Líder consolidado. Bateria tipo D, **até 10 anos** de operação **[L]** |
| **Senceive** | Tilt sensors, nó de deslocamento óptico | **Até 15 anos** de bateria; **explicitamente posicionado para taludes de barragens de rejeito, cavas e pilhas** **[L]** |
| Sisgeo, Geokon, Encardio-Rite | Inclinômetros MEMS in-place, IPI | Instrumentação clássica, resolução 0,0025° **[L]** |

**É preciso registrar com clareza: estes produtos são maduros, têm autonomia
superior à que projetamos e já atendem exatamente o caso de uso.** A Senceive
descreve tailings dams em material de produto. Não há lacuna tecnológica a
explorar contra esses fornecedores.

### Brasil

Empresas de instrumentação e monitoramento geotécnico atuando em território
nacional incluem **Mafrigeo**, **Auro Tecnologia**, **CPE Tecnologia** e **BVP
Engenharia** **[L]**. O mercado brasileiro de barragens já usa sensores IoT,
radar, piezômetros automatizados e câmeras 3D com transmissão em tempo real
([Revista Minérios](https://revistaminerios.com.br/sensores-iot-monitorar-barragens-mineracao/)) **[L]**.

**Há também ao menos uma startup brasileira** com solução IoT para previsão de
incidentes em encostas, barragens e alagamentos **[L]**. **[?]** Identificar
nome, estágio e clientes — item C-05.

### Referência de custo

| Referência | Custo por ponto | Fonte |
|---|---|---|
| Solução geotécnica tradicional | **US$ 8.000 – 10.000** por sítio | SitkaNet **[L]** |
| SitkaNet (rede acadêmica de baixo custo) | **US$ 940** por nó | **[L]** |
| Atalaia — estrutura de ancoragem | ~R$ 300 **[E]** | ANCORAGEM.md |
| Atalaia — alvo de preço instalado | R$ 3.000 – 6.000 **[E]** | MERCADO_MUNICIPIOS.md |

Worldsensing e Senceive **não publicam preço** — venda consultiva. **[?]**
Obter cotação real é o item mais importante desta frente (C-01): sem ele, todo o
posicionamento de preço é especulação.

---

## 2. Onde o Sentinela NÃO é original

Sendo franco, para não perdermos tempo:

- **Sensor de inclinação sem fio para talude** — existe, maduro, com autonomia
  melhor que a nossa.
- **LoRa/LoRaWAN para monitoramento ambiental** — amplamente usado.
- **Alerta por chuva acumulada** — a curva de Tatizana é de 1987 e o CEMADEN
  opera assim há mais de uma década **[L][G]**.
- **Plataforma de visualização de risco** — a própria Geopixel já tem, e há
  concorrentes.
- **Nó de baixo custo com ESP32 e sensores** — dezenas de projetos acadêmicos,
  incluindo o SitkaNet.

**Se a proposta fosse "construir um sensor de inclinação sem fio", a
recomendação seria comprar da Worldsensing e integrar.** Seria mais rápido, mais
barato em engenharia e com autonomia superior.

---

## 3. Onde há originalidade defensável

Três candidatos, em ordem de força:

### 3.1 Referência distribuída para diagnóstico de manutenção — **forte**

Usar a **mediana da própria frota** como referência de irradiância, para separar
perda local (sujeira, sombra) de variação climática, **dispensando painel de
referência ou sensor óptico** (MANUTENCAO.md §4).

O estado da técnica em fotovoltaica usa painel de referência limpo ou sensor
dedicado **[L]** — ambos com custo por ponto. **Não localizei, na busca
realizada, solução comercial de monitoramento geotécnico que use a própria rede
de nós como referência mútua para acionar manutenção.**

É o candidato mais forte a reivindicação. Ver [PATENTES.md](PATENTES.md).

### 3.2 Integração nativa com base geoespacial de risco — **moderada**

Não a telemetria, e sim o **cruzamento** com carta de suscetibilidade, cadastro
de edificações e população exposta, produzindo alerta com exposição quantificada
(GEOPIXEL.md §4). Os fornecedores de instrumentação entregam dado de sensor; a
tradução para decisão de defesa civil fica com o cliente.

Originalidade **de integração**, não de componente — dificilmente patenteável,
mas comercialmente defensável e difícil de copiar sem competência geoespacial.

### 3.3 Separação estrutural entre medição e antena — **fraca a moderada**

O arranjo com inclinômetro na base engastada e antena no topo, justificado pela
análise de deflexão (ANCORAGEM.md §2), resolve um conflito real. Mas é solução
de engenharia possivelmente já praticada. **[?]** Verificar no estado da técnica.

---

## 4. Conclusão honesta

**O hardware não é o diferencial, e perseguir superioridade de hardware é o
caminho errado.** Worldsensing e Senceive fazem melhor, há mais tempo, com
autonomia maior.

O que o projeto tem que eles não têm:

| Vantagem | Natureza |
|---|---|
| **Canal já aberto** com prefeituras | Comercial |
| **Competência geoespacial** para traduzir dado em decisão | Técnica |
| **Custo por ponto** viável para adensar malha | Econômica |
| **Referência distribuída** de manutenção | Possivelmente inventiva |
| Produto nacional — câmbio, suporte, licitação | Estrutural |

**Reposicionamento que decorre daí:** o Sentinela não é "mais um sensor de
inclinação". É **uma malha densa e barata de instrumentação, integrada a uma
base geoespacial de risco, com manutenção autodiagnosticada.** Concorre com o
*nada* que existe hoje na maioria dos taludes municipais — não com o instrumento
premium que já está na barragem crítica.

**Isso também sugere uma decisão de arquitetura:** manter o sistema capaz de
**ingerir dados de instrumentos de terceiros**. Se um cliente já tem
Worldsensing instalado, a plataforma deve consumir esse dado em vez de exigir
substituição. Reforça a decisão de padrões abertos (ADR-005, OGC SensorThings) e
transforma concorrente em complemento.

---

## 5. Pendências desta frente

| ID | Item | Situação |
|---|---|---|
| **C-01** | **Obter cotação real de Worldsensing e Senceive** — sem isso o preço é especulação | **[?] crítico** |
| C-02 | Levantar preço praticado por Mafrigeo, Auro, CPE e BVP | **[?]** |
| C-03 | Busca de anterioridade formal no INPI e Espacenet sobre referência distribuída | **[?]** — ver PATENTES.md |
| C-04 | Verificar estado da técnica sobre separação medição/antena | **[?]** |
| C-05 | Identificar a startup brasileira de IoT para encostas | **[?]** |
| C-06 | Avaliar viabilidade de ingerir dados de instrumentos de terceiros | **[?]** |
