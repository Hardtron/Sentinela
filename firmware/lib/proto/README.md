# lib/proto — codificação de payload

Compartilhada entre firmware e backend. **Esta é a fronteira que torna a
migração de enlace barata** (ADR-002): trocando LoRa P2P por LoRaWAN, o payload
não muda, e portanto o ingestor, o banco e o dashboard não mudam.

## Restrições de projeto

- **Orçamento de tamanho: ≤ 20 bytes.** Em SF10 há ~51 bytes úteis por quadro;
  em SF12, menos. Tempo no ar é bateria e é ocupação de canal.
- **Versionado.** Todo quadro carrega versão de esquema. Nós em campo não são
  atualizados todos no mesmo dia; backend precisa decodificar versões antigas.
- **Espaço reservado para autenticação** desde já, mesmo sem implementar na
  Fase 0 (RC-11). Em LoRaWAN isso vem da spec; no P2P, não.
- **Sem ponto flutuante.** Inteiros com escala fixa documentada.
- **Estado de sensor é parte do payload**, não implícito: sensor falho precisa
  ser distinguível de leitura válida (RC-07). Valor plausível porém errado é
  pior que valor ausente.

## Conteúdo previsto (Fase 1)

- Definição dos quadros: telemetria, evento, heartbeat, saúde do nó
- Codificador em C++ para o firmware
- Decodificador em Python para o ingestor
- Vetores de teste compartilhados pelos dois lados

## Estado atual

Vazio. A Fase 0 usa um quadro provisório de ping-pong declarado em
`firmware/src/main.cpp`, que **não** é o protocolo definitivo.
