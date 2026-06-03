"""Configuração da camada de ingestão (bronze).

Valores podem ser sobrescritos por variáveis de ambiente (prefixo INGEST_).
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path


def _env_list(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name)
    if not raw:
        return default
    return [item.strip().upper() for item in raw.split(",") if item.strip()]


def _env_competencia(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


@dataclass(frozen=True)
class IngestionConfig:
    ufs: list[str] = field(default_factory=lambda: _env_list("INGEST_UFS", ["RS"]))
    competencia_inicial: str = field(
        default_factory=lambda: _env_competencia("INGEST_COMPETENCIA_INICIAL", "2022-01")
    )
    lag_meses: int = field(default_factory=lambda: int(os.getenv("INGEST_LAG_MESES", "2")))
    data_root: Path = field(
        default_factory=lambda: Path(os.getenv("INGEST_DATA_ROOT", "/app/data"))
    )

    @property
    def bronze_root(self) -> Path:
        return self.data_root / "lake" / "bronze"

    @property
    def control_root(self) -> Path:
        return self.data_root / "lake" / "_control"

    @property
    def watermark_path(self) -> Path:
        return self.control_root / "watermarks.json"

    def competencia_final(self, today: date | None = None) -> str:
        """Última competência disponível dado o lag típico do DataSUS (M-2)."""
        today = today or date.today()
        month = today.month - self.lag_meses
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        return f"{year:04d}-{month:02d}"


CONFIG = IngestionConfig()
