"""Escrita do(s) parquet(s) bruto(s) na camada bronze, particionada por uf/ano/mes."""
from __future__ import annotations

import logging
import shutil
from pathlib import Path

import pyarrow.parquet as pq

from .config import CONFIG

logger = logging.getLogger(__name__)


def bronze_path(source: str, uf: str, ano: int, mes: int) -> Path:
    return (
        CONFIG.bronze_root
        / source
        / f"uf={uf}"
        / f"ano={ano:04d}"
        / f"mes={mes:02d}"
    )


def copy_files(
    paths: list[Path], source: str, uf: str, ano: int, mes: int
) -> tuple[Path, int]:
    """Copia parquet(s) de origem para a partição bronze e retorna (dir, total_rows).

    Re-execução é idempotente — arquivos antigos da partição são deletados antes da cópia.
    """
    target_dir = bronze_path(source, uf, ano, mes)
    target_dir.mkdir(parents=True, exist_ok=True)

    # Idempotência: remove arquivos antigos da partição antes de copiar
    for old in target_dir.glob("*.parquet"):
        old.unlink()

    total_rows = 0
    for i, src in enumerate(paths):
        target = target_dir / f"part-{i}.parquet"
        shutil.copy(src, target)
        total_rows += pq.read_metadata(target).num_rows

    logger.info(
        "bronze copy source=%s uf=%s ano=%d mes=%d files=%d rows=%d path=%s",
        source, uf, ano, mes, len(paths), total_rows, target_dir,
    )
    return target_dir, total_rows
