# pipelines.batch — pipelines batch (Medallion)
#
# Submódulos:
#   ingestion/  Bronze: FTP DataSUS / IBGE → parquet particionado
#   transform/  Silver: bronze parquet → trusted.* no PostgreSQL (PySpark)
#   aggregate/  Gold:   trusted.* → refined.* (mortalidade, leitos, etc.)
