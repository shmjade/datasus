"""Queries DuckDB compartilhadas pelos dashboards.

Padrão: funções recebem connection + filtros, retornam pd.DataFrame.
São envolvidas em @st.cache_data nas páginas (não aqui — pra reusar fora do
contexto Streamlit também, ex.: testes).
"""
from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
GOLD = DATA_ROOT / "lake" / "gold"
SILVER = DATA_ROOT / "lake" / "silver"


def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(":memory:")


def _path_exists(p: Path) -> bool:
    return p.exists() and any(p.rglob("*.parquet"))


def cobertura_dados(con: duckdb.DuckDBPyConnection) -> dict:
    """Retorna metadata de cobertura (range temporal, contagens)."""
    out: dict = {"continuum": None, "panel": None, "leitos": None}
    src = GOLD / "continuum_cid_mes"
    if _path_exists(src):
        df = con.execute(f"""
            SELECT
                MIN(competencia) AS inicio,
                MAX(competencia) AS fim,
                COUNT(DISTINCT cid3) AS n_cids,
                SUM(n_internacoes)::BIGINT AS total_internacoes,
                SUM(n_obitos_totais)::BIGINT AS total_obitos
            FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        """).df()
        out["continuum"] = df.iloc[0].to_dict()

    src = GOLD / "hospital_panel_cid_mes"
    if _path_exists(src):
        df = con.execute(f"""
            SELECT COUNT(DISTINCT cnes) AS n_hospitais
            FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        """).df()
        out["panel"] = df.iloc[0].to_dict()

    src = GOLD / "leitos_municipio_mes"
    if _path_exists(src):
        df = con.execute(f"""
            SELECT
                COUNT(DISTINCT codufmun) AS n_municipios,
                SUM(leitos_sus_total)::BIGINT AS soma_leitos
            FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        """).df()
        out["leitos"] = df.iloc[0].to_dict()

    return out


def continuum_por_cid(
    con: duckdb.DuckDBPyConnection,
    data_min: date,
    data_max: date,
    cid_prefix: str = "",
    top_n: int = 50,
) -> pd.DataFrame:
    src = GOLD / "continuum_cid_mes"
    if not _path_exists(src):
        return pd.DataFrame()
    where_cid = ""
    if cid_prefix:
        where_cid = f"AND cid3 LIKE '{cid_prefix.upper()}%'"
    return con.execute(f"""
        SELECT
            cid3,
            SUM(n_internacoes)::BIGINT          AS internacoes,
            SUM(n_internacoes_csap)::BIGINT     AS csap,
            SUM(n_mortes_hospital_sih)::BIGINT  AS mortes_hospital_sih,
            SUM(n_obitos_totais)::BIGINT        AS obitos_sim,
            CASE WHEN SUM(n_internacoes) > 0
                 THEN SUM(n_mortes_hospital_sih) * 1.0 / SUM(n_internacoes)
            END AS letalidade,
            AVG(perm_media)::DOUBLE             AS perm_media,
            SUM(custo_total)::DOUBLE            AS custo_total
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        WHERE competencia BETWEEN '{data_min}' AND '{data_max}'
        {where_cid}
        GROUP BY cid3
        HAVING internacoes > 0
        ORDER BY internacoes DESC
        LIMIT {top_n}
    """).df()


def continuum_temporal(
    con: duckdb.DuckDBPyConnection,
    data_min: date,
    data_max: date,
    cid_prefix: str = "",
) -> pd.DataFrame:
    src = GOLD / "continuum_cid_mes"
    if not _path_exists(src):
        return pd.DataFrame()
    where_cid = ""
    if cid_prefix:
        where_cid = f"AND cid3 LIKE '{cid_prefix.upper()}%'"
    return con.execute(f"""
        SELECT
            competencia,
            SUM(n_internacoes)::BIGINT    AS internacoes,
            SUM(n_obitos_totais)::BIGINT  AS obitos,
            SUM(n_internacoes_csap)::BIGINT AS csap,
            SUM(custo_total)::DOUBLE      AS custo
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        WHERE competencia BETWEEN '{data_min}' AND '{data_max}'
        {where_cid}
        GROUP BY competencia
        ORDER BY competencia
    """).df()


