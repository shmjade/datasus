"""F6 — Motor de decisão em tempo real (Kafka).

Consumer lê eventos de triagem do tópico `triagem-eventos`. Quando classifica
um caso como **Manchester Vermelho** (SpO2 < 90% OR Glasgow < 9 OR PAS < 80),
consulta as 3 unidades com maior disponibilidade de leitos SUS no município
de origem e nos municípios vizinhos, publica recomendação em
`alertas-risco` e registra em PostgreSQL.

Formato esperado dos eventos:
    {
      "id_evento": "uuid",
      "timestamp": "ISO",
      "paciente_anon": "hash16",
      "municipio_residencia": "430010",   // IBGE 6
      "spo2": 92,                          // %
      "glasgow": 13,                       // 3-15
      "pas": 110,                          // mmHg
      "queixa": "dor torácica",
      "idade": 67,
      "sexo": "M"
    }

Critérios Vermelho (Manchester adaptado): SpO2<90 OR Glasgow<9 OR PAS<80.

Uso:
    docker compose run --rm streamlit python -m pipelines.stream.triagem_consumer
"""
from __future__ import annotations

import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import duckdb
import psycopg2
from kafka import KafkaConsumer, KafkaProducer

logger = logging.getLogger("triagem_consumer")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC_IN = os.getenv("KAFKA_TOPIC_TRIAGEM", "triagem-eventos")
TOPIC_OUT = os.getenv("KAFKA_TOPIC_ALERTAS", "alertas-risco")

PG_DSN = os.getenv(
    "POSTGRES_DSN",
    f"host={os.getenv('POSTGRES_HOST', 'postgres')} "
    f"port={os.getenv('POSTGRES_PORT', '5432')} "
    f"dbname={os.getenv('POSTGRES_DB', 'datasus_db')} "
    f"user={os.getenv('POSTGRES_USER', 'datasus')} "
    f"password={os.getenv('POSTGRES_PASSWORD', 'datasus_secret')}",
)

DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
SILVER = DATA_ROOT / "lake" / "silver"
GOLD = DATA_ROOT / "lake" / "gold"

# Vizinhanças simplificadas — adjacência por mesma microrregião IBGE.
# Em produção, usaria GeoPandas com touches() pra fronteira real.
# Por enquanto: heurística do prefixo de 4 dígitos do código IBGE (mesoregião).


def classificar_vermelho(evento: dict) -> bool:
    spo2 = evento.get("spo2")
    glasgow = evento.get("glasgow")
    pas = evento.get("pas")
    return (
        (spo2 is not None and spo2 < 90)
        or (glasgow is not None and glasgow < 9)
        or (pas is not None and pas < 80)
    )


def carregar_top_unidades(
    duck: duckdb.DuckDBPyConnection,
    municipio: str,
    n: int = 3,
) -> list[dict]:
    """Top N CNES com mais leitos SUS no município + vizinhos.

    Vizinhança = mesmo prefixo de 4 dígitos IBGE (heurística simples).
    Retorna lista [{cnes, codufmun, leitos_sus, distancia_grupo}].
    """
    prefixo = municipio[:4]
    sql = f"""
        WITH leitos_recentes AS (
            SELECT
                lt.cnes,
                st.codufmun,
                SUM(lt.qt_sus) AS leitos_sus,
                CASE
                    WHEN st.codufmun = '{municipio}' THEN 0
                    WHEN substr(st.codufmun, 1, 4) = '{prefixo}' THEN 1
                    ELSE 2
                END AS distancia_grupo
            FROM read_parquet('{SILVER}/cnes_lt/**/*.parquet', hive_partitioning=true) lt
            LEFT JOIN (
                SELECT cnes, codufmun
                FROM read_parquet('{SILVER}/cnes_st/**/*.parquet', hive_partitioning=true)
                QUALIFY ROW_NUMBER() OVER (PARTITION BY cnes ORDER BY competencia DESC) = 1
            ) st USING (cnes)
            WHERE st.codufmun IS NOT NULL
              AND (st.codufmun = '{municipio}'
                   OR substr(st.codufmun, 1, 4) = '{prefixo}')
            GROUP BY lt.cnes, st.codufmun
            HAVING leitos_sus > 0
        )
        SELECT cnes, codufmun, leitos_sus, distancia_grupo
        FROM leitos_recentes
        ORDER BY distancia_grupo, leitos_sus DESC
        LIMIT {n}
    """
    return [dict(r) for r in duck.execute(sql).df().to_dict("records")]


