"""Silver CNES.LT — leitos por estabelecimento.

Entrada: bronze/cnes_lt/uf=*/ano=*/mes=*/*.parquet
Saída:   silver/cnes_lt/ano=YYYY/mes=MM/*.parquet

Classifica leitos em categorias funcionais úteis pra análise:
- uti        (CODLEITO 51-78)
- clinico    (TP_LEITO=2)
- cirurgico  (TP_LEITO=1)
- obstetrico (TP_LEITO=4)
- pediatrico (TP_LEITO=5)
- outras     (demais)
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

TIPOS_LEITO_CASE = """
    CASE
        WHEN TRY_CAST(CODLEITO AS INT) BETWEEN 51 AND 78 THEN 'uti'
        WHEN CAST(TP_LEITO AS VARCHAR) = '1' THEN 'cirurgico'
        WHEN CAST(TP_LEITO AS VARCHAR) = '2' THEN 'clinico'
        WHEN CAST(TP_LEITO AS VARCHAR) = '4' THEN 'obstetrico'
        WHEN CAST(TP_LEITO AS VARCHAR) = '5' THEN 'pediatrico'
        WHEN CAST(TP_LEITO AS VARCHAR) = '7' THEN 'hospital_dia'
        ELSE 'outros'
    END
"""


def transform(src_glob: str, out_dir: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()
    out_dir.mkdir(parents=True, exist_ok=True)

    sql = f"""
        COPY (
            SELECT
                CAST(CNES AS VARCHAR)                              AS cnes,
                CAST(CODUFMUN AS VARCHAR)                          AS codufmun,
                TRY_CAST(substr(CAST(COMPETEN AS VARCHAR), 1, 4) AS INT)   AS ano,
                TRY_CAST(substr(CAST(COMPETEN AS VARCHAR), 5, 2) AS INT)   AS mes,
                make_date(
                    TRY_CAST(substr(CAST(COMPETEN AS VARCHAR), 1, 4) AS INT),
                    TRY_CAST(substr(CAST(COMPETEN AS VARCHAR), 5, 2) AS INT),
                    1
                )                                                  AS competencia,
                CAST(TP_LEITO AS VARCHAR)                          AS tp_leito,
                CAST(CODLEITO AS VARCHAR)                          AS codleito,
                {TIPOS_LEITO_CASE}                                 AS categoria,
                TRY_CAST(QT_EXIST AS INT)                          AS qt_exist,
                TRY_CAST(QT_CONTR AS INT)                          AS qt_contr,
                TRY_CAST(QT_SUS AS INT)                            AS qt_sus,
                TRY_CAST(QT_NSUS AS INT)                           AS qt_nsus
            FROM read_parquet('{src_glob}', hive_partitioning=true, union_by_name=true)
            WHERE CNES IS NOT NULL
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano, mes), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Transformando CNES.LT bronze → silver")
    con.execute(sql)

    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("CNES.LT silver: %d linhas", n)
    return n
