"""F5 — Silêncio Epidemiológico.

Mapa coroplético interativo (Folium) destacando municípios com:
  - Taxa de mortalidade hospitalar > P75 regional
  - Disponibilidade de leitos SUS < P25 regional

Enriquecido com vulnerabilidade socioeconômica (IDHM, renda per capita —
Atlas Brasil 2010), evidenciando correlação entre exclusão social e baixa
oferta assistencial.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import date
from pathlib import Path

import duckdb
import folium
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.queries import get_conn  # noqa: E402

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
GOLD = DATA_ROOT / "lake" / "gold"
GEOJSON_PATH = DATA_ROOT / "ibge" / "rs_municipios.geojson"
IDHM_PATH = DATA_ROOT / "ibge" / "43_idhm_municipio.csv"

st.set_page_config(page_title="F5 Silêncio Epidemiológico — DataSUS RS", layout="wide")
st.title("🔇 F5 — Silêncio Epidemiológico")
st.caption(
    "Municípios com mortalidade alta (>p75) E baixa oferta de leitos (<p25). "
    "Enriquecido com IDHM/renda Atlas Brasil 2010 pra revelar correlação social."
)


@st.cache_resource
def _conn() -> duckdb.DuckDBPyConnection:
    return get_conn()


@st.cache_resource
def _geojson() -> dict:
    with open(GEOJSON_PATH) as f:
        return json.load(f)


@st.cache_resource
def _idhm() -> pd.DataFrame:
    if not IDHM_PATH.exists():
        st.warning(f"IDHM não encontrado em {IDHM_PATH}. Rode `scripts/download_idhm.py`.")
        return pd.DataFrame(columns=["cod6", "idhm", "renda_per_capita", "gini"])
    return pd.read_csv(IDHM_PATH, dtype={"cod6": str, "cod7": str})


@st.cache_data(ttl=60, show_spinner="Calculando silêncio epidemiológico...")
def _calcular(d_min: date, d_max: date) -> pd.DataFrame:
    """Mortalidade + leitos por município no período."""
    sql = f"""
        WITH mort AS (
            SELECT cod6,
                   SUM(internacoes)::BIGINT  AS internacoes,
                   SUM(obitos)::BIGINT       AS obitos,
                   CASE WHEN SUM(internacoes) > 0
                        THEN SUM(obitos) * 100.0 / SUM(internacoes)
                   END                       AS taxa_mortalidade
            FROM read_parquet('{GOLD}/mortalidade_municipio_competencia/**/*.parquet',
                              hive_partitioning=true)
            WHERE competencia BETWEEN '{d_min}' AND '{d_max}'
            GROUP BY cod6
            HAVING internacoes >= 5
        ),
        leitos AS (
            SELECT codufmun AS cod6,
                   AVG(leitos_sus_por_1000hab) AS leitos_por_1000hab,
                   AVG(populacao)              AS populacao,
                   AVG(leitos_sus_total)       AS leitos_sus_total
            FROM read_parquet('{GOLD}/leitos_municipio_mes/**/*.parquet',
                              hive_partitioning=true)
            WHERE competencia BETWEEN '{d_min}' AND '{d_max}'
              AND substr(codufmun, 1, 2) = '43'
            GROUP BY codufmun
        )
        SELECT
            COALESCE(mort.cod6, leitos.cod6) AS cod6,
            COALESCE(mort.internacoes, 0) AS internacoes,
            COALESCE(mort.obitos, 0) AS obitos,
            mort.taxa_mortalidade,
            leitos.leitos_por_1000hab,
            leitos.populacao,
            COALESCE(leitos.leitos_sus_total, 0) AS leitos_sus_total
        FROM mort FULL OUTER JOIN leitos USING (cod6)
    """
    df = _conn().execute(sql).df()

    # Adiciona IDHM
    idhm = _idhm()
    if not idhm.empty:
        df = df.merge(
            idhm[["cod6", "idhm", "renda_per_capita", "gini", "pct_pobres"]],
            on="cod6", how="left",
        )

    return df


# ---------------------------------------------------------------------------
# UI
# ---------------------------------------------------------------------------
col_a, col_b = st.columns(2)
with col_a:
    d_min = st.date_input("Data início", value=date(2020, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))

df = _calcular(d_min, d_max)
if df.empty or df["taxa_mortalidade"].isna().all() or df["leitos_por_1000hab"].isna().all():
    st.warning("Sem dados suficientes pra calcular silêncio epidemiológico.")
    st.stop()

# Quartis regionais
p75_mort = df["taxa_mortalidade"].quantile(0.75)
p25_leitos = df["leitos_por_1000hab"].quantile(0.25)

df["silencio"] = (
    (df["taxa_mortalidade"] > p75_mort) & (df["leitos_por_1000hab"] < p25_leitos)
).astype(int)

n_silencio = int(df["silencio"].sum())

# Mapa nome
nome_map = {f["properties"]["id"][:6]: f["properties"]["name"]
            for f in _geojson()["features"]}
df.insert(0, "municipio", df["cod6"].map(nome_map).fillna(df["cod6"]))

# KPIs
m1, m2, m3, m4 = st.columns(4)
m1.metric("Municípios analisados", f"{len(df):,}")
m2.metric("🚨 Silêncio epidemiológico", f"{n_silencio:,}",
          help=f"Mortalidade > {p75_mort:.2f}% E leitos/1k < {p25_leitos:.2f}")
m3.metric("p75 mortalidade", f"{p75_mort:.2f}%")
m4.metric("p25 leitos/1k hab", f"{p25_leitos:.2f}")

st.divider()

# Mapa Folium
st.subheader("Mapa — Silêncio Epidemiológico")

m = folium.Map(location=[-30.0, -53.5], zoom_start=6.5, tiles="cartodbpositron")

# Coloriza municípios — vermelho = silêncio, demais escala neutra
cods_silencio = set(df.loc[df["silencio"] == 1, "cod6"].astype(str))

def _style(feat):
    cod6 = str(feat["properties"].get("id", ""))[:6]
    if cod6 in cods_silencio:
        return {"fillColor": "#b30000", "color": "#b30000", "weight": 1,
                "fillOpacity": 0.7}
    return {"fillColor": "#cccccc", "color": "#999999", "weight": 0.5,
            "fillOpacity": 0.2}

dfx = df.set_index("cod6")
def _tooltip(feat):
    cod6 = str(feat["properties"].get("id", ""))[:6]
    if cod6 not in dfx.index:
        return feat["properties"].get("name", cod6)
    row = dfx.loc[cod6]
    parts = [f"<b>{row['municipio']}</b><br>"]
    if pd.notna(row.get("taxa_mortalidade")):
        parts.append(f"Mortalidade: {row['taxa_mortalidade']:.2f}%<br>")
    if pd.notna(row.get("leitos_por_1000hab")):
        parts.append(f"Leitos/1k hab: {row['leitos_por_1000hab']:.2f}<br>")
    if pd.notna(row.get("idhm")):
        parts.append(f"IDHM 2010: {row['idhm']:.3f}<br>")
    if pd.notna(row.get("renda_per_capita")):
        parts.append(f"Renda per capita: R$ {row['renda_per_capita']:.0f}<br>")
    if row["silencio"]:
        parts.append("<b style='color:#b30000'>🚨 SILÊNCIO EPIDEMIOLÓGICO</b>")
    return "".join(parts)

folium.GeoJson(
    _geojson(),
    style_function=_style,
    tooltip=folium.GeoJsonTooltip(fields=["name"], aliases=["Município:"]),
    popup=folium.GeoJsonPopup(fields=["name"], aliases=["Município"]),
).add_to(m)

# Legenda
legenda = """
<div style='position: fixed; bottom: 50px; left: 50px; width: 220px;
            background: white; border: 2px solid grey; padding: 10px;
            font-size: 13px; z-index:9999'>
  <b>Silêncio Epidemiológico</b><br>
  <span style='background:#b30000;width:15px;height:15px;display:inline-block'></span>
    Mortalidade > p75 E leitos < p25<br>
  <span style='background:#cccccc;width:15px;height:15px;display:inline-block'></span>
    Demais municípios
