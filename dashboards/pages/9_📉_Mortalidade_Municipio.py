"""F2 — Taxa de Mortalidade Hospitalar por Município e Competência.

Série temporal + mapa. Reusa gold/mortalidade_municipio_competencia que
materializa taxa_mortalidade = (óbitos / internações) × 100.
"""
from __future__ import annotations

import json
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
GOLD = DATA_ROOT / "lake" / "gold"
GEOJSON_PATH = DATA_ROOT / "ibge" / "rs_municipios.geojson"

st.set_page_config(page_title="F2 Mortalidade Município — DataSUS RS", layout="wide")
st.title("📉 F2 — Mortalidade Hospitalar por Município")
st.caption(
    "Taxa = (óbitos / internações) × 100, por município de residência × competência. "
    "Fonte: gold/mortalidade_municipio_competencia (materialização do SIH.RD)."
)


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    return get_conn()


@st.cache_resource
def _geojson() -> dict:
    with open(GEOJSON_PATH) as f:
        geo = json.load(f)
    for f in geo["features"]:
        cod7 = str(f["properties"].get("id", ""))
        f["properties"]["cod6"] = cod7[:6]
        f["properties"]["nome"] = f["properties"].get("name", "")
    return geo


@st.cache_resource
def _cod6_to_nome():
    return {f["properties"]["cod6"]: f["properties"]["nome"] for f in _geojson()["features"]}


@st.cache_data(ttl=60, show_spinner="Agregando mortalidade...")
def _agg_municipio(d_min: date, d_max: date):
    return _conn().execute(f"""
        SELECT
            cod6,
            SUM(internacoes)::BIGINT          AS internacoes,
            SUM(obitos)::BIGINT               AS obitos,
            CASE WHEN SUM(internacoes) > 0
                 THEN SUM(obitos) * 100.0 / SUM(internacoes)
            END                               AS taxa_mortalidade,
            AVG(permanencia_media)::DOUBLE    AS permanencia_media
        FROM read_parquet('{GOLD}/mortalidade_municipio_competencia/**/*.parquet',
                          hive_partitioning=true)
        WHERE competencia BETWEEN '{d_min}' AND '{d_max}'
        GROUP BY cod6
        HAVING internacoes >= 5
    """).df()


@st.cache_data(ttl=60, show_spinner="Carregando série temporal...")
def _agg_temporal(d_min: date, d_max: date):
    return _conn().execute(f"""
        SELECT
            competencia,
            SUM(internacoes)::BIGINT  AS internacoes,
            SUM(obitos)::BIGINT       AS obitos,
            CASE WHEN SUM(internacoes) > 0
                 THEN SUM(obitos) * 100.0 / SUM(internacoes)
            END                       AS taxa_mortalidade
        FROM read_parquet('{GOLD}/mortalidade_municipio_competencia/**/*.parquet',
                          hive_partitioning=true)
        WHERE competencia BETWEEN '{d_min}' AND '{d_max}'
        GROUP BY competencia ORDER BY competencia
    """).df()


# Filtros
col_a, col_b = st.columns(2)
with col_a:
    d_min = st.date_input("Data início", value=date(2020, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))

if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

df = _agg_municipio(d_min, d_max)
if df.empty:
    st.warning("Sem dados pra esse range.")
    st.stop()

nome_map = _cod6_to_nome()
df.insert(0, "municipio", df["cod6"].map(nome_map).fillna(df["cod6"]))

# KPIs
m1, m2, m3, m4 = st.columns(4)
m1.metric("Municípios", f"{len(df):,}")
m2.metric("Internações", f"{df['internacoes'].sum():,}")
m3.metric("Óbitos", f"{df['obitos'].sum():,}")
taxa_global = df["obitos"].sum() / df["internacoes"].sum() * 100
m4.metric("Taxa RS ponderada", f"{taxa_global:.2f}%")

st.divider()

# Mapa
st.subheader("Mapa — Taxa de mortalidade por município")
fig = px.choropleth_mapbox(
    df,
    geojson=_geojson(),
    locations="cod6",
    featureidkey="properties.cod6",
    color="taxa_mortalidade",
    color_continuous_scale="Reds",
    mapbox_style="carto-positron",
    center={"lat": -30.0, "lon": -53.5},
    zoom=5.7,
    opacity=0.75,
    hover_name="municipio",
    hover_data={"internacoes": True, "obitos": True, "taxa_mortalidade": ":.2f", "cod6": False},
    labels={"taxa_mortalidade": "Taxa %"},
)
fig.update_layout(height=600, margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

# Série temporal
st.divider()
serie = _agg_temporal(d_min, d_max)
if not serie.empty:
    st.subheader("Tendência temporal — Taxa RS")
    fig = px.line(serie, x="competencia", y="taxa_mortalidade", markers=True,
                  title="Taxa de mortalidade hospitalar mensal (RS)")
    fig.update_layout(yaxis_title="Taxa (%)")
    st.plotly_chart(fig, use_container_width=True)

# Tabela
st.divider()
st.subheader("Ranking — municípios por taxa de mortalidade")
st.dataframe(
    df.sort_values("taxa_mortalidade", ascending=False)
    [["municipio", "internacoes", "obitos", "taxa_mortalidade", "permanencia_media", "cod6"]],
    use_container_width=True,
    height=400,
)
