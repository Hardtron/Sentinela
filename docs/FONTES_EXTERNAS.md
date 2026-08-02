# Fontes ambientais e territoriais externas

## Escopo e regra de segurança

Esta camada enriquece o contexto disponível à equipe técnica. Ela **não soma
provedores**, **não cria limiar** e **não abre alarmes**. O Sentinela mantém
separados observação pontual, estimativa em grade, previsão, radar/satélite,
contexto territorial oficial e série histórica para pesquisa.

Uma previsão não vira observação. Uma imagem de radar não vira milímetros sem
contrato oficial e processamento validado. Um setor de risco do SGB continua
sendo classificação do SGB; o Sentinela não o reclassifica. Nada aqui substitui
a avaliação técnica da Defesa Civil.

## O que foi implementado

A migração `011_fontes_externas.sql` cria:

- catálogo de provedor e conjunto;
- execução de aquisição com início, término, estado e contagens;
- arquivo bruto imutável, identificado por SHA-256 e URI sem segredo;
- estações e observações pontuais com qualificação e revisão;
- ativos de grade, previsão, radar/satélite e contexto sem falsa normalização;
- quarentena de falha de download ou contrato;
- view `fonte_estado`, consumida por **Cadeia e fontes** no painel.

O coletor grava primeiro o bruto por `rename` atômico no mesmo filesystem. Uma
resposta idêntica já processada é `SEM_NOVIDADE`; não duplica ativo. Um bruto
em quarentena permanece reprocessável em execuções futuras. Correções do provedor
podem coexistir porque conteúdo diferente tem outro hash e observações têm
revisão. Corpos de erro, senhas, tokens e chaves não entram no log, banco ou URI
persistida.

Quando o servidor publica `ETag` ou `Last-Modified`, a próxima execução usa
`If-None-Match`/`If-Modified-Since`; HTTP 304 vira `SEM_NOVIDADE` sem baixar o
corpo. O teto padrão é 50 MiB por resposta e pode ser ajustado por provedor
(`INPE_MERGE_MAX_BYTES`, por exemplo) somente após dimensionar banda e
armazenamento; ultrapassar o teto envia a aquisição à quarentena.

## Catálogo e nível de integração

| Fonte | Contrato oficial verificado | Estado no coletor | Pré-condição externa |
|---|---|---|---|
| CEMADEN PED | REST, JSON/CSV/XML, token; acumulados 1–120 h | bruto + normalização dos acumulados | token, município/estação e fuso explícito |
| ANA HidroWebService | REST JSON, OAuth/JWT, inventário e séries | bruto auditável; normalização aguarda amostra real validada | cadastro, estações e intervalo |
| SGB Setorização de Risco | ArcGIS FeatureServer/GeoJSON | bruto + feições no mapa, sem reinterpretar risco | código IBGE/recorte definido |
| INPE MERGE/GPM | HTTPS, produtos GRIB2 | aquisição de URLs oficiais fixadas | produto/arquivo e recorte operacional |
| INPE WRF 7 km | HTTPS de produtos/recortes | aquisição de URLs oficiais fixadas | produto, rodada e horizonte |
| NOAA GFS | NOMADS/filter, GRIB2 | aquisição de URL oficial parametrizada | variáveis, níveis, domínio e rodada |
| REDEMET | API de produtos radar/satélite | bruto auditável | conta/chave e tipos de produto |
| INMET | arquivos históricos e feeds oficiais | aquisição de URL oficial fixada | arquivo/feed escolhido; endpoint não é presumido |
| NASA IMERG | arquivos/OPeNDAP | aquisição de URL oficial fixada | coleção e, conforme canal, Earthdata |
| CHIRPS | GeoTIFF/NetCDF/COG | aquisição de URL oficial fixada | produto e período; uso histórico |
| NOAA GOES/GLM | NetCDF/cloud/CLASS | aquisição de URL oficial fixada | coleção/setor e processamento definidos |

“Aquisição de URL fixada” preserva o produto escolhido; não significa que o
Sentinela interpreta seu GRIB2/NetCDF. A interpretação só deve ser adicionada
depois de validar variável, unidade, grade, calendário, rodada e licença do
produto concreto.

