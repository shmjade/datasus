"""F3 — Disponibilidade de Leitos SUS por 1.000 Habitantes.

Indicador-padrão de capacidade hospitalar SUS. Cruza CNES.LT (leitos SUS) com
IBGE Censo 2022 (população). Mostra mapa + ranking.

Fonte: gold/leitos_municipio_mes (com colunas per capita).
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

from utils import pergunta_box  # noqa: E402
from utils.queries import get_conn  # noqa: E402

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
GOLD = DATA_ROOT / "lake" / "gold"
GEOJSON_PATH = DATA_ROOT / "ibge" / "rs_municipios.geojson"

st.set_page_config(page_title="F3 Leitos per 1000 — DataSUS RS", layout="wide")
st.title("🏨 F3 — Leitos SUS por 1.000 Habitantes")
pergunta_box(
    "Quais cidades do RS mais precisam de leitos SUS por habitante — "
    "abaixo do parâmetro OMS (3 leitos / 1.000 hab)?"
)
st.caption(
    "Indicador-padrão de oferta hospitalar. OMS recomenda 3-5 leitos/1.000 hab. "
    "Brasil tem média ~2; RS varia muito por município."
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


@st.cache_data(ttl=60, show_spinner="Agregando leitos por município...")
def _leitos(d_min: date, d_max: date):
    return _conn().execute(f"""
        SELECT
            codufmun                                    AS cod6,
            AVG(leitos_sus_total)::DOUBLE               AS leitos_sus,
            AVG(leitos_uti_sus)::DOUBLE                 AS leitos_uti,
            AVG(populacao)::DOUBLE                      AS populacao,
            AVG(leitos_sus_por_1000hab)::DOUBLE         AS leitos_por_1000hab,
            AVG(leitos_uti_por_100khab)::DOUBLE         AS uti_por_100khab,
            AVG(n_hospitais)::DOUBLE                    AS n_hospitais
        FROM read_parquet('{GOLD}/leitos_municipio_mes/**/*.parquet',
                          hive_partitioning=true)
        WHERE competencia BETWEEN '{d_min}' AND '{d_max}'
          AND substr(codufmun, 1, 2) = '43'
        GROUP BY codufmun
        HAVING leitos_sus > 0
    """).df()


col_a, col_b = st.columns(2)
with col_a:
    d_min = st.date_input("Data início", value=date(2020, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))

df = _leitos(d_min, d_max)
if df.empty:
    st.warning("Sem dados pra esse range.")
    st.stop()

nome_map = _cod6_to_nome()
df.insert(0, "municipio", df["cod6"].map(nome_map).fillna(df["cod6"]))

m1, m2, m3, m4 = st.columns(4)
m1.metric("Municípios c/ leitos", f"{len(df):,}")
m2.metric("Mediana leitos/1k hab", f"{df['leitos_por_1000hab'].median():.2f}")
abaixo_oms = (df["leitos_por_1000hab"] < 3).sum()
m3.metric("Abaixo da OMS (<3)", f"{abaixo_oms:,}",
          help="OMS recomenda 3-5 leitos / 1.000 hab")
m4.metric("Sem UTI SUS", f"{(df['leitos_uti'] == 0).sum():,}")

st.divider()
st.subheader("Mapa — Leitos SUS por 1.000 habitantes")
fig = px.choropleth_mapbox(
    df,
    geojson=_geojson(),
    locations="cod6",
    featureidkey="properties.cod6",
    color="leitos_por_1000hab",
    color_continuous_scale="YlOrRd",
    range_color=(0, df["leitos_por_1000hab"].quantile(0.95)),
    mapbox_style="carto-positron",
    center={"lat": -30.0, "lon": -53.5},
    zoom=5.7,
    opacity=0.75,
    hover_name="municipio",
    hover_data={
        "leitos_sus": ":.0f",
        "populacao": ":.0f",
        "leitos_por_1000hab": ":.2f",
        "leitos_uti": ":.0f",
        "cod6": False,
    },
    labels={"leitos_por_1000hab": "Leitos/1k hab"},
)
fig.update_layout(height=600, margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

st.divider()
st.subheader("Top 30 municípios — maior oferta")
st.dataframe(
    df.sort_values("leitos_por_1000hab", ascending=False).head(30)
    [["municipio", "leitos_sus", "populacao", "leitos_por_1000hab",
      "leitos_uti", "n_hospitais", "cod6"]],
    use_container_width=True, height=400,
)
st.subheader("Bottom 30 (vazios assistenciais)")
st.dataframe(
    df.sort_values("leitos_por_1000hab", ascending=True).head(30)
    [["municipio", "leitos_sus", "populacao", "leitos_por_1000hab",
      "leitos_uti", "n_hospitais", "cod6"]],
    use_container_width=True, height=400,
)
