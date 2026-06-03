"""EDA univariada — Parte A: tamanho, nulos, classificação de colunas."""
import os
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_00_setup")
         .config("spark.sql.ansi.enabled", "false")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet("/app/data/lake/bronze/sih_rd/")
total = df.count()
cols = df.columns

# ===== Tamanho =====
print("=" * 60)
print("TAMANHO DO DATASET")
print("=" * 60)
print(f"  Linhas:      {total:>10,}")
print(f"  Colunas:     {len(cols):>10}")
print(f"  Partições:   {df.rdd.getNumPartitions():>10}")

bronze_root = "/app/data/lake/bronze/sih_rd"
total_bytes = 0
for root_, _, files in os.walk(bronze_root):
    for f_ in files:
        if f_.endswith(".parquet"):
            total_bytes += os.path.getsize(os.path.join(root_, f_))
print(f"  Tamanho:     {total_bytes/1024/1024:>10.2f} MB (snappy parquet em disco)")

print("\nVolume por competência:")
(df.groupBy("ANO_CMPT", "MES_CMPT").count()
   .orderBy("ANO_CMPT", "MES_CMPT").show(truncate=False))

# ===== Nulos / vazios — TODAS as 116 colunas =====
print("=" * 60)
print("COMPLETUDE — TODAS as 116 colunas")
print("=" * 60)

# para cada coluna: nulos reais + strings vazias
exprs = []
for c in cols:
    exprs.append(F.count(F.when(F.col(c).isNull() | (F.col(c) == ""), c)).alias(c))
nulls = df.select(exprs).collect()[0].asDict()

ranked = sorted(
    ((c, n, n/total*100) for c, n in nulls.items()),
    key=lambda x: -x[1],
)

print(f"\n{'coluna':<15} {'nulos':>10} {'pct':>8} {'cardinalidade (distintos)':>26}")
print("-" * 65)
# Cardinalidade para entender o "tipo" da coluna
for c, n, pct in ranked:
    card = df.select(c).distinct().limit(20).count()
    card_str = f"≥{card}" if card >= 20 else str(card)
    print(f"{c:<15} {n:>10,} {pct:>7.2f}%  {card_str:>26}")

spark.stop()