Na REDEMET, a chave é enviada no header `X-Api-Key`, nunca na URI persistida.
Os contratos oficiais confirmados são `produtos/satelite/{ir|realcada|vis}`,
`produtos/radar/{tipo}` e `produtos/stsc`. Radar também exige a área do radar;
essa escolha depende do município/da cobertura aprovada e não é inferida pelo
coletor. Respostas com caminhos de imagem continuam sendo evidência de produto,
não precipitação numérica.

Fontes primárias consultadas:

- [CEMADEN PED — Swagger](https://sws.cemaden.gov.br/PED/api/ui/)
- [ANA HidroWebService — Swagger](https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html)
- [SGB — FeatureServer da Setorização de Risco](https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/risco/FeatureServer/0)
- [CPTEC/INPE — MERGE/GPM](https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/)
- [CPTEC/INPE — WRF 7 km](https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/)
- [NOAA/NCEP — filtro GRIB do NOMADS](https://nomads.ncep.noaa.gov/info.php?page=gribfilter)
- [DECEA — API REDEMET](https://ajuda.decea.mil.br/base-de-conhecimento/api-redemet-o-que-e/)
- [INMET — dados históricos](https://portal.inmet.gov.br/dadoshistoricos)
- [NASA — IMERG](https://gpm.nasa.gov/data/imerg)
- [UCSB Climate Hazards Center — CHIRPS](https://www.chc.ucsb.edu/data/chirps)
- [NOAA/NCEI — GOES-R](https://www.ncei.noaa.gov/products/satellite/goes-r-series)

## Configuração no Home Server

O runtime é o Home Server Linux. O MacBook desenvolve, testa sem banco e
aciona/verifica o servidor por SSH. Os clones são sincronizados pelo GitHub;
não copiar o repositório por `rsync`.

Depois de o código chegar ao clone `/DATA/Projects/Sentinela`:

```bash
cd /DATA/Projects/Sentinela/backend
cp fontes.env.exemplo fontes.env
chmod 600 fontes.env
# preencher somente fontes e recortes aprovados
venv/bin/python fontes_externas.py --listar
venv/bin/python fontes_externas.py --seco
```

O bruto operacional fica fora do Git em
`/DATA/Projects/Sentinela-Data/externos` por padrão. O usuário dos serviços
precisa ter permissão de criação nesse diretório.

```bash
mkdir -p ~/.config/systemd/user
cp sentinela-fontes.service sentinela-fontes.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now sentinela-fontes.timer
systemctl --user status sentinela-fontes.timer
journalctl --user -u sentinela-fontes.service -n 50 --no-pager
```

O timer executa a cada 15 minutos com atraso aleatório de até 60 segundos. É
cadência técnica de consulta, **não** janela ou regra de alerta. Fontes sem
configuração são puladas; fonte em falha não impede as demais. Mudanças devem
considerar atualização e limites publicados por cada provedor.

## Verificação segura

No MacBook, sem rede externa, banco ou hardware:

```bash
python3 tools/testa_fontes_externas.py
python3 tools/verifica.py
```

No Home Server, validar migrações primeiro em banco descartável e fazer backup
do banco operacional antes de aplicação autorizada. `migra.py --listar` não é
inspeção read-only em banco virgem, pois cria a tabela de controle.

Depois da migração, consultas somente leitura:

```sql
SELECT * FROM fonte_estado ORDER BY provedor, titulo;
SELECT registrado_em, etapa, motivo, fonte_uri
  FROM fonte_quarentena ORDER BY registrado_em DESC LIMIT 20;
```

## Decisões e cadastros ainda externos ao código

Não podem ser preenchidos pelo projeto sem inventar responsabilidade:

- município(s)-piloto e códigos IBGE;
- estações ANA/CEMADEN representativas e política institucional de recorte;
- produto, variável, nível, domínio, rodada e horizonte de MERGE/WRF/GFS;
- produtos REDEMET e finalidade operacional de cada imagem;
- coleção/latência para IMERG, GOES/GLM e CHIRPS;
- credenciais CEMADEN PED, ANA, REDEMET e Earthdata quando exigida;
- licenças/atribuições aprovadas para redistribuição no painel público;
- qualquer regra que combine fonte externa com telemetria local ou alarme.
