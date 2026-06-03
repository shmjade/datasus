"""Baixa população por município do RS via API SIDRA/IBGE (Censo 2022).

Endpoint: servicodados.ibge.gov.br/api/v3/agregados/
  Tabela 4709 = "População residente, por situação do domicílio, sexo e grupos de idade"
  Variável 93 = "População residente"
  Localidades = N6[N3[43]]  → todos municípios (N6) da UF RS (N3=43)

Saída: data/ibge/rs_populacao_municipio.csv
  Colunas: cod6, cod7, nome, populacao

Uso:
    python scripts/download_rs_populacao.py
    python scripts/download_rs_populacao.py --uf-cod 42  # SC
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import urllib.parse
import urllib.request
from pathlib import Path

logger = logging.getLogger("rs_pop")

UF_CODE_TO_SIGLA = {
    11: "RO", 12: "AC", 13: "AM", 14: "RR", 15: "PA", 16: "AP", 17: "TO",
    21: "MA", 22: "PI", 23: "CE", 24: "RN", 25: "PB", 26: "PE", 27: "AL",
    28: "SE", 29: "BA",
    31: "MG", 32: "ES", 33: "RJ", 35: "SP",
    41: "PR", 42: "SC", 43: "RS",
    50: "MS", 51: "MT", 52: "GO", 53: "DF",
}

# Tabela 4709 (Censo 2022) / Variável 93 (População residente)
SIDRA_URL = (
    "https://servicodados.ibge.gov.br/api/v3/agregados/4709/"
    "periodos/2022/variaveis/93?localidades=N6%5BN3%5B{uf_cod}%5D%5D"
)


def buscar(uf_cod: int) -> list[dict]:
    """Busca dados do SIDRA. Trata resposta gzipped que o servidor pode mandar."""
    import gzip
    import io

    url = SIDRA_URL.format(uf_cod=uf_cod)
    logger.info("GET %s", url)
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "datasus-pipeline/1.0",
            "Accept-Encoding": "gzip",
        },
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        raw = r.read()
        if r.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list) or not data:
        raise RuntimeError(f"resposta SIDRA inesperada: {data}")
    series = data[0]["resultados"][0]["series"]
    return series


def parsear(series: list[dict], periodo: str = "2022") -> list[dict[str, object]]:
    out: list[dict[str, object]] = []
    for s in series:
        loc = s["localidade"]
        cod7 = str(loc["id"])
        nome_completo = loc["nome"]
        # "Aceguá - RS" → "Aceguá"
        nome = nome_completo.rsplit(" - ", 1)[0].strip()
        valor = s["serie"].get(periodo, "")
        try:
            pop = int(valor)
        except (ValueError, TypeError):
            logger.warning("população inválida pra %s: %r", nome, valor)
            continue
        out.append({
            "cod6": cod7[:6],
            "cod7": cod7,
            "nome": nome,
            "populacao": pop,
        })
    return out


def escrever(rows: list[dict[str, object]], out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["cod6", "cod7", "nome", "populacao"],
                           lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf-cod", type=int, default=43,
                        help="código UF IBGE (default: 43 = RS)")
    parser.add_argument("--out-dir", default="data/ibge")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    sigla = UF_CODE_TO_SIGLA.get(args.uf_cod, str(args.uf_cod))
    out_dir = Path(args.out_dir)
    out_csv = out_dir / f"{sigla.lower()}_populacao_municipio.csv"

    series = buscar(args.uf_cod)
    rows = parsear(series)
    escrever(rows, out_csv)
    total = sum(r["populacao"] for r in rows)
    logger.info("[ok] %d municípios → %s (pop total: %s)", len(rows), out_csv, f"{total:,}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
