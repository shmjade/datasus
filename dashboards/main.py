"""DataSUS RS — Dashboard principal.

Home com roteiro narrativo das análises (storytelling) +
visão geral da cobertura de dados disponível.
"""
from __future__ import annotations

import streamlit as st

from utils.queries import cobertura_dados, get_conn

st.set_page_config(
    page_title="DataSUS RS — Painel",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================================
# Cabeçalho + pergunta-pilar
# ============================================================================
st.title("🏥 DataSUS RS — Painel Analítico")
st.markdown(
    "**Como a oferta de serviços de saúde no Rio Grande do Sul se traduz em "
    "internações, custos e mortalidade — e onde estão as desigualdades?**"
)
st.caption(
    "Análise integrada de SIH, CNES, SIM e Censo IBGE 2022 via pipeline "
    "bronze → silver → gold em DuckDB. UFRGS · NF01006."
)


# ============================================================================
# Storytelling — arco narrativo
# ============================================================================
st.divider()
st.subheader("🧭 Roteiro da análise")

st.markdown(
    """
O painel é organizado em **5 perguntas encadeadas**, do panorama estadual ao detalhe
intra-municipal. Cada página responde uma pergunta específica e alimenta a próxima.
"""
)

# Cartões com numeração e cores semânticas (ordem narrativa, não alfabética)
story = [
    {
        "n": "1",
        "icone": "🗺️",
        "titulo": "Mapa Mortalidade RS",
        "pergunta": "Onde as pessoas adoecem, internam e morrem no RS?",
        "objetivo": (
            "Visão geográfica panorâmica: choropleth dos 497 municípios com mortalidade, "
            "volume de internações, custo SUS e óbitos — em valores absolutos **e per capita** "
            "(usando Censo 2022)."
        ),
        "insight": (
            "Identifica **clusters geográficos** de mortalidade alta, vazios assistenciais e "
            "iniquidades regionais. Ponto de partida pra qualquer investigação."
        ),
    },
    {
        "n": "2",
        "icone": "📊",
        "titulo": "Continuum CID",
        "pergunta": "Quais doenças explicam essa mortalidade? Qual a cascata clínica?",
        "objetivo": (
            "Perfil por CID-10: top causas de internação, óbitos no SIM, % de internações por "
            "**Condições Sensíveis à Atenção Primária (CSAP)** e tendência temporal. "
            "Cascata: consulta → internação → óbito."
        ),
        "insight": (
            "Revela **falha da APS** (CSAP alto = atenção primária não está prevenindo "
            "internação) e doenças com letalidade desproporcional ao volume."
        ),
    },
    {
        "n": "3",
        "icone": "🛏️",
        "titulo": "Leitos por Município",
        "pergunta": "Há oferta hospitalar adequada onde a demanda existe?",
        "objetivo": (
            "Capacidade instalada SUS por município, decomposta em categorias: "
            "UTI, clínico, cirúrgico, obstétrico, pediátrico. Top municípios por leitos."
        ),
        "insight": (
            "Cruza com a página 1 pra responder: **municípios com alta mortalidade têm "
            "menos leitos**? O famoso 'vazio assistencial' do SUS."
        ),
    },
    {
        "n": "4",
        "icone": "🩺",
        "titulo": "Painel Hospital",
        "pergunta": "Quais hospitais individuais performam melhor ou pior?",
        "objetivo": (
            "Visão por estabelecimento (CNES): casuística, mortalidade, permanência, "
            "custo médio. **Funnel plot** comparando volume × mortalidade com IC 95% — "
            "outliers ficam fora das bandas."
        ),
        "insight": (
            "Aponta **hospitais candidatos a auditoria clínica** (mortalidade acima do "
            "esperado pro volume) e referências de qualidade pra replicar."
        ),
    },
    {
        "n": "5",
        "icone": "🏙️",
        "titulo": "POA Bairros",
        "pergunta": "Mesmo dentro de uma cidade, a desigualdade persiste?",
        "objetivo": (
            "Zoom em Porto Alegre: choropleth dos **94 bairros oficiais** (Lei 12.112/2016) "
            "via CEP do paciente. Mortalidade, internações, custo — absolutos **e per capita** "
            "(Censo 2022)."
        ),
        "insight": (
            "Mostra que a **iniquidade não termina no município**. Bairros vizinhos podem "
            "ter taxas radicalmente diferentes — peça-chave pra políticas locais."
        ),
    },
]

for item in story:
    with st.container():
        col_n, col_main = st.columns([1, 14])
        with col_n:
            st.markdown(
                f"<div style='font-size:42px;font-weight:700;color:#2563eb;"
                f"text-align:center;line-height:1.1;'>{item['n']}</div>"
                f"<div style='font-size:32px;text-align:center;'>{item['icone']}</div>",
                unsafe_allow_html=True,
            )
        with col_main:
            st.markdown(f"### {item['titulo']}")
            st.markdown(f"**Pergunta:** _{item['pergunta']}_")
            st.markdown(f"**O que mostra:** {item['objetivo']}")
            st.markdown(f"💡 **Insight esperado:** {item['insight']}")
        st.markdown("")

st.info(
    "💬 **Sugestão de leitura:** percorra as páginas **na ordem acima** (1 → 5). "
    "Cada uma alimenta a próxima, formando um diagnóstico do SUS-RS de fora pra dentro "
    "(estado → doença → oferta → hospital → bairro)."
)

# ============================================================================
# Cobertura de dados
# ============================================================================
st.divider()
st.subheader("📂 Cobertura atual de dados")


@st.cache_data(ttl=300)
def _carrega_cobertura():
    con = get_conn()
    return cobertura_dados(con)


cov = _carrega_cobertura()

col1, col2, col3, col4 = st.columns(4)

if cov.get("continuum"):
    c = cov["continuum"]
    col1.metric("📅 Janela temporal", f"{c['inicio']} → {c['fim']}")
    col2.metric("🦠 CIDs distintos", f"{int(c['n_cids']):,}")
    col3.metric("🏥 Internações totais", f"{int(c['total_internacoes']):,}")
    col4.metric("⚰️ Óbitos no SIM", f"{int(c['total_obitos']):,}")
else:
    col1.warning("⚠️ Tabela gold/continuum_cid_mes ainda não existe.")
    col1.caption("Execute primeiro o pipeline silver + gold (ver Setup abaixo).")

col5, col6, col7, _ = st.columns(4)
if cov.get("panel"):
    col5.metric("🩺 Hospitais com dados", f"{int(cov['panel']['n_hospitais']):,}")
if cov.get("leitos"):
    col6.metric("🛏️ Municípios c/ leitos", f"{int(cov['leitos']['n_municipios']):,}")
col7.metric("👥 População RS (Censo 2022)", "10.882.965")


# ============================================================================
# Fontes de dados (transparência metodológica)
# ============================================================================
st.divider()
with st.expander("📚 Fontes de dados utilizadas"):
    st.markdown(
        """
| Fonte | Tabelas | Período | Granularidade |
|---|---|---|---|
| **SIH/SUS** (via pysus) | RD, SP, RJ, ER | 2022-2026 | mensal × UF × hospital |
| **CNES** (via pysus) | ST, LT, PF, HB, SR, … | mensal | × estabelecimento |
| **SIM/MS** (via pysus) | DO (Declaração de Óbito) | anual × UF | × município residência |
| **IBGE Censo 2022** (SIDRA API) | Tabela 4709 — população | 2022 | × município |
| **ObservaPOA** (SMPAE/PMPA) | População por bairro Censo 2022 | 2022 | × bairro POA |
| **SMAMUS/PMPA** | Shapefile dos 94 bairros oficiais | 2016+ | bairro POA |
| **tbrugz/geodata-br** | Shapefile dos 497 municípios RS | atual | município |
"""
    )

# ============================================================================
# Setup técnico (admin)
# ============================================================================
with st.expander("⚙️ Setup do pipeline (admin)"):
    st.markdown(
        """
**Para popular os dados** (uma vez, do host):

```bash
# 1. Seed bronze a partir de samples (se ainda não rodou ingestão completa)
python scripts/seed_bronze_from_samples.py

# 2. Baixar geo + população
python scripts/download_ibge_geo.py --uf RS
python scripts/download_rs_populacao.py
python scripts/download_poa_geo.py
python scripts/download_poa_populacao.py

# 3. Bronze → Silver
docker compose run --rm streamlit python -m pipelines.batch.silver.orchestrator

# 4. Silver → Gold
docker compose run --rm streamlit python -m pipelines.batch.gold.orchestrator

# 5. Suba o dashboard
docker compose up -d streamlit
```

Dashboard em http://localhost:8501.
"""
    )

# ============================================================================
# Rodapé
# ============================================================================
st.divider()
st.caption(
    "Pipeline: pysus → bronze (parquet) → silver (DuckDB) → gold (DuckDB) → "
    "Streamlit + Plotly. UFRGS · NF01006."
)
