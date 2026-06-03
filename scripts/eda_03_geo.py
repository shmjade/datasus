"""Fase 3 — Geografia, mortalidade por município, transferências inter-municipais."""
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_03_geo").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read.parquet("/app/data/lake/bronze/sih_rd/")
      .withColumn("morte", F.col("MORTE").cast("int"))
      .withColumn("val_tot", F.col("VAL_TOT").cast("double")))

total = df.count()
print(f"=== 3.1 Visão geral ===  ({total:,} internações)")
df.agg(
    F.countDistinct("MUNIC_RES").alias("munic_res"),
    F.countDistinct("MUNIC_MOV").alias("munic_atend"),
    F.countDistinct("CNES").alias("hospitais"),
    F.sum("morte").alias("obitos_totais"),
    (F.sum("morte")/total*100).alias("tx_mort_pct_geral"),
).show(truncate=False)

print("=== 3.2 Top 15 municípios de ATENDIMENTO por volume ===")
top_atend = (df.groupBy("MUNIC_MOV")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"),
        F.countDistinct("CNES").alias("hospitais"))
   .orderBy(F.desc("n"))
   .limit(15))
top_atend.show(truncate=False)

print("=== 3.3 Top 15 municípios de RESIDÊNCIA por volume ===")
(df.groupBy("MUNIC_RES")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"))
   .orderBy(F.desc("n"))
   .limit(15)
   .show(truncate=False))

print("=== 3.4 Mortalidade extrema — municípios com ≥500 internações ===")
print("    Top 10 com MAIOR taxa de mortalidade")
(df.groupBy("MUNIC_MOV")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .filter("n >= 500")
   .orderBy(F.desc("tx_mort_pct"))
   .limit(10)
   .show(truncate=False))

print("    Top 10 com MENOR taxa de mortalidade")
(df.groupBy("MUNIC_MOV")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .filter("n >= 500")
   .orderBy("tx_mort_pct")
   .limit(10)
   .show(truncate=False))

print("=== 3.5 Transferências inter-municipais ===")
transf = df.withColumn("transferido", F.col("MUNIC_RES") != F.col("MUNIC_MOV"))
(transf.groupBy("transferido")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .show(truncate=False))

print("=== 3.6 Top 10 destinos de transferência ===")
(transf.filter("transferido")
   .groupBy("MUNIC_MOV")
   .agg(F.count("*").alias("recebidos"),
        F.countDistinct("MUNIC_RES").alias("munic_origem"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_transf"))
   .orderBy(F.desc("recebidos"))
   .limit(10)
   .show(truncate=False))

print("=== 3.7 Municípios que MAIS exportam pacientes (top 10) ===")
(transf.filter("transferido")
   .groupBy("MUNIC_RES")
   .agg(F.count("*").alias("exportados"),
        F.countDistinct("MUNIC_MOV").alias("destinos"))
   .orderBy(F.desc("exportados"))
   .limit(10)
   .show(truncate=False))

spark.stop()
