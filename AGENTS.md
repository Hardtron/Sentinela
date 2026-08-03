# Regra global de trabalho e sincronização

<!-- REGRA_GLOBAL_SINCRONIZACAO_V1 -->

Estas regras se aplicam a qualquer equipe, pessoa ou agente automatizado que
trabalhe neste repositório. Regras específicas do projeto continuam valendo e
devem ser lidas depois deste arquivo.

## Topologia dos ambientes

- O remoto `origin` é a autoridade compartilhada sobre quais commits estão
  publicados.
- O Home Server mantém os clones canônicos de desenvolvimento e validação.
- Clones no Mac, Windows ou em outras máquinas são espaços auxiliares. Eles não
  se tornam canônicos apenas por terem arquivos mais novos no diretório.
- Arquivos ignorados pelo Git — dados reais, credenciais, logs e artefatos
  gerados — têm ciclo de vida próprio e não devem ser confundidos com código.

## Antes de qualquer leitura técnica ou alteração

No Home Server, execute a partir do repositório:

```bash
/DATA/Projects/Geo_Quality/scripts/projetos iniciar
```

Fora do Home Server, faça o equivalente:

```bash
git status --short --branch
git fetch --prune origin
git rev-list --left-right --count HEAD...@{upstream}
```

Só comece a trabalhar quando souber explicitamente:

1. qual é o repositório e a branch atuais;
2. se a árvore está limpa;
3. se há commits locais ainda não publicados;
4. se o clone está atrás ou divergiu do remoto.

Se estiver limpo e apenas atrás, atualize exclusivamente por fast-forward:

```bash
git pull --ff-only
```

Se houver alterações desconhecidas, commits não enviados ou divergência, não
sobrescreva, não faça `reset --hard` e não copie outra árvore por cima. Preserve o
estado numa branch/commit de segurança e só então reconcilie conscientemente.

## Durante o trabalho

- Nunca sincronize código por SMB, Syncthing, cópia integral de pasta ou `rsync`
  sobre uma árvore Git.
- Não misture mudanças independentes de equipes diferentes no mesmo commit.
- Antes de editar, leia os documentos de handoff, logs e regras específicas que
  existirem no repositório.
- Dados reais e segredos nunca entram no Git. Transporte de snapshots deve usar
  apenas os meios autorizados para o projeto.

## Antes de considerar a tarefa concluída

1. Execute as validações proporcionais ao projeto.
2. Registre decisões e limitações no log ou handoff aplicável.
3. Faça commit e push da branch correta.
4. No Home Server, execute:

```bash
/DATA/Projects/Geo_Quality/scripts/projetos finalizar
/DATA/Projects/Geo_Quality/scripts/projetos sync
```

`projetos finalizar` deve confirmar árvore limpa, zero commits a enviar e zero
commits a receber. Um clone offline não pode ser atualizado automaticamente: ele
deve ser registrado no handoff como ambiente ainda pendente, com o commit que
precisa receber.

## Handoff mínimo obrigatório

Toda entrega deve informar:

- repositório, branch e commit final;
- validações executadas e resultado;
- ambientes efetivamente atualizados;
- ambientes inacessíveis ou ainda pendentes;
- localização de qualquer branch/commit de segurança criado.
