# Frente 4 — Maturidade para depósito de patente

Análise da distância entre o estado atual do projeto e as exigências do INPI,
em escala de três níveis.

> **Este documento não substitui agente de propriedade industrial.** Ele
> organiza a informação para que a consulta profissional seja curta e produtiva.
> Proveniência conforme [REFERENCIAS.md](REFERENCIAS.md).

---

## 1. O que o INPI exige

Sob a **Lei nº 9.279/1996 (LPI)**, patente de invenção exige três requisitos
cumulativos **[N]**:

| Requisito | Significado |
|---|---|
| **Novidade** | Não estar compreendida no **estado da técnica** — tudo tornado acessível ao público antes do depósito |
| **Atividade inventiva** | Não decorrer **de maneira evidente** do estado da técnica para um técnico no assunto |
| **Aplicação industrial** | Poder ser utilizada ou produzida em qualquer tipo de indústria |

Somado a isso, a **suficiência descritiva**: a descrição precisa ser clara e
completa a ponto de **permitir a reprodução por um técnico no assunto** **[N]**.

### Duas vias, e a escolha importa

| | Patente de Invenção | Modelo de Utilidade |
|---|---|---|
| Objeto | Solução nova para problema técnico | **Objeto de uso prático** com nova forma ou disposição |
| Exigência inventiva | **Atividade** inventiva (maior) | **Ato** inventivo (menor) |
| Resultado exigido | — | **Melhoria funcional** no uso ou na fabricação |
| Vigência | **20 anos** do depósito | **15 anos** da concessão |

