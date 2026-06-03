"""Fase 1 — Schema, contagens por partição, taxa de nulos."""
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_01_schema")
         .config("spark.sql.session.timeZone", "America/Sao_Paulo")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet("/app/data/lake/bronze/sih_rd/")

print("=== 1.1 Tipos por coluna (primeiras 25) ===")
for f in df.schema.fields[:25]:
    print(f"  {f.name:<15} {f.dataType.simpleString()}")
print(f"  ... ({len(df.schema.fields)} colunas total)")

print("\n=== 1.2 Volume por (ano, mes) ===")
(df.groupBy("ANO_CMPT", "MES_CMPT")
   .count()
   .orderBy("ANO_CMPT", "MES_CMPT")
   .show(truncate=False))

print("=== 1.3 Top colunas por taxa de nulo (entre as 30 primeiras) ===")
cols = df.columns[:30]
null_counts = df.select([
    F.count(F.when(F.col(c).isNull() | (F.col(c) == ""), c)).alias(c)
    for c in cols
]).collect()[0].asDict()
total = df.count()
nulls = sorted(((c, n, n/total*100) for c, n in null_counts.items()), key=lambda x: -x[1])
for c, n, pct in nulls[:15]:
    print(f"  {c:<15} {n:>9,} nulos  ({pct:6.2f}%)")

print("\n=== 1.4 Campos críticos do projeto (sanidade) ===")
critical = ["UF_ZI", "MUNIC_MOV", "MUNIC_RES", "DT_INTER", "DT_SAIDA",
            "MORTE", "DIAG_PRINC", "N_AIH", "CNES", "SEXO", "NASC", "VAL_TOT"]
for c in critical:
    if c not in df.columns:
        print(f"  {c:<12} AUSENTE ❌")
        continue
    nn = df.filter(F.col(c).isNotNull() & (F.col(c) != "")).count()
    pct = nn/total*100
    print(f"  {c:<12} {nn:>9,} preenchidos ({pct:6.2f}%)")

spark.stop()
