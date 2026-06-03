"""Fase 5 — Janela de Risco e síntese.

Investigamos os achados que vão para análises da Silver/Gold:
- Mortalidade em diagnósticos urgentes (sepse, AVC, IAM) por transferência
- Hospitais com excesso de óbito (residual ajustado por mix-de-CID)
- Indicador candidato a "Silêncio Epidemiológico"
"""
from pyspark.sql import SparkSession, functions as F, Window

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_05_janela_risco").getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = (spark.read.parquet("/app/data/lake/bronze/sih_rd/")
      .withColumn("morte", F.col("MORTE").cast("int"))
      .withColumn("dt_inter", F.to_date("DT_INTER", "yyyyMMdd"))
      .withColumn("transferido", F.col("MUNIC_RES") != F.col("MUNIC_MOV"))
      .withColumn("cid_cap", F.substring("DIAG_PRINC", 1, 1)))

URGENTES = ["A419", "A418",       # Sepse
            "I64",                # AVC
            "I219", "I200",       # IAM
            "J960", "J969",       # Insuf. resp. aguda
            "J189", "J180",       # Pneumonia
            "I500", "I509"]       # Insuf. cardíaca
print("=== 5.1 Diagnósticos URGENTES — transferência vs in-loco ===")
print("(Janela de Risco: pacientes graves transferidos têm maior latência")
print(" até cuidado definitivo — esperamos mortalidade ≥ local)\n")

urg = df.filter(F.col("DIAG_PRINC").isin(URGENTES))
(urg.groupBy("DIAG_PRINC", "transferido")
   .agg(F.count("*").alias("n"),
        F.sum("morte").alias("obitos"),
        (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
   .orderBy("DIAG_PRINC", "transferido")
   .show(40, truncate=False))

print("=== 5.2 Mortalidade ajustada por mix-de-CID (capítulo) por hospital ===")
print("(taxa observada - taxa esperada do mix de CIDs do hospital)\n")

# taxa de mort esperada por capítulo CID (estado geral)
exp_by_cap = (df.groupBy("cid_cap")
              .agg((F.sum("morte")/F.count("*")).alias("exp_rate")))

# para cada internação, junta a esperada e calcula resíduo
joined = df.join(exp_by_cap, "cid_cap")
hosp = (joined.groupBy("CNES")
        .agg(F.count("*").alias("n"),
             F.sum("morte").alias("obitos_obs"),
             F.sum("exp_rate").alias("obitos_esp"))
        .withColumn("tx_obs_pct", F.col("obitos_obs")/F.col("n")*100)
        .withColumn("tx_esp_pct", F.col("obitos_esp")/F.col("n")*100)
        .withColumn("excesso_pp", F.col("tx_obs_pct") - F.col("tx_esp_pct"))
        .filter("n >= 500"))

print("    Hospitais com MAIOR excesso (piores que esperado)")
(hosp.orderBy(F.desc("excesso_pp"))
   .limit(10)
   .select("CNES", "n", "obitos_obs",
           F.round("tx_obs_pct", 2).alias("obs%"),
           F.round("tx_esp_pct", 2).alias("esp%"),
           F.round("excesso_pp", 2).alias("excesso_pp"))
   .show(truncate=False))

print("    Hospitais com MENOR excesso (melhores que esperado)")
(hosp.orderBy("excesso_pp")
   .limit(10)
   .select("CNES", "n", "obitos_obs",
           F.round("tx_obs_pct", 2).alias("obs%"),
           F.round("tx_esp_pct", 2).alias("esp%"),
           F.round("excesso_pp", 2).alias("excesso_pp"))
   .show(truncate=False))

print("=== 5.3 Candidatos a Silêncio Epidemiológico (proxy via SIH só) ===")
print("Sem CNES ainda — usamos VOLUME LOCAL baixo + TAXA DE EXPORTAÇÃO alta")
print("+ MORTALIDADE alta no município de residência\n")
muni = (df.groupBy("MUNIC_RES")
        .agg(F.count("*").alias("internacoes_residentes"),
             F.sum(F.when(F.col("transferido"), 1).otherwise(0)).alias("exportados"),
             F.sum("morte").alias("obitos"),
             (F.sum("morte")/F.count("*")*100).alias("tx_mort_pct"))
        .withColumn("pct_exportado",
                    F.col("exportados")/F.col("internacoes_residentes")*100)
        .filter("internacoes_residentes >= 1000"))

print("Municípios com >70% de exportação e mortalidade > média geral (5,6%)")
(muni.filter("pct_exportado > 70 AND tx_mort_pct > 5.6")
   .orderBy(F.desc("tx_mort_pct"))
   .limit(15)
   .select("MUNIC_RES",
           "internacoes_residentes",
           "exportados",
           F.round("pct_exportado", 1).alias("pct_exp"),
           "obitos",
           F.round("tx_mort_pct", 2).alias("tx_mort_pct"))
   .show(truncate=False))

print("=== 5.4 SÍNTESE — números-chave do bronze ===")
df.agg(
    F.count("*").alias("internacoes"),
    F.sum("morte").alias("obitos"),
    F.countDistinct("MUNIC_RES").alias("munic_res"),
    F.countDistinct("MUNIC_MOV").alias("munic_atend"),
    F.countDistinct("CNES").alias("hospitais"),
    F.countDistinct("DIAG_PRINC").alias("cids"),
    F.min("dt_inter").alias("primeira_internacao"),
    F.max("dt_inter").alias("ultima_internacao"),
).show(truncate=False, vertical=True)

spark.stop()
