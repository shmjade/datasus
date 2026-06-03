"""Baixa 1 arquivo de exemplo por (dataset, tipo) do catálogo pysus.

Salva em data/samples/{dataset}_{tipo}.parquet — separado do bronze pra deixar
claro que são amostras (não ingestão de produção). Idempotente: pula se já existe.

Útil pra inspecionar schemas de todos os datasets do DataSUS sem rodar a
ingestão completa.

Uso:
    python scripts/baixar_samples.py --uf RS
    python scripts/baixar_samples.py --uf RS --datasets sih,cnes,sia,sim,sinasc
    python scripts/baixar_samples.py --uf RS --force   # ignora arquivos já baixados
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import shutil
import sys
from pathlib import Path

from pysus.api.client import PySUS  # type: ignore[import-untyped]

from pipelines.batch.ingestion.sources import sih as _sih  # noqa: F401  # monkey-patch httpx

# Reusa parser/specs do inventario_pysus.py (mesmo diretório).
sys.path.insert(0, str(Path(__file__).parent))
from inventario_pysus import SPECS, Entry, parse_file  # noqa: E402

logger = logging.getLogger("baixar_samples")


async def baixar_amostras(
    uf: str,
    datasets_filter: set[str] | None,
    out_dir: Path,
    force: bool,
) -> tuple[int, int, int]:
    """Retorna (baixados, pulados, falhas)."""
    out_dir.mkdir(parents=True, exist_ok=True)
    baixados = pulados = falhas = 0

    async with PySUS() as p:
        for spec in SPECS:
            if datasets_filter and spec.name not in datasets_filter:
                continue

            kwargs: dict[str, str] = {"dataset": spec.name}
            if spec.has_uf:
                kwargs["state"] = uf

            try:
                files = await p.query(**kwargs)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001
                logger.warning("query falhou dataset=%s: %s", spec.name, exc)
                continue

            # Pra cada tipo, pega o arquivo mais recente do catálogo
            mais_recente: dict[str, tuple[Entry, object]] = {}
            for f in files:
                size = getattr(f, "size", 0) or 0
                entry = parse_file(spec, f.name, size)
                if entry is None:
                    continue
                if spec.has_uf and entry.uf != uf:
                    continue
                chave_ord = (entry.ano, entry.mes or 12)
                cur = mais_recente.get(entry.tipo)
                cur_ord = (cur[0].ano, cur[0].mes or 12) if cur else (-1, -1)
                if chave_ord > cur_ord:
                    mais_recente[entry.tipo] = (entry, f)

            logger.info(
                "dataset=%-7s tipos_encontrados=%d", spec.name, len(mais_recente),
            )

            for tipo, (entry, f) in sorted(mais_recente.items()):
                target = out_dir / f"{spec.name}_{tipo.lower()}.parquet"
                if target.exists() and not force:
                    logger.info("[skip] %s já existe", target.name)
                    pulados += 1
                    continue

                logger.info(
                    "[get ] %s/%s (%s, %.1f MB)",
                    spec.name, tipo, f.name, entry.size_bytes / 1024**2,
                )
                try:
                    local = await p.download(f)
                    shutil.copy(local.path, target)
                    baixados += 1
                except Exception:  # noqa: BLE001
                    logger.exception("falha no download %s/%s", spec.name, tipo)
                    falhas += 1

    return baixados, pulados, falhas


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uf", required=True, help="Sigla UF (ex: RS)")
    parser.add_argument(
        "--datasets",
        help="Lista de datasets separados por vírgula (default: todos os 6)",
    )
    parser.add_argument(
        "--out", default="/app/data/samples",
        help="Diretório destino (default: /app/data/samples)",
    )
    parser.add_argument(
        "--force", action="store_true",
        help="Re-baixa mesmo se arquivo destino já existe",
    )
    args = parser.parse_args(argv)

    uf = args.uf.upper()
    if len(uf) != 2 or not uf.isalpha():
        parser.error(f"--uf inválido: {args.uf}")

    filt: set[str] | None = None
    if args.datasets:
        filt = {d.strip().lower() for d in args.datasets.split(",")}
        validos = {s.name for s in SPECS}
        invalidos = filt - validos
        if invalidos:
            parser.error(f"datasets inválidos: {invalidos} — válidos: {sorted(validos)}")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    baixados, pulados, falhas = asyncio.run(
        baixar_amostras(uf, filt, Path(args.out), args.force)
    )
    logger.info("done: baixados=%d pulados=%d falhas=%d", baixados, pulados, falhas)
    return 0 if falhas == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
