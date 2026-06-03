# Dataset ML — Mortalidade Hospitalar (v1)

| Campo | Valor |
|---|---|
| **Versão** | v1 |
| **Gerado em** | 2026-06-03 (UTC) |
| **Caminho** | `data/lake/gold/ml_mortalidade_dataset/v1/` |
| **Fonte** | `data/lake/silver/sih_rd/**/*.parquet` |
| **Target** | `morte` (binário: 0/1) |
| **Tarefa** | Classificação binária — predição de óbito hospitalar |
| **n_total** | 264.728 |

---

## 1. Propósito

Dataset ML-ready destinado a treinar modelos supervisionados que estimam a
**probabilidade de óbito durante a internação** a partir de variáveis
disponíveis **no momento da admissão** (sem leakage de informação pós-desfecho).

### Pergunta de pesquisa

> *Dada uma admissão hospitalar no SUS (RS) com idade, sexo, CID principal,
> município de residência, hospital, caráter e especialidade conhecidos no
> momento da admissão — qual a probabilidade do paciente vir a óbito durante
> a estadia?*

Aplicações pretendidas:
- Triagem de risco assistencial.
- Benchmark de desempenho hospitalar (mortalidade observada × esperada).
- Insumo para análises de equidade (município de residência × hospital).

---

## 2. Esquema completo

Cada split (`train.parquet`, `val.parquet`, `test.parquet`) tem o **mesmo
schema**: 16 features + 1 target.

| Coluna           | Tipo     | Descrição |
|------------------|----------|-----------|
| `sexo`           | INTEGER  | Código DataSUS (1=M, 3=F; outros valores raros) |
| `idade_anos`     | INTEGER  | Idade em anos completos no momento da admissão |
| `faixa_etaria`   | VARCHAR  | Bucket derivado (`<1`, `1-14`, `15-29`, `30-44`, `45-59`, `60-74`, `75+`) |
| `raca_cor`       | VARCHAR  | Código SIH para raça/cor (01=Branca, 02=Preta, 03=Parda, 04=Amarela, 05=Indígena, 99=Sem info) |
| `munic_res`      | VARCHAR  | Município de residência (IBGE 6 dígitos) |
| `meso_res`       | VARCHAR  | Prefixo 4 dígitos de `munic_res` (proxy de mesorregião) |
| `cid_principal`  | VARCHAR  | CID-10 da causa de internação (até 4 chars) |
| `cid3`           | VARCHAR  | Primeiros 3 chars do CID (agrupador) |
| `csap_flag`      | BOOLEAN  | True se internação é por Condição Sensível à Atenção Primária |
| `carater`        | VARCHAR  | Caráter da internação (`01`=eletiva, `02`=urgência, etc.) |
| `especialidade`  | VARCHAR  | Especialidade do leito ocupado (código DataSUS) |
| `complexidade`   | VARCHAR  | Complexidade do atendimento (código DataSUS) |
| `cnes`           | VARCHAR  | CNES do hospital |
| `ano`            | INTEGER  | Ano da competência da AIH |
| `mes`            | INTEGER  | Mês da competência da AIH |
| `dow_admissao`   | INTEGER  | Dia da semana da admissão (0=Domingo, 6=Sábado) |
| **`morte`**      | INTEGER  | **TARGET** — 1 se houve óbito durante a internação, 0 caso contrário |

---

## 3. Features excluídas (vazamento — leakage)

As colunas abaixo **existem em silver** mas **foram removidas explicitamente**
do dataset porque só são conhecidas **após o desfecho** da internação. Usá-las
contamina o modelo com informação do futuro:

| Coluna | Por que é leakage |
|--------|-------------------|
| `dias_perm` | Soma total da permanência — só conhecida na alta. |
| `dt_saida`  | Data de saída (alta ou óbito). |
| `cobranca`  | Motivo de cobrança/encerramento (código de saída/óbito). |
| `val_tot`, `val_sh`, `val_sp`, `val_uti` | Valores faturados — calculados ao final. |
| `uti_dias`, `uso_uti`, `marca_uti` | UTI usada durante a estadia — não disponível na admissão. |
| `proc_rea` | Procedimento realizado — fechado no encerramento da AIH. |

> Variáveis disponíveis pré-admissão (sexo, idade, CID principal, caráter,
> especialidade) **foram mantidas** porque já estão preenchidas no momento
> em que o paciente entra no hospital.

---

## 4. Filtros aplicados

| Filtro | Critério SQL | Justificativa |
|--------|-------------|---------------|
| Target válido | `morte IS NOT NULL` | Sem target não há supervisão. |
| CID presente | `cid_principal IS NOT NULL` | Feature clínica obrigatória. |
| Idade presente | `idade_anos IS NOT NULL` | Feature demográfica obrigatória. |
| Idade plausível | `idade_anos BETWEEN 1 AND 120` | Exclui idades inválidas (>120) e neonatos/lactentes (<1 ano), cujo padrão de mortalidade hospitalar é estruturalmente diferente e merece modelo dedicado. |
| Sem causas externas | `NOT regexp_matches(cid_principal, '^[VWXY]')` | CIDs V-Y (Capítulo XX da CID-10 — acidentes, agressões, autolesão) são causas externas; o desfecho hospitalar reflete trauma e cuidados específicos, não condição clínica intrínseca. Devem ser modelados separadamente. |

---

## 5. Estatísticas descritivas

### 5.1 Tamanho e prevalência do target

| Split | Linhas | Target rate (morte=1) |
|-------|--------|----------------------|
| **_full**  | 264.728 | 5,82% |
| **train**  | 185.309 | 5,819% |
| **val**    | 39.709  | 5,817% |
| **test**   | 39.710  | 5,820% |

