# Requisitos de confiabilidade e alerta

## Premissa

Sistema de alerta de desastre tem **custo de erro assimétrico**: falso negativo
custa vidas, falso positivo custa credibilidade — e credibilidade perdida
produz falso negativo mais tarde, quando o aviso verdadeiro for ignorado.

Os requisitos abaixo derivam disso e valem desde a fase 0, porque decisões
tomadas no bring-up (como o nó se comporta sem contato com o gateway) já
dependem deles.

## Posicionamento

**RC-00.** O Sentinela é sistema de **apoio à decisão** da Defesa Civil.
Não aciona evacuação de forma autônoma e não substitui julgamento técnico.
Qualquer material de divulgação deve refletir isso.

## Confiabilidade

**RC-01 — Heartbeat obrigatório.** Todo nó transmite em intervalo definido
mesmo sem evento. Silêncio é informação: nó que não fala está em falha até
prova em contrário.

**RC-02 — Detecção de nó silencioso.** O servidor alerta sobre ausência de
heartbeat. Um nó morto em talude crítico é uma falha de segurança, não um
detalhe de manutenção.

**RC-03 — Telemetria de saúde.** Tensão de bateria, RSSI, SNR, contador de
reinícios e temperatura interna sobem junto com os dados. Degradação precisa
ser visível antes da falha.

**RC-04 — Watchdog.** Watchdog de hardware habilitado. Firmware travado que
mantém o rádio silencioso é indistinguível de nó destruído — e o RC-02 cobre
isso, mas o nó deve tentar se recuperar sozinho primeiro.

**RC-05 — Autonomia de decisão.** O nó avalia sua regra crítica localmente e
permanece funcional sem enlace (ADR-006).

**RC-06 — Persistência de estado.** Acumulados e referência de calibração
sobrevivem a reinício (NVS). Um reset não pode zerar a chuva acumulada de 72 h.

**RC-07 — Sem falha silenciosa de sensor.** Sensor que retorna valor fixo,
fora de faixa ou não responde é reportado como falho. Valor plausível porém
errado é pior que valor ausente.

## Alerta

**RC-08 — Alerta local independente.** Sinalização local (sirene/luz), quando
houver, é acionada pelo nó, sem depender de downlink.

**RC-09 — Confirmação cruzada.** Alerta de movimento exige corroboração —
persistência temporal e, quando possível, correlação com chuva acumulada ou
com nó vizinho. Ver nota de calibração em SENSORES.md: ciclo térmico diário é
a principal fonte esperada de falso positivo.

**RC-10 — Rastreabilidade.** Todo alerta guarda os dados brutos que o
originaram. Alerta que não pode ser auditado depois não sustenta decisão
pública.

**RC-11 — Integridade.** Payload autenticado. Em LoRaWAN isso vem da spec
(AES-128, contador anti-replay); no P2P das fases 0–1, o protocolo deve
reservar espaço para autenticação desde o início, mesmo que ainda não
implementada — ver `lib/proto/`.

## Fora de escopo declarado

- Previsão meteorológica própria (consumir dados públicos, não gerar).
- Detecção de sismos regionais (ver SENSORES.md).
- Acionamento automático de evacuação (RC-00).
