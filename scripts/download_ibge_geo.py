"""Baixa shapefile/GeoJSON IBGE da malha municipal por UF.

Fonte: github.com/tbrugz/geodata-br — mirror oficial do IBGE com GeoJSONs prontos.
Cada UF é ~5-10 MB. Salva em data/ibge/{uf}_municipios.geojson.

Uso:
    python scripts/download_ibge_geo.py --uf RS
    python scripts/download_ibge_geo.py --uf RS,SC,PR
"""
from __future__ import annotations

import argparse
import logging
import sys
import urllib.request
from pathlib import Path

logger = logging.getLogger("ibge_geo")

# Códigos UF IBGE (necessário pra montar URL)
UF_TO_CODE = {
    "RO": 11, "AC": 12, "AM": 13, "RR": 14, "PA": 15, "AP": 16, "TO": 17,
    "MA": 21, "PI": 22, "CE": 23, "RN": 24, "PB": 25, "PE": 26, "AL": 27,
    "SE": 28, "BA": 29,
    "MG": 31, "ES": 32, "RJ": 33, "SP": 35,
    "PR": 41, "SC": 42, "RS": 43,
    "MS": 50, "MT": 51, "GO": 52, "DF": 53,
}

BASE_URL = "https://raw.githubusercontent.com/tbrugz/geodata-br/master/geojson/geojs-{code}-mun.json"


def baixar_uf(uf: str, out_dir: Path) -> Path:
    uf = uf.upper()
    if uf not in UF_TO_CODE:
        raise ValueError(f"UF desconhecida: {uf}")
    code = UF_TO_CODE[uf]
    url = BASE_URL.format(code=code)
    out = out_dir / f"{uf.lower()}_municipios.geojson"

    out_dir.mkdir(parents=True, exist_ok=True)
    if out.exists():
        logger.info("já existe: %s", out)
        return out

    logger.info("baixando %s → %s", url, out)
    urllib.request.urlretrieve(url, out)
    size_mb = out.stat().st_size / 1024**2
    logger.info("[ok] %s (%.1f MB)", out, size_mb)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--uf", default="RS", help="lista separada por vírgula (default: RS)")
    parser.add_argument("--out", default="data/ibge", help="diretório destino")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out_dir = Path(args.out)
    ufs = [u.strip().upper() for u in args.uf.split(",")]
    for uf in ufs:
        try:
            baixar_uf(uf, out_dir)
        except Exception as exc:  # noqa: BLE001
            logger.error("falha pra %s: %s", uf, exc)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
