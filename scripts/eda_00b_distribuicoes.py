"""EDA univariada — Parte B: distribuições por tipo de coluna."""
from pyspark.sql import SparkSession, functions as F

spark = (SparkSession.builder.master("local[*]")
         .appName("eda_00b_distribuicoes")
         .config("spark.sql.ansi.enabled", "false")
         .getOrCreate())
spark.sparkContext.setLogLevel("ERROR")

df = spark.read.parquet("/app/data/lake/bronze/sih_rd/")
total = df.count()


# ---------- Numéricas ----------
NUMERICAS = {
    "IDADE":      "idade do paciente (anos, conforme COD_IDADE)",
    "DIAS_PERM":  "dias de permanência",
    "QT_DIARIAS": "quantidade de diárias cobradas",
    "VAL_TOT":    "valor total da AIH (R$)",
    "VAL_SH":     "valor serviços hospitalares (R$)",
    "VAL_SP":     "valor serviços profissionais (R$)",
    "VAL_UTI":    "valor da UTI (R$)",
    "VAL_UCI":    "valor da UCI (R$)",
    "UTI_MES_TO": "dias em UTI no mês",
    "UTI_INT_TO": "dias em UTI na internação",
    "US_TOT":     "valor total em US$",
    "DIAR_ACOM":  "diárias de acompanhante",
}

print("=" * 80)
print("DISTRIBUIÇÕES — COLUNAS NUMÉRICAS")
print("=" * 80)
num_df = df.select([F.col(c).cast("double").alias(c) for c in NUMERICAS])

for col, desc in NUMERICAS.items():
    stats = num_df.select(
        F.count(F.col(col)).alias("n_naonulos"),
        F.count(F.when(F.col(col) == 0, 1)).alias("n_zeros"),
        F.min(col).alias("min"),
        F.expr(f"percentile_approx({col}, 0.25)").alias("p25"),
        F.expr(f"percentile_approx({col}, 0.50)").alias("p50"),
        F.expr(f"percentile_approx({col}, 0.75)").alias("p75"),
        F.expr(f"percentile_approx({col}, 0.95)").alias("p95"),
        F.max(col).alias("max"),
        F.avg(col).alias("media"),
        F.stddev(col).alias("std"),
    ).collect()[0]
    print(f"\n{col}  ({desc})")
    print(f"  não-nulos: {stats['n_naonulos']:>9,}  zeros: {stats['n_zeros']:>9,}  "
          f"min: {stats['min']:>10.2f}  max: {stats['max']:>13.2f}")
    print(f"  p25: {stats['p25']:>10.2f}  p50: {stats['p50']:>10.2f}  "
          f"p75: {stats['p75']:>10.2f}  p95: {stats['p95']:>10.2f}")
    print(f"  média: {stats['media']:>10.2f}  desvio: {stats['std']:>10.2f}")


# ---------- Categóricas — value_counts ----------
CATEGORICAS = {
    "SEXO":       {"1": "Masculino", "3": "Feminino"},
    "RACA_COR":   {"1": "Branca", "2": "Preta", "3": "Parda", "4": "Amarela",
                   "5": "Indígena", "99": "Sem info"},
    "ETNIA":      None,  # códigos numéricos (etnias indígenas)
    "INSTRU":     {"1": "Analfabeto", "2": "Fund. incompleto", "3": "Fund. completo",
                   "4": "Médio completo", "5": "Superior"},
    "ESPEC":      {"1": "Cirurgia", "2": "Obstetrícia", "3": "Clínica médica",
                   "4": "Crônicos", "5": "Psiquiatria", "6": "Tisiologia",
                   "7": "Pediatria", "8": "Reabilitação", "9": "Hospital-dia"},
    "MARCA_UTI":  None,  # 00..99 (tipo de UTI)
    "COMPLEX":    {"02": "Média complex", "03": "Alta complex"},
    "FINANC":     {"04": "Estratégico", "05": "Atenção básica", "06": "Média",
                   "07": "Alta", "08": "FAEC"},
    "REGCT":      None,
    "CAR_INT":    {"01": "Eletivo", "02": "Urgência", "03": "Acid. trabalho típico",
                   "04": "Acid. trajeto", "05": "Outros traumas", "06": "Outros tipos"},
    "COBRANCA":   None,  # motivo da saída
    "GESTAO":     {"E": "Estadual", "M": "Municipal", "D": "Dupla"},
    "IDENT":      {"1": "AIH normal", "5": "Longa permanência"},
    "MORTE":      {"0": "Sobreviveu", "1": "Óbito"},
    "COD_IDADE":  {"2": "Dias", "3": "Meses", "4": "Anos", "5": "Anos>100"},
    "HOMONIMO":   {"0": "Não", "1": "Sim, conferido", "2": "Sim, não conferido"},
    "GESTRISCO":  {"0": "Não-gestação", "1": "Gestação de risco"},
    "VINCPREV":   None,
}

print("\n" + "=" * 80)
print("VALUE_COUNTS — COLUNAS CATEGÓRICAS")
print("=" * 80)
for col, mapa in CATEGORICAS.items():
    vc = (df.groupBy(col).count()
            .orderBy(F.desc("count"))
            .limit(10)
            .collect())
    print(f"\n{col}:")
    for r in vc:
        v = r[col] if r[col] is not None and r[col] != "" else "(vazio)"
        label = mapa.get(v, "") if mapa else ""
        pct = r["count"] / total * 100
        print(f"  {v:<6} {r['count']:>9,} {pct:>6.2f}%  {label}")


# ---------- Datas ----------
print("\n" + "=" * 80)
print("DATAS — range e validade")
print("=" * 80)
date_df = df.select(
    F.expr("try_to_date(DT_INTER, 'yyyyMMdd')").alias("dt_inter"),
    F.expr("try_to_date(DT_SAIDA, 'yyyyMMdd')").alias("dt_saida"),
    F.expr("try_to_date(NASC, 'yyyyMMdd')").alias("nasc"),
)
for c in ["dt_inter", "dt_saida", "nasc"]:
    s = date_df.select(
        F.count(F.col(c)).alias("validas"),
        F.count(F.when(F.col(c).isNull(), 1)).alias("nulas_ou_inval"),
        F.min(c).alias("min"),
        F.max(c).alias("max"),
    ).collect()[0]
    print(f"\n{c}:")
    print(f"  válidas:  {s['validas']:>9,}")
    print(f"  inválidas: {s['nulas_ou_inval']:>9,}  ({s['nulas_ou_inval']/total*100:5.2f}%)")
    print(f"  range:    {s['min']}  →  {s['max']}")

# ---------- Códigos altos (top 10 cada) ----------
print("\n" + "=" * 80)
print("CÓDIGOS DE ALTA CARDINALIDADE — top 10")
print("=" * 80)
for col in ["MUNIC_MOV", "MUNIC_RES", "CNES", "DIAG_PRINC"]:
    n_distinct = df.select(col).distinct().count()
    print(f"\n{col}  ({n_distinct:,} distintos)")
    (df.groupBy(col).count()
       .orderBy(F.desc("count"))
       .limit(10)
       .show(truncate=False))

spark.stop()
