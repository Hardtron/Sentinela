# Baseline operacional — Windows + GitHub

## Desenvolvimento

A estação local é Windows 11 Pro. Não é necessário manter Linux/WSL/Docker local.

- edição e feedback rápido: Windows;
- Python/PlatformIO local: quando conveniente ou quando USB/hardware exigir;
- Linux reproduzível: GitHub Actions;
- Linux interativo: Codespaces sob demanda;
- hardware: Raspberry Pi/placas/rádio em bancada ou campo;
- source: GitHub.

## O que o GitHub substitui

GitHub Actions substitui o Home Server para:

- verificação Python sem hardware;
- compilação de firmware sem upload;
- validação sintática do Docker Compose;
- checks determinísticos futuros.

GitHub Actions **não** substitui:

- banco persistente;
- MQTT persistente;
- painel sempre ativo;
- túnel até o Farol;
- USB/serial;
- rádio/LoRa;
- sensores/campo.

## Runtime legado no Home Server

A topologia anterior mantém TimescaleDB/PostGIS, ingestor, painel e túnel MQTT no Home Server. Como o servidor será desativado, essa superfície precisa de destino próprio e não deve ser movida para o notebook por conveniência.

Estado durante a transição:

```text
DEVELOPMENT_TOPOLOGY ............. migrating to Windows + GitHub
HOME_SERVER_CLONE ................ retiring
HOME_SERVER_PERSISTENT_RUNTIME ... BLOCKED_FOR_RUNTIME_MIGRATION
FIELD/RPI_RUNTIME ................ remains hardware-specific
```

O desenvolvimento pode ser tornado independente do Home Server antes da decisão final de runtime, mas nenhuma documentação deve declarar o backend persistente disponível após o desligamento sem evidência de uma nova implantação.

## Windows

Diretório sugerido: `C:\Dev\Sentinela`.

Feedback sem hardware:

```powershell
py -m venv .venv
.\.venv\Scripts\python -m pip install -r tools\requirements.txt -r backend\requirements.txt
.\.venv\Scripts\python tools\verifica.py
```

Para firmware, instale PlatformIO apenas se o trabalho local exigir compilação/USB. A compilação canônica sem hardware também roda no CI.

## Regra de retomada

Feature work só pode ser retomado depois que a PR de transição estiver integrada e o agente estiver usando este contrato. Trabalho que depende do backend persistente continua bloqueado até a migração específica de runtime.
