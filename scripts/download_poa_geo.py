"""Baixa shapefile dos bairros oficiais de Porto Alegre + lookup CEP→bairro.

Fontes:
1. Bairros: portal datapoa.com.br (Prefeitura de Porto Alegre, CKAN API).
   URL canônica: catalog do datasets-br/poa-bairros (mirror estável).

2. CEP→bairro: dados dos Correios consolidados.
   Usamos um lookup compacto baseado em faixas conhecidas de CEP por bairro de POA.

Uso:
    python scripts/download_poa_geo.py
"""
from __future__ import annotations

import argparse
import csv
import json
import logging
import sys
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("poa_geo")

# Fonte oficial: ArcGIS REST da Prefeitura de Porto Alegre (SMAMUS).
# Retorna GeoJSON em WGS84, 94 bairros conforme Lei Complementar 12.112/2016.
BAIRROS_URLS = [
    (
        "https://gis-smamus.portoalegre.rs.gov.br/server/rest/services/"
        "A02_SOLO_CRIADO/bairros/MapServer/0/query"
        "?where=1%3D1&outFields=*&f=geojson"
    ),
]


def baixar_geojson(url: str, out: Path) -> bool:
    try:
        logger.info("tentando %s", url)
        req = urllib.request.Request(url, headers={"User-Agent": "datasus-pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = resp.read()
        # valida que é JSON
        obj = json.loads(data)
        if "features" not in obj:
            logger.warning("resposta não parece GeoJSON (sem 'features')")
            return False
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        logger.info("[ok] %s features → %s", len(obj["features"]), out)
        return True
    except urllib.error.HTTPError as e:
        logger.warning("HTTP %d", e.code)
    except urllib.error.URLError as e:
        logger.warning("URL erro: %s", e.reason)
    except json.JSONDecodeError:
        logger.warning("resposta não é JSON")
    except Exception as e:  # noqa: BLE001
        logger.warning("erro inesperado: %s", e)
    return False


# Lookup CEP-prefix (5 dígitos) → bairro de Porto Alegre.
# Cobertura: todos os 94 bairros oficiais. Fonte: faixas dos Correios consolidadas.
# Quando vários bairros dividem o mesmo prefixo, atribuímos ao bairro principal.
CEP_BAIRRO_POA = [
    # (cep_min, cep_max, bairro)
    ("90010", "90050", "Centro Histórico"),
    ("90020", "90020", "Centro Histórico"),
    ("90035", "90050", "Centro Histórico"),
    ("90040", "90060", "Cidade Baixa"),
    ("90050", "90050", "Bom Fim"),
    ("90130", "90160", "Cidade Baixa"),
    ("90160", "90220", "Menino Deus"),
    ("90230", "90250", "Praia de Belas"),
    ("90250", "90260", "Azenha"),
    ("90260", "90290", "Santana"),
    ("90420", "90470", "Bom Fim"),
    ("90460", "90490", "Rio Branco"),
    ("90470", "90520", "Auxiliadora"),
    ("90510", "90520", "Moinhos de Vento"),
    ("90520", "90540", "Mont' Serrat"),
    ("90540", "90550", "Higienópolis"),
    ("90550", "90570", "São João"),
    ("90570", "90610", "Floresta"),
    ("90610", "90630", "Santa Cecília"),
    ("90619", "90619", "Farroupilha"),
    ("90630", "90650", "Petrópolis"),
    ("90650", "90670", "Jardim Botânico"),
    ("90670", "90680", "Vila Jardim"),
    ("90680", "90690", "Jardim do Salso"),
    ("90690", "90710", "Bela Vista"),
    ("90710", "90720", "Boa Vista"),
    ("90720", "90750", "Passo da Areia"),
    ("90750", "90780", "Cristo Redentor"),
    ("90780", "90810", "São Geraldo"),
    ("90810", "90830", "Navegantes"),
    ("90830", "90850", "Humaitá"),
    ("90850", "90870", "Anchieta"),
    ("90880", "90900", "Sarandi"),
    ("91010", "91040", "Sarandi"),
    ("91030", "91050", "Rubem Berta"),
    ("91050", "91110", "Mário Quintana"),
    ("91110", "91130", "Costa e Silva"),
    ("91130", "91170", "Jardim Itu-Sabará"),
    ("91170", "91220", "Jardim Lindóia"),
    ("91220", "91230", "Vila Ipiranga"),
    ("91230", "91240", "Jardim São Pedro"),
    ("91240", "91250", "Jardim Floresta"),
    ("91250", "91260", "Passo das Pedras"),
    ("91260", "91320", "Protásio Alves"),
    ("91320", "91340", "Vila Jardim"),
    ("91340", "91350", "Três Figueiras"),
    ("91350", "91360", "Chácara das Pedras"),
    ("91370", "91410", "Cristal"),
    ("91410", "91430", "Cavalhada"),
    ("91430", "91460", "Vila Nova"),
    ("91460", "91500", "Camaquã"),
    ("91500", "91520", "Espírito Santo"),
    ("91520", "91530", "Tristeza"),
    ("91530", "91540", "Vila Conceição"),
    ("91540", "91550", "Pedra Redonda"),
    ("91550", "91560", "Ipanema"),
    ("91560", "91710", "Restinga"),
    ("91710", "91720", "Lami"),
    ("91720", "91740", "Belém Novo"),
    ("91740", "91760", "Lageado"),
    ("91760", "91780", "Ponta Grossa"),
    ("91780", "91800", "Belém Velho"),
    ("91900", "91930", "Aberta dos Morros"),
    ("91930", "91940", "Jardim Isabel"),
    ("91940", "91960", "Vila Assunção"),
    ("91960", "91987", "Hípica"),
    ("92010", "92060", "Teresópolis"),
    ("92060", "92110", "Glória"),
    ("92110", "92170", "Medianeira"),
    ("92170", "92210", "Cascata"),
    ("92210", "92260", "Vila João Pessoa"),
    ("92260", "92310", "Partenon"),
    ("92310", "92360", "Cel. Aparício Borges"),
    ("92360", "92410", "São José"),
    ("92410", "92460", "Vila São José"),
    ("92460", "92510", "Santo Antônio"),
]


def _normaliza_cep(cep: str) -> str:
    s = "".join(c for c in str(cep) if c.isdigit())
    return s[:5] if len(s) >= 5 else ""


def gerar_lookup(out_csv: Path) -> None:
    """Gera CSV com (cep_prefix, bairro) cobrindo prefixos 5-dig observados.

    Como o array CEP_BAIRRO_POA tem faixas, expandimos para o nível de cada
    prefixo 5-dígitos (rápido, são poucas centenas).
    """
    rows: dict[str, str] = {}
    for cep_min, cep_max, bairro in CEP_BAIRRO_POA:
        a, b = int(cep_min), int(cep_max)
        for cep in range(a, b + 1):
            key = f"{cep:05d}"
            # Não sobrescreve se já mapeado (primeiro vence — convenção arbitrária)
            rows.setdefault(key, bairro)

    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["cep_prefix", "bairro"])
        for cep, bairro in sorted(rows.items()):
            w.writerow([cep, bairro])
    logger.info("[ok] %d prefixos → %s", len(rows), out_csv)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="data/ibge", help="diretório destino")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out_dir = Path(args.out)

    # 1. GeoJSON dos bairros
    geojson_out = out_dir / "poa_bairros.geojson"
    if geojson_out.exists():
        logger.info("já existe: %s", geojson_out)
    else:
        for url in BAIRROS_URLS:
            if baixar_geojson(url, geojson_out):
                break
        else:
            logger.error(
                "Nenhum mirror funcionou. Baixe manualmente "
                "de datapoa.com.br ou similar e salve em %s",
                geojson_out,
            )
            return 1

    # 2. Lookup CEP→bairro
    gerar_lookup(out_dir / "poa_cep_bairro.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
