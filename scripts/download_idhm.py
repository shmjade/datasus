"""Baixa IDHM por município do RS — Atlas Brasil 2010 (PNUD/IPEA/FJP).

Fonte: GitHub mirror mauriciocramos/IDHM (CSV bruto do Atlas Brasil 2013).
Filtra: UF=43 (RS), ANO=2010, colunas chave: IDHM total + 3 componentes,
renda per capita, Gini, % pobreza.

Saída: data/ibge/rs_idhm_municipio.csv
  Colunas: cod6, cod7, nome, idhm, idhm_renda, idhm_longevidade, idhm_educacao,
           renda_per_capita, gini, pct_pobreza
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger("idhm")

URL = "https://raw.githubusercontent.com/mauriciocramos/IDHM/main/municipal.csv"

# Colunas que queremos extrair (case-sensitive como no CSV)
COLS_INTERESSANTES = {
    "Codmun6":  "cod6",
    "Codmun7":  "cod7",
    "Município": "nome",
    "IDHM":     "idhm",
    "IDHM_R":   "idhm_renda",
    "IDHM_L":   "idhm_longevidade",
    "IDHM_E":   "idhm_educacao",
    "RDPC":     "renda_per_capita",  # Renda Domiciliar Per Capita
    "GINI":     "gini",
    "PMPOB":    "pct_pobres",        # % pobres
    "PIND":     "pct_extrema_pobreza",
    "ESPVIDA":  "esperanca_vida",
    "T_ANALF18M": "pct_analfabetismo_18mais",
}


def baixar(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        logger.info("já existe: %s", dest)
        return
    logger.info("baixando %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "datasus-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=120) as r:
        dest.write_bytes(r.read())
    logger.info("[ok] %.1f MB → %s", dest.stat().st_size / 1024**2, dest)


def filtrar(raw_path: Path, out_path: Path, uf: str = "43", ano: str = "2010") -> int:
    """Filtra CSV bruto pra RS + ano 2010 + colunas de interesse."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    with raw_path.open("r", encoding="utf-8") as src:
        reader = csv.DictReader(src, delimiter=";")
        # confere quais colunas esperadas existem
        cols_origem = [c for c in COLS_INTERESSANTES if c in reader.fieldnames]
        if not cols_origem:
            raise RuntimeError(
                f"nenhuma coluna esperada encontrada. Disponíveis: "
                f"{reader.fieldnames[:20]}..."
            )

        cols_destino = [COLS_INTERESSANTES[c] for c in cols_origem]
        logger.info("colunas filtradas: %s", cols_destino)

        n = 0
        with out_path.open("w", newline="", encoding="utf-8") as dst:
            writer = csv.DictWriter(dst, fieldnames=cols_destino, lineterminator="\n")
            writer.writeheader()
            for row in reader:
                if row.get("UF") != uf or row.get("ANO") != ano:
                    continue
                out_row = {}
                for src_col, dst_col in zip(cols_origem, cols_destino):
                    val = row.get(src_col, "").replace(",", ".").strip()
                    out_row[dst_col] = val
                writer.writerow(out_row)
                n += 1
    logger.info("[ok] %d municípios RS exportados → %s", n, out_path)
    return n


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/ibge")
    parser.add_argument("--uf-cod", default="43")
    parser.add_argument("--ano", default="2010")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out_dir = Path(args.out_dir)
    raw = out_dir / "idhm_brasil_raw.csv"
    out = out_dir / f"{args.uf_cod}_idhm_municipio.csv"

    baixar(URL, raw)
    filtrar(raw, out, args.uf_cod, args.ano)
    return 0


if __name__ == "__main__":
    sys.exit(main())
