# pipelines.batch — PySpark batch ETL pipelines
#
# Módulos planejados:
#   ingest_sih.py   — download e parsing dos arquivos RD do SIH/DataSUS
#   ingest_cnes.py  — download e parsing dos arquivos ST/LT do CNES
#   ingest_ibge.py  — download dos indicadores socioeconômicos IBGE
#   transform.py    — limpeza, tipagem e anonimização (raw → trusted)
#   aggregate.py    — cálculos analíticos (trusted → refined)
#   janela_risco.py — cálculo da Janela de Risco de regulação assistencial
