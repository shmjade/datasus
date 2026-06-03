# DataSUS-RS — Plataforma Analítica de Saúde Pública

> **Pipeline batch + streaming sobre microdados DataSUS, com 13 dashboards interativos e um motor de decisão Manchester em tempo real.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Docker Compose](https://img.shields.io/badge/docker--compose-v2-2496ED?logo=docker)](https://docs.docker.com/compose/)

Análise da distribuição de estabelecimentos de saúde no Rio Grande do Sul e seu impacto na mortalidade hospitalar — com pipeline reprodutível, dashboards de gestão e protótipo de motor de triagem.

**UFRGS · NF01006 — Projeto de Banco de Dados**

---

## Sumário

- [O que está pronto](#o-que-está-pronto)
- [Setup do zero](#setup-do-zero) ← _comece aqui_
- [Acessando os dashboards](#acessando-os-dashboards)
- [Motor de decisão F6 (Kafka)](#motor-de-decisão-f6-kafka)
- [Arquitetura](#arquitetura)
- [Estrutura do projeto](#estrutura-do-projeto)
- [Troubleshooting](#troubleshooting)
- [Comandos úteis](#comandos-úteis)
- [Documentação completa](#documentação-completa)
- [Licença](#licença)

---

## O que está pronto

| Componente | Estado |
|---|---|
| **13 dashboards Streamlit** (Continuum CID, Painel Hospital, Mapa Mortalidade RS, POA Bairros, F1–F6) | ✅ |
| **Pipeline Medallion** Bronze → Silver → Gold em Parquet + DuckDB | ✅ |
| **Ingestão** SIH/CNES/SIM/SIA/SINASC/SINAN via pysus | ✅ |
| **Dataset ML** `ml_mortalidade_dataset/v1/` com train/val/test stratified sklearn | ✅ |
| **Motor Kafka F6** simulador de triagem Manchester + consumer + persistência Postgres | ✅ |
| **6 dicionários de dados** + guia de joins + apresentação Reveal.js | ✅ |
| Modelo ML treinado (LightGBM + SHAP) | 🚧 em desenvolvimento |

---

## Setup do zero

> **Pré-requisitos:** [Docker Desktop](https://www.docker.com/products/docker-desktop/) com **8 GB de RAM** reservados, [Git](https://git-scm.com/), conexão de internet (pra baixar samples na primeira execução).
>
> **Sistemas testados:** macOS (Intel + Apple Silicon), Linux (Ubuntu 22.04+). Windows via WSL2.

### Resumo (TL;DR)

```bash
git clone git@github.com:shmjade/datasus.git && cd datasus
cp .env.example .env
docker compose build streamlit ingestor analysis
docker compose run --rm -v ./scripts:/app/scripts ingestor \
    python scripts/baixar_samples.py --uf RS                    # ~5 min, ~200 MB
docker compose run --rm -v ./scripts:/app/scripts analysis \
    python scripts/seed_bronze_from_samples.py --uf RS --force  # ~10 s
docker compose run --rm streamlit python -m pipelines.batch.silver.orchestrator
docker compose run --rm streamlit python -m pipelines.batch.gold.orchestrator
docker compose up -d streamlit
open http://localhost:8501
```

Se preferir entender **passo a passo o que cada comando faz**, siga a seção abaixo.

---

### Passo 1 — Clonar o repositório

```bash
git clone git@github.com:shmjade/datasus.git
cd datasus
```

### Passo 2 — Copiar variáveis de ambiente

```bash
cp .env.example .env
```

O arquivo `.env` contém credenciais default do PostgreSQL e configurações da ingestão. Pode editar se quiser personalizar (`INGEST_UFS`, `INGEST_COMPETENCIA_INICIAL`, `POSTGRES_PASSWORD`, etc.), mas pros defaults funcionam.

> ⚠️ **Não commite `.env` no Git** — ele está no `.gitignore`. Só `.env.example` deve ir pro repositório.

### Passo 3 — Buildar os containers

```bash
docker compose build streamlit ingestor analysis
```

Isso constrói as imagens Docker dos serviços que vamos usar nos próximos passos (cada uma com extras Python específicas). Demora ~5 minutos na primeira vez.

> 💡 Não precisa buildar `postgres`, `kafka`, `zookeeper` etc. — esses usam imagens prontas do Docker Hub.

### Passo 4 — Baixar samples do DataSUS

**Por que esse passo existe:** o repositório **não inclui dados** — `data/lake/` e `data/samples/` estão no `.gitignore` (são gigabytes). Pra ter algo pra mostrar nos dashboards, baixamos 81 arquivos sample (1 por dataset/tipo) usando a API pública do pysus.

```bash
docker compose run --rm -v ./scripts:/app/scripts ingestor \
    python scripts/baixar_samples.py --uf RS
```

**O que isso faz:** baixa 1 arquivo recente por cada (dataset, tipo) — SIH/RD, CNES/ST, SIM/DO, etc. Total: ~200 MB, ~5 minutos. Salva em `data/samples/{source}_{tipo}.parquet`.

Se quiser ver progresso ao vivo: a saída mostra cada download (`[get ] sih/RD (RDRS2507.parquet, 4.0 MB)`).

### Passo 5 — Popular o bronze a partir dos samples

```bash
docker compose run --rm -v ./scripts:/app/scripts analysis \
    python scripts/seed_bronze_from_samples.py --uf RS --force
```

**O que isso faz:** copia cada sample pra estrutura particionada do bronze (`data/lake/bronze/{source}/uf=RS/ano=YYYY/mes=MM/part-0.parquet`). Demora ~10 segundos.

### Passo 6 — Bronze → Silver

```bash
docker compose run --rm streamlit \
    python -m pipelines.batch.silver.orchestrator
```

**O que isso faz:** processa as 4 tabelas silver implementadas (SIH.RD, CNES.ST, CNES.LT, SIM.DO) com DuckDB — limpa, tipa, deriva colunas (`cid3`, `csap_flag`, `idade_anos`, etc.). Demora ~5 segundos. Saída: `data/lake/silver/{table}/ano=YYYY/mes=MM/data_0.parquet`.

### Passo 7 — Silver → Gold

```bash
docker compose run --rm streamlit \
    python -m pipelines.batch.gold.orchestrator
```

**O que isso faz:** materializa as 5 tabelas gold (continuum_cid_mes, hospital_panel_cid_mes, leitos_municipio_mes, mortalidade_municipio_competencia, ml_mortalidade_dataset). Demora ~10 segundos.

### Passo 8 — Subir o Streamlit

```bash
docker compose up -d streamlit
```

Aguarde ~5 segundos pro Streamlit inicializar. Verifique:

```bash
curl -s -o /dev/null -w "HTTP %{http_code}\n" http://localhost:8501
# Deve responder: HTTP 200
```

### Passo 9 — Acessar os dashboards

Abra no browser: **<http://localhost:8501>**

Você deve ver a página inicial com **roteiro narrativo de 5 atos** e um menu lateral com 13 páginas.

---

## Acessando os dashboards

| Página | URL direta | Pergunta que responde |
|---|---|---|
| 🏠 Home | <http://localhost:8501> | Storytelling + cobertura de dados |
| 📊 Continuum CID | <http://localhost:8501/Continuum_CID> | Quais doenças mais internam, matam e custam? |
| 🩺 Painel Hospital | <http://localhost:8501/Painel_Hospital> | Quais hospitais estão fora do esperado? |
| 🛏️ Leitos por Município | <http://localhost:8501/Leitos_Município> | Onde está concentrada a capacidade SUS? |
| 🗺️ Mapa Mortalidade RS | <http://localhost:8501/Mapa_Mortalidade> | Onde as pessoas mais morrem no RS? |
| 🏙️ POA Bairros | <http://localhost:8501/POA_Bairros> | Como varia a saúde dentro de Porto Alegre? |
| 🏢 F1 Distribuição Estab | <http://localhost:8501/Distribuicao_Estab> | Quais municípios estão descobertos? |
| 📉 F2 Mortalidade Município | <http://localhost:8501/Mortalidade_Municipio> | Como varia a taxa de mortalidade? |
| 🏨 F3 Leitos/1000 hab | <http://localhost:8501/Leitos_per_1000> | Quem precisa de mais leitos por habitante? |
| 🔍 F4 Rastreabilidade | <http://localhost:8501/Rastreabilidade> | Qual o histórico anonimizado de um CNES? |
| 🔇 F5 Silêncio Epidemiológico | <http://localhost:8501/Silencio_Epidemiologico> | Onde combinam alta mortalidade + baixa oferta? |
| 🚨 F6 Motor Decisão | <http://localhost:8501/Motor_Decisao> | Como rotear pacientes críticos em tempo real? |

> 💡 **Filtros padrão** estão calibrados pra cobrir as samples disponíveis (2020–2026). Selecione períodos específicos pra explorar cada janela.

---

## Motor de decisão F6 (Kafka)

A página `🚨 F6 Motor Decisão` consome a tabela `alertas_risco` do PostgreSQL. Pra ela mostrar dados reais, é preciso rodar o producer simulador + o consumer Kafka.

### Passo F6.1 — Subir Kafka e PostgreSQL

```bash
docker compose up -d postgres zookeeper kafka
```

Aguarde ~30 segundos pro Kafka inicializar (`docker compose ps kafka` deve mostrar "healthy" ou "running").

### Passo F6.2 — Criar tópicos Kafka

```bash
docker compose exec kafka kafka-topics \
    --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic triagem-eventos \
    --partitions 1 --replication-factor 1

docker compose exec kafka kafka-topics \
    --bootstrap-server localhost:9092 \
    --create --if-not-exists --topic alertas-risco \
    --partitions 1 --replication-factor 1
```

### Passo F6.3 — Rodar o consumer em background

```bash
docker compose exec -d streamlit \
    python -m pipelines.stream.triagem_consumer
```

> O consumer fica escutando o tópico `triagem-eventos`. Ele cria a tabela `alertas_risco` no Postgres no primeiro insert.

### Passo F6.4 — Disparar eventos de teste

```bash
docker compose exec streamlit \
    python -m pipelines.stream.triagem_producer --n 20 --interval 0.3
```

Isso publica 20 eventos sintéticos no tópico Kafka. O consumer classifica os Manchester Vermelho (SpO2 &lt; 90 OR Glasgow &lt; 9 OR PAS &lt; 80), consulta as 3 unidades com mais leitos SUS na vizinhança e persiste em PostgreSQL.

**Pra forçar TODOS os eventos como Vermelho** (debug):

```bash
docker compose exec streamlit \
    python -m pipelines.stream.triagem_producer --n 20 --all-red
```

### Passo F6.5 — Validar os alertas no Postgres

```bash
docker compose exec postgres psql -U datasus -d datasus_db -c \
    "SELECT COUNT(*) AS total FROM alertas_risco;"
```

E recarregue a página `🚨 F6 Motor Decisão` no Streamlit pra ver os alertas em tempo real.

---

## Arquitetura

```
┌─────────────────────────────────────────────────────────────────────┐
│  INGESTÃO                                                            │
│  pysus → bronze    /    IBGE SIDRA, Atlas Brasil, ObservaPOA → /data │
└──────────────────────────────┬───────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│  PIPELINE MEDALLION (Parquet + DuckDB)                               │
│                                                                       │
│  Bronze (bruto)  →  Silver (limpo, tipado)  →  Gold (agregado)      │
│  • 81 tipos         • 4 tabelas (SIH.RD,        • 5 tabelas         │
│  • Particionado       CNES.ST, CNES.LT,         • Pré-computadas    │
│    uf/ano/mes         SIM.DO)                    pra dashboards     │
│                     • Derivados: cid3,          • +ml_dataset/v1/   │
│                       csap_flag, idade,           train/val/test    │
│                       competencia                                    │
└──────┬─────────────────────┬─────────────────────────┬──────────────┘
       │                     │                         │
       ▼                     ▼                         ▼
┌──────────────┐    ┌─────────────────┐      ┌──────────────────────┐
│ DASHBOARDS   │    │ KAFKA + POSTGRES│      │ ML (treinamento batch)│
│ Streamlit +  │    │ F6 motor de     │      │ scikit-learn split   │
│ DuckDB embed │    │ decisão Manches │      │ LightGBM + SHAP      │
│ Plotly/Folium│    │ tópicos + audit │      │ (em desenvolvimento) │
└──────────────┘    └─────────────────┘      └──────────────────────┘
```

**Decisões-chave:**

- **DuckDB sobre Parquet** ao invés de Spark — 5-10× mais rápido em máquina única até ~100 GB. Spark fica no `docker-compose.yml` apenas como comparação descartada.
- **PostgreSQL** só pros alertas Kafka — onde ACID e inserts concorrentes importam. Dashboards lêem Parquet direto, sem servidor de banco.
- **Medallion Bronze → Silver → Gold** porque silver é consumido por 4 gold builders + 4 dashboards de grão individual + análises ad-hoc. Lógica de limpeza centralizada uma vez.

---

## Estrutura do projeto

```
datasus/
├── dashboards/
│   ├── main.py                          # Home (storytelling 5 atos)
│   ├── pages/                           # 13 páginas Streamlit
│   │   ├── 1_📊_Continuum_CID.py
│   │   ├── 2_🩺_Painel_Hospital.py
│   │   ├── ...
│   │   └── 13_🚨_Motor_Decisao.py
│   └── utils/
│       ├── __init__.py                  # Helper pergunta_box()
│       └── queries.py                   # DuckDB queries reutilizadas
│
├── pipelines/
│   ├── batch/
│   │   ├── ingestion/                   # pysus → bronze (orchestrator + sources)
│   │   ├── silver/                      # bronze → silver (4 transforms + utils)
│   │   └── gold/                        # silver → gold (5 builders)
│   │       └── ml_mortalidade_dataset.py  # Split sklearn train/val/test
│   └── stream/
│       ├── triagem_consumer.py          # Kafka → Postgres (F6)
│       └── triagem_producer.py          # Simulador de eventos
│
├── data/                                # Tudo gitignored exceto data/ibge/
│   ├── samples/                         # Baixados via scripts/baixar_samples.py
│   ├── ibge/                            # Geo + IDHM + populações (versionados)
│   └── lake/
│       ├── bronze/    {source}/uf=XX/ano=YYYY/mes=MM/part-0.parquet
│       ├── silver/    {table}/ano=YYYY/mes=MM/data_0.parquet
│       └── gold/      {table}/ano=YYYY/part-0.parquet
│
├── scripts/
│   ├── baixar_samples.py                # Download 81 samples pysus
│   ├── seed_bronze_from_samples.py      # samples → bronze partitions
│   ├── download_ibge_geo.py             # GeoJSON municípios RS
│   ├── download_rs_populacao.py         # IBGE SIDRA Censo 2022
│   ├── download_poa_geo.py              # SMAMUS bairros POA
│   ├── download_poa_populacao.py        # ObservaPOA Censo 2022 bairros
│   └── download_idhm.py                 # Atlas Brasil 2010
│
├── docs/
│   ├── dicionario_dados.html            # 6 dicts consolidados (TOC sidebar)
│   ├── joins_guia.md                    # 3 tiers de junção
│   ├── apresentacao_tcc.html            # Slides Reveal.js + Mermaid
│   ├── dataset_ml_v1.md                 # Lineage do dataset ML
│   └── {sih,cnes,sia,sim,sinasc,sinan}_dicionario.md
│
├── infra/
│   ├── streamlit/Dockerfile             # Container do dashboard
│   ├── analysis/Dockerfile              # Jupyter + PySpark
│   ├── cron/                            # Ingestor + supercronic
│   ├── postgres/init.sql                # Schema inicial
│   └── kafka/topics.sh                  # Criação de tópicos
│
├── docker-compose.yml                   # 8 serviços
├── pyproject.toml                       # Extras: ingestion/batch/analysis/dashboard
├── .env.example
├── .dlp-ignore.json                     # Exemptions DLP (coordenadas GeoJSON)
└── README.md                            # Este arquivo
```

---

## Troubleshooting

### "Erro ao conectar ao Streamlit / dashboards estão vazios"

Causa: bronze nunca foi populado, ou silver/gold não rodaram.

```bash
# Verifique se os parquets gold existem:
ls -la data/lake/gold/

# Se vazio, refaça desde o passo 4:
docker compose run --rm -v ./scripts:/app/scripts ingestor \
    python scripts/baixar_samples.py --uf RS
docker compose run --rm -v ./scripts:/app/scripts analysis \
    python scripts/seed_bronze_from_samples.py --uf RS --force
docker compose run --rm streamlit python -m pipelines.batch.silver.orchestrator
docker compose run --rm streamlit python -m pipelines.batch.gold.orchestrator
docker compose restart streamlit
```

### "Container Zookeeper está unhealthy"

O healthcheck usa `nc` que não vem no container Confluent. **Já contornado** no `docker-compose.yml` — Kafka depende de `service_started` ao invés de `service_healthy`. Se ainda assim travar:

```bash
docker compose up -d zookeeper kafka --no-deps
```

### "Port already in use"

Portas usadas: `5432` (Postgres), `8501` (Streamlit), `8888` (Jupyter), `9092` (Kafka), `2181` (Zookeeper), `8080` (Kafka UI), `7077` `8081` (Spark).

Verifique conflitos:

```bash
lsof -i :8501
```

Ou ajuste o port mapping no `docker-compose.yml`:

```yaml
services:
  streamlit:
    ports:
      - "8502:8501"   # mapeia 8502 do host pro 8501 do container
```

### "pysus.SIH.download timeout"

Pode ser instabilidade no FTP do DataSUS. Tente novamente após 10 minutos:

```bash
docker compose run --rm -v ./scripts:/app/scripts ingestor \
    python scripts/baixar_samples.py --uf RS
```

### "Tela em branco no F6 Motor Decisão"

A tabela `alertas_risco` só existe após o primeiro insert do consumer. Veja a seção [Motor de decisão F6](#motor-de-decisão-f6-kafka).

### "DLP block: CreditCardPolicy" ao commitar GeoJSON

Falso positivo — coordenadas geográficas são detectadas como números de cartão. Exemptions já estão em `.dlp-ignore.json` versionado. Se aparecer com novos arquivos GeoJSON, rode:

```bash
nu gitdlp exempt <path-do-geojson> CreditCardPolicy "coordenadas geográficas"
```

---

## Comandos úteis

### Operações diárias

```bash
# Subir todos os serviços
docker compose up -d

# Parar tudo
docker compose down

# Ver logs em tempo real
docker compose logs -f streamlit

# Restart só do Streamlit (após mudar código)
docker compose restart streamlit

# Status dos containers
docker compose ps
```

### Rodar pipelines manualmente

```bash
# Refazer silver
docker compose run --rm streamlit \
    python -m pipelines.batch.silver.orchestrator

# Refazer gold (todas as 5 tabelas)
docker compose run --rm streamlit \
    python -m pipelines.batch.gold.orchestrator

# Só uma tabela gold específica
docker compose run --rm streamlit \
    python -m pipelines.batch.gold.orchestrator --only continuum_cid

# Backfill SIH (após primeiro setup)
docker compose run --rm ingestor backfill
```

### Inspecionar dados

```bash
# Listar parquets do silver
find data/lake/silver -type f

# Inspecionar schema de um parquet
docker compose exec streamlit python -c "
import pyarrow.parquet as pq
print(pq.read_schema('/app/data/lake/silver/sih_rd/ano=2024/mes=6/data_0.parquet'))
"

# Query ad-hoc com DuckDB
docker compose exec streamlit python -c "
import duckdb
df = duckdb.sql('''
    SELECT cid3, COUNT(*) AS n
    FROM read_parquet('/app/data/lake/silver/sih_rd/**/*.parquet', hive_partitioning=true)
    GROUP BY cid3 ORDER BY n DESC LIMIT 10
''').df()
print(df)
"

# Acessar PostgreSQL
docker compose exec postgres psql -U datasus -d datasus_db
```

### Lint e testes (desenvolvimento local)

```bash
pip install -e ".[dev]"
ruff check .
pytest
```

---

## Documentação completa

| Documento | Conteúdo |
|---|---|
| [`docs/dicionario_dados.html`](docs/dicionario_dados.html) | 6 dicionários consolidados (SIH/CNES/SIA/SIM/SINASC/SINAN) com TOC sidebar |
| [`docs/joins_guia.md`](docs/joins_guia.md) | Guia de joins entre fontes (3 tiers: estabelecimento, geografia, pessoa) |
| [`docs/apresentacao_tcc.html`](docs/apresentacao_tcc.html) | Slides Reveal.js da apresentação acadêmica |
| [`docs/dataset_ml_v1.md`](docs/dataset_ml_v1.md) | Lineage e versionamento do dataset ML |
| [`docs/dicionarios_index.md`](docs/dicionarios_index.md) | Índice dos dicionários markdown individuais |
| [`docs/{sih,cnes,sia,sim,sinasc,sinan}_dicionario.md`](docs/) | Dicionários markdown por fonte |

---

## Licença

MIT © DataSUS Contributors. Veja [LICENSE](LICENSE).

## Sobre o projeto

Disciplina **NF01006 — Projeto de Banco de Dados**, Universidade Federal do Rio Grande do Sul (UFRGS), 2026.

Fontes de dados — todas **públicas e abertas**:
[SIH](https://datasus.saude.gov.br/transferencia-de-arquivos/) · [CNES](https://datasus.saude.gov.br/cadastro-de-estabelecimentos-de-saude-cnes/) · [SIM/SINASC/SINAN](https://datasus.saude.gov.br/transferencia-de-arquivos/) · [IBGE Censo 2022](https://www.ibge.gov.br/estatisticas/sociais/populacao/22827-censo-demografico-2022.html) · [Atlas Brasil PNUD](http://www.atlasbrasil.org.br/) · [ObservaPOA](https://prefeitura.poa.br/smpg/observapoa)

Nenhum dado individualmente identificável é armazenado neste repositório.
