# pipelines.stream — Kafka stream processing (simulação de triagem)
#
# Módulos planejados:
#   producer.py       — gerador de eventos de triagem (simulação baseada em SIH)
#   consumer.py       — consumidor de eventos e motor de decisão
#   triagem_model.py  — lógica de classificação de risco (Verde/Amarelo/Vermelho)
#   alocacao.py       — sugestão de melhor unidade para paciente crítico
