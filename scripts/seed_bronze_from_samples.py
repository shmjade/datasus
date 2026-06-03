"""Popula bronze a partir de data/samples/ (modo demo end-to-end).

Cada sample em data/samples/{source}_{tipo}.parquet vira uma "competência"
fake no bronze, com particionamento uf/ano/mes correto. A competência usada
é derivada do conteúdo do arquivo (lendo COMPETEN/ANO_CMPT/etc.) ou
fallback pra 2026-02.

Uso:
    python scripts/seed_bronze_from_samples.py
    python scripts/seed_bronze_from_samples.py --uf RS --force
"""
from __future__ import annotations

import argparse
import logging
import shutil
from pathlib import Path

import pyarrow.parquet as pq

logger = logging.getLogger("seed_bronze")

DEFAULT_COMP = (2026, 2)


def _infer_competencia(sample: Path, source: str, tipo: str) -> tuple[int, int]:
    """Lê 1 linha pra inferir competência. Fallback: 2026-02."""
    try:
        df = next(pq.ParquetFile(sample).iter_batches(batch_size=1)).to_pandas()
        if source == "sih":
            if "ANO_CMPT" in df.columns and "MES_CMPT" in df.columns:
                return int(df["ANO_CMPT"].iloc[0]), int(df["MES_CMPT"].iloc[0])
            if "ANO" in df.columns and "MES" in df.columns:  # ER
                return int(df["ANO"].iloc[0]), int(df["MES"].iloc[0])
        if source == "cnes" and "COMPETEN" in df.columns:
            c = str(df["COMPETEN"].iloc[0])
            return int(c[:4]), int(c[4:6])
        if source == "sia":
            if "PA_CMP" in df.columns:
                c = str(df["PA_CMP"].iloc[0])
                return int(c[:4]), int(c[4:6])
            if "DT_PROCESS" in df.columns:
                c = str(df["DT_PROCESS"].iloc[0])
                return int(c[:4]), int(c[4:6])
        if source == "sim" and "DTOBITO" in df.columns:
            d = str(df["DTOBITO"].iloc[0])
            # DDMMYYYY → ano = últimos 4
            return int(d[-4:]), 1
        if source == "sinasc" and "DTNASC" in df.columns:
            d = str(df["DTNASC"].iloc[0])
            return int(d[-4:]), 1
        if source == "sinan" and "DT_NOTIFIC" in df.columns:
            d = str(df["DT_NOTIFIC"].iloc[0])
            return int(d[:4]), 1
    except Exception as exc:  # noqa: BLE001
        logger.debug("inferência falhou pra %s/%s: %s", source, tipo, exc)
    return DEFAULT_COMP


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples-root", default="data/samples")
    parser.add_argument("--bronze-root", default="data/lake/bronze")
    parser.add_argument("--uf", default="RS")
    parser.add_argument("--force", action="store_true",
                        help="sobrescreve mesmo se a partição já existir")
    parser.add_argument("--only", help="lista de samples (sem .parquet)")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    samples_root = Path(args.samples_root)
    bronze_root = Path(args.bronze_root)
    if not samples_root.exists():
        logger.error("samples_root não existe: %s", samples_root)
        return 1

    samples = sorted(samples_root.glob("*.parquet"))
    if args.only:
        wanted = {s.strip() for s in args.only.split(",")}
        samples = [s for s in samples if s.stem in wanted]
    logger.info("encontrados %d samples", len(samples))

    copied = skipped = 0
    for sample in samples:
        # nome: source_tipo.parquet (ex.: sih_rd, cnes_st, sinan_dengue)
        stem = sample.stem
        if "_" not in stem:
            logger.warning("sample sem '_', pulando: %s", sample.name)
            continue
        source, tipo = stem.split("_", 1)

        ano, mes = _infer_competencia(sample, source, tipo)
        bronze_dir = (
            bronze_root / stem /
            f"uf={args.uf}" / f"ano={ano:04d}" / f"mes={mes:02d}"
        )
        target = bronze_dir / "part-0.parquet"

        if target.exists() and not args.force:
            skipped += 1
            logger.debug("[skip] %s", target)
            continue

        bronze_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(sample, target)
        logger.info("[copy] %s → %s", sample.name, target.relative_to(bronze_root))
        copied += 1

    logger.info("done: copied=%d skipped=%d", copied, skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
