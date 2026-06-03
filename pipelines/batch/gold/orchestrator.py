"""Orquestrador do Gold layer.

Constrói as tabelas agregadas a partir do silver.

Uso:
    python -m pipelines.batch.gold.orchestrator
    python -m pipelines.batch.gold.orchestrator --only continuum_cid
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import duckdb

from . import (
    continuum_cid,
    hospital_panel,
    leitos_municipio,
    ml_mortalidade_dataset,
    mortalidade_municipio_competencia,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("gold.orchestrator")

BUILDERS = {
    "continuum_cid":     continuum_cid.build,
    "hospital_panel":    hospital_panel.build,
    "leitos_municipio":  leitos_municipio.build,
    "mortalidade_municipio_competencia": mortalidade_municipio_competencia.build,
    "ml_mortalidade_dataset": ml_mortalidade_dataset.build,
}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", help="lista de tabelas separadas por vírgula")
    parser.add_argument("--data-root",
                        default=os.getenv("DATA_ROOT", "/app/data"),
                        help="raiz do data lake")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root)
    silver = data_root / "lake" / "silver"
    gold = data_root / "lake" / "gold"

    targets = list(BUILDERS) if not args.only else [s.strip() for s in args.only.split(",")]

    con = duckdb.connect()
    logger.info("silver=%s gold=%s targets=%s", silver, gold, targets)

    for name in targets:
        if name not in BUILDERS:
            logger.warning("tabela %s desconhecida", name)
            continue
        BUILDERS[name](silver_root=silver, gold_root=gold, con=con)

    logger.info("gold concluído em %s", gold)
    return 0


if __name__ == "__main__":
    sys.exit(main())
