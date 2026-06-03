# =============================================================================
# DataSUS — Container de análise (PySpark local + Jupyter)
#
# Uso:
#   Jupyter:        docker compose up -d analysis  → http://localhost:8888
#   Script python:  docker compose run --rm analysis python scripts/foo.py
#   Notebook exec:  docker compose run --rm analysis jupyter nbconvert \
#                       --to notebook --execute --inplace notebooks/x.ipynb
# =============================================================================
FROM python:3.11-slim AS base

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

# default-jre-headless — JRE para o PySpark (resolve automaticamente Java 17+)
# libgomp1 — runtime do numpy/scipy
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        default-jre-headless \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# JAVA_HOME setado dinamicamente — resolve para o JRE default instalado
ENV JAVA_HOME=/usr/lib/jvm/default-java

RUN useradd --create-home --shell /bin/bash analyst

WORKDIR /app

# Instala pacote em modo editable com extras [analysis]
COPY pyproject.toml README.md ./
COPY pipelines/__init__.py pipelines/__init__.py
RUN pip install -e ".[analysis]"

COPY pipelines/ ./pipelines/

RUN mkdir -p /app/data /app/notebooks /app/scripts /home/analyst/.jupyter \
    && chown -R analyst:analyst /app /home/analyst

USER analyst

EXPOSE 8888

CMD ["jupyter", "lab", "--ip=0.0.0.0", "--port=8888", "--no-browser", \
     "--ServerApp.token=", "--ServerApp.password=", \
     "--ServerApp.allow_origin=*"]
