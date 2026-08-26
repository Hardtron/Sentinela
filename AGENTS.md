# Sentinela — regras globais de trabalho e continuidade

Estas regras se aplicam a qualquer pessoa ou agente automatizado que trabalhe neste repositório.

## 1. Baseline operacional de desenvolvimento

- `origin` (`Hardtron/Sentinela`) é a autoridade compartilhada sobre commits publicados.
- A workstation de desenvolvimento é Windows 11 Pro.
- WSL, Ubuntu e Docker local **não são requisitos** de desenvolvimento.
- GitHub Actions em Linux é a validação reproduzível para código Python, firmware compilável e contratos do backend que não exijam hardware/estado real.
- GitHub Codespaces é Linux interativo sob demanda.
- O Raspberry Pi/Farol e as placas de campo continuam sendo ambientes de hardware/runtime; não são fontes canônicas de código.
- O Home Server deixa de ser clone canônico e está em retirada. Nenhuma nova dependência nele pode ser introduzida.
- Código circula somente por Git. Nunca sincronize árvores Git por SMB, Syncthing, cópia integral ou `rsync`.

Leia antes de trabalhar:

1. `docs/WORKSTATION_GITHUB_BASELINE.md`;
2. `README.md`;
3. `LOG.md` e `ERROS.md`;
4. documentação específica da frente em `docs/`.

## 2. Freeze da transição

Desenvolvimento funcional fica pausado até o encerramento formal da migração operacional. Durante o freeze, só altere portabilidade, CI, documentação, segurança ou superfícies necessárias para retirar a dependência do Home Server.

## 3. Preflight Git

Antes de editar:

```text
git status --short --branch
git fetch --prune origin
git rev-list --left-right --count HEAD...@{upstream}
```

Se estiver limpo e apenas atrás, use `git pull --ff-only`. Preserve divergências e trabalho desconhecido; nunca use `reset --hard` ou force-push para escondê-los.

## 4. Separação de execução

### Windows local

Use para edição, Python, ferramentas de análise, PlatformIO e interação com USB/hardware quando o dispositivo estiver fisicamente conectado ao notebook. Scripts de feedback local novos devem ser compatíveis com Windows sempre que não dependerem intrinsecamente de Linux.

### GitHub Actions

Use como gate canônico para verificações sem hardware: `tools/verifica.py`, compilação de firmware, validação de Compose/configuração e demais testes determinísticos. Resultado local não substitui CI.

### Codespaces

Use apenas se for necessário depurar comportamento Linux/container interativamente. Não mantenha estado único no Codespace.

### Hardware/runtime

Gravação de firmware, rádio, GPIO, LoRa, sensores e ensaios físicos exigem o hardware correspondente. O GitHub não substitui evidência de bancada/campo.

## 5. Backend persistente — atenção de transição

O backend descrito historicamente como TimescaleDB/PostGIS + ingestor + painel no Home Server é uma **dependência de runtime**, não uma carga de CI. GitHub Actions é efêmero e não pode substituir esse serviço persistente.

Enquanto o destino permanente desse backend não estiver migrado para edge/cloud apropriado, considere essa superfície `BLOCKED_FOR_RUNTIME_MIGRATION`. Não transfira banco, MQTT persistente ou serviços para o notebook Windows como solução permanente.

## 6. Segurança e produto

- O Sentinela é apoio à decisão; não automatiza evacuação.
- Dados reais, chaves LoRaWAN, credenciais, bancos, logs e artefatos operacionais não entram no Git.
- Critérios experimentais não podem ser apresentados como critérios geotécnicos oficiais.
- Evidência de CI, runtime e campo são categorias distintas.

## 7. Handoff mínimo

Toda entrega informa repositório, branch, SHA, validações, CI, hardware/runtime efetivamente exercido, ambientes não exercidos, riscos, bloqueios e próximo passo. Nenhum estado necessário à continuidade pode existir apenas no notebook, Home Server ou memória do agente.
