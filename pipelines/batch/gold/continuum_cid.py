"""Gold: continuum_cid_mes — cascata de cuidado por CID × município × mês.

Agregação base pra dashboards de "perfil de doença":
- n_internacoes (SIH.RD)
- n_obitos_hospitalares (SIM.DO + filtro LOCOCOR=1)
- n_obitos_totais (SIM.DO)
- n_internacoes_csap (subset CSAP)
- mortalidade_hospitalar (derivado: n_obitos_hosp / n_internacoes)
- letalidade (derivado: morte=1 / total internações)
- permanencia_media
- custo_total

Granularidade: (cid3, munic_res, ano, mes).
"""
from __future__ import annotations

import logging
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)


def build(silver_root: Path, gold_root: Path, con: duckdb.DuckDBPyConnection | None = None) -> int:
    if con is None:
        con = duckdb.connect()

    out_dir = gold_root / "continuum_cid_mes"
    out_dir.mkdir(parents=True, exist_ok=True)

    sih = silver_root / "sih_rd"
    sim = silver_root / "sim_do"

    has_sih = (sih / "ano=*" if (sih).exists() else None) and any(sih.glob("ano=*"))
    has_sim = sim.exists() and any(sim.glob("ano=*"))

    if not has_sih:
        logger.warning("Sem dados silver.sih_rd — gold/continuum_cid_mes não pode ser construído")
        return 0

    sih_glob = f"{sih}/**/*.parquet"
    sim_glob = f"{sim}/**/*.parquet" if has_sim else None

    # CTE com agregação de internações
    sih_cte = f"""
        sih AS (
            SELECT
                cid3,
                munic_res,
                ano,
                mes,
                COUNT(*)                          AS n_internacoes,
                SUM(CASE WHEN csap_flag THEN 1 ELSE 0 END)  AS n_internacoes_csap,
                SUM(morte)                        AS n_mortes_hospital,
                AVG(dias_perm)                    AS perm_media,
                AVG(idade_anos)                   AS idade_media,
                SUM(val_tot)                      AS custo_total,
                AVG(val_tot)                      AS custo_medio,
                SUM(uso_uti)                      AS n_uti
            FROM read_parquet('{sih_glob}', hive_partitioning=true)
            WHERE cid3 IS NOT NULL AND munic_res IS NOT NULL
            GROUP BY cid3, munic_res, ano, mes
        )
    """

    if sim_glob:
        sim_cte = f"""
            , sim AS (
                SELECT
                    cid3,
                    munic_res,
                    ano,
                    mes,
                    COUNT(*)                       AS n_obitos_totais,
                    SUM(obito_hospitalar)          AS n_obitos_hospitalares
                FROM read_parquet('{sim_glob}', hive_partitioning=true)
                WHERE cid3 IS NOT NULL AND munic_res IS NOT NULL
                GROUP BY cid3, munic_res, ano, mes
            )
        """
        select = """
            SELECT
                COALESCE(sih.cid3, sim.cid3) AS cid3,
                COALESCE(sih.munic_res, sim.munic_res) AS munic_res,
                COALESCE(sih.ano, sim.ano) AS ano,
                COALESCE(sih.mes, sim.mes) AS mes,
                make_date(
                    COALESCE(sih.ano, sim.ano),
                    COALESCE(sih.mes, sim.mes),
                    1
                ) AS competencia,
                COALESCE(sih.n_internacoes, 0) AS n_internacoes,
                COALESCE(sih.n_internacoes_csap, 0) AS n_internacoes_csap,
                COALESCE(sih.n_mortes_hospital, 0) AS n_mortes_hospital_sih,
                COALESCE(sim.n_obitos_totais, 0) AS n_obitos_totais,
                COALESCE(sim.n_obitos_hospitalares, 0) AS n_obitos_hospitalares,
                sih.perm_media,
                sih.idade_media,
                sih.custo_total,
                sih.custo_medio,
                COALESCE(sih.n_uti, 0) AS n_uti,
                CASE WHEN sih.n_internacoes > 0
                     THEN sih.n_mortes_hospital * 1.0 / sih.n_internacoes
                END AS letalidade_hospitalar
            FROM sih FULL OUTER JOIN sim USING (cid3, munic_res, ano, mes)
        """
    else:
        sim_cte = ""
        select = """
            SELECT
                cid3,
                munic_res,
                ano,
                mes,
                make_date(ano, mes, 1) AS competencia,
                n_internacoes,
                n_internacoes_csap,
                n_mortes_hospital AS n_mortes_hospital_sih,
                0 AS n_obitos_totais,
                0 AS n_obitos_hospitalares,
                perm_media,
                idade_media,
                custo_total,
                custo_medio,
                n_uti,
                CASE WHEN n_internacoes > 0
                     THEN n_mortes_hospital * 1.0 / n_internacoes
                END AS letalidade_hospitalar
            FROM sih
        """

    sql = f"""
        COPY (
            WITH {sih_cte} {sim_cte}
            {select}
        )
        TO '{out_dir}'
        (FORMAT PARQUET, PARTITION_BY (ano), OVERWRITE_OR_IGNORE,
         COMPRESSION 'zstd')
    """
    logger.info("Construindo gold/continuum_cid_mes (SIM disponível: %s)", has_sim)
    con.execute(sql)
    n = con.execute(
        f"SELECT COUNT(*) FROM read_parquet('{out_dir}/**/*.parquet', hive_partitioning=true)"
    ).fetchone()[0]
    logger.info("gold/continuum_cid_mes: %d linhas", n)
    return n
