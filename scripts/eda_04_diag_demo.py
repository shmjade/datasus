"""Fase 4 — CID-10 (capítulos + top diagnósticos) + demografia (sexo, idade)."""
from datetime import date
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_04_diag_demo").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read.parquet("/app/data/lake/bronze/sih_rd/")
      .withColumn("morte", F.col("MORTE").cast("int"))
      .withColumn("nasc", F.to_date("NASC", "yyyyMMdd"))
      .withColumn("dt_inter", F.to_date("DT_INTER", "yyyyMMdd"))
      .withColumn("idade",
                  (F.datediff("dt_inter", "nasc") / 365.25).cast("int"))
      .withColumn("cid_cap", F.substring("DIAG_PRINC", 1, 1)))

# Mapa de capítulos CID-10 por letra inicial (aproximação — capítulos reais
# vão por intervalo, mas a inicial cobre bem para visão geral)
cid_cap_nomes = {
    "A": "I-II  Infecciosas/parasitárias",
    "B": "I-II  Infecciosas/parasitárias",
    "C": "II    Neoplasias",
    "D": "II-III Neoplasias/sangue",
    "E": "IV    Endócrinas/metabólicas",
    "F": "V     Transtornos mentais",
    "G": "VI    Sistema nervoso",
    "H": "VII-VIII Olhos/ouvidos",
    "I": "IX    Circulatório",
    "J": "X     Respiratório",
    "K": "XI    Digestivo",
    "L": "XII   Pele",
    "M": "XIII  Musculoesquelético",
    "N": "XIV   Genitourinário",
    "O": "XV    Gravidez/parto",
    "P": "XVI   Perinatal",
    "Q": "XVII  Malformações",
    "R": "XVIII Sintomas/sinais",
    "S": "XIX   Lesões/trauma",
    "T": "XIX   Lesões/trauma (toxicológico)",
    "V": "XX    Causas externas (acidentes)",
    "W": "XX    Causas externas",
    "X": "XX    Causas externas",
    "Y": "XX    Causas externas",
    "Z": "XXI   Fatores de saúde",
}

print("=== 4.1 Distribuição por capítulo CID-10 ===")
cap = (df.groupBy("cid_cap")
       .agg(F.count("*").alias("n"),
            F.sum("morte").alias("obitos"),
            (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
       .orderBy(F.desc("n"))).toPandas()
total = cap["n"].sum()
print(f"  {'cap':<3} {'descrição':<32} {'n':>8} {'%':>6} {'óbitos':>7} {'tx mort %':>10}")
for _, r in cap.iterrows():
    nome = cid_cap_nomes.get(r["cid_cap"], "?")
    print(f"  {r['cid_cap']:<3} {nome:<32} {r['n']:>8,} {r['n']/total*100:>6.2f} {r['obitos']:>7,} {r['tx_mort_pct']:>10.2f}")

print("\n=== 4.2 Top 20 CIDs (volume) ===")
(df.groupBy("DIAG_PRINC")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .orderBy(F.desc("n"))
   .limit(20)
   .show(truncate=False))

print("=== 4.3 Top 15 CIDs por taxa de mortalidade (≥200 ocorrências) ===")
(df.groupBy("DIAG_PRINC")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .filter("n >= 200")
   .orderBy(F.desc("tx_mort_pct"))
   .limit(15)
   .show(truncate=False))

print("=== 4.4 Distribuição por sexo ===")
(df.groupBy("SEXO")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .orderBy("SEXO")
   .show(truncate=False))

print("=== 4.5 Faixa etária ===")
faixas = (df.withColumn("faixa",
            F.when(F.col("idade") < 1, "0 <1ano")
             .when(F.col("idade") < 15, "1 1-14")
             .when(F.col("idade") < 30, "2 15-29")
             .when(F.col("idade") < 45, "3 30-44")
             .when(F.col("idade") < 60, "4 45-59")
             .when(F.col("idade") < 75, "5 60-74")
             .when(F.col("idade") < 90, "6 75-89")
             .otherwise("7 90+"))
        .groupBy("faixa")
        .agg(F.count("*").alias("n"),
             F.sum("morte").alias("obitos"),
             (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
        .orderBy("faixa"))
faixas.show(truncate=False)

print("=== 4.6 Outliers de idade (sanidade) ===")
df.agg(
    F.min("idade").alias("min_idade"),
    F.max("idade").alias("max_idade"),
    F.count(F.when(F.col("idade") < 0, 1)).alias("idade_negativa"),
    F.count(F.when(F.col("idade") > 110, 1)).alias("idade_maior_110"),
).show(truncate=False)

spark.stop()
