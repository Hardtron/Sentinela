# lib/hal — abstração de hardware

Uma implementação por plataforma. A camada `app/` enxerga apenas as interfaces.

```
hal/
  hal.h          Interfaces: Radio, SensorBus, Power, Clock, Storage
  esp32/         Implementação para Heltec V2 (desenvolvimento)
  stm32wl/       Implementação para RAK3172 (campo) — Fase 4
  host/          Implementação falsa para teste no computador
```

## Interfaces previstas

| Interface | Responsabilidade |
|---|---|
| `Radio` | Enviar e receber quadros; RSSI/SNR; potência e SF |
| `SensorBus` | I2C/SPI/ADC e contagem de pulso da báscula |
| `Power` | Sono profundo, despertar por RTC e por interrupção, tensão de bateria |
| `Clock` | Tempo monotônico e tempo de parede |
| `Storage` | Persistência de acumulados e calibração (RC-06) |

## Nota sobre a implementação `host/`

Existe para permitir que `app/` seja testada sem hardware. Não é código
descartável: é o que torna possível validar a lógica de alerta contra séries
sintéticas de chuva e movimento.

## Nota sobre energia

O porte para `stm32wl/` é o que viabiliza autonomia de anos. A Heltec V2
consome ~1 mA em deep sleep e serve apenas para desenvolvimento — nenhuma
conclusão de autonomia de campo deve ser tirada dela (armadilha A-005).
