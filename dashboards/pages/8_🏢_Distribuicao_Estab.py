"""F1 — Distribuição de Estabelecimentos por Tipo e Município.

Mostra, para cada município do RS, a contagem de unidades de saúde por tipo
(TP_UNID do CNES). Permite identificar municípios descobertos de determinado
nível de atenção.

Tipos analisados (códigos oficiais CNES):
  02 — Centro de Saúde / UBS
  05 — Hospital Geral
  36 — Clínica / Centro de Especialidades
  73 — Pronto Atendimento (UPA)

Fonte: silver/cnes_st (snapshot mais recente).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import duckdb
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import pergunta_box  # noqa: E402
from utils.queries import get_conn  # noqa: E402

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
SILVER = DATA_ROOT / "lake" / "silver"
GEOJSON_PATH = DATA_ROOT / "ibge" / "rs_municipios.geojson"

st.set_page_config(page_title="F1 Distribuição Estab — DataSUS RS", layout="wide")
st.title("🏢 F1 — Distribuição de Estabelecimentos por Tipo")
pergunta_box(
    "Quais municípios do RS estão descobertos de hospital geral, UBS, UPA ou centro de "
    "especialidades — e onde estão os vazios assistenciais?"
)
st.caption(
    "Cobertura territorial dos principais tipos de unidade SUS. "
    "Municípios sem hospital geral, UBS ou UPA são vazios assistenciais."
)

# Códigos TP_UNID oficiais (CNES)
TIPOS_INTERESSE = {
    "02": "UBS",
    "05": "Hospital Geral",
    "36": "Centro Especialidades",
    "73": "UPA",
}


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    return get_conn()


@st.cache_resource(show_spinner="Carregando GeoJSON RS...")
def _geojson() -> dict:
    with open(GEOJSON_PATH) as f:
        geo = json.load(f)
    for f in geo["features"]:
        cod7 = str(f["properties"].get("id", ""))
        f["properties"]["cod6"] = cod7[:6]
        f["properties"]["nome"] = f["properties"].get("name", "")
    return geo


@st.cache_data(ttl=300, show_spinner="Contando estabelecimentos por município...")
def _distribuicao_por_municipio():
    """Snapshot mais recente do CNES.ST. Pivota por tipo."""
    tipos_list = ", ".join(f"'{t}'" for t in TIPOS_INTERESSE)
    return _conn().execute(f"""
        WITH snap AS (
            SELECT
                codufmun,
                tp_unid,
                cnes,
                ROW_NUMBER() OVER (
                    PARTITION BY cnes ORDER BY competencia DESC
                ) AS rn
            FROM read_parquet('{SILVER}/cnes_st/**/*.parquet', hive_partitioning=true)
            WHERE codufmun IS NOT NULL
              AND substr(codufmun, 1, 2) = '43'   -- RS
        ),
        unicos AS (
            SELECT codufmun, tp_unid
            FROM snap WHERE rn = 1
        )
        SELECT
            codufmun                                                          AS cod6,
            COUNT(*) FILTER (WHERE tp_unid IN ({tipos_list}))                AS total_interesse,
            COUNT(*) FILTER (WHERE tp_unid = '02') AS qt_ubs,
            COUNT(*) FILTER (WHERE tp_unid = '05') AS qt_hospital_geral,
            COUNT(*) FILTER (WHERE tp_unid = '36') AS qt_centro_especialidades,
            COUNT(*) FILTER (WHERE tp_unid = '73') AS qt_upa,
            COUNT(*) AS qt_total_estabelecimentos
        FROM unicos
        GROUP BY codufmun
        ORDER BY total_interesse DESC
    """).df()


@st.cache_resource
def _cod6_to_nome() -> dict[str, str]:
    return {
        f["properties"]["cod6"]: f["properties"]["nome"]
        for f in _geojson()["features"]
    }


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
df = _distribuicao_por_municipio()
nome_map = _cod6_to_nome()
df.insert(0, "municipio", df["cod6"].map(nome_map).fillna(df["cod6"]))

# KPIs
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Municípios RS", f"{len(df):,}")
m2.metric("Sem UBS", f"{(df['qt_ubs'] == 0).sum():,}")
m3.metric("Sem Hospital Geral", f"{(df['qt_hospital_geral'] == 0).sum():,}")
m4.metric("Sem Centro Esp.", f"{(df['qt_centro_especialidades'] == 0).sum():,}")
m5.metric("Sem UPA", f"{(df['qt_upa'] == 0).sum():,}")

# Filtro de tipo
st.divider()
col_a, col_b = st.columns([1, 2])
with col_a:
    tipo_sel_nome = st.selectbox(
        "Tipo de unidade para mapear",
        options=list(TIPOS_INTERESSE.values()),
        index=1,  # Hospital Geral
    )
    col_label = {
        "UBS": "qt_ubs",
        "Hospital Geral": "qt_hospital_geral",
        "Centro Especialidades": "qt_centro_especialidades",
        "UPA": "qt_upa",
    }[tipo_sel_nome]

with col_b:
    st.info(
        f"**{(df[col_label] == 0).sum():,} municípios** estão **sem {tipo_sel_nome}** "
        f"({(df[col_label] == 0).sum() / len(df):.0%} do RS)."
    )

# Choropleth
st.subheader(f"Mapa — {tipo_sel_nome} por município")
plot_df = df.copy()
plot_df["tem_unidade"] = (plot_df[col_label] > 0).astype(int)

fig = px.choropleth_mapbox(
    plot_df,
    geojson=_geojson(),
    locations="cod6",
    featureidkey="properties.cod6",
    color=col_label,
    color_continuous_scale="Greens",
    range_color=(0, max(1, plot_df[col_label].quantile(0.95))),
    mapbox_style="carto-positron",
    center={"lat": -30.0, "lon": -53.5},
    zoom=5.7,
    opacity=0.75,
    hover_name="municipio",
    hover_data={
        "qt_ubs": True,
        "qt_hospital_geral": True,
        "qt_centro_especialidades": True,
        "qt_upa": True,
        "cod6": False,
    },
)
fig.update_layout(height=600, margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

# Lista de "vazios" assistenciais
st.divider()
vazios = df[df[col_label] == 0]
if len(vazios):
    st.subheader(f"🚨 Municípios sem {tipo_sel_nome} ({len(vazios):,})")
    st.dataframe(
        vazios[["municipio", "cod6", "qt_total_estabelecimentos"]]
        .sort_values("municipio"),
        use_container_width=True,
        height=300,
    )

# Tabela completa
st.divider()
st.subheader("Tabela completa — ranking por unidades de interesse")
cols_show = [
    "municipio", "qt_ubs", "qt_hospital_geral", "qt_centro_especialidades",
    "qt_upa", "qt_total_estabelecimentos", "cod6",
]
st.dataframe(
    df[cols_show].sort_values("total_interesse" if "total_interesse" in df.columns else "qt_total_estabelecimentos", ascending=False),
    use_container_width=True,
    height=400,
)
