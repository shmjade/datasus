"""F4 — Rastreabilidade de Internações por Estabelecimento.

Para um CNES escolhido, retorna histórico anonimizado:
- N_AIH → SHA-256 hash (identidade preservada, ID original irreversível)
- Volume por competência
- Taxa de mortalidade interna
- % pacientes transferidos de outros municípios (MUNIC_RES != MUNIC_MOV)
"""
from __future__ import annotations

import hashlib
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.queries import get_conn  # noqa: E402

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
SILVER = DATA_ROOT / "lake" / "silver"

st.set_page_config(page_title="F4 Rastreabilidade — DataSUS RS", layout="wide")
st.title("🔍 F4 — Rastreabilidade por Estabelecimento")
st.caption(
    "Histórico anonimizado de internações de um CNES. "
    "N_AIH é hasheado com SHA-256 — preserva consistência sem expor identificador."
)


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    return get_conn()


@st.cache_data(ttl=300)
def _lista_cnes():
    df = _conn().execute(f"""
        SELECT
            cnes,
            COUNT(*) AS internacoes,
            MIN(competencia) AS primeira_comp,
            MAX(competencia) AS ultima_comp
        FROM read_parquet('{SILVER}/sih_rd/**/*.parquet', hive_partitioning=true)
        WHERE cnes IS NOT NULL
        GROUP BY cnes
        HAVING internacoes >= 50
        ORDER BY internacoes DESC
        LIMIT 200
    """).df()
    df["label"] = df["cnes"] + " · " + df["internacoes"].astype(str) + " AIHs"
    return df


@st.cache_data(ttl=60, show_spinner="Buscando histórico do CNES...")
def _historico(cnes: str, d_min: date, d_max: date):
    return _conn().execute(f"""
        SELECT
            n_aih,
            competencia,
            ano, mes,
            morte,
            dias_perm,
            val_tot,
            cid_principal,
            munic_res,
            munic_mov,
            CASE WHEN munic_res != munic_mov THEN 1 ELSE 0 END AS transferido_de_outro
        FROM read_parquet('{SILVER}/sih_rd/**/*.parquet', hive_partitioning=true)
        WHERE cnes = '{cnes}'
          AND competencia BETWEEN '{d_min}' AND '{d_max}'
    """).df()


def _hash_aih(n_aih) -> str:
    """SHA-256 truncado a 16 chars — irreversível mas determinístico."""
    if n_aih is None or str(n_aih) == "":
        return ""
    return hashlib.sha256(str(n_aih).encode()).hexdigest()[:16]


# Filtros
col_a, col_b, col_c = st.columns([2, 1, 1])
with col_a:
    lista = _lista_cnes()
    if lista.empty:
        st.warning("Sem dados de hospitais no silver.")
        st.stop()
    cnes_sel = st.selectbox(
        "Selecione o CNES",
        options=lista["cnes"].tolist(),
        format_func=lambda c: lista.loc[lista["cnes"] == c, "label"].iloc[0],
    )
with col_b:
    d_min = st.date_input("Data início", value=date(2020, 1, 1))
with col_c:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))

if not cnes_sel or d_min > d_max:
    st.stop()

hist = _historico(cnes_sel, d_min, d_max)
if hist.empty:
    st.warning("Sem internações pra esse CNES no período.")
    st.stop()

# Hash do N_AIH (anonimização)
hist["aih_hash"] = hist["n_aih"].apply(_hash_aih)
hist.drop(columns=["n_aih"], inplace=True)

# KPIs
m1, m2, m3, m4 = st.columns(4)
m1.metric("Internações", f"{len(hist):,}")
m2.metric("Óbitos", f"{int(hist['morte'].sum()):,}")
taxa = hist["morte"].mean() * 100 if len(hist) else 0
m3.metric("Taxa mortalidade interna", f"{taxa:.2f}%")
pct_transf = hist["transferido_de_outro"].mean() * 100
m4.metric("% pacientes de outros municípios", f"{pct_transf:.1f}%",
          help="MUNIC_RES != MUNIC_MOV: paciente reside fora do município do hospital")

st.divider()

# Volume + mortalidade por competência
st.subheader("Volume e mortalidade por competência")
agg = (
    hist.groupby("competencia")
    .agg(internacoes=("aih_hash", "count"),
         obitos=("morte", "sum"),
         transferidos=("transferido_de_outro", "sum"))
    .reset_index()
)
agg["taxa_mortalidade"] = agg["obitos"] / agg["internacoes"] * 100
agg["pct_transferidos"] = agg["transferidos"] / agg["internacoes"] * 100

tab1, tab2, tab3 = st.tabs(["Volume", "Mortalidade", "% transferidos"])
with tab1:
    fig = px.bar(agg, x="competencia", y="internacoes",
                 title="Internações por competência")
    st.plotly_chart(fig, use_container_width=True)
with tab2:
    fig = px.line(agg, x="competencia", y="taxa_mortalidade", markers=True,
                  title="Taxa de mortalidade hospitalar (%)")
    st.plotly_chart(fig, use_container_width=True)
with tab3:
    fig = px.line(agg, x="competencia", y="pct_transferidos", markers=True,
                  title="% pacientes de outros municípios")
    st.plotly_chart(fig, use_container_width=True)

# Histórico anonimizado
st.divider()
st.subheader("Histórico anonimizado (SHA-256)")
st.caption(
    "Cada linha = 1 AIH. `aih_hash` é determinístico (mesma AIH → mesmo hash) "
    "mas irreversível."
)
st.dataframe(
    hist[["aih_hash", "competencia", "morte", "dias_perm", "val_tot",
          "cid_principal", "munic_res", "munic_mov", "transferido_de_outro"]],
    use_container_width=True, height=400,
)
