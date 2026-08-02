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
| CEMADEN PED | REST, JSON/CSV/XML, JWT do SGAA; acumulados 1–120 h | ativo para Caraguatatuba; bruto + normalização dos acumulados | credencial protegida e fuso explícito |
| ANA HidroWebService | REST JSON, OAuth/JWT, inventário e séries | bruto auditável; normalização aguarda amostra real validada | cadastro, estações e intervalo |
| SGB Setorização de Risco | ArcGIS FeatureServer/GeoJSON | adaptador pronto; camada consultada não contém Caraguatatuba | publicação de feições pelo SGB para o piloto |
| INPE MERGE/GPM | HTTPS, produtos GRIB2 | aquisição de URLs oficiais fixadas | produto/arquivo e recorte operacional |
| INPE WRF 7 km | HTTPS de produtos/recortes | aquisição de URLs oficiais fixadas | produto, rodada e horizonte |
| NOAA GFS | NOMADS/filter, GRIB2 | aquisição de URL oficial parametrizada | variáveis, níveis, domínio e rodada |
| REDEMET | API de produtos radar/satélite | ativo: 3 satélites, STSC e 2 produtos do radar São Roque | imagens permanecem contexto, sem conversão para chuva |
| INMET | arquivos históricos e feeds oficiais | aquisição de URL oficial fixada | arquivo/feed escolhido; endpoint não é presumido |
| NASA IMERG | ImageServer/GeoTIFF da coleção Early V07 | ativo: recorte raster imutável + células da grade no perímetro IBGE | canal oficial público, sem token |
| CHIRPS | GeoTIFF/NetCDF/COG | aquisição de URL oficial fixada | produto e período; uso histórico |
| NOAA GOES/GLM | NetCDF/cloud/CLASS | aquisição de URL oficial fixada | coleção/setor e processamento definidos |

“Aquisição de URL fixada” preserva o produto escolhido; não significa que o
Sentinela interpreta seu GRIB2/NetCDF. A interpretação só deve ser adicionada
depois de validar variável, unidade, grade, calendário, rodada e licença do
produto concreto.

### Recorte piloto aprovado

Caraguatatuba/SP é o município-piloto definido, código IBGE `3510500`. O
perímetro mínimo obtido da API de Malhas do IBGE foi versionado em
`backend/recortes/3510500.geojson`, junto da URL, qualidade e data da aquisição.
Ele é recorte espacial de coleta, não setor de risco nem classificação de
suscetibilidade.

Na consulta de 01/08/2026, a camada oficial de Setorização de Risco do SGB
retornou zero feições tanto por `cd_geocmu='3510500'` quanto por nome do
município. O catálogo de municípios distintos da camada também não continha
Caraguatatuba. Por isso `SGB_WHERE` continua desativado: sucesso HTTP com lista
vazia não será apresentado como cobertura territorial.

### REDEMET

Na REDEMET, a chave é enviada no header `X-Api-Key`, nunca na URI persistida.
Os contratos oficiais confirmados são `produtos/satelite/{ir|realcada|vis}`,
`produtos/radar/{tipo}` e `produtos/stsc`. Radar também exige a área do radar;
para o piloto foi selecionada e verificada a área `sr`, Radar São Roque/SP.
O coletor preserva `03km` (CAPPI a 3,1 km, raio publicado de 250 km) e
`maxcappi` (máximo na coluna, raio publicado de 400 km). Em 01/08/2026 os dois
endpoints responderam com produto, radar, localidade, raio, instante e caminho
de imagem. Isso confirma disponibilidade da API; não demonstra qualidade sobre
Caraguatatuba nem converte refletividade em precipitação de superfície.

### NASA IMERG

