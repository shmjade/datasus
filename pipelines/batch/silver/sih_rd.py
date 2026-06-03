"""Silver SIH.RD — limpa e deriva campos analíticos.

Entrada: bronze/sih_rd/uf=*/ano=*/mes=*/*.parquet
Saída:   silver/sih_rd/ano=YYYY/mes=MM/*.parquet

Campos derivados:
- cid3:        primeiros 3 chars do DIAG_PRINC (para agregação)
- csap_flag:   internação é CSAP (Cond. Sensíveis Atenção Primária)
- idade_anos:  decodificada de IDADE + COD_IDADE
- competencia: DATE no primeiro dia da competência (pra filtros temporais)
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

from .utils import CSAP_REGEX_DUCKDB, DECODE_IDADE_SIH_SQL

logger = logging.getLogger(__name__)


def transform(src_glob: str, out_dir: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    """Transforma bronze → silver. Retorna número de linhas processadas."""
    if con is None:
        con = duckdb.connect()

    out_dir.mkdir(parents=True, exist_ok=True)

    sql = f"""
        COPY (
            SELECT
                TRY_CAST(N_AIH AS BIGINT)                          AS n_aih,
                CAST(CNES AS VARCHAR)                              AS cnes,
                TRY_CAST(ANO_CMPT AS INT)                          AS ano,
                TRY_CAST(MES_CMPT AS INT)                          AS mes,
                make_date(
                    TRY_CAST(ANO_CMPT AS INT),
                    TRY_CAST(MES_CMPT AS INT),
                    1
                )                                                  AS competencia,
                DIAG_PRINC                                         AS cid_principal,
                CASE WHEN length(DIAG_PRINC) >= 3 THEN substr(DIAG_PRINC, 1, 3) END AS cid3,
                regexp_matches(DIAG_PRINC, '{CSAP_REGEX_DUCKDB}')  AS csap_flag,
                TRY_CAST(SEXO AS INT)                              AS sexo,
                {DECODE_IDADE_SIH_SQL}                             AS idade_anos,
                CASE
                    WHEN {DECODE_IDADE_SIH_SQL} < 1 THEN '<1'
                    WHEN {DECODE_IDADE_SIH_SQL} < 15 THEN '1-14'
                    WHEN {DECODE_IDADE_SIH_SQL} < 30 THEN '15-29'
                    WHEN {DECODE_IDADE_SIH_SQL} < 45 THEN '30-44'
                    WHEN {DECODE_IDADE_SIH_SQL} < 60 THEN '45-59'
                    WHEN {DECODE_IDADE_SIH_SQL} < 75 THEN '60-74'
                    ELSE '75+'
                END                                                AS faixa_etaria,
                RACA_COR                                           AS raca_cor,
                CAST(MUNIC_RES AS VARCHAR)                         AS munic_res,
                CAST(MUNIC_MOV AS VARCHAR)                         AS munic_mov,
                CAST(CEP AS VARCHAR)                               AS cep,
                try_strptime(DT_INTER, '%Y%m%d')::DATE             AS dt_inter,
                try_strptime(DT_SAIDA, '%Y%m%d')::DATE             AS dt_saida,
                TRY_CAST(DIAS_PERM AS INT)                         AS dias_perm,
                TRY_CAST(MORTE AS INT)                             AS morte,
                TRY_CAST(VAL_TOT AS DOUBLE)                        AS val_tot,
                TRY_CAST(VAL_SH AS DOUBLE)                         AS val_sh,
                TRY_CAST(VAL_SP AS DOUBLE)                         AS val_sp,
                TRY_CAST(VAL_UTI AS DOUBLE)                        AS val_uti,
                TRY_CAST(UTI_MES_TO AS INT)                        AS uti_dias,
                CASE WHEN TRY_CAST(UTI_MES_TO AS INT) > 0 THEN 1 ELSE 0 END AS uso_uti,
                MARCA_UTI                                          AS marca_uti,
                PROC_REA                                           AS proc_rea,
                ESPEC                                              AS especialidade,
                CAR_INT                                            AS carater,
                COMPLEX                                            AS complexidade,
                COBRANCA                                           AS cobranca
            FROM read_parquet('{src_glob}', hive_partitioning=true, union_by_name=true)
            WHERE N_AIH IS NOT NULL
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano, mes), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Transformando SIH.RD bronze → silver")
    con.execute(sql)

    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("SIH.RD silver: %d linhas", n)
    return n