> Estratificação preservou a prevalência (variação < 0,01 pp entre splits).

### 5.2 Distribuição por sexo (dataset completo)

| Sexo | Linhas | % |
|------|--------|---|
| 3 (F) | 146.469 | 55,3% |
| 1 (M) | 118.259 | 44,7% |

### 5.3 Distribuição por faixa etária

| Faixa | Linhas | % |
|-------|--------|---|
| 60-74 | 64.905 | 24,5% |
| 45-59 | 49.307 | 18,6% |
| 30-44 | 46.612 | 17,6% |
| 15-29 | 44.082 | 16,7% |
| 75+   | 40.185 | 15,2% |
| 1-14  | 19.637 |  7,4% |

| Estatística | Valor |
|-------------|-------|
| Idade mínima | 1 |
| Idade máxima | 117 |
| Idade média  | 49,4 |
| Idade mediana | 52 |

### 5.4 Distribuição por ano

| Ano | Linhas | Target rate |
|-----|--------|-------------|
| 2022 | 60.767  | 5,95% |
| 2024 | 132.981 | 5,60% |
| 2025 | 70.980  | 6,11% |

> Cobertura temporal: 2022, 2024 e 2025. Ausência de 2023 reflete o estado
> atual do silver lake; backfill posterior pode preencher o gap.

---

## 6. Estratégia de split

- **Algoritmo**: `sklearn.model_selection.train_test_split`, executado **duas vezes**:
  1. 70/30 (train vs. tmp).
  2. tmp dividido 50/50 (val vs. test).
- **Estratificação**: pelo target `morte` em ambas as chamadas.
- **`random_state` = 42** (constante).

### Por que estratificado?

A classe positiva (`morte=1`) é minoritária (~5,8%). Sem estratificação,
splits aleatórios podem ter prevalências divergentes (especialmente em
val/test menores), distorcendo métricas como recall e AUC-PR.

### Por que `random_state` fixo?

Reprodutibilidade: rodar o builder duas vezes na mesma versão do silver
gera **exatamente os mesmos splits** (confirmado pelos hashes MD5 abaixo).

> **Aviso temporal**: o split é aleatório, não temporal. Para avaliação out-of-time
> (treinar em 2022/2024, testar em 2025), os splits aqui **não servem**. Crie
> uma v2 baseada em filtro por `ano` quando essa avaliação for desejada.

---

## 7. Reprodutibilidade

### 7.1 Comando

```bash
docker compose run --rm streamlit \
    python -m pipelines.batch.gold.orchestrator --only ml_mortalidade_dataset
```

Saída em `data/lake/gold/ml_mortalidade_dataset/v1/`:

```
_full.parquet       1,6 MB   (dataset completo após filtros)
train.parquet       1,5 MB   (70%)
val.parquet         354 KB   (15%)
test.parquet        353 KB   (15%)
metadata.json       2 KB
```

### 7.2 Hashes MD5 (gerados 2026-06-03)

| Arquivo | MD5 |
|---------|-----|
| `_full.parquet` | `1072cb8901f831dc8a4d70c338ec9815` |
| `train.parquet` | `4cc93fb59ba4c0f031544a86a248a864` |
| `val.parquet`   | `14af8b93c394d001095946371070404b` |
| `test.parquet`  | `60a957e4eeed71c53d5b01913b089035` |

Hashes também ficam em `metadata.json` (campo `md5`).

### 7.3 Dependências

- `scikit-learn>=1.4.0` (incluído nos extras `[dashboard]` do `pyproject.toml`).
- `duckdb`, `pandas`, `pyarrow` (já presentes).

---

## 8. Limitações conhecidas

1. **Volume baixo** — ~265 mil linhas no silver atual. Modelos com alta
   cardinalidade categórica (ex. `cnes`, `munic_res`, `cid_principal`)
   provavelmente vão precisar de encoding agregador (target encoding,
   embeddings) ou regularização forte.

2. **Sem features históricas** — não há linkage entre AIHs do mesmo paciente
   (campo de identificação anonimizado/não disponível). Variáveis tipo
   "n_internacoes_12m", "uso_uti_previo", "obito_familiar_recente" são
   impossíveis sem prontuário ligado.

3. **Sem features de hospital** — nenhuma característica do CNES é juntada
   (porte, esfera, tipo). Para enriquecer, fazer LEFT JOIN com
   `silver/cnes_st` no momento do treino, ou pré-computar uma versão v2.

4. **Cobertura temporal com gap** — falta 2023. Modelo treinado nesse
   dataset herda esse viés temporal.

5. **Sem comorbidades** — só o CID principal é usado. CIDs secundários
   existem na SIH (`DIAG_SEC*`) mas não estão materializados em silver
   nesta versão.

6. **Sem ajuste de calibração** — o target rate (~5,8%) reflete a
   distribuição empírica. Quem for produzir scores calibrados deve aplicar
   pós-processamento (Platt, isotonic) ou treinar com `class_weight`.

7. **Idade < 1 ano excluída** — recém-nascidos têm padrão de mortalidade
   estruturalmente distinto (causas perinatais) e merecem modelo dedicado.

8. **Causas externas excluídas** — CIDs V/W/X/Y removidos por terem
   determinantes (trauma, intencionalidade) que pedem features específicas
   não presentes aqui.

---

## 9. Próximos passos sugeridos

- v2 com split **out-of-time** (treina 2022/2024, valida/testa 2025).
- v3 com JOIN em `cnes_st` para incluir características do hospital.
- Mover variáveis temporais para `competencia` (DATE) ao invés de `ano/mes` separadamente.
- Acrescentar comorbidades quando o silver expor `DIAG_SEC*`.

---

*Documento gerado como parte da Fase 0.7 do projeto DataSUS-RS.*