def hospitais_por_volume(
    con: duckdb.DuckDBPyConnection,
    data_min: date,
    data_max: date,
    cid_prefix: str = "",
    top_n: int = 30,
) -> pd.DataFrame:
    src = GOLD / "hospital_panel_cid_mes"
    if not _path_exists(src):
        return pd.DataFrame()
    where_cid = ""
    if cid_prefix:
        where_cid = f"AND cid3 LIKE '{cid_prefix.upper()}%'"
    return con.execute(f"""
        SELECT
            cnes,
            SUM(n_internacoes)::BIGINT          AS internacoes,
            SUM(n_mortes)::BIGINT               AS mortes,
            CASE WHEN SUM(n_internacoes) > 0
                 THEN SUM(n_mortes) * 1.0 / SUM(n_internacoes)
            END                                 AS mortalidade,
            AVG(perm_media)::DOUBLE             AS perm_media,
            AVG(uti_pct)::DOUBLE                AS uti_pct,
            SUM(custo_total)::DOUBLE            AS custo_total,
            AVG(custo_medio)::DOUBLE            AS custo_medio
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        WHERE competencia BETWEEN '{data_min}' AND '{data_max}'
        {where_cid}
        GROUP BY cnes
        HAVING internacoes >= 10
        ORDER BY internacoes DESC
        LIMIT {top_n}
    """).df()


def perfil_hospital(
    con: duckdb.DuckDBPyConnection,
    cnes: str,
    data_min: date,
    data_max: date,
    top_n_cids: int = 30,
) -> pd.DataFrame:
    src = GOLD / "hospital_panel_cid_mes"
    if not _path_exists(src):
        return pd.DataFrame()
    return con.execute(f"""
        SELECT
            cid3,
            SUM(n_internacoes)::BIGINT          AS internacoes,
            SUM(n_mortes)::BIGINT               AS mortes,
            CASE WHEN SUM(n_internacoes) > 0
                 THEN SUM(n_mortes) * 1.0 / SUM(n_internacoes)
            END                                 AS mortalidade,
            AVG(perm_media)::DOUBLE             AS perm_media,
            AVG(uti_pct)::DOUBLE                AS uti_pct,
            AVG(custo_medio)::DOUBLE            AS custo_medio,
            SUM(custo_total)::DOUBLE            AS custo_total,
            AVG(idade_media)::DOUBLE            AS idade_media,
            SUM(n_csap)::BIGINT                 AS csap
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        WHERE cnes = '{cnes}'
          AND competencia BETWEEN '{data_min}' AND '{data_max}'
        GROUP BY cid3
        HAVING internacoes >= 5
        ORDER BY internacoes DESC
        LIMIT {top_n_cids}
    """).df()


def leitos_por_municipio(
    con: duckdb.DuckDBPyConnection,
    data_min: date,
    data_max: date,
    top_n: int = 50,
) -> pd.DataFrame:
    src = GOLD / "leitos_municipio_mes"
    if not _path_exists(src):
        return pd.DataFrame()
    return con.execute(f"""
        SELECT
            codufmun,
            AVG(n_hospitais)::DOUBLE             AS n_hospitais,
            AVG(leitos_sus_total)::DOUBLE        AS leitos_sus,
            AVG(leitos_total)::DOUBLE            AS leitos_total,
            AVG(leitos_uti_sus)::DOUBLE          AS uti_sus,
            AVG(leitos_clinico_sus)::DOUBLE      AS clinico_sus,
            AVG(leitos_cirurgico_sus)::DOUBLE    AS cirurgico_sus,
            AVG(leitos_obstetrico_sus)::DOUBLE   AS obstetrico_sus,
            AVG(leitos_pediatrico_sus)::DOUBLE   AS pediatrico_sus
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        WHERE competencia BETWEEN '{data_min}' AND '{data_max}'
        GROUP BY codufmun
        HAVING leitos_sus > 0
        ORDER BY leitos_sus DESC
        LIMIT {top_n}
    """).df()


def cids_disponiveis(con: duckdb.DuckDBPyConnection) -> list[str]:
    src = GOLD / "continuum_cid_mes"
    if not _path_exists(src):
        return []
    df = con.execute(f"""
        SELECT cid3, SUM(n_internacoes) AS n
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        GROUP BY cid3 ORDER BY n DESC LIMIT 200
    """).df()
    return df["cid3"].dropna().tolist()


def hospitais_disponiveis(con: duckdb.DuckDBPyConnection) -> list[str]:
    src = GOLD / "hospital_panel_cid_mes"
    if not _path_exists(src):
        return []
    df = con.execute(f"""
        SELECT cnes, SUM(n_internacoes) AS n
        FROM read_parquet('{src}/**/*.parquet', hive_partitioning=true)
        GROUP BY cnes
        HAVING n >= 10
        ORDER BY n DESC LIMIT 500
    """).df()
    return df["cnes"].dropna().tolist()