O produto fixado é `GPM_3IMERGHHE.07`, IMERG Early V07, precipitação em
intervalos de 30 minutos. A cada ciclo, o coletor consulta o ImageServer oficial
da NASA, bloqueia a exportação no `objectid` mais recente, alinha a caixa do
perímetro à grade publicada de 0,1°, baixa e preserva o GeoTIFF e mantém somente
centros das células contidos no perímetro IBGE do piloto. Instante, variável,
resolução, URI, hash e recorte ficam associados ao ativo.

No painel, esses valores aparecem como **centros de célula de uma estimativa em
grade**, com faixa observada e idade. Não são pluviômetros, média municipal,
calibração local ou regra de alerta. O GeoTIFF recortado é mantido para
auditoria; o canal público ImageServer evita depender do acesso autenticado ao
arquivo global. O token Earthdata recebido permanece protegido, mas não é
enviado nessa integração.

No CEMADEN, o portal PED obtém um JWT no SGAA. Como o token observado em
operação tem validade curta, o coletor aceita `CEMADEN_PED_EMAIL` e
`CEMADEN_PED_PASSWORD` no arquivo protegido e solicita um token no início da
coleta. `CEMADEN_PED_TOKEN` existe somente como alternativa manual e expira;
credenciais e corpo de autenticação não entram no plano, log, banco ou Git.
O próprio CEMADEN declara que seus dados são registrados em UTC/GMT. Por isso
`datahora` sem sufixo é interpretado exclusivamente como `UTC`, e cada
observação carrega `fuso_origem=UTC`; configuração em horário local é recusada.
No Home Server, a instalação sem eco é feita diretamente no terminal:

```bash
cd /DATA/Projects/Sentinela
backend/venv/bin/python tools/configura_cemaden.py
```

Fontes primárias consultadas:

- [CEMADEN PED — Swagger](https://sws.cemaden.gov.br/PED/api/ui/)
- [CEMADEN SGAA — emissão de token](https://sgaa.cemaden.gov.br/SGAA/api/ui/)
- [CEMADEN — convenção temporal UTC/GMT](https://mapainterativo.cemaden.gov.br/)
- [ANA HidroWebService — Swagger](https://www.ana.gov.br/hidrowebservice/swagger-ui/index.html)
- [SGB — FeatureServer da Setorização de Risco](https://geoportal.sgb.gov.br/server/rest/services/gestaoterritorial/risco/FeatureServer/0)
- [IBGE — API de Malhas](https://servicodados.ibge.gov.br/api/docs/malhas?versao=3)
- [CPTEC/INPE — MERGE/GPM](https://ftp.cptec.inpe.br/modelos/tempo/MERGE/GPM/)
- [CPTEC/INPE — WRF 7 km](https://ftp.cptec.inpe.br/modelos/tempo/WRF/ams_07km/)
- [NOAA/NCEP — filtro GRIB do NOMADS](https://nomads.ncep.noaa.gov/info.php?page=gribfilter)
- [DECEA — API REDEMET](https://ajuda.decea.mil.br/base-de-conhecimento/api-redemet-o-que-e/)
- [DECEA — produtos radar](https://ajuda.decea.mil.br/base-de-conhecimento/api-redemet-produtos-radar/)
- [INMET — dados históricos](https://portal.inmet.gov.br/dadoshistoricos)
- [NASA — IMERG](https://gpm.nasa.gov/data/imerg)
- [NASA Earthdata — GPM_3IMERGHHE ImageServer](https://gis.earthdata.nasa.gov/portal/home/item.html?id=598df0e6fd674ab7855f448f7f6f0e39)
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

- contato e responsabilidades institucionais do piloto em Caraguatatuba;
- estações ANA representativas e política institucional de adoção;
- produto, variável, nível, domínio, rodada e horizonte de MERGE/WRF/GFS;
- critérios de interpretação e validação local dos produtos REDEMET;
- coleção/latência e processamento para GOES/GLM e CHIRPS;
- credenciais ANA quando o acesso for concedido;
- licenças/atribuições aprovadas para redistribuição no painel público;
- qualquer regra que combine fonte externa com telemetria local ou alarme.
