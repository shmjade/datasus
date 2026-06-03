"""Orquestrador do Silver layer.

Roda todas as transformações bronze → silver. Pode ler de:
- bronze (default, layout particionado hive)
- samples (fallback pra demo end-to-end com 1 competência)

Uso:
    python -m pipelines.batch.silver.orchestrator
    python -m pipelines.batch.silver.orchestrator --source samples
    python -m pipelines.batch.silver.orchestrator --only sih_rd,cnes_st
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

import duckdb

from . import cnes_lt, cnes_st, sih_rd, sim_do

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("silver.orchestrator")

TRANSFORMS = {
    "sih_rd":  sih_rd.transform,
    "cnes_st": cnes_st.transform,
    "cnes_lt": cnes_lt.transform,
    "sim_do":  sim_do.transform,
}


def _src_glob(data_root: Path, source_mode: str, table: str) -> str:
    if source_mode == "samples":
        # samples/<source>_<tipo>.parquet -> uma "competência" só
        # source = "sih", tipo = "rd"  →  samples/sih_rd.parquet
        return str(data_root / "samples" / f"{table}.parquet")
    return str(data_root / "lake" / "bronze" / table / "**" / "*.parquet")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", choices=["bronze", "samples"], default="bronze",
                        help="De onde ler. samples é fallback pra demo.")
    parser.add_argument("--only", help="lista de tabelas separadas por vírgula")
    parser.add_argument("--data-root",
                        default=os.getenv("DATA_ROOT", "/app/data"),
                        help="raiz do data lake (default: /app/data)")
    args = parser.parse_args(argv)

    data_root = Path(args.data_root)
    targets = list(TRANSFORMS) if not args.only else [s.strip() for s in args.only.split(",")]

    con = duckdb.connect()
    silver_root = data_root / "lake" / "silver"

    logger.info("source=%s data_root=%s targets=%s", args.source, data_root, targets)

    for table in targets:
        if table not in TRANSFORMS:
            logger.warning("tabela %s desconhecida, pulando", table)
            continue
        src = _src_glob(data_root, args.source, table)

        # Confirma que o arquivo/glob existe
        try:
            n_files = con.execute(
                f"SELECT COUNT(*) FROM glob('{src}')"
            ).fetchone()[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("glob falhou pra %s: %s", table, exc)
            continue
        if n_files == 0:
            logger.warning("sem arquivos em %s, pulando %s", src, table)
            continue

        out = silver_root / table
        logger.info("[%s] %d arquivo(s) source → %s", table, n_files, out)
        TRANSFORMS[table](src_glob=src, out_dir=out, con=con)

    logger.info("silver concluído em %s", silver_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
