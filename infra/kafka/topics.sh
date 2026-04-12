#!/usr/bin/env bash
# =============================================================================
# DataSUS — Criação de Tópicos Kafka
#
# Execute após o broker estar healthy:
#   docker compose exec kafka bash /opt/datasus/topics.sh
# Ou diretamente do host:
#   bash infra/kafka/topics.sh
# =============================================================================

set -euo pipefail

BROKER="${KAFKA_BOOTSTRAP_SERVERS:-localhost:9092}"

echo ">>> Criando tópicos no broker: ${BROKER}"

# ---------------------------------------------------------------------------
# triagem-eventos
# Eventos de entrada de pacientes no sistema de triagem (simulados via stream)
# Partições: 3 (paralelismo para múltiplas UPAs/hospitais)
# Retenção: 7 dias
# ---------------------------------------------------------------------------
kafka-topics.sh \
  --bootstrap-server "${BROKER}" \
  --create \
  --if-not-exists \
  --topic triagem-eventos \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000

echo "  [OK] triagem-eventos"

# ---------------------------------------------------------------------------
# alertas-risco
# Alertas gerados pelo motor de decisão para pacientes classificados como
# "Vermelho" (risco imediato). Consumido pelo dashboard em tempo real.
# Partições: 1 (baixo volume, alta prioridade)
# Retenção: 24 horas
# ---------------------------------------------------------------------------
kafka-topics.sh \
  --bootstrap-server "${BROKER}" \
  --create \
  --if-not-exists \
  --topic alertas-risco \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=86400000

echo "  [OK] alertas-risco"

# ---------------------------------------------------------------------------
# regulacao-solicitacoes
# Solicitações de regulação assistencial (transferências entre unidades)
# Usado para calcular a "Janela de Risco" (tempo entre solicitação e desfecho)
# ---------------------------------------------------------------------------
kafka-topics.sh \
  --bootstrap-server "${BROKER}" \
  --create \
  --if-not-exists \
  --topic regulacao-solicitacoes \
  --partitions 3 \
  --replication-factor 1 \
  --config retention.ms=604800000

echo "  [OK] regulacao-solicitacoes"

echo ""
echo ">>> Tópicos criados com sucesso. Listagem:"
kafka-topics.sh --bootstrap-server "${BROKER}" --list
