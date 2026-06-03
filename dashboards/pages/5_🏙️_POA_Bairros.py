"""Página: Mapa de Porto Alegre por bairro.

Por que só Porto Alegre (e não toda a RMPA)?
  Bairros oficiais com shapefile estável só existem pra POA (Lei Complementar
  12.112/2016 + ArcGIS SMAMUS). Pra outros municípios da RMPA, a divisão por
  bairro varia em qualidade, e shapefiles unificados não existem.

  Pra fluxos RMPA ↔ outros municípios (residência), use a página
  "🗺️ Mapa Mortalidade RS" e filtre pela faixa de municípios desejada.

Granularidade: bairro (via cep do SIH.RD).
Lookup cep→bairro: data/ibge/poa_cep_bairro.csv (gerado pelo script
download_poa_geo.py com base em faixas dos Correios).
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.queries import get_conn  # noqa: E402

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
GEOJSON_PATH = DATA_ROOT / "ibge" / "poa_bairros.geojson"
CEP_LOOKUP_PATH = DATA_ROOT / "ibge" / "poa_cep_bairro.csv"
POPULACAO_PATH = DATA_ROOT / "ibge" / "poa_populacao_bairro.csv"
SILVER = DATA_ROOT / "lake" / "silver"

POA_COD6 = "431490"   # IBGE 6-dígitos de Porto Alegre

st.set_page_config(page_title="POA Bairros — DataSUS RS", layout="wide")
st.title("🏙️ Mapa de Porto Alegre por Bairro")
st.caption(
    "Choropleth dos 94 bairros oficiais de POA. "
    "Granularidade: bairro (via cep do SIH.RD). "
    "Fora do escopo de POA, ver a página '🗺️ Mapa Mortalidade RS'."
)


@st.cache_resource(show_spinner="Carregando shapefile de bairros POA...")
def _load_geojson() -> dict:
    if not GEOJSON_PATH.exists():
        st.error(
            f"GeoJSON não encontrado em {GEOJSON_PATH}. "
            "Rode: `python scripts/download_poa_geo.py`"
        )
        st.stop()
    with open(GEOJSON_PATH) as f:
        geo = json.load(f)
    # Normaliza propriedade `bairro` em todas as features (já vem assim)
    for feat in geo["features"]:
        props = feat["properties"]
        props["bairro"] = (props.get("bairro") or "").strip()
    return geo


@st.cache_resource(show_spinner="Carregando lookup CEP → bairro...")
def _load_cep_lookup() -> pd.DataFrame:
    if not CEP_LOOKUP_PATH.exists():
        st.error(
            f"Lookup CEP não encontrado em {CEP_LOOKUP_PATH}. "
            "Rode: `python scripts/download_poa_geo.py`"
        )
        st.stop()
    df = pd.read_csv(CEP_LOOKUP_PATH, dtype={"cep_prefix": str})
    return df


@st.cache_resource(show_spinner="Carregando população por bairro (Censo 2022)...")
def _load_populacao() -> pd.DataFrame:
    if not POPULACAO_PATH.exists():
        st.warning(
            f"População por bairro não encontrada em {POPULACAO_PATH}. "
            "Métricas per capita ficarão indisponíveis. "
            "Rode: `python scripts/download_poa_populacao.py`"
        )
        return pd.DataFrame(columns=["bairro", "populacao"])
    return pd.read_csv(POPULACAO_PATH)


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    con = get_conn()
    # Registra lookups como tabelas DuckDB pra fazer joins SQL eficientes
    con.register("cep_bairro_lookup", _load_cep_lookup())
    con.register("populacao_bairro", _load_populacao())
    return con


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------
@st.cache_data(ttl=60, show_spinner="Agregando SIH por bairro...")
def _metrica_sih_bairro(d_min: date, d_max: date):
    return _conn().execute(f"""
        WITH sih_poa AS (
            SELECT
                CASE WHEN length(CAST(CAST(TRY_CAST(cep AS BIGINT) AS VARCHAR) AS VARCHAR)) >= 5
                    THEN lpad(CAST(TRY_CAST(cep AS BIGINT) AS VARCHAR), 8, '0')
                END AS cep_norm,
                morte, dias_perm, val_tot, uso_uti, idade_anos
            FROM read_parquet('{SILVER}/sih_rd/**/*.parquet', hive_partitioning=true)
            WHERE munic_res = '{POA_COD6}'
              AND competencia BETWEEN '{d_min}' AND '{d_max}'
        ),
        sih_join AS (
            SELECT
                lookup.bairro,
                morte, dias_perm, val_tot, uso_uti, idade_anos
            FROM sih_poa
            JOIN cep_bairro_lookup lookup
              ON substr(sih_poa.cep_norm, 1, 5) = lookup.cep_prefix
            WHERE bairro IS NOT NULL
        )
        SELECT
            sih_join.bairro,
            COUNT(*)::BIGINT                    AS internacoes,
            SUM(morte)::BIGINT                  AS mortes_hospital,
            CASE WHEN COUNT(*) > 0
                 THEN SUM(morte) * 100.0 / COUNT(*)
            END                                 AS taxa_mortalidade,
            AVG(dias_perm)::DOUBLE              AS perm_media,
            SUM(val_tot)::DOUBLE                AS custo_total,
            AVG(val_tot)::DOUBLE                AS custo_medio,
            SUM(uso_uti)::BIGINT                AS n_uti,
            AVG(idade_anos)::DOUBLE             AS idade_media,
            -- População do bairro (Censo 2022 / ObservaPOA)
            populacao_bairro.populacao          AS populacao,
            -- Métricas per capita (NULL quando população desconhecida)
            CASE WHEN populacao_bairro.populacao > 0
                 THEN COUNT(*) * 1000.0 / populacao_bairro.populacao
            END                                 AS internacoes_por_1000,
            CASE WHEN populacao_bairro.populacao > 0
                 THEN SUM(morte) * 100000.0 / populacao_bairro.populacao
            END                                 AS mortes_por_100k,
            CASE WHEN populacao_bairro.populacao > 0
                 THEN SUM(val_tot) / populacao_bairro.populacao
            END                                 AS custo_per_capita
        FROM sih_join
        LEFT JOIN populacao_bairro USING (bairro)
        GROUP BY sih_join.bairro, populacao_bairro.populacao
        HAVING internacoes >= 1
    """).df()


@st.cache_data(ttl=60, show_spinner="Cobertura cep→bairro (qualidade)...")
def _cobertura_cep(d_min: date, d_max: date):
    """Quantos % das internações em POA têm cep mapeado pra bairro?"""
    return _conn().execute(f"""
        WITH sih_poa AS (
            SELECT cep
            FROM read_parquet('{SILVER}/sih_rd/**/*.parquet', hive_partitioning=true)
            WHERE munic_res = '{POA_COD6}'
              AND competencia BETWEEN '{d_min}' AND '{d_max}'
        ),
        cls AS (
            SELECT
                CASE
                    WHEN cep IS NULL OR length(trim(cep)) = 0 THEN 'sem_cep'
                    WHEN lookup.bairro IS NULL THEN 'cep_sem_bairro'
                    ELSE 'mapeado'
                END AS status
            FROM sih_poa
            LEFT JOIN cep_bairro_lookup lookup
                ON substr(lpad(CAST(TRY_CAST(cep AS BIGINT) AS VARCHAR), 8, '0'), 1, 5)
                   = lookup.cep_prefix
        )
        SELECT status, COUNT(*)::BIGINT AS n FROM cls GROUP BY status
    """).df()


METRICAS = {
    "Mortalidade hospitalar (SIH)": {
        "color_col": "taxa_mortalidade",
        "color_label": "% mortalidade",
        "hover_cols": ["internacoes", "mortes_hospital", "taxa_mortalidade", "perm_media"],
        "color_scale": "Reds",
        "tipo": "rate",
        "rate_num": "mortes_hospital",
        "rate_den": "internacoes",
    },
    "Volume de internações (SIH)": {
        "color_col": "internacoes",
        "color_label": "Internações",
        "hover_cols": ["internacoes", "mortes_hospital", "taxa_mortalidade", "uti_pct"],
        "color_scale": "Blues",
        "log": True,
        "tipo": "count",
    },
    "Custo total SUS (SIH)": {
        "color_col": "custo_total",
        "color_label": "R$",
        "hover_cols": ["internacoes", "custo_total", "custo_medio"],
        "color_scale": "Purples",
        "log": True,
        "tipo": "count",
    },
    "Permanência média (SIH)": {
        "color_col": "perm_media",
        "color_label": "Dias",
        "hover_cols": ["internacoes", "perm_media"],
        "color_scale": "Oranges",
        "tipo": "count",
    },
    # --- per capita (Censo 2022 / ObservaPOA) ---------------------------------
    "Internações por 1.000 hab (SIH)": {
        "color_col": "internacoes_por_1000",
        "color_label": "Int. / 1k hab",
        "hover_cols": ["internacoes", "populacao", "internacoes_por_1000"],
        "color_scale": "Blues",
        "tipo": "count",
        "fmt": "{:,.1f}",
    },
    "Mortes hospitalares por 100k hab (SIH)": {
        "color_col": "mortes_por_100k",
        "color_label": "Mortes / 100k hab",
        "hover_cols": ["internacoes", "mortes_hospital", "populacao", "mortes_por_100k"],
        "color_scale": "Reds",
        "tipo": "count",
        "fmt": "{:,.1f}",
    },
    "Custo SUS per capita (SIH)": {
        "color_col": "custo_per_capita",
        "color_label": "R$ / hab",
        "hover_cols": ["internacoes", "custo_total", "populacao", "custo_per_capita"],
        "color_scale": "Purples",
        "tipo": "count",
        "fmt": "R$ {:,.2f}",
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
    metrica_nome = st.selectbox("Métrica", options=list(METRICAS), index=0)

if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

metrica = METRICAS[metrica_nome]

# ---------------------------------------------------------------------------
# Carrega dados + geo
# ---------------------------------------------------------------------------
df = _metrica_sih_bairro(d_min, d_max)
geo = _load_geojson()

if df.empty:
    st.warning(
        "Sem dados pra essa janela em Porto Alegre. "
        "Verifique se silver/sih_rd cobre essa data + se a coluna cep está populada."
    )
    st.stop()

# ---------------------------------------------------------------------------
# Cobertura — qualidade do lookup cep→bairro
# ---------------------------------------------------------------------------
cobertura = _cobertura_cep(d_min, d_max)
total = int(cobertura["n"].sum())
mapeados = int(cobertura.loc[cobertura["status"] == "mapeado", "n"].sum())
pct_mapeado = mapeados / total if total else 0
if pct_mapeado < 0.7:
    st.warning(
        f"⚠️ Só {pct_mapeado:.0%} das internações em POA tiveram cep mapeado pra bairro "
        f"({mapeados:,} de {total:,}). Resultado pode estar enviesado pros bairros "
        "que o lookup cobre melhor."
    )

# ---------------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------------
tipo = metrica.get("tipo", "count")

m1, m2, m3 = st.columns(3)
m1.metric("Bairros com dado", f"{len(df):,}")

if tipo == "count":
    serie = df[metrica["color_col"]].dropna()
    total_v = serie.sum()
    media_v = serie.mean() if len(serie) else 0
    fmt = metrica.get("fmt") or (
        "R$ {:,.0f}" if metrica["color_label"] == "R$" else (
            "{:.1f} dias" if "Dias" in metrica["color_label"] else "{:,.0f}"
        )
    )
    # Pra métricas per capita, "Total" não faz sentido (somar taxas) — mostra
    # apenas média entre bairros, e usa a contagem absoluta separadamente.
    if metrica["color_col"] in ("internacoes_por_1000", "mortes_por_100k", "custo_per_capita"):
        m2.metric(
            f"Média entre bairros — {metrica['color_label']}",
            fmt.format(media_v),
        )
        # Mediana é mais robusta a outliers (bairros pequenos)
        m3.metric(
            f"Mediana — {metrica['color_label']}",
            fmt.format(serie.median() if len(serie) else 0),
        )
    else:
        m2.metric(f"Total — {metrica['color_label']}", fmt.format(total_v))
        m3.metric("Média por bairro", fmt.format(media_v))
elif tipo == "rate":
    num_total = df[metrica["rate_num"]].sum()
    den_total = df[metrica["rate_den"]].sum()
    num_media = df[metrica["rate_num"]].mean()
    taxa = (num_total / den_total * 100) if den_total else 0
    m2.metric(
        f"Total de casos em POA ({metrica['rate_num']})",
        f"{num_total:,.0f}",
        help=f"Taxa ponderada POA: {taxa:.2f}% ({num_total:,.0f} / {den_total:,.0f})",
    )
    m3.metric(
        f"Média por bairro ({metrica['rate_num']})",
        f"{num_media:,.1f}",
        help=f"Média aritmética entre os {len(df):,} bairros com dado.",
    )

# ---------------------------------------------------------------------------
# Choropleth
# ---------------------------------------------------------------------------
st.subheader(metrica_nome)

color_col = metrica["color_col"]
plot_df = df.copy()

if metrica.get("log"):
    import numpy as np
    plot_df["__color"] = np.log10(plot_df[color_col].clip(lower=1))
    color_for_plot = "__color"
    color_label_plot = f"log₁₀ {metrica['color_label']}"
else:
    color_for_plot = color_col
    color_label_plot = metrica["color_label"]

hover_data: dict[str, bool] = {"bairro": True}
for c in metrica["hover_cols"]:
    if c in plot_df.columns:
        hover_data[c] = True
if metrica.get("log"):
    hover_data["__color"] = False

fig = px.choropleth_mapbox(
    plot_df,
    geojson=geo,
    locations="bairro",
    featureidkey="properties.bairro",
    color=color_for_plot,
    color_continuous_scale=metrica["color_scale"],
    mapbox_style="carto-positron",
    center={"lat": -30.05, "lon": -51.20},
    zoom=10.5,
    opacity=0.75,
    hover_name="bairro",
    hover_data=hover_data,
    labels={color_for_plot: color_label_plot, "bairro": "Bairro"},
)
fig.update_layout(height=650, margin={"r": 0, "t": 0, "l": 0, "b": 0})
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# Tabela
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Tabela — bairros ordenados pela métrica")
st.dataframe(
    df.sort_values(color_col, ascending=False),
    use_container_width=True,
    height=400,
)

# ---------------------------------------------------------------------------
# Limitações
# ---------------------------------------------------------------------------
with st.expander("ℹ️ Limitações desta análise"):
    st.markdown(f"""
**Cobertura do lookup cep→bairro:**

- Total de internações em POA no período: **{total:,}**
- Com cep mapeado: **{mapeados:,} ({pct_mapeado:.1%})**
- Sem cep ou prefixo não mapeado: **{total - mapeados:,}**

O lookup cobre as faixas conhecidas de cep dos 94 bairros oficiais de POA
(Lei Complementar 12.112/2016). ceps que não casam:

1. Internações **fora de POA** registradas com município de residência POA (erro de cadastro)
2. ceps **comerciais/grandes empresas** que têm faixa própria
3. Bairros **muito novos** ou divididos após 2016

**Não inclui:** demais municípios da RMPA. Pra Canoas, São Leopoldo, etc.,
veja a página de mapa estadual.

**Granularidade do dado clínico:** SIH.RD usa cep do paciente (residência),
não do hospital. Ou seja, este mapa mostra "**onde os pacientes que internam vivem**",
não "onde estão os hospitais".
""")
