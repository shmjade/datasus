# pipelines.batch.ingestion.sources — adapters por fonte
#
# Cada submódulo expõe `fetch(uf, ano, mes) -> pandas.DataFrame` retornando
# o DataFrame cru lido do FTP do DataSUS (ou equivalente).
