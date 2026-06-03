"""F6 — Monitor do Motor de Decisão de Triagem (Kafka).

Mostra os últimos alertas de risco processados pelo consumer
`pipelines.stream.triagem_consumer`. Lê de PostgreSQL (tabela alertas_risco).

Pra gerar carga de teste:
    docker compose run --rm streamlit \\
        python -m pipelines.stream.triagem_producer --n 50 --interval 0.3

Pra rodar o consumer (em outro terminal):
    docker compose run --rm streamlit python -m pipelines.stream.triagem_consumer
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import psycopg2
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from utils import pergunta_box  # noqa: E402


PG_DSN = (
    f"host={os.getenv('POSTGRES_HOST', 'postgres')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'datasus_db')} "
    f"user={os.getenv('POSTGRES_USER', 'datasus')} "
    f"password={os.getenv('POSTGRES_PASSWORD', 'datasus_secret')}"
)

st.set_page_config(page_title="F6 Motor Decisão — DataSUS RS", layout="wide")
st.title("🚨 F6 — Motor de Decisão em Tempo Real")
pergunta_box(
    "Como rotear pacientes em estado crítico (Manchester Vermelho) para unidades com "
    "leitos SUS disponíveis nas vizinhanças, em tempo real?"
)
st.caption(
    "Alertas Manchester Vermelho processados via Kafka. "
    "Critério: SpO2 < 90% OR Glasgow < 9 OR PAS < 80 mmHg."
)


@st.cache_resource
def _conn():
    return psycopg2.connect(PG_DSN)


def _carrega_alertas(limit: int = 50) -> pd.DataFrame:
    try:
        with _conn().cursor() as cur:
            cur.execute("""
                SELECT id_evento, ts_processado, paciente_anon,
                       municipio_residencia, criterio_vermelho,
                       spo2, glasgow, pas, idade, sexo, queixa,
                       recomendacao_json
                FROM alertas_risco
                ORDER BY ts_processado DESC
                LIMIT %s
            """, (limit,))
            cols = [d.name for d in cur.description]
            rows = cur.fetchall()
        df = pd.DataFrame(rows, columns=cols)
        return df
    except psycopg2.Error as exc:
        st.error(
            f"Sem conexão com Postgres / tabela alertas_risco não existe: {exc}\n\n"
            "Rode o consumer primeiro: "
            "`docker compose run --rm streamlit python -m pipelines.stream.triagem_consumer`"
        )
        return pd.DataFrame()


def _carrega_pop_map() -> dict[str, str]:
    p = Path(os.getenv("DATA_ROOT", "/app/data")) / "ibge" / "rs_populacao_municipio.csv"
    if not p.exists():
        return {}
    df = pd.read_csv(p, dtype={"cod6": str})
    return dict(zip(df["cod6"], df["nome"]))


# UI ---
col_a, col_b, col_c = st.columns([1, 1, 2])
with col_a:
    limit = st.slider("Mostrar últimos N alertas", 10, 200, 50)
with col_b:
    if st.button("🔄 Atualizar"):
        st.cache_data.clear()
with col_c:
    auto_refresh = st.checkbox("Auto-refresh (5s)", value=False)
    if auto_refresh:
        import time
        time.sleep(5)
        st.rerun()

df = _carrega_alertas(limit)
nome_map = _carrega_pop_map()

if df.empty:
    st.warning("Nenhum alerta registrado ainda. Gere eventos com o producer:")
    st.code(
        "docker compose run --rm streamlit \\\n"
        "    python -m pipelines.stream.triagem_producer --n 50 --interval 0.3",
        language="bash",
    )
    st.stop()

df["municipio_nome"] = df["municipio_residencia"].map(nome_map).fillna(df["municipio_residencia"])

# KPIs
agora = datetime.now()
df["ts_processado_dt"] = pd.to_datetime(df["ts_processado"], utc=True).dt.tz_localize(None)
ult_min = (agora - df["ts_processado_dt"]).dt.total_seconds().min() / 60 if len(df) else 0

m1, m2, m3, m4 = st.columns(4)
m1.metric("Alertas registrados", f"{len(df):,}")
m2.metric("Último há", f"{ult_min:.1f} min" if ult_min < 60 else f"{ult_min/60:.1f} h")
m3.metric("Municípios distintos", f"{df['municipio_residencia'].nunique():,}")
m4.metric("Idade média", f"{df['idade'].mean():.0f} anos")

st.divider()
st.subheader("📋 Alertas recentes")

for _, row in df.head(10).iterrows():
    with st.container():
        col_l, col_m, col_r = st.columns([2, 3, 4])
        with col_l:
            st.markdown(f"#### 🔴 {row['municipio_nome']}")
            st.caption(f"`{row['id_evento'][:8]}`")
            st.caption(row["ts_processado_dt"].strftime("%H:%M:%S — %d/%m/%y"))
        with col_m:
            st.markdown(f"**Idade:** {row['idade']} · **Sexo:** {row['sexo']}")
            st.markdown(f"**Queixa:** {row['queixa']}")
            st.markdown(
                f"**Critério:** `{row['criterio_vermelho']}`<br>"
                f"SpO2={row['spo2']}% · Glasgow={row['glasgow']} · PAS={row['pas']}",
                unsafe_allow_html=True,
            )
        with col_r:
            st.markdown("**Unidades recomendadas:**")
            try:
                rec = row["recomendacao_json"]
                if isinstance(rec, str):
                    rec = json.loads(rec)
                if not rec:
                    st.caption("(nenhuma encontrada)")
                for u in rec:
                    nome_mun = nome_map.get(u.get("codufmun", ""), u.get("codufmun", ""))
                    dist = ["mesmo município", "vizinho", "região"][
                        min(u.get("distancia_grupo", 0), 2)
                    ]
                    st.markdown(
                        f"- **CNES {u.get('cnes')}** — {nome_mun} "
                        f"({int(u.get('leitos_sus', 0))} leitos · {dist})"
                    )
            except Exception as e:  # noqa: BLE001
                st.caption(f"erro parse recomendação: {e}")
        st.divider()

st.subheader("Tabela completa")
df_show = df[["ts_processado_dt", "municipio_nome", "criterio_vermelho",
              "idade", "sexo", "queixa", "spo2", "glasgow", "pas"]]
df_show.columns = ["timestamp", "município", "critério", "idade", "sexo",
                   "queixa", "SpO2", "Glasgow", "PAS"]
st.dataframe(df_show, use_container_width=True, height=400)
