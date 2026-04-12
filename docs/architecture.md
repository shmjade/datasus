# Decisões de Arquitetura

Este documento registra as principais decisões de design do projeto, incluindo o racional por trás de cada escolha tecnológica. Serve como referência para contribuidores e avaliadores.

---

## 1. Padrão Medallion no PostgreSQL

**Decisão:** Usar schemas `raw`, `trusted` e `refined` dentro do mesmo banco PostgreSQL, em vez de múltiplos bancos ou tecnologias separadas.

**Racional:**
- Simplicidade operacional — um único serviço para gerenciar em ambiente acadêmico.
- Isolamento lógico suficiente para demonstrar o conceito de camadas de qualidade de dados.
- Facilidade de joins cross-schema sem overhead de rede.

**Trade-off aceito:** Em produção real, cada camada seria um sistema de armazenamento distinto (ex: S3/GCS para `raw`, Delta Lake para `trusted`, DW colunar para `refined`).

---

## 2. Kafka para Simulação de Stream (em vez de dados reais em tempo real)

**Decisão:** Usar Apache Kafka com producers Python simulando eventos de triagem, em vez de integração com sistemas hospitalares reais.

**Racional:**
- Sistemas de triagem hospitalares (ex: SOUL MV, Tasy) são sistemas fechados sem API pública.
- O objetivo pedagógico é demonstrar a **arquitetura de processamento de eventos**, não a integração real.
- Kafka é o padrão de mercado para este tipo de pipeline, sendo relevante para o portfolio.

**Dados simulados:** Os eventos de triagem serão gerados com base nas distribuições estatísticas observadas nos dados históricos do SIH (horários de pico, perfil de pacientes, etc.).

---

## 3. PostgreSQL (em vez de DuckDB puro)

**Decisão:** PostgreSQL como banco principal, com DuckDB podendo ser usado pontualmente para queries analíticas exploratórias nos notebooks.

**Racional:**
- O escopo da disciplina (Projeto de Banco de Dados) requer um SGBD relacional completo com suporte a DDL, constraints, schemas e transações.
- PostgreSQL suporta as extensões geoespaciais (PostGIS — futura fase) necessárias para análise espacial.
- DuckDB é excellent para OLAP em notebook, mas não atende ao requisito de um servidor de banco persistente.

---

## 4. Anonimização do Número de AIH

**Decisão:** Armazenar o hash SHA-256 do número da AIH (campo `n_aih`) em vez do valor original.

**Racional:**
- O número da AIH, combinado com data de nascimento e município, pode ser usado para re-identificar pacientes (quasi-identificador).
- O hash permite rastreabilidade dentro do sistema (detectar duplicatas, linkar internações do mesmo paciente) sem expor o dado sensível.
- Alinhado com LGPD (Lei nº 13.709/2018) — dado de saúde é dado sensível (Art. 11).

---

## 5. Bitnami Spark (em vez de imagem oficial Apache)

**Decisão:** Usar `bitnami/spark:3.5` no Docker Compose.

**Racional:**
- A imagem Bitnami é mais completa para uso em Docker Compose: inclui configurações de worker, scripts de inicialização e suporte a modo standalone sem configuração adicional.
- A imagem oficial do Apache Spark requer mais configuração manual para ambiente standalone com worker.

**Limitação:** Em produção, usaria-se Spark no modo cluster gerenciado (EMR, Dataproc, Databricks).

---

## 6. Sem ORM — SQLAlchemy Core apenas

**Decisão:** Usar SQLAlchemy Core para construção de queries, sem ORM (sem models mapeados).

**Racional:**
- Os dados de saúde pública têm estrutura bastante estável e bem definida pelo DataSUS — não há benefício no overhead de mapeamento ORM.
- SQLAlchemy Core permite queries expressivas e parametrizadas sem abrir mão de controle sobre o SQL gerado.
- Mais transparente para fins acadêmicos (o SQL gerado é explícito).

---

## 7. Região Sul como Recorte Inicial

**Decisão:** Focar inicialmente nos estados PR, SC e RS.

**Racional:**
- A Região Sul tem boa cobertura de dados no SIH e CNES, com menor proporção de registros inválidos que outras regiões.
- Volume manejável para desenvolvimento e testes locais (~15-20% dos registros nacionais).
- Porto Alegre (RS) tem dados socioeconômicos do IBGE bem estruturados por bairro, facilitando a análise espacial.
- O recorte pode ser expandido para nacional nas fases futuras sem mudança de arquitetura.

---

## Diagrama de Fluxo de Dados Detalhado

```
[DataSUS FTP]          [CNES API/FTP]         [IBGE Downloads]
     │                      │                       │
     ▼                      ▼                       ▼
download_sih.py      download_cnes.py        download_ibge.py
     │                      │                       │
     └──────────────────────┴───────────────────────┘
                            │
                            ▼
                   data/raw/*.parquet
                   (particionado por UF e competência)
                            │
                            ▼
              ┌─────────────────────────┐
              │  PySpark ETL (batch/)   │
              │                         │
              │  1. Leitura do .parquet  │
              │  2. Schema enforcement  │
              │  3. Limpeza / filtros   │
              │  4. Anonimização AIH    │
              │  5. Carga → raw.*       │
              │  6. Transform → trusted.*│
              │  7. Agrega → refined.*  │
              └─────────────┬───────────┘
                            │
                            ▼
              ┌─────────────────────────┐
              │     PostgreSQL 16       │
              │  raw / trusted / refined │
              └─────────────┬───────────┘
                            │
              ┌─────────────┴───────────┐
              │                         │
              ▼                         ▼
    ┌──────────────────┐    ┌───────────────────────┐
    │  Análise Espacial│    │  Motor de Decisão     │
    │  (notebooks/)    │    │  (stream/ + Kafka)    │
    │  Silêncio        │    │  Triagem → alertas    │
    │  Epidemiológico  │    │  Alocação de leitos   │
    └──────────────────┘    └───────────────────────┘
```
