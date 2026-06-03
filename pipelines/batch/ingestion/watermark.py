"""Watermark de competências já ingeridas com sucesso.

Estado persistido em JSON simples — atômico via rename. Granularidade:
(source, uf) → lista de competências YYYY-MM concluídas.

Por que lista (e não um único "último"): o catálogo do pysus tem lacunas no
meio (ex.: 2023-04 ausente, 2023-05 presente). Sem um conjunto explícito, não
conseguimos distinguir "já tentei e não tinha" de "ainda não tentei".
"""
from __future__ import annotations

import json
import logging
import os
import tempfile
from pathlib import Path

from .config import CONFIG

logger = logging.getLogger(__name__)

# {source: {uf: {"completed": ["YYYY-MM", ...]}}}
WatermarkState = dict[str, dict[str, dict[str, list[str]]]]


def _load(path: Path) -> WatermarkState:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _atomic_save(state: WatermarkState, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, delete=False, encoding="utf-8", suffix=".tmp"
    ) as tmp:
        json.dump(state, tmp, indent=2, sort_keys=True)
        tmp_path = Path(tmp.name)
    os.replace(tmp_path, path)


def completed(source: str, uf: str) -> set[str]:
    state = _load(CONFIG.watermark_path)
    return set(state.get(source, {}).get(uf, {}).get("completed", []))


def mark_completed(source: str, uf: str, competencia: str) -> None:
    state = _load(CONFIG.watermark_path)
    entry = state.setdefault(source, {}).setdefault(uf, {"completed": []})
    if competencia not in entry["completed"]:
        entry["completed"].append(competencia)
        entry["completed"].sort()
    _atomic_save(state, CONFIG.watermark_path)
    logger.info("watermark mark source=%s uf=%s competencia=%s", source, uf, competencia)
