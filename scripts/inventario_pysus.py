"""Inventário de disponibilidade do catálogo pysus — todos os datasets.

Consulta os 6 datasets do pysus (sih, sia, cnes, sim, sinasc, sinan) e gera:

1. CSV grid: data/lake/_control/inventario_pysus_{uf}.csv
   Colunas: dataset, tipo, ano, mes, disponivel
   - mes fica vazio para datasets anuais (sim, sinasc, sinan).
   - SINAN é Brasil-wide; aparece com uf=BR no parquet de auditoria.

2. Snapshot parquet: data/lake/_control/pysus_catalog/dt={data}/uf={uf}/snapshot.parquet
   Audit log da execução. Particionado por dia × UF — múltiplas execuções no
   mesmo dia sobrescrevem; dias diferentes acumulam (lê com pyarrow.dataset).
   Colunas: dataset, tipo, uf, ano, mes, size_bytes, file_name, snapshot_ts.

Uso:
    python scripts/inventario_pysus.py --uf RS
    python scripts/inventario_pysus.py --uf SP --comp-min 2015-01 --comp-max 2024-12
    python scripts/inventario_pysus.py --uf RS --comp-min 2016-05 --comp-max 2026-05

Env vars (sobrepõem defaults):
    INVENTARIO_COMP_MIN   default 2008-01   (formato YYYY-MM)
    INVENTARIO_COMP_MAX   default 2026-12
    INGEST_DATA_ROOT      default /app/data
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pysus.api.client import PySUS  # type: ignore[import-untyped]

# Importa o módulo do source pra disparar o monkey-patch do httpx.AsyncClient
# (catálogo DuckLake do pysus tem ~440 MB; default 5s estoura).
from pipelines.batch.ingestion.sources import sih as _sih  # noqa: F401

logger = logging.getLogger("inventario")


# ---------------------------------------------------------------------------
# Specs por dataset
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class DatasetSpec:
    name: str
    granularity: str  # "monthly" | "yearly"
    has_uf: bool      # SINAN é Brasil-wide; não tem UF no nome do arquivo


SPECS: tuple[DatasetSpec, ...] = (
    DatasetSpec("sih",    "monthly", has_uf=True),
    DatasetSpec("sia",    "monthly", has_uf=True),
    DatasetSpec("cnes",   "monthly", has_uf=True),
    DatasetSpec("sim",    "yearly",  has_uf=True),
    DatasetSpec("sinasc", "yearly",  has_uf=True),
    DatasetSpec("sinan",  "yearly",  has_uf=False),
)


# ---------------------------------------------------------------------------
# Parser de nome de arquivo
# ---------------------------------------------------------------------------
# Mensais (SIH/SIA/CNES):  {TIPO}{UF:2}{YY:2}{MM:2}.parquet   ex: RDRS2401.parquet
# Anuais UF (SIM/SINASC):  {TIPO}{UF:2}{YYYY:4}.parquet        ex: DORS2024.parquet
# Anuais BR (SINAN):       {DOENCA}BR{YY:2}.parquet            ex: DENGBR24.parquet
#
# Parseamos do fim pra começo: os últimos N chars têm largura fixa, o prefixo
# (tipo) varia (2-5 chars: RD, ATD, DOFET, IMPBO, etc.).

def _yy_to_yyyy(yy: int) -> int:
    return 2000 + yy if yy < 80 else 1900 + yy


@dataclass(frozen=True)
class Entry:
    dataset: str
    tipo: str
    uf: str          # "BR" pra SINAN
    ano: int
    mes: int | None  # None pra datasets anuais
    size_bytes: int
    file_name: str


def parse_file(spec: DatasetSpec, file_name: str, size: int) -> Entry | None:
    if not file_name.lower().endswith(".parquet"):
        return None
    stem = file_name[: -len(".parquet")].upper()

    if spec.granularity == "monthly":
        if len(stem) < 8 or not stem[-4:].isdigit() or not stem[-6:-4].isalpha():
            return None
        tipo, uf = stem[:-6], stem[-6:-4]
        yy, mm = int(stem[-4:-2]), int(stem[-2:])
        if not 1 <= mm <= 12:
            return None
        return Entry(spec.name, tipo, uf, _yy_to_yyyy(yy), mm, size, file_name)

    if spec.has_uf:  # yearly + UF (SIM, SINASC)
        if len(stem) < 8 or not stem[-4:].isdigit() or not stem[-6:-4].isalpha():
            return None
        tipo, uf = stem[:-6], stem[-6:-4]
        yyyy = int(stem[-4:])
        return Entry(spec.name, tipo, uf, yyyy, None, size, file_name)

    # yearly + BR (SINAN): {tipo}BR{YY}
    if len(stem) < 6 or stem[-4:-2] != "BR" or not stem[-2:].isdigit():
        return None
    tipo = stem[:-4]
    yy = int(stem[-2:])
    return Entry(spec.name, tipo, "BR", _yy_to_yyyy(yy), None, size, file_name)


# ---------------------------------------------------------------------------
# Coleta do catálogo
# ---------------------------------------------------------------------------
async def coletar(uf: str) -> list[Entry]:
    """Consulta o catálogo pra todos os datasets. SINAN ignora UF (Brasil-wide)."""
    entries: list[Entry] = []
    parse_fail: Counter[str] = Counter()

    async with PySUS() as p:
        for spec in SPECS:
            kwargs: dict[str, str] = {"dataset": spec.name}
            if spec.has_uf:
                kwargs["state"] = uf

            try:
                files = await p.query(**kwargs)  # type: ignore[arg-type]
            except Exception as exc:  # noqa: BLE001 — quero log e continue
                logger.warning("query falhou dataset=%s: %s", spec.name, exc)
                continue

            antes = len(entries)
            for f in files:
                size = getattr(f, "size", 0) or 0
                entry = parse_file(spec, f.name, size)
                if entry is None:
                    parse_fail[spec.name] += 1
                    continue
                # Pra datasets com UF, descarta entries de outras UFs por garantia
                # (pysus às vezes não filtra corretamente no servidor).
                if spec.has_uf and entry.uf != uf:
                    continue
                entries.append(entry)

            logger.info(
                "dataset=%-7s arquivos_catalogo=%4d aceitos=%4d parse_fail=%d",
                spec.name, len(files), len(entries) - antes, parse_fail[spec.name],
            )

    return entries


# ---------------------------------------------------------------------------
# Snapshot parquet — audit log particionado por dt × uf
# ---------------------------------------------------------------------------
def salvar_snapshot(entries: list[Entry], snapshot_ts: datetime, uf: str, root: Path) -> Path:
    dt = snapshot_ts.strftime("%Y-%m-%d")
    out_dir = root / f"dt={dt}" / f"uf={uf}"
    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / "snapshot.parquet"

    table = pa.table({
        "dataset":     [e.dataset for e in entries],
        "tipo":        [e.tipo for e in entries],
        "uf":          [e.uf for e in entries],
        "ano":         [e.ano for e in entries],
        "mes":         [e.mes for e in entries],
        "size_bytes":  [e.size_bytes for e in entries],
        "file_name":   [e.file_name for e in entries],
        "snapshot_ts": [snapshot_ts] * len(entries),
    })
    pq.write_table(table, out)
    return out


# ---------------------------------------------------------------------------
# Grade fixa (dataset × tipo × competência) com X/vazio
# ---------------------------------------------------------------------------
def _iter_competencias(comp_min: tuple[int, int], comp_max: tuple[int, int]):
    """Itera (ano, mês) entre [comp_min, comp_max] inclusivos."""
    ano, mes = comp_min
    while (ano, mes) <= comp_max:
        yield ano, mes
        mes += 1
        if mes > 12:
            mes = 1
            ano += 1


def construir_grade(
    entries: list[Entry],
    comp_min: tuple[int, int],
    comp_max: tuple[int, int],
) -> list[dict[str, object]]:
    """Gera grade restrita à janela [comp_min, comp_max].

    Para datasets anuais (sim, sinasc, sinan) usa só a parte do ano da janela.
    Para datasets mensais usa precisão de competência (mês inicial/final).
    Tipos: apenas os observados no catálogo — não inferimos hipotéticos.
    """
    disponiveis: set[tuple[str, str, int, int | None]] = {
        (e.dataset, e.tipo, e.ano, e.mes) for e in entries
    }
    tipos_por_dataset: dict[str, set[str]] = {}
    for e in entries:
        tipos_por_dataset.setdefault(e.dataset, set()).add(e.tipo)

    ano_min, ano_max = comp_min[0], comp_max[0]

    rows: list[dict[str, object]] = []
    for spec in SPECS:
        tipos = sorted(tipos_por_dataset.get(spec.name, set()))
        if not tipos:
            continue
        for tipo in tipos:
            if spec.granularity == "yearly":
                for ano in range(ano_min, ano_max + 1):
                    rows.append({
                        "dataset": spec.name,
                        "tipo": tipo,
                        "ano": ano,
                        "mes": "",
                        "disponivel": "X" if (spec.name, tipo, ano, None) in disponiveis else "",
                    })
            else:
                for ano, mes in _iter_competencias(comp_min, comp_max):
                    rows.append({
                        "dataset": spec.name,
                        "tipo": tipo,
                        "ano": ano,
                        "mes": mes,
                        "disponivel": "X" if (spec.name, tipo, ano, mes) in disponiveis else "",
                    })
    return rows


# ---------------------------------------------------------------------------
# CSV (LF, não CRLF)
# ---------------------------------------------------------------------------
def salvar_csv(rows: list[dict[str, object]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["dataset", "tipo", "ano", "mes", "disponivel"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)


# ---------------------------------------------------------------------------
# Resumo no stdout
# ---------------------------------------------------------------------------
def resumir(rows: list[dict[str, object]]) -> None:
    total: Counter[tuple[str, str]] = Counter()
    presentes: Counter[tuple[str, str]] = Counter()
    for r in rows:
        key = (str(r["dataset"]), str(r["tipo"]))
        total[key] += 1
        if r["disponivel"] == "X":
            presentes[key] += 1

    print()
    print(f"{'dataset':<8}{'tipo':<10}{'presentes':>12}{'esperados':>12}{'cobertura':>12}")
    print("-" * 54)
    cur_dataset = ""
    for (dataset, tipo) in sorted(total.keys()):
        if dataset != cur_dataset and cur_dataset:
            print()
        cur_dataset = dataset
        n_pres = presentes[(dataset, tipo)]
        n_tot = total[(dataset, tipo)]
        cob = n_pres / n_tot if n_tot else 0.0
        print(f"{dataset:<8}{tipo:<10}{n_pres:>12}{n_tot:>12}{cob:>11.0%}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def _parse_comp(value: str, label: str) -> tuple[int, int]:
    try:
        ano_str, mes_str = value.split("-")
        ano, mes = int(ano_str), int(mes_str)
        if not 1 <= mes <= 12:
            raise ValueError
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"{label} inválido: {value!r} — esperado YYYY-MM"
        ) from exc
    return ano, mes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--uf", required=True, help="Sigla UF de 2 letras (ex: RS)")
    parser.add_argument(
        "--comp-min",
        default=os.getenv("INVENTARIO_COMP_MIN", "2008-01"),
        help="Competência mínima YYYY-MM (default: env INVENTARIO_COMP_MIN ou 2008-01)",
    )
    parser.add_argument(
        "--comp-max",
        default=os.getenv("INVENTARIO_COMP_MAX", "2026-12"),
        help="Competência máxima YYYY-MM (default: env INVENTARIO_COMP_MAX ou 2026-12)",
    )
    parser.add_argument(
        "--data-root",
        default=os.getenv("INGEST_DATA_ROOT", "/app/data"),
        help="Raiz do data lake (default: env INGEST_DATA_ROOT ou /app/data)",
    )
    args = parser.parse_args(argv)

    uf = args.uf.upper()
    if len(uf) != 2 or not uf.isalpha():
        parser.error(f"--uf inválido: {args.uf}")

    comp_min = _parse_comp(args.comp_min, "--comp-min")
    comp_max = _parse_comp(args.comp_max, "--comp-max")
    if comp_min > comp_max:
        parser.error(f"--comp-min ({args.comp_min}) > --comp-max ({args.comp_max})")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    data_root = Path(args.data_root)
    csv_out = data_root / "lake" / "_control" / f"inventario_pysus_{uf.lower()}.csv"
    parquet_root = data_root / "lake" / "_control" / "pysus_catalog"

    snapshot_ts = datetime.now(timezone.utc).replace(microsecond=0)

    logger.info("consultando catálogo pysus uf=%s ...", uf)
    entries = asyncio.run(coletar(uf))
    logger.info(
        "coleta concluída: %d arquivos em %d datasets",
        len(entries), len({e.dataset for e in entries}),
    )

    parquet_path = salvar_snapshot(entries, snapshot_ts, uf, parquet_root)
    logger.info("snapshot parquet: %s (%d linhas)", parquet_path, len(entries))

    rows = construir_grade(entries, comp_min, comp_max)
    salvar_csv(rows, csv_out)
    logger.info(
        "grade CSV: %s (%d linhas, competências %04d-%02d → %04d-%02d)",
        csv_out, len(rows), comp_min[0], comp_min[1], comp_max[0], comp_max[1],
    )

    resumir(rows)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
