"""Gold: ml_mortalidade_dataset — dataset ML-ready para prever mortalidade hospitalar.

Lê silver/sih_rd, seleciona features SEM LEAKAGE (variáveis disponíveis
no momento da admissão), exclui causas externas (CIDs V/W/X/Y) e idades
inválidas, e gera splits train/val/test estratificados pelo target (`morte`).

Saída: data/lake/gold/ml_mortalidade_dataset/v1/
  - _full.parquet        (dataset completo, para debug/replicação)
  - train.parquet        (70%)
  - val.parquet          (15%)
  - test.parquet         (15%)
  - metadata.json        (esquema, filtros, estatísticas)

Estratégia de split: stratified_by_target_70_15_15, random_state=42.
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


# --- Features usadas no dataset (excluindo target) ---
# Cada entrada: nome final → expressão SQL para extração do silver.
FEATURE_EXPRS: dict[str, str] = {
    # Demografia
    "sexo":         "CAST(sexo AS INTEGER)",
    "idade_anos":   "CAST(idade_anos AS INTEGER)",
    "faixa_etaria": "CAST(faixa_etaria AS VARCHAR)",
    "raca_cor":     "CAST(raca_cor AS VARCHAR)",
    # Geo
    "munic_res":    "CAST(munic_res AS VARCHAR)",
    "meso_res":     "SUBSTR(CAST(munic_res AS VARCHAR), 1, 4)",
    # Clínicas (conhecidas na admissão)
    "cid_principal": "CAST(cid_principal AS VARCHAR)",
    "cid3":          "CAST(cid3 AS VARCHAR)",
    "csap_flag":     "CAST(csap_flag AS BOOLEAN)",
    # Internação (carater, especialidade e complexidade são definidos na admissão)
    "carater":       "CAST(carater AS VARCHAR)",
    "especialidade": "CAST(especialidade AS VARCHAR)",
    "complexidade":  "CAST(complexidade AS VARCHAR)",
    # Hospital
    "cnes":          "CAST(cnes AS VARCHAR)",
    # Temporal
    "ano":           "CAST(ano AS INTEGER)",
    "mes":           "CAST(mes AS INTEGER)",
    "dow_admissao":  "EXTRACT(dow FROM dt_inter)::INTEGER",
}

# Tipos lógicos (registrados no metadata.json)
FEATURE_TYPES: dict[str, str] = {
    "sexo":          "INTEGER",
    "idade_anos":    "INTEGER",
    "faixa_etaria":  "VARCHAR",
    "raca_cor":      "VARCHAR",
    "munic_res":     "VARCHAR",
    "meso_res":      "VARCHAR",
    "cid_principal": "VARCHAR",
    "cid3":          "VARCHAR",
    "csap_flag":     "BOOLEAN",
    "carater":       "VARCHAR",
    "especialidade": "VARCHAR",
    "complexidade":  "VARCHAR",
    "cnes":          "VARCHAR",
    "ano":           "INTEGER",
    "mes":           "INTEGER",
    "dow_admissao":  "INTEGER",
}

TARGET = "morte"

# Variáveis explicitamente removidas (conhecidas só pós-desfecho)
EXCLUDED_LEAKAGE = [
    "dias_perm",
    "dt_saida",
    "cobranca",
    "val_tot",
    "val_sh",
    "val_sp",
    "val_uti",
    "uti_dias",
    "uso_uti",
    "marca_uti",
    "proc_rea",
]

FILTERS_APPLIED = {
    "morte_not_null":       "morte IS NOT NULL",
    "cid_principal_present": "cid_principal IS NOT NULL",
    "idade_present":         "idade_anos IS NOT NULL",
    "idade_valid_range":     "idade_anos BETWEEN 1 AND 120 (exclui <1 ano e idades inválidas)",
    "exclude_causas_externas": (
        "NOT regexp_matches(cid_principal, '^[VWXY]') "
        "(remove causas externas: V/W/X/Y — sem relação clínica intrínseca)"
    ),
}

RANDOM_STATE = 42
SPLIT_STRATEGY = "stratified_by_target_70_15_15"


def _select_sql(sih_glob: str) -> str:
    """SQL que extrai features + target do silver com filtros aplicados."""
    select_cols = ",\n            ".join(
        f"{expr} AS {name}" for name, expr in FEATURE_EXPRS.items()
    )
    return f"""
        SELECT
            {select_cols},
            CAST(morte AS INTEGER) AS {TARGET}
        FROM read_parquet('{sih_glob}', hive_partitioning=true)
        WHERE morte IS NOT NULL
          AND cid_principal IS NOT NULL
          AND idade_anos IS NOT NULL
          AND idade_anos BETWEEN 1 AND 120
          AND NOT regexp_matches(cid_principal, '^[VWXY]')
    """


def _md5(path: Path) -> str:
    h = hashlib.md5()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build(silver_root: Path, gold_root: Path,
          con: duckdb.DuckDBPyConnection | None = None) -> int:
    """Constrói o dataset ML-ready em gold/ml_mortalidade_dataset/v1/."""
    if con is None:
        con = duckdb.connect()

    out_dir = gold_root / "ml_mortalidade_dataset" / "v1"
    out_dir.mkdir(parents=True, exist_ok=True)

    sih = silver_root / "sih_rd"
    if not (sih.exists() and any(sih.glob("ano=*"))):
        logger.warning("Sem silver.sih_rd — pulando ml_mortalidade_dataset")
        return 0

    sih_glob = f"{sih}/**/*.parquet"
    full_parquet = out_dir / "_full.parquet"

    # --- 1) Materializa dataset completo (filtrado, com features) ---
    select_sql = _select_sql(sih_glob)
    logger.info("Construindo gold/ml_mortalidade_dataset/v1 — materializando _full.parquet")
    con.execute(f"""
        COPY ({select_sql})
        TO '{full_parquet}'
        (FORMAT PARQUET, COMPRESSION 'zstd')
    """)

    n_total = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{full_parquet}')"
    ).fetchone()[0]
    logger.info("ml_mortalidade_dataset _full: %d linhas", n_total)

    if n_total == 0:
        logger.warning("Dataset vazio após filtros — abortando split")
        return 0

    # --- 2) Split stratificado 70/15/15 com sklearn ---
    # Importação tardia: sklearn é opcional (extras [dashboard]).
    try:
        from sklearn.model_selection import train_test_split  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "scikit-learn não está instalado. Adicione ao extras [dashboard] "
            "do pyproject.toml e rebuild do container."
        ) from e

    df = con.execute(f"SELECT * FROM read_parquet('{full_parquet}')").fetchdf()
    logger.info("Carregado em pandas: shape=%s", df.shape)

    y = df[TARGET]
    train_df, tmp_df = train_test_split(
        df, test_size=0.30, random_state=RANDOM_STATE, stratify=y
    )
    val_df, test_df = train_test_split(
        tmp_df, test_size=0.50, random_state=RANDOM_STATE, stratify=tmp_df[TARGET]
    )

    train_path = out_dir / "train.parquet"
    val_path   = out_dir / "val.parquet"
    test_path  = out_dir / "test.parquet"

    train_df.to_parquet(train_path, compression="zstd", index=False)
    val_df.to_parquet(val_path,   compression="zstd", index=False)
    test_df.to_parquet(test_path, compression="zstd", index=False)

    n_train, n_val, n_test = len(train_df), len(val_df), len(test_df)
    target_rate = {
        "train": float(train_df[TARGET].mean()),
        "val":   float(val_df[TARGET].mean()),
        "test":  float(test_df[TARGET].mean()),
    }
    logger.info(
        "splits: train=%d val=%d test=%d | target_rate=%s",
        n_train, n_val, n_test, target_rate,
    )

    # --- 3) Metadata ---
    metadata = {
        "version":              "v1",
        "created_at":           datetime.now(timezone.utc).isoformat(),
        "source_silver_glob":   sih_glob,
        "n_total":              int(n_total),
        "n_train":              int(n_train),
        "n_val":                int(n_val),
        "n_test":               int(n_test),
        "target":               TARGET,
        "target_rate":          target_rate,
        "features":             list(FEATURE_EXPRS.keys()),
        "feature_types":        FEATURE_TYPES,
        "excluded_features_leakage": EXCLUDED_LEAKAGE,
        "filters_applied":      FILTERS_APPLIED,
        "random_state":         RANDOM_STATE,
        "split_strategy":       SPLIT_STRATEGY,
        "md5": {
            "_full.parquet": _md5(full_parquet),
            "train.parquet": _md5(train_path),
            "val.parquet":   _md5(val_path),
            "test.parquet":  _md5(test_path),
        },
    }
    metadata_path = out_dir / "metadata.json"
    with metadata_path.open("w") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    logger.info("metadata.json escrito em %s", metadata_path)

    return int(n_total)