**[N]** — [LPI](https://www.planalto.gov.br/ccivil_03/leis/l9279.htm),
[Diretriz de Exame de MU do INPI](https://www.gov.br/inpi/pt-br/servicos/patentes/consultas-publicas/arquivos/diretriz_de_mu_versao_2_original.pdf).

O Modelo de Utilidade é via realista para o **arranjo físico da Atalaia**
(separação estrutural entre medição e antena, ancoragem por ponteira cravada).
A Patente de Invenção é a via para o **método de referência distribuída**.

---

## 2. A escala de três níveis

| Nível | Nome | Significado |
|---|---|---|
| **N1** | **Conceito documentado** | A ideia existe, está descrita e datada. Não sustenta depósito |
| **N2** | **Prova de conceito com evidência** | Implementado e medido. Sustenta depósito, com risco de exame |
| **N3** | **Pronto para depósito** | Anterioridade pesquisada, reivindicações redigidas, suficiência atendida |

---

## 3. Onde cada candidato está hoje

### Candidato A — Referência distribuída para manutenção **[o mais forte]**

Método que usa a mediana da própria frota como referência de irradiância para
separar perda local de variação climática, acionando manutenção sem sensor de
referência (MANUTENCAO.md §4).

| Aspecto | Situação | Nível |
|---|---|---|
| Conceito descrito | Documentado, com mecanismo e justificativa | **N2** |
| Aplicação industrial | Clara — manutenção de rede de sensores | **N3** |
| Suficiência descritiva | Método descrito; **falta a formulação completa** com limiares e tratamento de exceção | **N2** |
| **Novidade** | **Não pesquisada formalmente** | **N1** |
| Atividade inventiva | Plausível, não avaliada por profissional | **N1** |
| Implementação | **Não implementado** — não há frota | **N1** |
| Evidência experimental | **Nenhuma** | **N1** |

**Nível consolidado: N1–N2.** O conceito é bom e está datado no repositório; o
que falta é **busca de anterioridade** e **implementação com dado real**.

### Candidato B — Arranjo estrutural da Atalaia

Separação entre elemento de medição engastado e antena elevada, com ancoragem
por ponteira cravada dentro do horizonte mobilizável.

| Aspecto | Situação | Nível |
|---|---|---|
| Conceito descrito | Documentado com justificativa quantitativa | **N2** |
| **Fundamentação técnica** | **Forte** — deflexão calculada sobre NBR 6123 | **N3** |
| Aplicação industrial | Clara | **N3** |
| Novidade | **Duvidosa** — arranjo possivelmente já praticado | **N1** |
| Protótipo físico | **Não construído** | **N1** |

**Nível consolidado: N1–N2**, com **novidade sob suspeita**. Via mais provável:
Modelo de Utilidade, se houver forma ou disposição nova com melhoria funcional
demonstrável.

### Candidato C — Integração geoespacial de alerta

**Nível: N1.** Provavelmente **não patenteável** — é integração de técnicas
conhecidas, e métodos de apresentação de informação enfrentam restrição. Protege-se
melhor por **segredo industrial e vantagem de execução**, não por patente.

---

## 4. O que o projeto já tem a favor

Isto não é pouco, e vale reconhecer:

**Registro datado e rastreável.** O repositório documenta cada decisão com
justificativa, data e autoria — 20+ commits com mensagens substantivas, log de
sessões, ADRs. Para demonstrar **quando** e **por quem** a contribuição surgiu,
isso é material de primeira qualidade.

**Separação explícita entre nosso e estado da técnica.** A política de
proveniência (REFERENCIAS.md) já marca o que é medido por nós, o que é norma e o
que é literatura. **Essa fronteira é a primeira coisa examinada** — e a maioria
dos projetos precisa reconstruí-la retroativamente.

**Suficiência descritiva em construção.** ANCORAGEM.md, PROPAGACAO.md e
MANUTENCAO.md descrevem mecanismo, dimensionamento e justificativa em nível que
se aproxima do exigido para reprodução por técnico no assunto.

**Sigilo preservado.** O repositório é privado e não houve divulgação pública.
**A opção de depósito está intacta** — e isso é frágil: uma apresentação, um
artigo ou o painel publicado pode comprometer a novidade.

---

## 5. O que falta — e é isto que responde à sua pergunta

**Não, o projeto ainda não atinge o mínimo para depósito.** Falta o essencial:

| Lacuna | Peso | Por quê |
|---|---|---|
| **Busca de anterioridade** | **Bloqueante** | Sem saber o estado da técnica, não há como afirmar novidade. É o primeiro passo, não o último |
| **Implementação e evidência** | **Alto** | O candidato mais forte não foi implementado nem testado. Não há frota, não há dado |
| Reivindicações redigidas | Alto | Exige agente de PI |
| Definição de titularidade | **Alto** | Projeto vinculado à empresa? Invenção de empregado? **Resolver antes** |
| Orçamento e estratégia | Médio | Depósito nacional, PCT, prazos |

### Ordem correta das ações

1. **Busca de anterioridade** — INPI, Espacenet, Google Patents. Pode ser feita
   por você mesmo em caráter preliminar, com termos como *distributed reference
   soiling detection*, *sensor network self-referencing maintenance*,
   *photovoltaic soiling detection without reference cell*. **Se houver
   anterioridade, o assunto se encerra e economiza-se muito.**
2. **Consulta a agente de PI** — com este documento em mãos, é uma conversa
   curta.
3. **Resolver titularidade** com a empresa, **antes** de qualquer depósito.
4. **Implementar e medir** o candidato A com frota real.
5. **Depositar antes de divulgar.**

---

## 6. Veredito por candidato

| Candidato | Nível | Recomendação |
|---|---|---|
| **A — Referência distribuída** | **N1–N2** | **Perseguir.** Busca de anterioridade **agora**; é barata e decide tudo |
| **B — Arranjo da Atalaia** | N1–N2 | Avaliar como **Modelo de Utilidade** após protótipo físico |
| **C — Integração geoespacial** | N1 | **Não patentear.** Proteger por execução e segredo |

**Resposta direta à pergunta:** o projeto está no **Nível 1 a 2 de 3**. Tem
conceito documentado, datado e bem fundamentado — o que é mais do que a maioria
dos projetos nesta fase tem. Mas **não atinge o mínimo para depósito**, porque
falta a busca de anterioridade e a implementação do candidato mais forte.

**A distância até o N3 é menor do que parece** e depende de duas coisas: uma
busca de anterioridade, que custa tempo e não dinheiro; e implementar o método
de referência distribuída quando houver frota — o que já está previsto para a
fase 3.

> **Alerta de prazo.** Divulgação pública antes do depósito compromete a
> novidade. Isso inclui o painel para a Geopixel, apresentações e publicação do
> repositório. A LPI prevê **período de graça de 12 meses** para divulgação pelo
> próprio inventor **[N]** — **[?]** confirmar aplicabilidade com agente antes
> de contar com ele.

---

## 7. Pendências desta frente

| ID | Item | Situação |
|---|---|---|
| **PT-01** | **Busca de anterioridade** — INPI, Espacenet, Google Patents | **[?] primeiro passo** |
| PT-02 | Consulta a agente de PI com este documento | **[?]** |
| PT-03 | Definir titularidade com a empresa | **[?] antes do depósito** |
| PT-04 | Confirmar período de graça de 12 meses e seu alcance | **[?]** |
| PT-05 | Implementar referência distribuída e gerar evidência | Fase 3 |
| PT-06 | Avaliar Modelo de Utilidade para o arranjo físico | Após protótipo |
