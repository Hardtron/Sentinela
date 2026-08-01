# Parâmetros, proveniência e uso decisório

Este documento define como o Sentinela registra parâmetros sem transformar
estimativa em regra operacional. Complementa a política de proveniência de
[REFERENCIAS.md](REFERENCIAS.md) e os requisitos RC-10 e RC-18.

## Estado não é evidência

Cada critério de comissionamento possui um estado explícito:

- `EXPERIMENTAL`: valor de bancada, ensaio ou hipótese ainda não aprovado para
  uso decisório fora do contexto em que foi medido;
- `INFORMATIVO`: pode contextualizar a interface, mas não aprova instalação nem
  dispara ação;
- `VALIDADO`: só pode ser atribuído depois da validação exigida pela própria
  fonte e por profissional ou instituição competente quando aplicável.

A migração 010 classifica conservadoramente os critérios existentes como
`EXPERIMENTAL`. Ela não promove nenhum número. Uma marca `[M]`, `[L]`, `[G]` ou
`[N]` descreve a origem; não prova, por si só, que o valor se aplica ao
município, talude, equipamento ou decisão em questão.

## Histórico e snapshots

`criterio_comissionamento_historico` preserva o baseline e alterações futuras.
Novos checklists recebem `criterio_snapshot`, contendo os critérios vigentes no
momento da submissão. Checklists anteriores à migração permanecem sem snapshot:
o catálogo atual não deve ser apresentado como se fosse o catálogo histórico.

Alarmes mantêm o JSON `evidencia` compatível e passam a declarar
`evidencia_versao` e `evidencia_proveniencia`. Esses campos preparam a cadeia de
custódia, mas não criam o gerador de alarmes que ainda falta.

## O que permanece pendente

- **Campo:** critérios de enlace, energia, vedação, manutenção e assinaturas de
  falha precisam dos ensaios previstos nos documentos do projeto.
- **Literatura/profissional habilitado:** correlação geotécnica, limiares locais
  e a releitura do RC-09 após o ADR-009.
- **Instituição:** quem pode promover um parâmetro, reconhecer/encerrar alarmes,
  política de retenção e níveis de serviço.
- **Implementação futura:** identidade institucional, regras locais no nó,
  ingestão dos quadros de sensor e abertura automática de alarmes.

Nenhuma dessas dependências pode ser substituída por valor padrão no código.
