"""Adapter pysus → bronze para SIH (Sistema de Informações Hospitalares).

Suporta os 4 sub-arquivos publicados pelo DataSUS por competência:
    RD — AIH Reduzida (internação completa: diagnóstico, datas, valores, desfecho)
    SP — Serviços Profissionais (procedimentos por AIH)
    RJ — AIHs Rejeitadas
    ER — Estabelecimentos Rejeitados

Estratégia: como o pysus 2.1.0 já entrega cada arquivo como `.parquet` no
S3 deles, o source retorna apenas os PATHS locais — o bronze_writer copia
direto pro lake sem round-trip por DataFrame. Vital para SP, que tem
~900k linhas/mês e estourava memória ao ser carregado em pandas.

A API high-level `pysus.sih(state, year, month, group="RD")` não funciona
no pysus 2.1.0: o catálogo DuckLake guarda `group=None` para todos os
arquivos, então o filtro por grupo retorna 0. Filtramos pelo prefixo do
nome do arquivo (`{TIPO}{UF}{YYMM}.parquet`).
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path

import httpx

# pysus 2.1.0 baixa um catálogo DuckLake (~440 MB) hospedado na Hetzner DE
# na primeira chamada. Timeout default do httpx (5s) é insuficiente.
_DEFAULT_TIMEOUT = httpx.Timeout(600.0, connect=30.0)
_OriginalAsyncClient = httpx.AsyncClient


class _PatchedAsyncClient(_OriginalAsyncClient):  # type: ignore[misc]
    def __init__(self, *args, **kwargs):  # type: ignore[no-untyped-def]
        kwargs.setdefault("timeout", _DEFAULT_TIMEOUT)
        super().__init__(*args, **kwargs)


httpx.AsyncClient = _PatchedAsyncClient  # type: ignore[misc]

from pysus.api.client import PySUS  # type: ignore[import-untyped]  # noqa: E402

logger = logging.getLogger(__name__)

TIPOS_VALIDOS = ("RD", "SP", "RJ", "ER")


async def _adownload(uf: str, ano: int, mes: int, tipo: str) -> list[Path]:
    async with PySUS() as pysus:
        files = await pysus.query(dataset="sih", state=uf, year=ano, month=mes)
        wanted = [f for f in files if f.name.upper().startswith(tipo)]
        paths: list[Path] = []
        for f in wanted:
            local = await pysus.download(f)
            paths.append(Path(local.path))
        return paths


def download_files(uf: str, ano: int, mes: int, tipo: str = "RD") -> list[Path]:
    """Baixa os arquivos {tipo}{UF}{YYMM}.parquet do pysus e retorna seus paths.

    Não carrega o conteúdo em memória — o bronze_writer copia o(s) parquet(s)
    direto pro lake. Memory-safe para SP (~900k linhas/mês).

    Args:
        uf: sigla de 2 letras (ex.: 'RS').
        ano: ano da competência.
        mes: mês da competência (1-12).
        tipo: 'RD' | 'SP' | 'RJ' | 'ER'. Default 'RD'.

    Returns:
        Lista de paths locais (vazia se catálogo do pysus não tem esse tipo
        para essa competência).
    """
    tipo = tipo.upper()
    if tipo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo inválido: {tipo} — esperado um de {TIPOS_VALIDOS}")

    logger.info("SIH/%s download start uf=%s ano=%d mes=%d", tipo, uf, ano, mes)
    paths = asyncio.run(_adownload(uf, ano, mes, tipo))
    logger.info(
        "SIH/%s download done uf=%s ano=%d mes=%d files=%d",
        tipo, uf, ano, mes, len(paths),
    )
    return paths


# Adapters por tipo registrados no orchestrator.SOURCES
def download_rd(uf: str, ano: int, mes: int) -> list[Path]:
    return download_files(uf, ano, mes, "RD")


def download_sp(uf: str, ano: int, mes: int) -> list[Path]:
    return download_files(uf, ano, mes, "SP")


def download_rj(uf: str, ano: int, mes: int) -> list[Path]:
    return download_files(uf, ano, mes, "RJ")


def download_er(uf: str, ano: int, mes: int) -> list[Path]:
    return download_files(uf, ano, mes, "ER")
