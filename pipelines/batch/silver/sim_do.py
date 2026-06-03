"""Silver SIM.DO — Declarações de óbito.

Entrada: bronze/sim_do/uf=*/ano=*/*.parquet
Saída:   silver/sim_do/ano=YYYY/*.parquet

Trata a peculiaridade do SIM: datas em DDMMYYYY (não YYYYMMDD).
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from .utils import DECODE_IDADE_SIM_SQL

logger = logging.getLogger(__name__)


def transform(src_glob: str, out_dir: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()
    out_dir.mkdir(parents=True, exist_ok=True)

    sql = f"""
        COPY (
            SELECT
                CAST(CONTADOR AS BIGINT)                           AS contador,
                CAST(NUMEROLOTE AS VARCHAR)                        AS numero_lote,
                CAST(ORIGEM AS VARCHAR)                            AS origem,
                CAST(TIPOBITO AS VARCHAR)                          AS tipobito,
                -- DTOBITO vem como DDMMYYYY → converter pra DATE
                try_strptime(DTOBITO, '%d%m%Y')::DATE              AS dt_obito,
                EXTRACT(year FROM try_strptime(DTOBITO, '%d%m%Y')::DATE)::INT  AS ano,
                EXTRACT(month FROM try_strptime(DTOBITO, '%d%m%Y')::DATE)::INT AS mes,
                try_strptime(DTNASC, '%d%m%Y')::DATE               AS dt_nasc,
                {DECODE_IDADE_SIM_SQL}                             AS idade_anos,
                CAST(SEXO AS VARCHAR)                              AS sexo,
                CAST(RACACOR AS VARCHAR)                           AS raca_cor,
                CAST(ESTCIV AS VARCHAR)                            AS estado_civil,
                CAST(ESC2010 AS VARCHAR)                           AS escolaridade,
                CAST(OCUP AS VARCHAR)                              AS ocupacao,
                CAST(IDADE AS VARCHAR)                             AS idade_raw,
                CAST(CODMUNRES AS VARCHAR)                         AS munic_res,
                CAST(CODMUNOCOR AS VARCHAR)                        AS munic_ocor,
                CAST(LOCOCOR AS VARCHAR)                           AS local_ocorrencia,
                CAST(CODESTAB AS VARCHAR)                          AS cnes_estab,
                ESTABDESCR                                         AS estab_descr,
                CAUSABAS                                           AS causa_basica,
                CASE WHEN length(CAUSABAS) >= 3
                     THEN substr(CAUSABAS, 1, 3) END               AS cid3,
                substr(CAUSABAS, 1, 1)                             AS capitulo_cid,
                CASE
                    WHEN substr(CAUSABAS, 1, 1) IN ('V','W','X','Y') THEN 1
                    ELSE 0
                END                                                AS causa_externa,
                CASE
                    WHEN substr(CAUSABAS, 1, 1) = 'O' THEN 1
                    ELSE 0
                END                                                AS causa_materna,
                CAUSABAS_O                                         AS causa_basica_original,
                CASE WHEN TIPOBITO = '1' THEN 1 ELSE 0 END         AS obito_fetal,
                CASE WHEN LOCOCOR = '1' THEN 1 ELSE 0 END          AS obito_hospitalar,
                ASSISTMED                                          AS assistencia_medica,
                NECROPSIA                                          AS necropsia,
                STDOEPIDEM                                         AS investigado_epidemio,
                LINHAA, LINHAB, LINHAC, LINHAD, LINHAII,
                ATESTADO                                           AS atestado_texto
            FROM read_parquet('{src_glob}', hive_partitioning=true, union_by_name=true)
            WHERE DTOBITO IS NOT NULL
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Transformando SIM.DO bronze → silver")
    con.execute(sql)

    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("SIM.DO silver: %d linhas", n)
    return n