def ensure_table(pg: psycopg2.extensions.connection) -> None:
    with pg.cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS alertas_risco (
                id_evento TEXT PRIMARY KEY,
                ts_recebido TIMESTAMPTZ NOT NULL,
                ts_processado TIMESTAMPTZ NOT NULL DEFAULT now(),
                paciente_anon TEXT,
                municipio_residencia TEXT,
                classificacao TEXT,
                criterio_vermelho TEXT,
                spo2 INT, glasgow INT, pas INT, idade INT, sexo TEXT, queixa TEXT,
                recomendacao_json JSONB
            )
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_alertas_ts ON alertas_risco(ts_processado DESC)
        """)
    pg.commit()


def registrar(
    pg: psycopg2.extensions.connection,
    evento: dict,
    criterio: str,
    recomendacao: list[dict],
) -> None:
    with pg.cursor() as cur:
        cur.execute("""
            INSERT INTO alertas_risco
              (id_evento, ts_recebido, paciente_anon, municipio_residencia,
               classificacao, criterio_vermelho,
               spo2, glasgow, pas, idade, sexo, queixa, recomendacao_json)
            VALUES (%s, %s, %s, %s, 'VERMELHO', %s,
                    %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (id_evento) DO NOTHING
        """, (
            evento.get("id_evento"),
            evento.get("timestamp"),
            evento.get("paciente_anon"),
            evento.get("municipio_residencia"),
            criterio,
            evento.get("spo2"),
            evento.get("glasgow"),
            evento.get("pas"),
            evento.get("idade"),
            evento.get("sexo"),
            evento.get("queixa"),
            json.dumps(recomendacao, ensure_ascii=False),
        ))
    pg.commit()


def descrever_criterio(evento: dict) -> str:
    motivos = []
    if (s := evento.get("spo2")) is not None and s < 90:
        motivos.append(f"SpO2={s}%")
    if (g := evento.get("glasgow")) is not None and g < 9:
        motivos.append(f"Glasgow={g}")
    if (p := evento.get("pas")) is not None and p < 80:
        motivos.append(f"PAS={p}mmHg")
    return ", ".join(motivos)


def processar(
    eventos: Iterable[dict],
    duck: duckdb.DuckDBPyConnection,
    producer: KafkaProducer,
    pg: psycopg2.extensions.connection,
) -> None:
    for ev in eventos:
        try:
            if not classificar_vermelho(ev):
                continue
            criterio = descrever_criterio(ev)
            municipio = str(ev.get("municipio_residencia", ""))
            if len(municipio) != 6:
                logger.warning("evento sem municipio_residencia válido: %s",
                               ev.get("id_evento"))
                continue
            recom = carregar_top_unidades(duck, municipio, n=3)

            alerta = {
                "id_evento": ev.get("id_evento"),
                "classificacao": "VERMELHO",
                "criterio": criterio,
                "ts_processado": datetime.now(timezone.utc).isoformat(),
                "municipio_origem": municipio,
                "unidades_recomendadas": recom,
            }

            producer.send(TOPIC_OUT, alerta)
            registrar(pg, ev, criterio, recom)
            logger.info("VERMELHO %s → %d unidades recomendadas (%s)",
                        ev.get("id_evento"), len(recom), criterio)
        except Exception:  # noqa: BLE001
            logger.exception("falha processando evento %s", ev.get("id_evento"))


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logger.info("Iniciando consumer triagem | kafka=%s topic=%s",
                KAFKA_BOOTSTRAP, TOPIC_IN)

    duck = duckdb.connect()
    pg = psycopg2.connect(PG_DSN)
    ensure_table(pg)

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )
    consumer = KafkaConsumer(
        TOPIC_IN,
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        auto_offset_reset="latest",
        enable_auto_commit=True,
        group_id="triagem-consumer",
    )

    # SIGTERM handling
    rodando = [True]
    def stop(*_):
        rodando[0] = False
    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    try:
        for msg in consumer:
            if not rodando[0]:
                break
            processar([msg.value], duck, producer, pg)
    finally:
        consumer.close()
        producer.flush(); producer.close()
        pg.close()
        duck.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
