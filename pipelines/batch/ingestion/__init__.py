# pipelines.batch.ingestion — Bronze layer
#
# Baixa microdados do DataSUS (SIH, CNES) e do IBGE e escreve em parquet
# particionado em data/lake/bronze/. Watermark mantém estado entre execuções.
#
# Entrypoint principal: orchestrator.py (alvo do cron mensal).
