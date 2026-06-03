"""Silver layer — limpa, tipa e deriva campos a partir do bronze.

Cada módulo transforma uma tabela bronze numa tabela silver particionada por
(ano, mes) ou (ano). Usa DuckDB COPY pra streaming sobre parquet.
"""
