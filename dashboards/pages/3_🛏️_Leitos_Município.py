"""Página: Leitos SUS por Município.

Capacidade instalada SUS por município (CNES.LT agregado),
com decomposição por categoria de leito.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import pergunta_box  # noqa: E402
from utils.queries import get_conn, leitos_por_municipio  # noqa: E402

st.set_page_config(page_title="Leitos SUS — DataSUS RS", layout="wide")
st.title("🛏️ Capacidade SUS por Município")
pergunta_box(
    "Onde está concentrada a capacidade hospitalar SUS do RS — "
    "e como ela se decompõe entre UTI, clínico, cirúrgico e obstétrico?"
)
st.caption("Leitos SUS médios no período, decomposto por categoria funcional.")


@st.cache_resource
def _conn():
    return get_conn()


@st.cache_data(ttl=60, show_spinner="Carregando leitos por município...")
def _query(d_min, d_max, top_n):
    return leitos_por_municipio(_conn(), d_min, d_max, top_n=top_n)


# -- Filtros ------------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    d_min = st.date_input("Data início", value=date(2022, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))
with col_c:
    top_n = st.slider("Top N municípios", 10, 100, 30)


if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

df = _query(d_min, d_max, top_n)

if df.empty:
    st.warning("Sem dados de leitos. Rode o pipeline gold antes.")
    st.stop()

# -- KPIs --------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Municípios com leitos SUS", f"{len(df):,}")
m2.metric("Leitos SUS (top N)", f"{df['leitos_sus'].sum():,.0f}")
m3.metric("UTI SUS (top N)", f"{df['uti_sus'].sum():,.0f}")
m4.metric("Hospitais (top N)", f"{df['n_hospitais'].sum():,.0f}")

# -- Bar chart por município --------------------------------------------------
st.subheader(f"Top {top_n} municípios por leitos SUS")
fig = px.bar(
    df.head(top_n).sort_values("leitos_sus"),
    x="leitos_sus", y="codufmun",
    orientation="h",
    hover_data=["uti_sus", "clinico_sus", "cirurgico_sus", "obstetrico_sus", "n_hospitais"],
    labels={"leitos_sus": "Leitos SUS médios", "codufmun": "Município IBGE"},
)
fig.update_layout(height=max(400, top_n * 25))
st.plotly_chart(fig, use_container_width=True)

# -- Mix por categoria --------------------------------------------------------
st.subheader("Mix de leitos — top 20 municípios")
mix = (
    df.head(20)
    .set_index("codufmun")[["uti_sus", "clinico_sus", "cirurgico_sus",
                            "obstetrico_sus", "pediatrico_sus"]]
    .reset_index()
    .melt(id_vars="codufmun", var_name="categoria", value_name="leitos")
)
fig = px.bar(
    mix, x="codufmun", y="leitos", color="categoria",
    title="Composição de leitos por município (top 20)",
)
fig.update_xaxes(type="category")
fig.update_layout(height=500)
st.plotly_chart(fig, use_container_width=True)

# -- Tabela completa ---------------------------------------------------------
st.subheader("Tabela completa")
st.dataframe(df, use_container_width=True, height=400)
