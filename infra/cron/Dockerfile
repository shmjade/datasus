# =============================================================================
# DataSUS — Container ingestor
#
# Roda supercronic (cron amigável a containers) com o crontab versionado.
# Cada tick dispara `python -m pipelines.batch.ingestion.orchestrator`, que
# baixa do FTP DataSUS as competências faltantes e escreve em
# /app/data/lake/bronze/.
# =============================================================================
FROM python:3.11-slim AS base

ARG SUPERCRONIC_VERSION=v0.2.45
ARG SUPERCRONIC_SHA1SUM=e894b193bea75a5ee644e700c59e30eedc804cf7
ARG TARGETARCH=amd64

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# Dependências de sistema:
#   curl            — baixar o binário do supercronic
#   ca-certificates — TLS para o FTP do DataSUS
#   gcc + libffi    — compilar pyreaddbc (extensão C usada por pysus[dbc])
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        curl ca-certificates gcc libc6-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Supercronic — binário estático, sem deps
RUN curl -fsSL -o /usr/local/bin/supercronic \
        "https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${TARGETARCH}" \
    && echo "${SUPERCRONIC_SHA1SUM}  /usr/local/bin/supercronic" | sha1sum -c - \
    && chmod +x /usr/local/bin/supercronic

# Usuário não-privilegiado
RUN useradd --create-home --shell /bin/bash ingestor

WORKDIR /app

# Instala o pacote `pipelines` em modo editable, apenas com extras `ingestion`.
# pyproject.toml é copiado isolado primeiro para aproveitar cache de camadas.
COPY pyproject.toml README.md ./
COPY pipelines/__init__.py pipelines/__init__.py
RUN pip install -e ".[ingestion]"

# Código real (sobrescreve o stub copiado acima)
COPY pipelines/ ./pipelines/

# Crontab + entrypoint
COPY infra/cron/crontab /etc/crontab
COPY infra/cron/entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh \
    && mkdir -p /app/data /home/ingestor/pysus \
    && chown -R ingestor:ingestor /app /etc/crontab /home/ingestor

USER ingestor

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
