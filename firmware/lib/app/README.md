# lib/app — lógica de aplicação

Máquina de estados do nó, avaliação de limiares e decisão de alerta.

## Regra desta camada

**Nenhum código específico de chip.** Sem `#include <Arduino.h>`, sem
`digitalWrite`, sem registrador. Tudo o que precisar de hardware entra por
interface definida em `lib/hal/`.

O motivo está no ADR-004: os nós de campo vão migrar de ESP32 para STM32WLE5.
Se a lógica de decisão estiver colada no Arduino, a migração vira reescrita.

## Consequência prática

Esta camada compila e roda no host, o que permite testar a lógica de alerta com
séries de chuva e inclinação simuladas — sem hardware e sem esperar um evento
real. Para um sistema em que o caso crítico é raro e não pode ser reproduzido em
campo, isso é a única forma séria de validar a decisão.

## Conteúdo previsto (Fase 1)

- Acumuladores de chuva com janelas de 24 h / 72 h / 96 h (RC-06)
- Limiar intensidade-duração
- Detecção de deriva de inclinação com compensação térmica (A-007)
- Confirmação cruzada antes de alertar (RC-09)
- Máquina de estados: normal → observação → atenção → alerta
