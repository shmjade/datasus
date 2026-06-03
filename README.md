# DataSUS — Análise da Distribuição de Estabelecimentos de Saúde na Região Sul

> **Plataforma de dados híbrida (Batch/Stream) para correlacionar a latência na regulação assistencial com desfechos de mortalidade na Região Sul do Brasil.**

[![CI — Lint](https://github.com/shmjade/datasus/actions/workflows/lint.yml/badge.svg)](https://github.com/shmjade/datasus/actions/workflows/lint.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)

---

## Sumário

- [Visão Geral](#visão-geral)
- [Arquitetura](#arquitetura)
- [Stack Tecnológica](#stack-tecnológica)
- [Quickstart](#quickstart)
- [Estrutura do Projeto](#estrutura-do-projeto)
- [Roadmap](#roadmap)
- [Fontes de Dados](#fontes-de-dados)
- [Contribuindo](#contribuindo)

---

## Visão Geral

Este projeto open source constrói uma **plataforma de análise em saúde pública** capaz de:

1. **Mapear silêncio epidemiológico** — regiões onde alta mortalidade hospitalar coexiste com baixa oferta de serviços especializados.
2. **Calcular a "Janela de Risco"** — latência entre a solicitação de regulação assistencial e o desfecho do paciente (óbito ou agravamento).
3. **Simular triagem em tempo real** — ao detectar um paciente de risco alto ("Vermelho"), o motor de decisão consulta disponibilidade de leitos em unidades próximas e sugere a melhor alocação.

**Fontes de dados:** SIH/DataSUS · CNES/DataSUS · IBGE/POA

**Disciplina:** NF01006 — Projeto de Banco de Dados | Horas de Extensão

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FONTES DE DADOS                              │
│  SIH/DataSUS (AIH)   CNES/DataSUS (estab.)   IBGE (socioecon.)     │
└────────────┬───────────────────┬─────────────────────┬─────────────┘
             │                   │                     │
             ▼                   ▼                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DATALAKE (Object Storage)                         │
│              Arquivos .parquet por competência/UF                   │
│            data/raw/sih/   data/raw/cnes/   data/raw/ibge/          │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
              ┌─────────────────┴──────────────────┐
              │                                    │
              ▼                                    ▼
┌─────────────────────────┐        ┌───────────────────────────────┐
│   PIPELINE BATCH        │        │   PIPELINE STREAM (Simulado)  │
│   PySpark 3.5           │        │   Apache Kafka                │
│                         │        │                               │
│  raw → trusted → refined│        │  Producer: eventos de triagem │
│  Limpeza, tipagem,      │        │  Consumer: motor de decisão   │
│  anonimização (AIH)     │        │  Tópicos:                     │
│  Janela de Risco        │        │    · triagem-eventos          │
└──────────┬──────────────┘        │    · alertas-risco            │
           │                       │    · regulacao-solicitacoes   │
           ▼                       └───────────────┬───────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│                    BANCO RELACIONAL (PostgreSQL 16)                  │
│                                                                     │
│   Schema raw      → dados ingeridos (mirror das fontes)             │
│   Schema trusted  → dados limpos e validados                        │
│   Schema refined  → agregações analíticas                           │
└───────────────────────────────┬─────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   VISUALIZAÇÃO / DASHBOARDS                          │
│          Indicadores: taxa de mortalidade · leitos/hab              │
│          Mapa: silêncio epidemiológico por município                 │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Stack Tecnológica

| Camada | Tecnologia | Versão | Função |
|---|---|---|---|
| Armazenamento | Parquet (filesystem) | — | Datalake local |
| Banco Relacional | PostgreSQL | 16 | Camadas raw/trusted/refined |
| Processamento Batch | Apache Spark (PySpark) | 3.5 | ETL e limpeza |
| Streaming | Apache Kafka | 7.6 (Confluent) | Simulação de triagem |
| Coordenação | Zookeeper | 7.6 (Confluent) | Gestão do cluster Kafka |
| Monitoramento | Kafka UI | latest | Inspeção de tópicos |
| Linguagem | Python | 3.11+ | Pipelines e scripts |
| Linting | Ruff + mypy | 0.4+ / 1.9+ | Qualidade de código |
| Conteinerização | Docker Compose | v2 | Portabilidade da stack |

---

## Quickstart

### Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (v4.x+) com pelo menos **4 GB de RAM** reservados
- [Git](https://git-scm.com/)
- Python 3.11+ (opcional — para rodar pipelines localmente)

### 1. Clonar o repositório

```bash
git clone git@github.com:shmjade/datasus.git
cd datasus
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Edite .env se necessário (credenciais do Postgres, etc.)
```

### 3. Subir a stack completa

```bash
docker compose up -d
```

### 4. Validar os serviços

```bash
docker compose ps
# Todos os serviços devem estar "healthy" após ~60 segundos

# PostgreSQL — verificar schemas
docker compose exec postgres psql -U datasus -d datasus_db -c "\dn"
# Deve listar: raw, trusted, refined

# Kafka — criar tópicos
docker compose exec kafka bash /opt/datasus/topics.sh
```

### 5. Acessar as UIs

| Serviço | URL |
|---|---|
| Kafka UI | http://localhost:8080 |
| Spark Master UI | http://localhost:8081 |
| PostgreSQL | `localhost:5432` (via psql ou DBeaver) |

### 6. Rodar o backfill inicial de ingestão (SIH/RS)

O container `ingestor` já está agendado para rodar mensalmente (cron via supercronic), mas a primeira carga histórica deve ser disparada manualmente:

```bash
docker compose run --rm ingestor backfill
# Baixa todas as competências disponíveis (AAAA-MM) de INGEST_COMPETENCIA_INICIAL
# até hoje - INGEST_LAG_MESES para cada UF em INGEST_UFS.

# Acompanhar a execução agendada (após o backfill, o cron mensal cuida do resto):
docker compose logs -f ingestor
```

Parâmetros via `.env`:

| Variável | Default | Função |
|---|---|---|
| `INGEST_UFS` | `RS` | UFs alvo, separadas por vírgula |
| `INGEST_COMPETENCIA_INICIAL` | `2022-01` | Primeira competência (AAAA-MM) |
| `INGEST_LAG_MESES` | `2` | Lag DataSUS (M-2 padrão) |

Saída do backfill: `data/lake/bronze/sih_rd/uf=<UF>/ano=<AAAA>/mes=<MM>/part-0.parquet`.

### 7. Instalar dependências Python (desenvolvimento local)

```bash
pip install -e ".[dev]"
ruff check .       # lint
pytest             # testes
```

---

## Estrutura do Projeto

```
datasus/
├── .devcontainer/                 # Config GitHub Codespaces
├── .github/workflows/             # CI/CD — lint automático
├── data/
│   └── lake/
│       ├── bronze/                # Parquet espelho do FTP DataSUS (gitignored)
│       │   └── <source>/uf=<UF>/ano=<AAAA>/mes=<MM>/
│       └── _control/              # Watermarks e dead-letter (gitignored)
├── docs/
│   ├── architecture.md            # Decisões de design
│   ├── data_dictionary.md         # Dicionário das fontes SIH, CNES, IBGE
│   └── pbd_poa_sus.tex            # Artigo do projeto (formato SBC)
├── infra/
│   ├── postgres/init.sql          # DDL — schemas e tabelas iniciais
│   ├── kafka/topics.sh            # Script de criação de tópicos
│   └── cron/                      # Container `ingestor` (supercronic + pysus)
│       ├── Dockerfile
│       ├── crontab
│       └── entrypoint.sh
├── pipelines/
│   ├── batch/
│   │   ├── ingestion/             # Bronze: FTP → parquet (pysus)
│   │   ├── transform/             # Silver: parquet → trusted.* (PySpark)
│   │   └── aggregate/             # Gold:   trusted.* → refined.*
│   └── stream/                    # Kafka producers/consumers
├── notebooks/exploration/         # EDA exploratória
├── tests/                         # Testes unitários e de integração
├── .env.example
├── docker-compose.yml
├── pyproject.toml
└── CONTRIBUTING.md
```

---

## Roadmap

- [x] **Fase 0 — Bootstrap**: Estrutura do projeto, Docker stack, DDL inicial
- [~] **Fase 1 — Ingestão Batch**: SIH/RS via pysus + supercronic (mensal); CNES e IBGE pendentes
- [ ] **Fase 2 — Pipeline ETL**: Limpeza, tipagem, anonimização e carga no PostgreSQL
- [ ] **Fase 3 — Janela de Risco**: Cálculo de latência na regulação assistencial
- [ ] **Fase 4 — Stream**: Simulação de triagem via Kafka + motor de decisão
- [ ] **Fase 5 — Análise Espacial**: Mapeamento do silêncio epidemiológico
- [ ] **Fase 6 — Dashboards**: Visualização de indicadores de gestão

---

## Fontes de Dados

| Base | Órgão | Descrição | Acesso |
|---|---|---|---|
| SIH/RD | DataSUS/MS | Registros de Autorização de Internação Hospitalar | [datasus.saude.gov.br](https://datasus.saude.gov.br/transferencia-de-arquivos/) |
| CNES | DataSUS/MS | Cadastro Nacional de Estabelecimentos de Saúde | [datasus.saude.gov.br](https://datasus.saude.gov.br/cadastro-de-estabelecimentos-de-saude-cnes/) |
| Censo / POF | IBGE | Indicadores socioeconômicos por setor censitário | [ibge.gov.br](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html) |

Todos os dados são **públicos e de domínio aberto**, disponibilizados pelas respectivas instituições. Nenhum dado individual identificável é armazenado neste repositório.

---

## Contribuindo

Veja [CONTRIBUTING.md](CONTRIBUTING.md) para o guia completo de contribuição, convenções de commit e fluxo de pull requests.

---

## Licença

MIT © DataSUS Contributors. Veja [LICENSE](LICENSE) para detalhes.
