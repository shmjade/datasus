"""Página: Leitos SUS por Município.

Capacidade instalada SUS por município (CNES.LT agregado),
com decomposição por categoria de leito.
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import pandas as pd
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


@st.cache_resource
def _nome_map() -> dict[str, str]:
    """Mapa cod6 → nome do município (Censo 2022)."""
    p = Path(os.getenv("DATA_ROOT", "/app/data")) / "ibge" / "rs_populacao_municipio.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype={"cod6": str})
    return dict(zip(df["cod6"], df["nome"]))


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

# Enriquece com nome do município
nome_map = _nome_map()
df["municipio"] = df["codufmun"].map(nome_map).fillna(df["codufmun"])

# -- KPIs --------------------------------------------------------------------
m1, m2, m3, m4 = st.columns(4)
m1.metric("Municípios com leitos SUS", f"{len(df):,}")
m2.metric("Leitos SUS (top N)", f"{df['leitos_sus'].sum():,.0f}")
m3.metric("UTI SUS (top N)", f"{df['uti_sus'].sum():,.0f}")
m4.metric("Hospitais (top N)", f"{df['n_hospitais'].sum():,.0f}")

# -- Mix de leitos (top 20) ---------------------------------------------------
st.subheader("Mix de leitos — top 20 municípios")
st.caption(
    "Composição dos leitos SUS por categoria funcional. Compare 2 visões: "
    "**absoluta** (em quantos leitos cada categoria contribui) e "
    "**proporcional** (qual fatia de cada hospital é UTI, clínico, etc.)."
)

CATEGORIAS = ["uti_sus", "clinico_sus", "cirurgico_sus",
              "obstetrico_sus", "pediatrico_sus"]
LABELS_CAT = {
    "uti_sus": "UTI",
    "clinico_sus": "Clínico",
    "cirurgico_sus": "Cirúrgico",
    "obstetrico_sus": "Obstétrico",
    "pediatrico_sus": "Pediátrico",
}

top20 = df.head(20).copy()
# Ordena pelo total de leitos pra dar uma ordem natural visualmente
top20 = top20.sort_values("leitos_sus", ascending=False)

mix = top20[["municipio"] + CATEGORIAS].melt(
    id_vars="municipio", var_name="categoria", value_name="leitos"
)
mix["categoria"] = mix["categoria"].map(LABELS_CAT)

# Mantém ordem dos municípios (descendente de leitos)
mix["municipio"] = pd.Categorical(
    mix["municipio"], categories=top20["municipio"].tolist(), ordered=True,
)

tab_abs, tab_pct, tab_cat = st.tabs([
    "Valores absolutos",
    "Composição percentual (100%)",
    "Por categoria",
])

with tab_abs:
    fig = px.bar(
        mix, x="municipio", y="leitos", color="categoria",
        labels={"municipio": "Município", "leitos": "Leitos SUS médios",
                "categoria": "Categoria"},
        category_orders={"categoria": list(LABELS_CAT.values())},
    )
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_layout(height=520, legend_title_text="Categoria")
    st.plotly_chart(fig, use_container_width=True)

with tab_pct:
    fig = px.bar(
        mix, x="municipio", y="leitos", color="categoria",
        labels={"municipio": "Município", "leitos": "% do total de leitos",
                "categoria": "Categoria"},
        category_orders={"categoria": list(LABELS_CAT.values())},
    )
    fig.update_traces(hovertemplate="%{x}<br>%{fullData.name}: %{y:.1f}%<extra></extra>")
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_layout(
        height=520,
        barnorm="percent",       # normaliza cada barra empilhada a 100%
        yaxis=dict(tickformat=".0f", ticksuffix="%"),
        legend_title_text="Categoria",
    )
    st.plotly_chart(fig, use_container_width=True)
    st.caption(
        "Mesmas barras, mas normalizadas em % do total de leitos do município. "
        "Mostra o perfil assistencial (ex.: alta % de UTI sugere hospital de referência)."
    )

with tab_cat:
    st.caption(
        "Selecione uma categoria pra ver isoladamente os top 20 municípios. "
        "Útil pra responder perguntas focadas — ex.: 'quem tem mais UTI?'"
    )
    cat_sel = st.selectbox(
        "Categoria",
        options=list(LABELS_CAT.values()),
        index=0,   # UTI por padrão
    )
    # Volta o label pro nome da coluna original
    col_sel = {v: k for k, v in LABELS_CAT.items()}[cat_sel]

    cat_df = (
        top20[["municipio", col_sel]]
        .rename(columns={col_sel: "leitos"})
        .sort_values("leitos", ascending=False)
    )
    fig = px.bar(
        cat_df,
        x="municipio", y="leitos",
        labels={"municipio": "Município", "leitos": f"Leitos SUS — {cat_sel}"},
        text="leitos",
    )
    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
        marker_color="rgb(37,99,235)",   # azul forte consistente com a paleta
    )
    fig.update_xaxes(type="category", tickangle=-45)
    fig.update_layout(height=520, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

# -- Tabela completa ---------------------------------------------------------
st.subheader("Tabela completa")
cols_show = ["municipio", "codufmun", "leitos_sus", "leitos_total",
             "uti_sus", "clinico_sus", "cirurgico_sus",
             "obstetrico_sus", "pediatrico_sus", "n_hospitais"]
cols_show = [c for c in cols_show if c in df.columns]
st.dataframe(df[cols_show], use_container_width=True, height=400)