</div>
"""
m.get_root().html.add_child(folium.Element(legenda))

st_folium(m, width=None, height=600, returned_objects=[])

# Lista de municípios em silêncio
st.divider()
sil_df = df[df["silencio"] == 1].copy()
if not sil_df.empty:
    st.subheader(f"🚨 Municípios em silêncio epidemiológico ({len(sil_df):,})")
    sil_df["renda_per_capita_fmt"] = sil_df["renda_per_capita"].apply(
        lambda v: f"R$ {v:.0f}" if pd.notna(v) else "—")
    st.dataframe(
        sil_df.sort_values("taxa_mortalidade", ascending=False)
        [["municipio", "taxa_mortalidade", "leitos_por_1000hab", "internacoes",
          "obitos", "idhm", "renda_per_capita_fmt", "gini", "pct_pobres", "cod6"]]
        .rename(columns={
            "taxa_mortalidade": "mort_%",
            "leitos_por_1000hab": "leitos/1k",
            "renda_per_capita_fmt": "renda/cap",
        }),
        use_container_width=True, height=400,
    )

    # Correlação social
    st.divider()
    st.subheader("Correlação com vulnerabilidade social")
    sil_idhm_mean = sil_df["idhm"].mean()
    todos_idhm_mean = df["idhm"].mean()
    sil_renda_mean = sil_df["renda_per_capita"].mean()
    todos_renda_mean = df["renda_per_capita"].mean()

    c1, c2 = st.columns(2)
    c1.metric("IDHM médio — em silêncio", f"{sil_idhm_mean:.3f}",
              delta=f"{sil_idhm_mean - todos_idhm_mean:+.3f} vs média RS")
    c2.metric("Renda per capita — em silêncio",
              f"R$ {sil_renda_mean:.0f}",
              delta=f"R$ {sil_renda_mean - todos_renda_mean:+.0f} vs média RS")
else:
    st.success("Nenhum município em silêncio epidemiológico no período selecionado.")
