"""Baixa população por bairro de Porto Alegre (Censo 2022 / ObservaPOA).

Fonte oficial: Secretaria Municipal de Planejamento (SMPAE) — ObservaPOA.
URL: https://prefeitura.poa.br/sites/default/files/usu_doc/hotsites/smpae/
     observapoa/Pop_Bairro_Censo_2022.csv

O CSV original vem em ISO-8859-1, CRLF, separador ';', números em formato BR
("62.448" = 62448, "4,69" = 4.69). Este script normaliza:
  - encoding → UTF-8
  - separador → ','
  - números → formato C (sem milhar, ponto decimal)
  - nomes de bairros normalizados pra casar com poa_bairros.geojson

Saída: data/ibge/poa_populacao_bairro.csv
  Colunas: bairro, populacao, percentual_cidade
"""
from __future__ import annotations

import argparse
import csv
import logging
import sys
import unicodedata
import urllib.request
from pathlib import Path

logger = logging.getLogger("poa_pop")

URL = (
    "https://prefeitura.poa.br/sites/default/files/usu_doc/hotsites/smpae/"
    "observapoa/Pop_Bairro_Censo_2022.csv"
)


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


# Aliases pra casar nomes do CSV ObservaPOA com o GeoJSON da SMAMUS.
# Quando o nome no CSV difere do oficial do GeoJSON, mapeamos pro nome do GeoJSON.
ALIAS_PARA_GEOJSON = {
    "Coronel Aparício Borges": "Aparício Borges",
    "Mont'Serrat": "Montserrat",
    "Passo da Areia": "Passo D'Areia",
}


def _normalizar_bairro(nome: str) -> str:
    """Chave de comparação — minúsculas, sem acentos, sem espaços extras."""
    return _strip_accents(nome.strip().lower())


def _aplicar_alias(nome: str) -> str:
    return ALIAS_PARA_GEOJSON.get(nome.strip(), nome.strip())


def _parse_numero_br(s: str) -> float:
    """'62.448' → 62448.0; '4,69' → 4.69."""
    s = s.strip().replace(".", "").replace(",", ".")
    return float(s) if s else 0.0


def baixar(url: str, dest_raw: Path) -> None:
    dest_raw.parent.mkdir(parents=True, exist_ok=True)
    if dest_raw.exists():
        logger.info("já existe: %s", dest_raw)
        return
    logger.info("baixando %s", url)
    req = urllib.request.Request(url, headers={"User-Agent": "datasus-pipeline/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        dest_raw.write_bytes(r.read())
    logger.info("[ok] %s (%.1f KB)", dest_raw, dest_raw.stat().st_size / 1024)


def normalizar(raw: Path, out: Path) -> int:
    """Lê CSV BR, devolve CSV padronizado. Retorna número de bairros."""
    with raw.open("r", encoding="latin-1") as f:
        lines = f.read().splitlines()

    # linha 0 = título; linha 1 = header; linhas 2+ = dados; última pode ser total
    if len(lines) < 3:
        raise ValueError(f"CSV inesperado em {raw}: < 3 linhas")

    rows: list[dict[str, object]] = []
    for line in lines[2:]:
        if not line.strip():
            continue
        parts = [p.strip() for p in line.split(";")]
        if len(parts) < 3:
            continue
        bairro, num, pct = parts[0], parts[1], parts[2]
        # ignora totais/agregados ("Total", "Porto Alegre", etc.)
        if not bairro or bairro.lower().startswith(("total", "porto alegre")):
            continue
        try:
            pop = int(_parse_numero_br(num))
            percentual = _parse_numero_br(pct)
        except ValueError:
            logger.warning("linha não numérica, pulando: %s", line)
            continue
        bairro_geo = _aplicar_alias(bairro)   # nome compatível com GeoJSON
        rows.append({
            "bairro": bairro_geo,
            "populacao": pop,
            "percentual_cidade": percentual,
            "bairro_norm": _normalizar_bairro(bairro_geo),
        })

    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["bairro", "populacao", "percentual_cidade", "bairro_norm"],
            lineterminator="\n",
        )
        w.writeheader()
        w.writerows(rows)
    logger.info("[ok] %d bairros → %s", len(rows), out)
    return len(rows)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", default="data/ibge")
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out_dir = Path(args.out_dir)
    raw = out_dir / "poa_pop_bairro_raw.csv"
    out = out_dir / "poa_populacao_bairro.csv"
    if args.force and raw.exists():
        raw.unlink()
    baixar(URL, raw)
    n = normalizar(raw, out)
    logger.info("done: %d bairros disponíveis", n)
    return 0


if __name__ == "__main__":
    sys.exit(main())
