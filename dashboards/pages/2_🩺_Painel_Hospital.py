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

from utils import pergunta_box  # noqa: E402
from utils.queries import (  # noqa: E402
    cids_disponiveis,
    get_conn,
    hospitais_disponiveis,
    hospitais_por_volume,
    perfil_hospital,
)

st.set_page_config(page_title="Painel Hospital — DataSUS RS", layout="wide")
st.title("🩺 Painel do Hospital")
pergunta_box(
    "Quais hospitais apresentam mortalidade fora do esperado para o seu volume — "
    "candidatos a investigação clínica ou referência de qualidade?"
)
st.caption("Casuística e indicadores operacionais por estabelecimento.")


@st.cache_resource
def _conn():
    return get_conn()


@st.cache_data(ttl=300)
def _list_hospitais():
    return hospitais_disponiveis(_conn())


@st.cache_data(ttl=300)
def _list_cids():
    return cids_disponiveis(_conn())


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
    cids_disp = _list_cids()
    cid_filter = st.selectbox(
        "Filtro CID (3 chars)",
        options=[""] + sorted(cids_disp),
        index=0,
        format_func=lambda c: "(todos)" if c == "" else c,
        help="Lista carregada do gold — só CIDs com dado aparecem.",
    )
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
        # Explicação ANTES do gráfico — funnel plot é técnico e exige contexto.
        with st.expander("ℹ️ Como ler o funnel plot (Spiegelhalter, 2005)", expanded=True):
            st.markdown("""
            **O que é:** ferramenta clássica de comparação de hospitais usada
            internacionalmente em auditoria de qualidade. Cada ponto = 1 hospital.

            **Os 3 elementos visuais:**

            - 🔘 **Pontos** — cada hospital. Eixo X = volume de internações (log).
              Eixo Y = sua taxa de mortalidade.
            - ➖ **Linha tracejada preta** — mortalidade **média** do conjunto de hospitais
              no período. É o "esperado" se todos performassem igual.
            - 🟫 **Banda cinza (IC 95%)** — intervalo de confiança 95% calculado pela
              distribuição binomial. Hospitais **dentro da banda** estão dentro da
              variação estatisticamente esperada pelo seu volume (hospitais pequenos
              têm banda mais larga porque pouco volume → mais incerteza).

            **Como interpretar:**

            | Posição | Significa | Ação |
            |---|---|---|
            | Dentro da banda | Performance estatisticamente normal | Nada |
            | **Acima** da banda | Mortalidade **maior** que esperada pro volume | 🔴 Investigar |
            | **Abaixo** da banda | Mortalidade **menor** que esperada | 🟢 Estudar boas práticas |

            **Cuidados:**

            - Mortalidade bruta NÃO é ajustada por mix de casos (gravidade) — hospital
              de referência terciária tende a aparecer alto.
            - Filtre por CID específico (ex.: I21 = IAM) pra reduzir esse viés.
            - 1 ponto fora da banda ≠ culpa: requer análise clínica caso a caso.
            """)

        p_global = rank["mortes"].sum() / rank["internacoes"].sum()
        n_grid = np.linspace(10, rank["internacoes"].max(), 50)
        se = np.sqrt(p_global * (1 - p_global) / n_grid)
        upper = (p_global + 1.96 * se).clip(0, 1)
        lower = (p_global - 1.96 * se).clip(0, 1)

        fig = go.Figure()
        # Banda IC 95% (preenchida)
        fig.add_trace(go.Scatter(
            x=n_grid, y=upper,
            line=dict(dash="dot", color="rgb(150,150,150)"),
            name="Limite superior IC 95%",
            hovertemplate="N=%{x:.0f}<br>Limite sup: %{y:.2%}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=n_grid, y=lower,
            line=dict(dash="dot", color="rgb(150,150,150)"),
            fill="tonexty", fillcolor="rgba(200,200,200,0.25)",
            name="Limite inferior IC 95%",
            hovertemplate="N=%{x:.0f}<br>Limite inf: %{y:.2%}<extra></extra>",
        ))
        # Linha média
        fig.add_trace(go.Scatter(
            x=[10, rank["internacoes"].max()],
            y=[p_global, p_global],
            mode="lines",
            line=dict(color="black", dash="dash", width=2),
            name=f"Média do conjunto ({p_global:.2%})",
            hovertemplate="Média: %{y:.2%}<extra></extra>",
        ))

        # Outliers: fora da banda
        def _classify(row):
            # interpola limite no volume desse hospital
            n = row["internacoes"]
            se_h = np.sqrt(p_global * (1 - p_global) / n)
            sup = min(p_global + 1.96 * se_h, 1)
            inf = max(p_global - 1.96 * se_h, 0)
            if row["mortalidade"] > sup:
                return "🔴 Acima do esperado"
            if row["mortalidade"] < inf:
                return "🟢 Abaixo do esperado"
            return "🔘 Dentro do esperado"

        rank = rank.copy()
        rank["classe"] = rank.apply(_classify, axis=1)

        COR_CLASSE = {
            "🔴 Acima do esperado":    "rgb(220,38,38)",
            "🟢 Abaixo do esperado":   "rgb(22,163,74)",
            "🔘 Dentro do esperado":   "rgb(70,130,180)",
        }
        for classe, cor in COR_CLASSE.items():
            sub = rank[rank["classe"] == classe]
            if sub.empty:
                continue
            destaque = (sub["cnes"] == cnes_sel) if cnes_sel else None
            sz = [14 if (cnes_sel and c == cnes_sel) else 9 for c in sub["cnes"]]
            fig.add_trace(go.Scatter(
                x=sub["internacoes"], y=sub["mortalidade"],
                mode="markers",
                marker=dict(
                    color=cor, size=sz,
                    line=dict(width=2 if cnes_sel else 1, color="white"),
                ),
                text=sub["cnes"].astype(str),
                hovertemplate="CNES: %{text}<br>Internações: %{x:,}<br>Mortalidade: %{y:.2%}<extra></extra>",
                name=f"{classe} ({len(sub)})",
            ))

        fig.update_layout(
            title=dict(
                text="Funnel plot — Mortalidade × Volume<br>"
                     "<sub>Pontos fora da banda cinza são estatisticamente diferentes da média do conjunto</sub>",
                x=0.5,
                xanchor="center",
            ),
            xaxis_title="Internações (escala log)",
            yaxis_title="Taxa de mortalidade hospitalar",
            xaxis_type="log",
            yaxis_tickformat=".1%",
            height=560,
            showlegend=True,
            legend=dict(
                orientation="v",
                yanchor="top", y=1.0,
                xanchor="left", x=1.02,
                bgcolor="rgba(255,255,255,0.9)",
                bordercolor="lightgray", borderwidth=1,
            ),
            hovermode="closest",
        )
        st.plotly_chart(fig, use_container_width=True)

        # Caption com ação
        n_acima = (rank["classe"].str.startswith("🔴")).sum()
        n_abaixo = (rank["classe"].str.startswith("🟢")).sum()
        st.caption(
            f"**{n_acima} hospital(is) acima** do IC 95% (candidatos a investigação clínica) · "
            f"**{n_abaixo} abaixo** (candidatos a estudo de boas práticas). "
            "Selecione um CNES no filtro acima pra ver o ponto destacado em tamanho maior."
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
