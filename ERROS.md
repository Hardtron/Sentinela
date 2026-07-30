# Registro de erros e armadilhas

Objetivo: **não repetir investigação já feita.** Erro resolvido aqui não
volta a custar tempo.

Registrar também as armadilhas conhecidas *antes* de tropeçar nelas — a seção
final existe para isso.

Formato:

```
### E-NNN — Título

**Contexto:** onde apareceu
**Sintoma:** mensagem ou comportamento exato
**Causa:** o que estava realmente acontecendo
**Solução:** o que resolveu
**Status:** resolvido | contornado | aberto
```

---

## Erros encontrados

### E-001 — Falha ao ler a flash em 460800 baud

**Contexto:** dump da flash da `HTC-01` com esptool, 30/07/2026.
**Sintoma:** `A fatal error occurred: Invalid head of packet (0xFF): Possible serial noise or corruption.` logo após `Changing baud rate to 460800`.
**Causa:** o CP2102 não sustenta 460800 de forma confiável neste enlace USB.
**Solução:** usar `--baud 230400`. Os 4 MB saíram íntegros em ~196 s (171 kbit/s).
**Status:** resolvido.

> Regra prática: **230400 é o teto confiável** para essas placas. Não insistir
> em 460800 nem 921600.

---

### E-002 — `git@github.com: Permission denied (publickey)`

**Contexto:** preparação para publicar o repositório, 30/07/2026.
**Sintoma:** o teste `ssh -T git@github.com` retorna permissão negada.
**Causa:** existe chave `~/.ssh/id_ed25519.pub` na máquina, mas ela **não está
autorizada na conta do GitHub**. Não há `gh` CLI nem `GITHUB_TOKEN`.
**Solução:** adicionar a chave pública em GitHub → Settings → SSH and GPG keys.
É ação de conta, precisa ser feita pelo titular.
**Status:** aberto — pendência P-001.

---

### E-003 — Placa "muda" no serial após o boot

**Contexto:** primeira inspeção da `HTC-01`, 30/07/2026.
**Sintoma:** o serial mostra o log do bootloader ROM e para em
`entry 0x400802e4`. Nada depois, em nenhum baud rate testado.
**Causa:** **não é defeito.** O firmware de fábrica da Heltec (FactoryTest) não
imprime no serial durante a operação normal.
**Solução:** nenhuma necessária. Identificação foi feita por dump da flash e
extração de strings (`HelTec_AutoMation`, `LoRa Initial success!`).
**Status:** resolvido — comportamento esperado.

---

### E-004 — Aviso de OpenSSL no PlatformIO

**Contexto:** qualquer comando `pio`.
**Sintoma:** `NotOpenSSLWarning: urllib3 v2 only supports OpenSSL 1.1.1+,
currently the 'ssl' module is compiled with 'LibreSSL 2.8.3'`.
**Causa:** o Python 3.9 do sistema no macOS é compilado com LibreSSL.
**Solução:** nenhuma — é **cosmético**, o PlatformIO funciona. Só se tornaria
relevante se houvesse falha de download; nesse caso, instalar Python via
Homebrew e recriar o venv.
**Status:** contornado — ignorar.

---

## Armadilhas conhecidas (ainda não encontradas)

Registradas preventivamente. Se alguma se manifestar, promover para a seção
acima com o número de erro.

### A-001 — GPIO 12 impede o boot

Strapping pin (MTDI). Nível alto no boot seleciona 1,8 V para a flash e a placa
não sobe. **Não usar para sensores**, ou garantir pull-down externo.

### A-002 — GPIO 34–39 são somente entrada

Não têm pull-up interno e não podem ser saída. Vale para os pinos livres 36, 38
e 39 — e lembrar que 34 e 35 já são DIO2/DIO1 do rádio.

### A-003 — Transmitir sem antena danifica o PA

Nunca energizar o rádio em transmissão sem antena conectada.

### A-004 — Vext é ativo em nível BAIXO

`digitalWrite(21, LOW)` **liga** a alimentação dos periféricos. Invertido em
relação à intuição.

### A-005 — Deep sleep da Heltec V2 consome ~1 mA

Regulador e CP2102 permanecem alimentados. Não tirar conclusão de autonomia de
campo a partir de medição feita nesta placa (ADR-004).

### A-006 — Faixa 907,5–915 MHz não é permitida no Brasil

Anatel libera 902–907,5 e 915–928 MHz para radiação restrita. Conferir a
frequência antes de qualquer transmissão (ADR-003).

### A-007 — Deriva térmica do inclinômetro gera falso positivo

MEMS deriva com temperatura, e talude exposto ao sol varia dezenas de graus por
dia. Sem compensação térmica, o ciclo diário vira "movimento". É a principal
fonte de falso positivo esperada (RC-09).

### A-008 — Sensor travado no I2C do OLED derruba o diagnóstico

Por isso sensores externos vão em `Wire1` (sugerido GPIO 22/23), separados do
barramento do display.
