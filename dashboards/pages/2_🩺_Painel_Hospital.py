"""Página: Painel do Hospital.

Para um CNES selecionado:
- Top 30 CIDs internados
- Mortalidade, permanência, UTI %, custo médio
- Funnel plot: volume × mortalidade comparada aos outros hospitais
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils.queries import (  # noqa: E402
    get_conn,
    hospitais_disponiveis,
    hospitais_por_volume,
    perfil_hospital,
)

st.set_page_config(page_title="Painel Hospital — DataSUS RS", layout="wide")
st.title("🩺 Painel do Hospital")
st.caption("Casuística e indicadores operacionais por estabelecimento.")


@st.cache_resource
def _conn():
    return get_conn()


@st.cache_data(ttl=300)
def _list_hospitais():
    return hospitais_disponiveis(_conn())


@st.cache_data(ttl=60, show_spinner="Carregando ranking de hospitais...")
def _ranking(d_min, d_max, cid):
    return hospitais_por_volume(_conn(), d_min, d_max, cid_prefix=cid, top_n=100)


@st.cache_data(ttl=60, show_spinner="Carregando perfil do hospital...")
def _perfil(cnes, d_min, d_max):
    return perfil_hospital(_conn(), cnes, d_min, d_max)


# -- Filtros ------------------------------------------------------------------
col_a, col_b, col_c, col_d = st.columns([1, 1, 1, 2])
with col_a:
    d_min = st.date_input("Data início", value=date(2022, 1, 1))
with col_b:
    d_max = st.date_input("Data fim", value=date(2026, 12, 31))
with col_c:
    cid_filter = st.text_input("Filtro CID (opcional)", "").strip().upper()
with col_d:
    hospitais = _list_hospitais()
    if not hospitais:
        st.warning("Sem dados de hospitais. Rode o pipeline gold antes.")
        st.stop()
    cnes_sel = st.selectbox(
        "Hospital (CNES)",
        options=[""] + hospitais,
        format_func=lambda x: f"CNES {x}" if x else "— escolha —",
    )

if d_min > d_max:
    st.error("Data início > data fim")
    st.stop()

# -- Ranking (funnel plot) ----------------------------------------------------
st.subheader("Ranking de hospitais")
rank = _ranking(d_min, d_max, cid_filter)
if not rank.empty:
    m1, m2, m3 = st.columns(3)
    m1.metric("Hospitais com ≥10 AIHs", f"{len(rank):,}")
    m2.metric("Mortalidade global", f"{rank['mortes'].sum() / max(rank['internacoes'].sum(), 1):.1%}")
    m3.metric("Permanência média", f"{rank['perm_media'].mean():.1f} dias")

    # Funnel plot — volume × mortalidade com bandas de IC 95% (binomial)
    if len(rank) >= 5:
        p_global = rank["mortes"].sum() / rank["internacoes"].sum()
        n_grid = np.linspace(10, rank["internacoes"].max(), 50)
        se = np.sqrt(p_global * (1 - p_global) / n_grid)
        upper = (p_global + 1.96 * se).clip(0, 1)
        lower = (p_global - 1.96 * se).clip(0, 1)

        fig = go.Figure()
        fig.add_trace(go.Scatter(x=n_grid, y=upper, line=dict(dash="dot", color="lightgray"),
                                 name="IC 95% sup"))
        fig.add_trace(go.Scatter(x=n_grid, y=lower, line=dict(dash="dot", color="lightgray"),
                                 fill="tonexty", fillcolor="rgba(200,200,200,0.2)",
                                 name="IC 95% inf"))
        fig.add_trace(go.Scatter(x=[10, rank["internacoes"].max()],
                                 y=[p_global, p_global],
                                 mode="lines", line=dict(color="black", dash="dash"),
                                 name=f"Média ({p_global:.2%})"))
        cor = ["red" if c == cnes_sel else "steelblue" for c in rank["cnes"]]
        size = [14 if c == cnes_sel else 7 for c in rank["cnes"]]
        fig.add_trace(go.Scatter(
            x=rank["internacoes"], y=rank["mortalidade"],
            mode="markers",
            marker=dict(color=cor, size=size, line=dict(width=1, color="white")),
            text=rank["cnes"].astype(str),
            hovertemplate="CNES: %{text}<br>N: %{x:,}<br>Mort: %{y:.2%}<extra></extra>",
            name="Hospital",
        ))
        fig.update_layout(
            title="Funnel plot — volume × mortalidade hospitalar",
            xaxis_title="Internações (log)",
            yaxis_title="Mortalidade",
            xaxis_type="log",
            yaxis_tickformat=".0%",
            height=500,
            showlegend=False,
        )
        st.plotly_chart(fig, use_container_width=True)
        st.caption(
            "Pontos fora das bandas (cinza) sugerem mortalidade significativamente "
            "acima/abaixo da média do conjunto — candidatos a investigação."
        )

# -- Perfil do hospital selecionado ------------------------------------------
if cnes_sel:
    st.divider()
    st.subheader(f"Perfil — CNES {cnes_sel}")
    perfil = _perfil(cnes_sel, d_min, d_max)
    if perfil.empty:
        st.info("Sem dados pra esse hospital no período.")
    else:
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Internações no período", f"{int(perfil['internacoes'].sum()):,}")
        mort = perfil["mortes"].sum() / max(perfil["internacoes"].sum(), 1)
        m2.metric("Mortalidade global", f"{mort:.1%}")
        m3.metric("UTI %", f"{perfil['uti_pct'].mean():.1%}")
        m4.metric("Custo médio AIH", f"R$ {perfil['custo_medio'].mean():,.0f}")

        st.markdown("**Top 30 CIDs deste hospital**")
        st.dataframe(
            perfil.assign(
                mortalidade=lambda d: (d["mortalidade"] * 100).round(2),
                uti_pct=lambda d: (d["uti_pct"] * 100).round(1),
            ),
            use_container_width=True,
            height=500,
        )

        # Plotly: distribuição de mortalidade por CID
        sub = perfil[perfil["internacoes"] >= 5].copy()
        if not sub.empty:
            fig = px.bar(
                sub.head(20),
                x="cid3", y="mortalidade",
                hover_data=["internacoes", "perm_media", "uti_pct"],
                title="Mortalidade por CID (top 20 por volume)",
            )
            fig.update_layout(yaxis_tickformat=".0%", height=400)
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Selecione um hospital pra ver o perfil detalhado.")
