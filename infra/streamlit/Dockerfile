# =============================================================================
# DataSUS — Container Streamlit (dashboards interativos)
#
# Acesso: http://localhost:8501
# =============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# libgomp1 — runtime do numpy
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --create-home --shell /bin/bash dashboard

WORKDIR /app

COPY pyproject.toml README.md ./
COPY pipelines/__init__.py pipelines/__init__.py
RUN pip install -e ".[dashboard]"

COPY pipelines/ ./pipelines/
COPY dashboards/ ./dashboards/

RUN mkdir -p /app/data && chown -R dashboard:dashboard /app

USER dashboard

EXPOSE 8501

CMD ["streamlit", "run", "dashboards/main.py", \
     "--server.address=0.0.0.0", \
     "--server.port=8501", \
     "--server.headless=true"]
