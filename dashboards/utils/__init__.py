"""Helpers compartilhados pelos dashboards."""
from __future__ import annotations

import streamlit as st


def pergunta_box(pergunta: str) -> None:
    """Renderiza um callout com a 'pergunta norteadora' da view.

    Padrão visual: caixa azul clara com borda esquerda azul forte, ícone 🔎.
    Coloca logo após st.title() e antes de st.caption() em cada página.
    """
    st.markdown(
        f"""
        <div style="
            background: #eff6ff;
            border-left: 5px solid #2563eb;
            padding: 0.85em 1.2em;
            border-radius: 0 6px 6px 0;
            margin: 0.3em 0 1em;
            font-size: 1.05em;
            line-height: 1.45;
            color: #0f172a;
        ">
            <strong style="color:#1e40af;">🔎 Pergunta norteadora:</strong>
            <em style="color:#0f172a;">{pergunta}</em>
        </div>
        """,
        unsafe_allow_html=True,
    )
