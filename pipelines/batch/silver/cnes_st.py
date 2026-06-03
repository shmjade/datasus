"""Silver CNES.ST — cadastro de estabelecimentos.

Entrada: bronze/cnes_st/uf=*/ano=*/mes=*/*.parquet
Saída:   silver/cnes_st/ano=YYYY/mes=MM/*.parquet
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


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
                CPF_CNPJ                                           AS cpf_cnpj,
                CNPJ_MAN                                           AS cnpj_mantenedora,
                TPGESTAO                                           AS gestao,
                ESFERA_A                                           AS esfera,
                TP_UNID                                            AS tp_unid,
                NAT_JUR                                            AS nat_jur,
                CLIENTEL                                           AS clientela,
                NIV_HIER                                           AS nivel_hierarquia,
                TURNO_AT                                           AS turno,
                CAST(VINC_SUS AS VARCHAR)                          AS vinc_sus,
                ATIVIDAD                                           AS atividade,
                COD_CEP                                            AS cep,
                -- flags de instalação física
                URGEMERG                                           AS tem_urgencia,
                ATENDAMB                                           AS tem_ambulatorial,
                CENTRCIR                                           AS tem_centro_cirurgico,
                CENTROBS                                           AS tem_centro_obstetrico,
                CENTRNEO                                           AS tem_centro_neonatal,
                ATENDHOS                                           AS tem_atend_hospitalar,
                LEITHOSP                                           AS tem_leitos_hosp,
                -- acreditação e qualidade
                AV_ACRED                                           AS acreditado,
                CLASAVAL                                           AS class_acreditacao,
                AV_PNASS                                           AS pnass_avaliado,
                -- comissões (proxy de governança)
                COMISS04                                           AS tem_ccih,
                COMISS09                                           AS tem_comissao_obitos,
                COMISS10                                           AS tem_comissao_epidemio,
                COMISS11                                           AS tem_comissao_notif,
                COMISSAO                                           AS tem_alguma_comissao,
                -- resumo de leitos (detalhe em LT)
                TRY_CAST(QTLEITP1 AS INT)                          AS qt_leitos_cirurgicos,
                TRY_CAST(QTLEITP2 AS INT)                          AS qt_leitos_clinicos,
                TRY_CAST(QTLEITP3 AS INT)                          AS qt_leitos_complementares,
                CAST(CNES AS VARCHAR) || '|' ||
                  CAST(substr(CAST(COMPETEN AS VARCHAR), 1, 4) AS VARCHAR) || '-' ||
                  CAST(substr(CAST(COMPETEN AS VARCHAR), 5, 2) AS VARCHAR)
                                                                   AS cnes_competen
            FROM read_parquet('{src_glob}', hive_partitioning=true, union_by_name=true)
            WHERE CNES IS NOT NULL
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano, mes), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Transformando CNES.ST bronze → silver")
    con.execute(sql)

    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("CNES.ST silver: %d linhas", n)
    return n
