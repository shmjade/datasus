"""Utilities compartilhadas pelo silver layer."""
from __future__ import annotations

# ---------------------------------------------------------------------------
# CSAP (Condições Sensíveis à Atenção Primária)
# ---------------------------------------------------------------------------
# Lista baseada na Portaria SAS/MS 221/2008 — agrupada por grupos CID-10.
# Cobre os principais blocos; não substitui a lista oficial completa (76 itens),
# mas captura ~90% dos casos relevantes pra dashboards estaduais.
CSAP_PATTERNS = [
    r"^A0[0-9]",            # gastroenterites
    r"^A1[5-9]",            # tuberculose pulmonar
    r"^B05", r"^B06",       # sarampo, rubéola
    r"^B16", r"^B26",       # hepatite B aguda, parotidite
    r"^B50", r"^B51",       # malária
    r"^B52", r"^B53", r"^B54",
    r"^D50",                # anemia ferropriva
    r"^E1[0-4]",            # diabetes mellitus
    r"^E4[0-6]",            # desnutrição
    r"^E50", r"^E51", r"^E52", r"^E53", r"^E54", r"^E55", r"^E56", r"^E64",
    r"^G4[0-1]",            # epilepsia
    r"^I1[0-1]",            # hipertensão arterial
    r"^I20",                # angina
    r"^I50",                # insuficiência cardíaca
    r"^I63", r"^I64", r"^I69",  # AVC (incluído com restrições)
    r"^J0[0-6]",            # IVAS
    r"^J1[2-8]",            # pneumonias bacterianas
    r"^J2[0-2]",            # bronquites agudas
    r"^J3[0-9]",            # sinusites, etc.
    r"^J4[0-7]",            # asma/DPOC
    r"^K2[5-8]",            # úlcera péptica
    r"^L0[0-8]",            # piodermites
    r"^N1[0-2]",            # infecções renais
    r"^N30", r"^N34", r"^N39",  # cistites, uretrites
    r"^N7[0-7]",            # DIP
    r"^O23",                # infecção urinária na gestação
    r"^P3[5-9]",            # sífilis congênita, outras infecções perinatais
]

CSAP_REGEX_DUCKDB = "(" + "|".join(CSAP_PATTERNS) + ")"
"""Regex única pra usar com regexp_matches no DuckDB."""


# ---------------------------------------------------------------------------
# Decodificação da idade do SIM/SINAN
# ---------------------------------------------------------------------------
# Formato: 4 dígitos (1º = unidade temporal, restantes = valor)
#   1XXX = horas    →   < 1 dia
#   2XXX = dias     →   < 1 mês
#   3XXX = meses    →   < 1 ano
#   4XXX = anos
#   5XXX = centenários (≥100)
DECODE_IDADE_SIM_SQL = """
    CASE
        WHEN IDADE IS NULL OR length(CAST(IDADE AS VARCHAR)) < 2 THEN NULL
        WHEN substr(CAST(IDADE AS VARCHAR), 1, 1) = '4'
            THEN TRY_CAST(substr(CAST(IDADE AS VARCHAR), 2) AS INT)
        WHEN substr(CAST(IDADE AS VARCHAR), 1, 1) = '5'
            THEN TRY_CAST(substr(CAST(IDADE AS VARCHAR), 2) AS INT) + 100
        ELSE 0
    END
"""

DECODE_IDADE_SIH_SQL = """
    CASE
        WHEN COD_IDADE = '4' THEN TRY_CAST(IDADE AS INT)
        WHEN COD_IDADE = '5' THEN TRY_CAST(IDADE AS INT) + 100
        ELSE 0
    END
"""


# ---------------------------------------------------------------------------
# Paths convencionais
# ---------------------------------------------------------------------------
def bronze_path(data_root, source: str) -> str:
    return f"{data_root}/lake/bronze/{source}/**/*.parquet"


def silver_path(data_root, source: str) -> str:
    return f"{data_root}/lake/silver/{source}"


def samples_path(data_root, source: str, tipo: str) -> str:
    """Fallback pra demo: lê do diretório de samples."""
    return f"{data_root}/samples/{source}_{tipo}.parquet"
