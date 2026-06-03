"""Orquestrador de ingestão batch — entrypoint do cron mensal.

Modos:
  python -m pipelines.batch.ingestion.orchestrator
      Pull incremental: para cada (source, uf), tenta baixar todas as
      competências entre CONFIG.competencia_inicial e CONFIG.competencia_final
      que ainda não estão no watermark. Lacunas no catálogo do pysus são
      registradas como "vazias" e retentadas em execuções futuras.

  python -m pipelines.batch.ingestion.orchestrator --backfill
      Ignora watermark e tenta todas as competências do range padrão.

  python -m pipelines.batch.ingestion.orchestrator --uf RS --start 2024-01 --end 2024-12
      Range explícito (ignora watermark, não atualiza watermark).
"""
from __future__ import annotations

import argparse
import logging
import sys
from collections.abc import Iterator

from . import bronze_writer, watermark
from .config import CONFIG
from .sources import sih as sih_source

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)
logger = logging.getLogger("ingestion.orchestrator")

SOURCES = {
    "sih_rd": sih_source.download_rd,  # AIH Reduzida — internação completa
    "sih_sp": sih_source.download_sp,  # Serviços Profissionais — procedimentos por AIH
    "sih_rj": sih_source.download_rj,  # AIHs Rejeitadas
    "sih_er": sih_source.download_er,  # Estabelecimentos Rejeitados
}


def _parse_competencia(value: str) -> tuple[int, int]:
    ano_str, mes_str = value.split("-")
    return int(ano_str), int(mes_str)


def _next_competencia(comp: str) -> str:
    ano, mes = _parse_competencia(comp)
    mes += 1
    if mes > 12:
        mes = 1
        ano += 1
    return f"{ano:04d}-{mes:02d}"


def _competencias(start: str, end: str) -> Iterator[tuple[int, int]]:
    current = start
    while current <= end:
        yield _parse_competencia(current)
        current = _next_competencia(current)


def run(
    source: str,
    uf: str,
    start: str,
    end: str,
    *,
    persist_watermark: bool,
    skip_completed: bool = True,
) -> tuple[int, int, int]:
    """Tenta baixar [start, end] para (source, uf). Retorna (ok, vazias, falhas)."""
    fetch = SOURCES[source]
    done = watermark.completed(source, uf) if (persist_watermark and skip_completed) else set()

    logger.info(
        "run source=%s uf=%s start=%s end=%s skip_already_done=%d",
        source, uf, start, end, len(done),
    )

    ok = empty = failed = 0
    for ano, mes in _competencias(start, end):
        competencia = f"{ano:04d}-{mes:02d}"
        if competencia in done:
            continue

        try:
            paths = fetch(uf, ano, mes)
        except Exception:
            logger.exception("download failed source=%s uf=%s comp=%s", source, uf, competencia)
            failed += 1
            continue

        if not paths:
            logger.warning("empty (catálogo sem arquivo) source=%s uf=%s comp=%s", source, uf, competencia)
            empty += 1
            continue

        bronze_writer.copy_files(paths, source, uf, ano, mes)
        if persist_watermark:
            watermark.mark_completed(source, uf, competencia)
        ok += 1

    logger.info(
        "run done source=%s uf=%s ok=%d empty=%d failed=%d",
        source, uf, ok, empty, failed,
    )
    return ok, empty, failed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backfill", action="store_true", help="ignora watermark, tenta tudo")
    parser.add_argument("--uf", action="append", help="UF (pode repetir); default = CONFIG.ufs")
    parser.add_argument("--source", action="append", help="source (default = todas)")
    parser.add_argument("--start", help="competência inicial AAAA-MM (range explícito)")
    parser.add_argument("--end", help="competência final AAAA-MM (range explícito)")
    args = parser.parse_args(argv)

    ufs = args.uf or CONFIG.ufs
    sources = args.source or list(SOURCES.keys())
    end_default = CONFIG.competencia_final()
    range_mode = args.start is not None or args.end is not None

    for source in sources:
        for uf in ufs:
            if range_mode:
                start = args.start or CONFIG.competencia_inicial
                end = args.end or end_default
                run(source, uf, start, end, persist_watermark=False)
                continue

            start = CONFIG.competencia_inicial
            end = end_default
            run(
                source, uf, start, end,
                persist_watermark=True,
                skip_completed=not args.backfill,
            )

    return 0


if __name__ == "__main__":
    sys.exit(main())
