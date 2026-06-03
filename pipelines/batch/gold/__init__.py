"""Gold layer — agregações pré-computadas pra alimentar dashboards.

Cada módulo gera uma "tabela de fatos" agregada, particionada por ano.
Tamanho pequeno (geralmente < 1 GB) → resposta sub-segundo no Streamlit.
"""
