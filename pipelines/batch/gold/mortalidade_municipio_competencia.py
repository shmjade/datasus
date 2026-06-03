"""F2 — Gold: mortalidade_municipio_competencia.

Taxa de mortalidade hospitalar por município de residência × competência:
  taxa_mortalidade = (óbitos / internações) × 100

Fonte: silver/sih_rd. Filtra RS (munic_res prefix '43').
Granularidade: (munic_res, ano, mes).
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def build(silver_root: Path, gold_root: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()

    out_dir = gold_root / "mortalidade_municipio_competencia"
    out_dir.mkdir(parents=True, exist_ok=True)

    sih = silver_root / "sih_rd"
    if not (sih.exists() and any(sih.glob("ano=*"))):
        logger.warning("Sem silver.sih_rd — pulando mortalidade_municipio_competencia")
        return 0

    sih_glob = f"{sih}/**/*.parquet"

    sql = f"""
        COPY (
            SELECT
                munic_res                            AS cod6,
                ano,
                mes,
                make_date(ano, mes, 1)               AS competencia,
                COUNT(*)::BIGINT                     AS internacoes,
                SUM(morte)::BIGINT                   AS obitos,
                -- Coluna "computada" (equivalente a STORED em PG)
                CASE WHEN COUNT(*) > 0
                     THEN SUM(morte) * 100.0 / COUNT(*)
                END                                  AS taxa_mortalidade,
                AVG(dias_perm)::DOUBLE               AS permanencia_media,
                SUM(uso_uti)::BIGINT                 AS internacoes_uti,
                SUM(val_tot)::DOUBLE                 AS custo_total
            FROM read_parquet('{sih_glob}', hive_partitioning=true)
            WHERE munic_res IS NOT NULL
              AND substr(munic_res, 1, 2) = '43'   -- só RS
              AND ano IS NOT NULL
              AND mes IS NOT NULL
            GROUP BY munic_res, ano, mes
            HAVING internacoes >= 1
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Construindo gold/mortalidade_municipio_competencia")
    con.execute(sql)
    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("gold/mortalidade_municipio_competencia: %d linhas", n)
    return n
