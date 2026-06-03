"""Simulador de eventos de triagem (pra testes).

Gera eventos aleatórios no tópico triagem-eventos com perfis variados
(verde, amarelo, vermelho conforme Manchester). Vermelhos forçam classifcação
crítica pra exercitar o consumer.

Uso:
    docker compose run --rm streamlit python -m pipelines.stream.triagem_producer
    docker compose run --rm streamlit python -m pipelines.stream.triagem_producer --n 100 --interval 0.5
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from kafka import KafkaProducer

logger = logging.getLogger("triagem_producer")

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
TOPIC = os.getenv("KAFKA_TOPIC_TRIAGEM", "triagem-eventos")
DATA_ROOT = Path(os.getenv("DATA_ROOT", "/app/data"))
POP_CSV = DATA_ROOT / "ibge" / "rs_populacao_municipio.csv"

QUEIXAS = [
    "dor torácica", "dispneia", "cefaleia intensa", "trauma craniano",
    "convulsão", "hemorragia digestiva", "febre alta", "queda da própria altura",
    "AVC sintomas", "AIH descompensada", "intoxicação", "ferimento por arma",
]


def amostrar_municipio() -> str:
    """Sorteia município RS ponderado por população."""
    if POP_CSV.exists():
        pop = pd.read_csv(POP_CSV, dtype={"cod6": str})
        return random.choices(pop["cod6"].tolist(),
                              weights=pop["populacao"].tolist(), k=1)[0]
    return "431490"  # POA como fallback


def gerar_evento(forcar_vermelho: bool = False) -> dict:
    """Gera 1 evento de triagem realista."""
    idade = random.choices(
        [random.randint(0, 14), random.randint(15, 29), random.randint(30, 59),
         random.randint(60, 95)],
        weights=[10, 20, 35, 35], k=1)[0]
    sexo = random.choice(["M", "F"])

    if forcar_vermelho or random.random() < 0.15:  # ~15% vermelhos no simulador
        # Pelo menos um critério altera
        criterio = random.choice(["spo2", "glasgow", "pas"])
        spo2 = random.randint(75, 89) if criterio == "spo2" else random.randint(94, 100)
        glasgow = random.randint(3, 8) if criterio == "glasgow" else random.randint(13, 15)
        pas = random.randint(55, 79) if criterio == "pas" else random.randint(110, 145)
    else:
        spo2 = random.randint(93, 100)
        glasgow = random.randint(13, 15)
        pas = random.randint(100, 145)

    return {
        "id_evento": str(uuid.uuid4()),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "paciente_anon": uuid.uuid4().hex[:16],
        "municipio_residencia": amostrar_municipio(),
        "spo2": spo2,
        "glasgow": glasgow,
        "pas": pas,
        "queixa": random.choice(QUEIXAS),
        "idade": idade,
        "sexo": sexo,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=20, help="número de eventos a gerar")
    parser.add_argument("--interval", type=float, default=1.0, help="segundos entre eventos")
    parser.add_argument("--all-red", action="store_true",
                        help="forçar todos os eventos como Vermelho (debug)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP,
        value_serializer=lambda v: json.dumps(v, ensure_ascii=False).encode("utf-8"),
    )

    for i in range(args.n):
        ev = gerar_evento(forcar_vermelho=args.all_red)
        producer.send(TOPIC, ev)
        cor = "🔴" if (ev["spo2"] < 90 or ev["glasgow"] < 9 or ev["pas"] < 80) else "🟢"
        logger.info("%s evento %d/%d mun=%s SpO2=%d Glasgow=%d PAS=%d",
                    cor, i+1, args.n, ev["municipio_residencia"],
                    ev["spo2"], ev["glasgow"], ev["pas"])
        time.sleep(args.interval)

    producer.flush()
    producer.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
