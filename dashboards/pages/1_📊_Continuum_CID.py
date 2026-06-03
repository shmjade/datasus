"""Página: Continuum de Cuidado por CID.

Mostra a "cascata" agregada por CID:
internações (SIH) → óbitos (SIM) → letalidade hospitalar,
com filtro de período e CID. Inclui tendência temporal.
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import plotly.express as px
import streamlit as st

# Resolve import quando rodando dentro do container (cwd=/app)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import pergunta_box  # noqa: E402
from utils.queries import (  # noqa: E402
    cids_disponiveis,
    continuum_por_cid,
    continuum_temporal,
    get_conn,
)

st.set_page_config(page_title="Continuum CID — DataSUS RS", layout="wide")
st.title("📊 Continuum de Cuidado por CID")
pergunta_box(
    "Quais doenças mais internam, mais matam e mais custam ao SUS no RS — "
    "e como cada CID se comporta ao longo do tempo?"
)
st.caption("Internações × Óbitos × CSAP agregados por CID-10 (3 caracteres).")


@st.cache_resource
def _conn():
    return get_conn()


@st.cache_data(ttl=300)
def _cids():
    return cids_disponiveis(_conn())


@st.cache_data(ttl=60, show_spinner="Consultando agregação por CID...")
def _query_por_cid(d_min, d_max, cid):
    return continuum_por_cid(_conn(), d_min, d_max, cid)


@st.cache_data(ttl=60, show_spinner="Consultando série temporal...")
def _query_temporal(d_min, d_max, cid):
    return continuum_temporal(_conn(), d_min, d_max, cid)


# -- Filtros ------------------------------------------------------------------
col_a, col_b, col_c = st.columns([1, 1, 1])
with col_a:
    d_min = st.date_input("Data início", value=date(2022, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))
with col_c:
    cids_disp = _cids()
    cid_filter = st.selectbox(
        "Filtro CID (3 chars)",
        options=[""] + sorted(cids_disp),
        index=0,
        format_func=lambda c: "(todos)" if c == "" else c,
        help="Lista carregada do gold/continuum_cid_mes — só CIDs com dado aparecem.",
    )


if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

# -- Agregado por CID ---------------------------------------------------------
df = _query_por_cid(d_min, d_max, cid_filter)

if df.empty:
    st.warning("Sem dados pra esse filtro. Verifique se o pipeline silver/gold foi rodado.")
    st.stop()

st.subheader("Top causas no período")

m1, m2, m3, m4 = st.columns(4)
m1.metric("Internações", f"{int(df['internacoes'].sum()):,}")
m2.metric("Óbitos SIM", f"{int(df['obitos_sim'].sum()):,}")
let_global = df["mortes_hospital_sih"].sum() / max(df["internacoes"].sum(), 1)
m3.metric("Letalidade hospitalar", f"{let_global:.1%}")
csap_pct = df["csap"].sum() / max(df["internacoes"].sum(), 1)
m4.metric("% CSAP", f"{csap_pct:.1%}")

c1, c2 = st.columns([2, 3])

with c1:
    st.markdown("**Tabela completa**")
    st.dataframe(
        df.assign(
            letalidade=lambda d: (d["letalidade"] * 100).round(2),
            pct_csap=lambda d: (d["csap"] / d["internacoes"] * 100).round(1),
        ).drop(columns=["custo_total"], errors="ignore"),
        use_container_width=True,
        height=500,
    )

with c2:
    st.markdown("**Top CIDs por letalidade** (mín. 20 internações)")
    sub = df[df["internacoes"] >= 20].copy()
    if not sub.empty:
        top = (
            sub.assign(letalidade_pct=lambda d: d["letalidade"] * 100)
            .sort_values("letalidade_pct", ascending=False)
            .head(20)
            .sort_values("letalidade_pct", ascending=True)   # invertido pra Plotly
        )
        fig = px.bar(
            top,
            y="cid3",
            x="letalidade_pct",
            orientation="h",
            color="internacoes",
            color_continuous_scale="Blues",
            text=top["letalidade_pct"].round(1).astype(str) + "%",
            labels={
                "cid3": "CID-10",
                "letalidade_pct": "Letalidade hospitalar (%)",
                "internacoes": "Internações",
            },
        )
        fig.update_traces(textposition="outside")
        fig.update_layout(height=500, margin={"l": 0, "r": 20, "t": 10, "b": 10})
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Filtro de 20+ internações evita CIDs raros com letalidade enganosa "
            "(ex.: 1 morte em 1 internação = 100%). Cor = volume; barra = letalidade."
        )
    else:
        st.info("Sem CIDs com volume suficiente (≥20) no período.")

# -- Série temporal -----------------------------------------------------------
st.divider()
st.subheader("Série temporal")
serie = _query_temporal(d_min, d_max, cid_filter)
if not serie.empty:
    tab1, tab2, tab3 = st.tabs(["Internações", "Óbitos", "CSAP"])
    with tab1:
        fig = px.line(serie, x="competencia", y="internacoes", markers=True,
                      title="Internações por competência")
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        fig = px.line(serie, x="competencia", y="obitos", markers=True,
                      title="Óbitos por competência (SIM)")
        st.plotly_chart(fig, use_container_width=True)
    with tab3:
        fig = px.line(serie, x="competencia", y="csap", markers=True,
                      title="Internações CSAP por competência")
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Sem série temporal pra esse filtro.")
