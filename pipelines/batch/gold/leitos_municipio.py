"""Gold: leitos_municipio_mes — capacidade hospitalar agregada por município × mês.

Pivota CNES.LT por categoria funcional do leito (uti, clínico, cirúrgico, etc).
Útil pra dashboards de capacidade vs demanda.

Também faz LEFT JOIN com IBGE (rs_populacao_municipio.csv) pra calcular
leitos por 1.000 hab. Se faltar população, valor fica NULL.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def build(silver_root: Path, gold_root: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()

    out_dir = gold_root / "leitos_municipio_mes"
    out_dir.mkdir(parents=True, exist_ok=True)

    lt = silver_root / "cnes_lt"
    if not (lt.exists() and any(lt.glob("ano=*"))):
        logger.warning("Sem silver.cnes_lt — pulando leitos_municipio")
        return 0

    lt_glob = f"{lt}/**/*.parquet"

    # Tenta carregar população (RS, Censo 2022) pra calcular per capita
    pop_csv = silver_root.parent.parent / "ibge" / "rs_populacao_municipio.csv"
    pop_join = ""
    pop_cols = ""
    if pop_csv.exists():
        con.execute(f"""
            CREATE OR REPLACE TEMP VIEW pop_temp AS
            SELECT cod6, populacao
            FROM read_csv_auto('{pop_csv}')
        """)
        pop_join = "LEFT JOIN pop_temp ON pop_temp.cod6 = agg.codufmun"
        pop_cols = """,
                pop_temp.populacao                                            AS populacao,
                CASE WHEN pop_temp.populacao > 0
                     THEN agg.leitos_sus_total * 1000.0 / pop_temp.populacao
                END                                                            AS leitos_sus_por_1000hab,
                CASE WHEN pop_temp.populacao > 0
                     THEN agg.leitos_uti_sus * 100000.0 / pop_temp.populacao
                END                                                            AS leitos_uti_por_100khab"""
        logger.info("Join com população RS Censo 2022")
    else:
        logger.warning("População CSV não encontrada (%s) — sem per capita", pop_csv)

    sql = f"""
        COPY (
            WITH agg AS (
                SELECT
                    codufmun,
                    ano,
                    mes,
                    make_date(ano, mes, 1) AS competencia,
                    COUNT(DISTINCT cnes)                                AS n_hospitais,
                    SUM(qt_sus)                                         AS leitos_sus_total,
                    SUM(qt_exist)                                       AS leitos_total,
                    SUM(CASE WHEN categoria = 'uti' THEN qt_sus ELSE 0 END)        AS leitos_uti_sus,
                    SUM(CASE WHEN categoria = 'clinico' THEN qt_sus ELSE 0 END)    AS leitos_clinico_sus,
                    SUM(CASE WHEN categoria = 'cirurgico' THEN qt_sus ELSE 0 END)  AS leitos_cirurgico_sus,
                    SUM(CASE WHEN categoria = 'obstetrico' THEN qt_sus ELSE 0 END) AS leitos_obstetrico_sus,
                    SUM(CASE WHEN categoria = 'pediatrico' THEN qt_sus ELSE 0 END) AS leitos_pediatrico_sus,
                    SUM(CASE WHEN categoria = 'outros' THEN qt_sus ELSE 0 END)     AS leitos_outros_sus
                FROM read_parquet('{lt_glob}', hive_partitioning=true)
                WHERE codufmun IS NOT NULL
                GROUP BY codufmun, ano, mes
            )
            SELECT agg.* {pop_cols}
            FROM agg
            {pop_join}
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Construindo gold/leitos_municipio_mes")
    con.execute(sql)
    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("gold/leitos_municipio_mes: %d linhas", n)
    return n
