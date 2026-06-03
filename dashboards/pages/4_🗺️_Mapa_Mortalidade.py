"""Página: Mapa coroplético de mortalidade no RS.

Plot choropleth com Plotly usando GeoJSON dos municípios IBGE.
Métricas disponíveis:
- Mortalidade hospitalar (SIH.RD: MORTE=1 / total internações)
- Óbitos totais (SIM.DO)
- Óbitos hospitalares (SIM.DO + LOCOCOR=1)
- Internações totais (volume base)

Granularidade: município de residência (IBGE 6 dígitos).
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
GEOJSON_PATH = DATA_ROOT / "ibge" / "rs_municipios.geojson"
POPULACAO_PATH = DATA_ROOT / "ibge" / "rs_populacao_municipio.csv"
SILVER = DATA_ROOT / "lake" / "silver"
GOLD = DATA_ROOT / "lake" / "gold"

st.set_page_config(page_title="Mapa Mortalidade RS — DataSUS", layout="wide")
st.title("🗺️ Mapa de Mortalidade — RS")
st.caption(
    "Choropleth no nível municipal usando GeoJSON IBGE + agregação DuckDB. "
    "Granularidade: município de residência (6 dígitos IBGE). "
    "CEP não é usado — município é o nível adequado pra mapa estadual."
)


@st.cache_resource(show_spinner="Carregando shapefile RS...")
def _load_geojson() -> dict:
    """Carrega GeoJSON e adiciona propriedade `cod6` (6 dígitos)
    pra casar com os dados DataSUS."""
    if not GEOJSON_PATH.exists():
        st.error(
            f"GeoJSON não encontrado em {GEOJSON_PATH}. "
            "Rode: `python scripts/download_ibge_geo.py --uf RS`"
        )
        st.stop()
    with open(GEOJSON_PATH) as f:
        geo = json.load(f)
    for feat in geo["features"]:
        props = feat["properties"]
        cod7 = str(props.get("id", ""))
        props["cod6"] = cod7[:6]
        props["nome"] = props.get("name", "")
    return geo


@st.cache_resource
def _cod6_to_nome() -> dict[str, str]:
    """Dict {cod6: nome_municipio} pra enriquecer DataFrames."""
    geo = _load_geojson()
    return {
        f["properties"]["cod6"]: f["properties"]["nome"]
        for f in geo["features"]
    }


@st.cache_resource(show_spinner="Carregando população por município (Censo 2022)...")
def _load_populacao() -> "pd.DataFrame":
    import pandas as pd
    if not POPULACAO_PATH.exists():
        st.warning(
            f"População não encontrada em {POPULACAO_PATH}. "
            "Métricas per capita ficarão indisponíveis. "
            "Rode: `python scripts/download_rs_populacao.py`"
        )
        return pd.DataFrame(columns=["cod6", "populacao"])
    return pd.read_csv(POPULACAO_PATH, dtype={"cod6": str, "cod7": str})


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    con = get_conn()
    con.register("populacao_municipio", _load_populacao())
    return con


# ---------------------------------------------------------------------------
# Queries por métrica
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner="Calculando métrica por município...")
def _metrica_internacoes_morte(d_min: date, d_max: date):
    return _conn().execute(f"""
        WITH agg AS (
            SELECT
                munic_res                          AS cod6,
                COUNT(*)::BIGINT                   AS internacoes,
                SUM(morte)::BIGINT                 AS mortes_hospital,
                AVG(dias_perm)::DOUBLE             AS perm_media,
                SUM(val_tot)::DOUBLE               AS custo_total
            FROM read_parquet('{SILVER}/sih_rd/**/*.parquet', hive_partitioning=true)
            WHERE munic_res IS NOT NULL
              AND competencia BETWEEN '{d_min}' AND '{d_max}'
              AND substr(munic_res, 1, 2) = '43'   -- só RS
            GROUP BY munic_res
            HAVING internacoes >= 5
        )
        SELECT
            agg.cod6,
            agg.internacoes,
            agg.mortes_hospital,
            CASE WHEN agg.internacoes > 0
                 THEN agg.mortes_hospital * 100.0 / agg.internacoes
            END                                AS taxa_mortalidade,
            agg.perm_media,
            agg.custo_total,
            pop.populacao,
            -- Métricas per capita (NULL se população desconhecida)
            CASE WHEN pop.populacao > 0
                 THEN agg.internacoes * 1000.0 / pop.populacao
            END                                AS internacoes_por_1000,
            CASE WHEN pop.populacao > 0
                 THEN agg.mortes_hospital * 100000.0 / pop.populacao
            END                                AS mortes_por_100k,
            CASE WHEN pop.populacao > 0
                 THEN agg.custo_total / pop.populacao
            END                                AS custo_per_capita
        FROM agg
        LEFT JOIN populacao_municipio pop USING (cod6)
    """).df()


@st.cache_data(ttl=60, show_spinner="Calculando óbitos SIM por município...")
def _metrica_obitos_sim(d_min: date, d_max: date):
    return _conn().execute(f"""
        WITH agg AS (
            SELECT
                munic_res                                          AS cod6,
                COUNT(*)::BIGINT                                   AS obitos_totais,
                SUM(obito_hospitalar)::BIGINT                      AS obitos_hospitalares,
                SUM(causa_externa)::BIGINT                         AS obitos_causas_externas,
                SUM(causa_materna)::BIGINT                         AS obitos_maternos,
                AVG(idade_anos)::DOUBLE                            AS idade_media
            FROM read_parquet('{SILVER}/sim_do/**/*.parquet', hive_partitioning=true)
            WHERE munic_res IS NOT NULL
              AND dt_obito BETWEEN '{d_min}' AND '{d_max}'
              AND substr(munic_res, 1, 2) = '43'   -- só RS
            GROUP BY munic_res
            HAVING obitos_totais >= 1
        )
        SELECT
            agg.*,
            pop.populacao,
            CASE WHEN pop.populacao > 0
                 THEN agg.obitos_totais * 100000.0 / pop.populacao
            END AS obitos_por_100k,
            CASE WHEN pop.populacao > 0
                 THEN agg.obitos_causas_externas * 100000.0 / pop.populacao
            END AS obitos_externas_por_100k
        FROM agg
        LEFT JOIN populacao_municipio pop USING (cod6)
    """).df()


METRICAS = {
    "Mortalidade hospitalar (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "taxa_mortalidade",
        "color_label": "% mortalidade",
        "hover_cols": ["internacoes", "mortes_hospital", "taxa_mortalidade", "perm_media"],
        "color_scale": "Reds",
        "tipo": "rate",
        "rate_num": "mortes_hospital",   # numerador pra agregação ponderada
        "rate_den": "internacoes",       # denominador
        "fmt": "{:.2f}%",
    },
    "Volume de internações (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "internacoes",
        "color_label": "Internações",
        "hover_cols": ["internacoes", "mortes_hospital", "taxa_mortalidade"],
        "color_scale": "Blues",
        "log": True,
        "tipo": "count",
        "fmt": "{:,.0f}",
    },
    "Custo total SUS (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "custo_total",
        "color_label": "R$",
        "hover_cols": ["internacoes", "custo_total"],
        "color_scale": "Purples",
        "log": True,
        "tipo": "count",
        "fmt": "R$ {:,.0f}",
    },
    "Óbitos totais (SIM)": {
        "fn": _metrica_obitos_sim,
        "color_col": "obitos_totais",
        "color_label": "Óbitos",
        "hover_cols": ["obitos_totais", "obitos_hospitalares", "obitos_causas_externas", "obitos_maternos"],
        "color_scale": "Reds",
        "log": True,
        "tipo": "count",
        "fmt": "{:,.0f}",
    },
    "Óbitos hospitalares (SIM)": {
        "fn": _metrica_obitos_sim,
        "color_col": "obitos_hospitalares",
        "color_label": "Óbitos hosp.",
        "hover_cols": ["obitos_totais", "obitos_hospitalares"],
        "color_scale": "Reds",
        "log": True,
        "tipo": "count",
        "fmt": "{:,.0f}",
    },
    "Óbitos por causas externas (SIM)": {
        "fn": _metrica_obitos_sim,
        "color_col": "obitos_causas_externas",
        "color_label": "Causas externas",
        "hover_cols": ["obitos_totais", "obitos_causas_externas"],
        "color_scale": "Oranges",
        "tipo": "count",
        "fmt": "{:,.0f}",
    },
    # --- per capita (Censo 2022 / IBGE SIDRA) ---------------------------------
    "Internações por 1.000 hab (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "internacoes_por_1000",
        "color_label": "Int. / 1k hab",
        "hover_cols": ["internacoes", "populacao", "internacoes_por_1000"],
        "color_scale": "Blues",
        "tipo": "per_capita",
        "fmt": "{:,.1f}",
    },
    "Mortes hospitalares por 100k hab (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "mortes_por_100k",
        "color_label": "Mortes hosp. / 100k hab",
        "hover_cols": ["internacoes", "mortes_hospital", "populacao", "mortes_por_100k"],
        "color_scale": "Reds",
        "tipo": "per_capita",
        "fmt": "{:,.1f}",
    },
    "Custo SUS per capita (SIH)": {
        "fn": _metrica_internacoes_morte,
        "color_col": "custo_per_capita",
        "color_label": "R$ / hab",
        "hover_cols": ["internacoes", "custo_total", "populacao", "custo_per_capita"],
        "color_scale": "Purples",
        "tipo": "per_capita",
        "fmt": "R$ {:,.2f}",
    },
    "Óbitos totais por 100k hab (SIM)": {
        "fn": _metrica_obitos_sim,
        "color_col": "obitos_por_100k",
        "color_label": "Óbitos / 100k hab",
        "hover_cols": ["obitos_totais", "populacao", "obitos_por_100k"],
        "color_scale": "Reds",
        "tipo": "per_capita",
        "fmt": "{:,.1f}",
    },
    "Óbitos por causas externas por 100k hab (SIM)": {
        "fn": _metrica_obitos_sim,
        "color_col": "obitos_externas_por_100k",
        "color_label": "Externas / 100k hab",
        "hover_cols": ["obitos_causas_externas", "populacao", "obitos_externas_por_100k"],
        "color_scale": "Oranges",
        "tipo": "per_capita",
        "fmt": "{:,.1f}",
    },
}


# ---------------------------------------------------------------------------
# UI — filtros
# ---------------------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    d_min = st.date_input("Data início", value=date(2022, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))
with col_c:
    metrica_nome = st.selectbox(
        "Métrica",
        options=list(METRICAS),
        index=0,
    )

if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

metrica = METRICAS[metrica_nome]

# ---------------------------------------------------------------------------
# Carrega dados + geo
# ---------------------------------------------------------------------------
df = metrica["fn"](d_min, d_max)
geo = _load_geojson()

if df.empty:
    st.warning(
        "Sem dados pra essa janela. Verifique se o silver tem cobertura — "
        "os samples ingeridos são pontuais (1 competência por dataset)."
    )
    st.stop()

# Enriquece com nome do município (do GeoJSON IBGE)
nome_map = _cod6_to_nome()
df.insert(0, "municipio", df["cod6"].map(nome_map).fillna(df["cod6"]))

# ---------------------------------------------------------------------------
# KPIs (semântica depende do tipo da métrica)
# ---------------------------------------------------------------------------
tipo = metrica.get("tipo", "count")
fmt = metrica.get("fmt", "{:,.0f}")

m1, m2, m3 = st.columns(3)
m1.metric("Municípios com dado", f"{len(df):,}")

if tipo == "count":
    # Counts: soma faz sentido (total estadual) + média por município
    total = df[metrica["color_col"]].sum()
    media = df[metrica["color_col"]].mean()
    m2.metric(f"Total estadual — {metrica['color_label']}", fmt.format(total))
    m3.metric("Média por município", fmt.format(media))

elif tipo == "rate":
    # Quando a métrica do mapa é taxa (%), os KPIs mostram a CONTAGEM absoluta
    # (numerador) — total de casos no RS e média por município. A taxa estadual
    # ponderada vai no hover de cada KPI pra referência.
    num_total = df[metrica["rate_num"]].sum()
    den_total = df[metrica["rate_den"]].sum()
    num_media_mun = df[metrica["rate_num"]].mean()
    taxa_global = (num_total / den_total * 100) if den_total else 0

    m2.metric(
        f"Total de casos no RS ({metrica['rate_num']})",
        f"{num_total:,.0f}",
        help=(
            f"Soma de {metrica['rate_num']} em todos os municípios. "
            f"Taxa estadual ponderada: {taxa_global:.2f}% "
            f"({num_total:,.0f} / {den_total:,.0f})."
        ),
    )
    m3.metric(
        f"Média por município ({metrica['rate_num']})",
        f"{num_media_mun:,.1f}",
        help=(
            f"Média aritmética de {metrica['rate_num']} entre os "
            f"{len(df):,} municípios com dado."
        ),
    )

elif tipo == "per_capita":
    # Métricas per capita: somar taxas é absurdo. Mostramos média e mediana.
    # Mediana é importante porque municípios pequenos (denominador pequeno) podem
    # explodir a taxa — efeito do small denominator.
    serie = df[metrica["color_col"]].dropna()
    media_v = serie.mean() if len(serie) else 0
    mediana_v = serie.median() if len(serie) else 0
    m2.metric(
        f"Média entre municípios — {metrica['color_label']}",
        fmt.format(media_v),
        help="Média aritmética entre os municípios com dado. "
             "Sensível a outliers de municípios pequenos."
    )
    m3.metric(
        f"Mediana — {metrica['color_label']}",
        fmt.format(mediana_v),
        help="50% dos municípios estão abaixo desse valor. Robusta a outliers."
    )

# ---------------------------------------------------------------------------
# Choropleth
# ---------------------------------------------------------------------------
st.subheader(metrica_nome)

color_col = metrica["color_col"]
plot_df = df.copy()

# Escala log opcional pra métricas com cauda longa
if metrica.get("log"):
    import numpy as np
    plot_df["__color"] = np.log10(plot_df[color_col].clip(lower=1))
    color_for_plot = "__color"
    color_label_plot = f"log₁₀ {metrica['color_label']}"
else:
    color_for_plot = color_col
    color_label_plot = metrica["color_label"]

# Hover: nome do município em destaque + as métricas relevantes; oculta cod6 e helper col
hover_data: dict[str, bool] = {"municipio": True, "cod6": False}
for c in metrica["hover_cols"]:
    hover_data[c] = True
if metrica.get("log"):
    hover_data["__color"] = False

fig = px.choropleth_mapbox(
    plot_df,
    geojson=geo,
    locations="cod6",
    featureidkey="properties.cod6",
    color=color_for_plot,
    color_continuous_scale=metrica["color_scale"],
    range_color=(plot_df[color_for_plot].min(), plot_df[color_for_plot].max()),
    mapbox_style="carto-positron",
    center={"lat": -30.0, "lon": -53.5},
    zoom=5.7,
    opacity=0.75,
    hover_name="municipio",
    hover_data=hover_data,
    labels={color_for_plot: color_label_plot, "municipio": "Município"},
)
fig.update_layout(
    height=650,
    margin={"r": 0, "t": 0, "l": 0, "b": 0},
)
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabela completa — município primeiro, código IBGE no final pra referência
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Tabela — municípios ordenados pela métrica")

cols_ordem = ["municipio"] + [c for c in df.columns if c not in {"municipio", "cod6"}] + ["cod6"]
st.dataframe(
    df[cols_ordem].sort_values(color_col, ascending=False),
    use_container_width=True,
    height=400,
)

# ---------------------------------------------------------------------------
# Sobre CEP
# ---------------------------------------------------------------------------
with st.expander("ℹ️ Por que não usar CEP pra este mapa?"):
    st.markdown(
        """
**CEP é fino demais pra um mapa estadual.**

| Nível | Granularidade | RS |
|---|---|---|
| CEP completo (8 dígitos) | rua/quarteirão | ~750k áreas |
| CEP 5 dígitos | bairro | ~1.500 áreas |
| **Município IBGE 6 dígitos** | município | **497 áreas** |

**Município é o nível adequado** porque:
1. Tem shapefile oficial do IBGE pronto (este GeoJSON)
2. Casa com `MUNIC_RES` que vem direto do DataSUS
3. População per capita disponível por município (IBGE)

**CEP é útil em análises intra-municipais** — p. ex., heatmap de Porto Alegre
por bairro. Pra isso, precisaria de outro shapefile (Postmon/Brasilapi + Censo) e
focar em uma única cidade. Fora do escopo deste mapa estadual.
"""
    )
