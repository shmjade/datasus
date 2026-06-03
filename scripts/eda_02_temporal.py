"""Fase 2 — Padrões temporais: dia da semana, permanência, sazonalidade intra-mês."""
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_02_temporal").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

raw = spark.read.parquet("/app/data/lake/bronze/sih_rd/")

# parse das datas YYYYMMDD em string → date
df = (raw
      .withColumn("dt_inter", F.to_date("DT_INTER", "yyyyMMdd"))
      .withColumn("dt_saida", F.to_date("DT_SAIDA", "yyyyMMdd"))
      .withColumn("morte", F.col("MORTE").cast("int"))
      .withColumn("dias_perm", F.datediff("dt_saida", "dt_inter"))
      .withColumn("dow_inter", F.date_format("dt_inter", "E"))
      .withColumn("dom_inter", F.dayofmonth("dt_inter")))

print("=== 2.1 Distribuição de dias de permanência ===")
df.select(
    F.min("dias_perm").alias("min"),
    F.expr("percentile_approx(dias_perm, 0.25)").alias("p25"),
    F.expr("percentile_approx(dias_perm, 0.5)").alias("median"),
    F.expr("percentile_approx(dias_perm, 0.75)").alias("p75"),
    F.expr("percentile_approx(dias_perm, 0.95)").alias("p95"),
    F.max("dias_perm").alias("max"),
    F.avg("dias_perm").alias("mean"),
).show(truncate=False)

print("=== 2.2 Permanência por óbito (vivos vs óbitos) ===")
(df.groupBy("morte")
   .agg(F.count("*").alias("n"),
        F.expr("percentile_approx(dias_perm, 0.5)").alias("median"),
        F.avg("dias_perm").alias("mean"))
   .orderBy("morte")
   .show(truncate=False))

print("=== 2.3 Internações por dia da semana ===")
ordem = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
dow = (df.groupBy("dow_inter").count().toPandas())
dow = dow.set_index("dow_inter").reindex(ordem)
total = dow["count"].sum()
for d, n in dow["count"].items():
    bar = "█" * int(40 * n / dow["count"].max())
    print(f"  {d}  {n:>6,}  {n/total*100:5.2f}%  {bar}")

print("\n=== 2.4 Mortalidade por dia da semana ===")
(df.groupBy("dow_inter")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .orderBy(F.desc("tx_mort_pct"))
   .show(truncate=False))

print("=== 2.5 Distribuição por dia do mês (sazonalidade intra-mês) ===")
(df.groupBy("dom_inter")
   .count()
   .orderBy("dom_inter")
   .show(31, truncate=False))

spark.stop()
