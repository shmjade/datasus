"""Gold: hospital_panel_cid_mes — métricas por hospital × CID × mês.

Tabela base do "Painel do Diretor": pra cada (cnes, cid3, ano-mes):
- n_internacoes
- mortalidade (taxa)
- permanencia_media
- uso_uti_pct
- custo_medio
- custo_total

Granularidade: (cnes, cid3, ano, mes). Tipicamente < 100k linhas/ano pro RS.
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def build(silver_root: Path, gold_root: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()

    out_dir = gold_root / "hospital_panel_cid_mes"
    out_dir.mkdir(parents=True, exist_ok=True)

    sih = silver_root / "sih_rd"
    cnes = silver_root / "cnes_st"

    if not (sih.exists() and any(sih.glob("ano=*"))):
        logger.warning("Sem silver.sih_rd — pulando hospital_panel")
        return 0

    sih_glob = f"{sih}/**/*.parquet"

    # Join com CNES.ST pra trazer características do hospital (sem competência exata —
    # toma a competência mais próxima por CNES). Pra simplificar e ser robusto a
    # gaps, fazemos LEFT JOIN sem casar competência (snapshot mais recente).
    if cnes.exists() and any(cnes.glob("ano=*")):
        cnes_join = f"""
            LEFT JOIN (
                SELECT cnes, codufmun, tp_unid, esfera, nat_jur, clientela,
                       tem_centro_cirurgico, tem_centro_obstetrico
                FROM read_parquet('{cnes}/**/*.parquet', hive_partitioning=true)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY cnes ORDER BY competencia DESC) = 1
            ) cnes USING (cnes)
        """
        cnes_cols = """,
                ANY_VALUE(codufmun) AS codufmun_hosp,
                ANY_VALUE(tp_unid) AS tp_unid,
                ANY_VALUE(esfera) AS esfera,
                ANY_VALUE(clientela) AS clientela"""
    else:
        cnes_join = ""
        cnes_cols = ""

    sql = f"""
        COPY (
            SELECT
                cnes,
                cid3,
                ano,
                mes,
                make_date(ano, mes, 1) AS competencia,
                COUNT(*)                                      AS n_internacoes,
                SUM(morte)                                    AS n_mortes,
                AVG(morte)::DOUBLE                            AS taxa_mortalidade,
                AVG(dias_perm)::DOUBLE                        AS perm_media,
                MEDIAN(dias_perm)::DOUBLE                     AS perm_mediana,
                SUM(uso_uti)                                  AS n_uti,
                AVG(uso_uti)::DOUBLE                          AS uti_pct,
                SUM(val_tot)                                  AS custo_total,
                AVG(val_tot)                                  AS custo_medio,
                AVG(idade_anos)::DOUBLE                       AS idade_media,
                SUM(CASE WHEN csap_flag THEN 1 ELSE 0 END)   AS n_csap
                {cnes_cols}
            FROM read_parquet('{sih_glob}', hive_partitioning=true) sih
            {cnes_join}
            WHERE cid3 IS NOT NULL AND cnes IS NOT NULL
            GROUP BY cnes, cid3, ano, mes
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Construindo gold/hospital_panel_cid_mes")
    con.execute(sql)
    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("gold/hospital_panel_cid_mes: %d linhas", n)
    return n
