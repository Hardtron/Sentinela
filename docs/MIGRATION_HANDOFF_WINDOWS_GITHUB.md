# Handoff — migração Windows + GitHub

**Data:** 2026-08-26  
**Projeto:** `Hardtron/Sentinela`

## Escopo desta migração

O objetivo atual é deixar o **repositório e o desenvolvimento compatíveis** com
Windows 11 Pro + GitHub. Não é requisito manter o sistema Sentinela operacional
durante ou imediatamente após o desligamento do NODE-01/Home Server.

## Estado entregue

- Home Server/Mac removidos do contrato canônico de desenvolvimento;
- GitHub é a fonte de verdade;
- GitHub Actions cobre verificações Python/Compose/firmware independentes de hardware;
- descoberta serial local aceita portas `COM` no Windows para futura retomada de bancada;
- backend persistente atual (TimescaleDB/PostGIS/ingestor/painel/túneis) pode ficar offline;
- nenhuma tentativa foi feita de converter GitHub Actions em servidor persistente.

## Ações do agente ao retomar o projeto no futuro

1. clonar em `C:\Dev\Sentinela`;
2. ler `AGENTS.md`, este handoff e a documentação de arquitetura/hardware;
3. confirmar o CI hardware-independent verde;
4. instalar Python/PlatformIO no Windows quando a bancada voltar a ser necessária;
5. validar portas COM e compilação de firmware antes de conectar/energizar hardware real;
6. **antes de reativar o backend**, desenhar novo runtime persistente (cloud/edge/server dedicado) e migração de estado;
7. não assumir que o banco/ingestor/túneis do Home Server ainda existem;
8. preservar todas as regras de segurança de RF, hardware e decisão geotécnica.

## Critério para desligar NODE-01

O projeto **não bloqueia o desligamento**. Seu runtime pode permanecer
intencionalmente indisponível até uma futura rodada de infraestrutura. O que deve
estar preservado agora é código, documentação, histórico e capacidade de
reconstrução/desenvolvimento pelo GitHub.

## Fora do escopo

- migração do banco TimescaleDB/PostGIS;
- migração do MQTT/ingestor;
- painel operacional persistente;
- túneis até Raspberry Pi;
- dados operacionais vivos;
- nova topologia de produção/piloto.
