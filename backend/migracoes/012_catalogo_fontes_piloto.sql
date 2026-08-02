-- Sentinela — 012: alinha o catálogo ao recorte piloto efetivamente validado.
--
-- Não cria regra de alerta nem altera observações. Registra no próprio painel
-- os contratos usados e as ausências verificadas em 01/08/2026.

UPDATE fonte_provedor
   SET acesso='ArcGIS ImageServer/GeoTIFF',
       documentacao_url='https://gis.earthdata.nasa.gov/portal/home/item.html?id=598df0e6fd674ab7855f448f7f6f0e39',
       exige_cadastro=FALSE
 WHERE codigo='NASA_IMERG';

UPDATE fonte_conjunto
   SET unidade='mm/hr', uso='CONTEXTO',
       limitacao='IMERG Early V07 em grade de 0,1°; células no perímetro IBGE não são pluviômetros, média municipal ou regra de alerta.'
 WHERE provedor_codigo='NASA_IMERG' AND codigo='imerg';

UPDATE fonte_conjunto
   SET limitacao='Radar São Roque 03km/maxcappi, satélite e STSC são imagens contextuais; não são convertidos em precipitação de superfície.'
 WHERE provedor_codigo='REDEMET' AND codigo='radar-satelite';

UPDATE fonte_conjunto
   SET estado=CASE WHEN estado='ATIVO' THEN estado ELSE 'PAUSADO' END,
       limitacao='A camada oficial consultada em 01/08/2026 não contém feições para Caraguatatuba (IBGE 3510500); vazio não é cobertura.'
 WHERE provedor_codigo='SGB' AND codigo='setorizacao-risco';

UPDATE fonte_conjunto
   SET limitacao='O GRIB2 HOURLY_NOW observado diverge nos descritores do README (rdp/prmsl versus precip/nest); exige validação do mapeamento antes de ativar.'
 WHERE provedor_codigo='INPE_MERGE' AND codigo='gpm-merge';

UPDATE fonte_conjunto
   SET limitacao='Previsão regional exige variáveis, rodada, horizonte e validação definidos; não será ativada como observação.'
 WHERE provedor_codigo='INPE_WRF' AND codigo='ams-07km';

UPDATE fonte_conjunto
   SET limitacao='Previsão global exige variáveis, níveis, rodada, horizonte e recorte definidos; não será ativada como observação.'
 WHERE provedor_codigo='NOAA_GFS' AND codigo='gfs';

UPDATE fonte_conjunto
   SET limitacao='Aguardar seleção de feed oficial e estações úteis ao piloto; não presumir endpoint nem representatividade.'
 WHERE provedor_codigo='INMET' AND codigo='arquivos-oficiais';

UPDATE fonte_conjunto
   SET limitacao='Série histórica para pesquisa/calibração; período e método de recorte precisam ser definidos, sem uso como estado corrente.'
 WHERE provedor_codigo='CHIRPS' AND codigo='chirps';

UPDATE fonte_conjunto
   SET limitacao='Raio e descargas são contexto distinto de chuva; coleção, setor e processamento precisam ser validados antes da ativação.'
 WHERE provedor_codigo='NOAA_GOES' AND codigo='goes-glm';
