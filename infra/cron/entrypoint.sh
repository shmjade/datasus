#!/usr/bin/env bash
# Entrypoint do container `ingestor`.
#
# - Sem argumentos: executa supercronic em foreground, lendo /etc/crontab.
# - "backfill":     executa o orquestrador uma vez em modo backfill e sai.
# - Qualquer outro: executa o comando dado (debug: `docker compose run ingestor bash`).
set -euo pipefail

case "${1:-}" in
    "")
        exec supercronic -passthrough-logs /etc/crontab
        ;;
    backfill)
        exec python -m pipelines.batch.ingestion.orchestrator --backfill
        ;;
    *)
        exec "$@"
        ;;
esac
